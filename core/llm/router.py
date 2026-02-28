#!/usr/bin/env python3
"""
ATOMIC CLAUDE - LLM Router

Intelligent provider routing with fallback chains and health tracking.
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Generator

from .base import BaseLLMProvider, LLMResponse, TokenUsage
from .cache import LLMCache
from .exceptions import (
    LLMException,
    ProviderUnavailableException,
    RateLimitException,
    TimeoutException,
)
from .types import ModelRole, UsageStats, ProviderHealth, HealthStatus


logger = logging.getLogger(__name__)


@dataclass
class ProviderFailure:
    """Track provider failure for circuit breaker."""
    provider_name: str
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    disabled_until: Optional[datetime] = None


@dataclass
class RouterConfig:
    """Router configuration."""
    # Fallback chains by role
    fallback_chains: Dict[str, List[str]] = field(default_factory=dict)

    # Circuit breaker settings
    failure_threshold: int = 3  # Disable after N consecutive failures
    cooldown_minutes: int = 5  # Re-enable after N minutes

    # Health check settings
    health_check_interval: int = 60  # Seconds between health checks

    # Cache settings
    enable_cache: bool = True
    cache_ttl: int = 900  # 15 minutes
    cache_max_size: int = 100

    # Load balancing
    enable_load_balancing: bool = False
    load_balance_strategy: str = "round_robin"  # round_robin, random


class LLMRouter:
    """
    Intelligent LLM provider router.

    Features:
    - Role-based routing (primary, fast, gardener, heavyweight)
    - Automatic fallback chains
    - Provider health checking
    - Circuit breaker pattern
    - Response caching
    - Usage tracking
    - Load balancing (optional)
    """

    def __init__(self, config: Optional[RouterConfig] = None):
        """
        Initialize router.

        Args:
            config: Router configuration
        """
        self.config = config or RouterConfig()

        # Registered providers by name
        self._providers: Dict[str, BaseLLMProvider] = {}

        # Provider roles mapping
        self._roles: Dict[ModelRole, List[str]] = {
            ModelRole.PRIMARY: [],
            ModelRole.FAST: [],
            ModelRole.GARDENER: [],
            ModelRole.HEAVYWEIGHT: [],
        }

        # Fallback chains cache
        self._fallback_chains: Dict[str, List[str]] = {}

        # Provider health tracking
        self._provider_health: Dict[str, ProviderHealth] = {}
        self._last_health_check: Dict[str, datetime] = {}

        # Circuit breaker tracking
        self._failures: Dict[str, ProviderFailure] = {}

        # Usage statistics
        self._usage_stats: Dict[str, UsageStats] = defaultdict(
            lambda: UsageStats()
        )

        # Response cache
        if self.config.enable_cache:
            self._cache = LLMCache(
                max_size=self.config.cache_max_size,
                ttl_seconds=self.config.cache_ttl,
            )
        else:
            self._cache = None

        # Thread safety for stats updates
        self._stats_lock = threading.Lock()

        # Load balancing state
        self._round_robin_index: Dict[str, int] = defaultdict(int)

    def register_provider(
        self,
        name: str,
        provider: BaseLLMProvider,
        roles: Optional[List[ModelRole]] = None
    ) -> None:
        """
        Register a provider.

        Args:
            name: Provider name (unique identifier)
            provider: Provider instance
            roles: Roles this provider can fulfill
        """
        self._providers[name] = provider

        # Register roles
        if roles:
            for role in roles:
                if name not in self._roles[role]:
                    self._roles[role].append(name)

        # Initialize health status
        self._provider_health[name] = ProviderHealth(
            provider=name,
            status=HealthStatus.UNKNOWN,
            available=False,
            last_check=datetime.now(timezone.utc),
        )

        logger.info(f"Registered provider: {name} with roles: {roles}")

    def unregister_provider(self, name: str) -> bool:
        """
        Unregister a provider.

        Args:
            name: Provider name

        Returns:
            True if provider existed
        """
        if name not in self._providers:
            return False

        # Remove from providers
        del self._providers[name]

        # Remove from roles
        for role_providers in self._roles.values():
            if name in role_providers:
                role_providers.remove(name)

        # Remove from health tracking
        if name in self._provider_health:
            del self._provider_health[name]

        logger.info(f"Unregistered provider: {name}")
        return True

    def get_provider(self, role: str = "primary") -> Optional[BaseLLMProvider]:
        """
        Get provider for a role.

        Args:
            role: Role name (primary, fast, gardener, heavyweight)

        Returns:
            Provider instance or None
        """
        # Resolve fallback chain
        chain = self.get_fallback_chain(role)

        # Find first available provider
        for provider_name in chain:
            if self._is_provider_available(provider_name):
                return self._providers.get(provider_name)

        return None

    def invoke(
        self,
        role: str = "primary",
        prompt: str = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        timeout: int = 300,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Route and invoke LLM request.

        Args:
            role: Role to use (primary, fast, gardener, heavyweight)
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature
            timeout: Timeout in seconds
            use_cache: Use cache if available
            **kwargs: Additional parameters

        Returns:
            LLMResponse

        Raises:
            ProviderUnavailableException: No providers available
            Other LLM exceptions from provider
        """
        # Check cache first
        if use_cache and self._cache:
            cache_key = LLMCache.make_cache_key(
                prompt, system_prompt, model, max_tokens, temperature, **kwargs
            )
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                logger.info("Returning cached LLM response (tokens not re-tracked)")
                if isinstance(cached.get("usage"), dict):
                    cached["usage"] = TokenUsage(**cached["usage"])
                return LLMResponse(**cached)

        # Get fallback chain
        chain = self.get_fallback_chain(role)

        if not chain:
            raise ProviderUnavailableException(
                f"No providers available for role: {role}"
            )

        # Try each provider in chain
        last_exception = None
        for provider_name in chain:
            # Skip unavailable providers
            if not self._is_provider_available(provider_name):
                continue

            provider = self._providers[provider_name]

            try:
                # Invoke provider
                start_time = time.time()
                response = provider.invoke(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                    **kwargs
                )

                # Update success metrics
                self._record_success(provider_name, time.time() - start_time, response)

                # Cache response
                if use_cache and self._cache:
                    self._cache.set(cache_key, response.to_dict())

                return response

            except (RateLimitException, TimeoutException) as e:
                # Retryable errors - try next provider
                last_exception = e
                self._record_failure(provider_name, retryable=True)
                logger.warning(
                    f"Provider {provider_name} failed (retryable): {str(e)}"
                )
                continue

            except LLMException as e:
                # Non-retryable errors - try next provider
                last_exception = e
                self._record_failure(provider_name, retryable=False)
                logger.error(
                    f"Provider {provider_name} failed: {str(e)}"
                )
                continue

            except Exception as e:
                # Unexpected errors
                last_exception = e
                self._record_failure(provider_name, retryable=False)
                logger.exception(
                    f"Provider {provider_name} unexpected error: {str(e)}"
                )
                continue

        # All providers failed
        raise ProviderUnavailableException(
            f"All providers failed for role {role}. Last error: {str(last_exception)}"
        )

    def stream(
        self,
        role: str = "primary",
        prompt: str = None,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Route and stream LLM response.

        Args:
            role: Role to use
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature
            **kwargs: Additional parameters

        Yields:
            Text chunks

        Raises:
            ProviderUnavailableException: No providers available
        """
        # Get fallback chain
        chain = self.get_fallback_chain(role)

        if not chain:
            raise ProviderUnavailableException(
                f"No providers available for role: {role}"
            )

        # Try each provider
        for provider_name in chain:
            if not self._is_provider_available(provider_name):
                continue

            provider = self._providers[provider_name]

            try:
                # Stream from provider
                for chunk in provider.stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                ):
                    yield chunk

                # Success
                self._record_success(provider_name, 0, None)
                return

            except Exception as e:
                logger.error(f"Provider {provider_name} streaming failed: {str(e)}")
                self._record_failure(provider_name, retryable=True)
                continue

        # All providers failed
        raise ProviderUnavailableException(
            f"All providers failed for streaming role {role}"
        )

    def get_fallback_chain(self, role: str) -> List[str]:
        """
        Get fallback chain for a role.

        Args:
            role: Role name

        Returns:
            List of provider names in fallback order
        """
        # Check cache
        if role in self._fallback_chains:
            return self._fallback_chains[role]

        # Check config
        if role in self.config.fallback_chains:
            chain = self.config.fallback_chains[role]
            self._fallback_chains[role] = chain
            return chain

        # Build default chain from role mapping
        try:
            role_enum = ModelRole(role.lower())
            chain = self._roles.get(role_enum, [])
        except ValueError:
            logger.debug("Unknown model role '%s', falling back to all providers", role)
            chain = []

        # Fallback to all providers if no role-specific chain
        if not chain:
            chain = list(self._providers.keys())

        self._fallback_chains[role] = chain
        return chain

    def check_health(self) -> Dict[str, ProviderHealth]:
        """
        Check health of all providers.

        Returns:
            Dict of provider name to health status
        """
        for provider_name, provider in self._providers.items():
            self._check_provider_health(provider_name)

        return dict(self._provider_health)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Statistics dict
        """
        stats = {
            "providers": {},
            "cache": None,
            "failures": {},
        }

        # Provider stats
        for provider_name, usage in self._usage_stats.items():
            stats["providers"][provider_name] = {
                "total_requests": usage.total_requests,
                "failed_requests": usage.failed_requests,
                "success_rate": usage.success_rate,
                "total_tokens": usage.total_tokens,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "avg_latency_ms": usage.avg_latency_ms,
            }

        # Cache stats
        if self._cache:
            stats["cache"] = self._cache.get_stats()

        # Failure stats
        for provider_name, failure in self._failures.items():
            stats["failures"][provider_name] = {
                "failure_count": failure.failure_count,
                "last_failure": failure.last_failure.isoformat() if failure.last_failure else None,
                "disabled_until": failure.disabled_until.isoformat() if failure.disabled_until else None,
            }

        return stats

    def _is_provider_available(self, provider_name: str) -> bool:
        """
        Check if provider is available (not circuit broken).

        Args:
            provider_name: Provider name

        Returns:
            True if available
        """
        # Check if provider exists
        if provider_name not in self._providers:
            return False

        # Check circuit breaker
        failure = self._failures.get(provider_name)
        if failure and failure.disabled_until:
            # Check if cooldown expired
            if datetime.now(timezone.utc) < failure.disabled_until:
                return False
            else:
                # Re-enable provider
                failure.disabled_until = None
                failure.failure_count = 0
                logger.info(f"Re-enabled provider: {provider_name}")

        return True

    def _check_provider_health(self, provider_name: str) -> HealthStatus:
        """
        Check provider health.

        Args:
            provider_name: Provider name

        Returns:
            Health status
        """
        # Check if health check needed
        last_check = self._last_health_check.get(provider_name)
        if last_check:
            elapsed = (datetime.now(timezone.utc) - last_check).total_seconds()
            if elapsed < self.config.health_check_interval:
                # Use cached status
                return self._provider_health[provider_name].status

        # Perform health check
        provider = self._providers[provider_name]
        try:
            status = provider.health_check()

            self._provider_health[provider_name] = ProviderHealth(
                provider=provider_name,
                status=status,
                available=(status == HealthStatus.HEALTHY),
                last_check=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Health check failed for {provider_name}: {str(e)}")
            self._provider_health[provider_name] = ProviderHealth(
                provider=provider_name,
                status=HealthStatus.UNAVAILABLE,
                available=False,
                last_check=datetime.now(timezone.utc),
                error_message=str(e),
            )

        self._last_health_check[provider_name] = datetime.now(timezone.utc)
        return self._provider_health[provider_name].status

    def _record_success(
        self,
        provider_name: str,
        latency: float,
        response: Optional[LLMResponse]
    ) -> None:
        """
        Record successful invocation.

        Args:
            provider_name: Provider name
            latency: Latency in seconds
            response: Response object
        """
        with self._stats_lock:
            stats = self._usage_stats[provider_name]
            stats.total_requests += 1

            # Update latency
            if latency > 0:
                total_latency = stats.avg_latency_ms * (stats.total_requests - 1)
                stats.avg_latency_ms = (total_latency + latency * 1000) / stats.total_requests

            # Update token usage
            if response:
                usage = response.usage
                stats.input_tokens += getattr(usage, 'input_tokens', 0) or 0
                stats.output_tokens += getattr(usage, 'output_tokens', 0) or 0
                stats.cache_read_tokens += getattr(usage, 'cache_read_tokens', 0) or 0
                stats.cache_write_tokens += getattr(usage, 'cache_write_tokens', 0) or 0

            # Reset failure count on success
            if provider_name in self._failures:
                self._failures[provider_name].failure_count = 0

    def _record_failure(self, provider_name: str, retryable: bool = False) -> None:
        """
        Record failed invocation.

        Args:
            provider_name: Provider name
            retryable: Whether failure is retryable
        """
        with self._stats_lock:
            stats = self._usage_stats[provider_name]
            stats.total_requests += 1
            stats.failed_requests += 1

        # Update circuit breaker
        if provider_name not in self._failures:
            self._failures[provider_name] = ProviderFailure(provider_name=provider_name)

        failure = self._failures[provider_name]
        failure.failure_count += 1
        failure.last_failure = datetime.now(timezone.utc)

        # Check if we should disable provider (circuit breaker)
        if failure.failure_count >= self.config.failure_threshold:
            failure.disabled_until = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.cooldown_minutes
            )
            logger.warning(
                f"Circuit breaker: Disabled provider {provider_name} "
                f"until {failure.disabled_until}"
            )

    def invalidate_cache(self) -> None:
        """Clear response cache."""
        if self._cache:
            self._cache.clear()
            logger.info("Cache cleared")

    def reset_failures(self, provider_name: Optional[str] = None) -> None:
        """
        Reset failure tracking.

        Args:
            provider_name: Specific provider or None for all
        """
        if provider_name:
            if provider_name in self._failures:
                del self._failures[provider_name]
        else:
            self._failures.clear()

        logger.info(f"Reset failures for: {provider_name or 'all providers'}")
