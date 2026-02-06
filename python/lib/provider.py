#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Provider Routing Library
Hybrid LLM provider routing for cost-optimized operations

Usage:
    from lib.provider import ProviderManager

    pm = ProviderManager()
    provider = pm.resolve_for_task("critical")

Task Types:
    critical   - PRD authoring, architecture, human gates (→ Anthropic API)
    bulk       - Audit execution, code scanning, analysis (→ Ollama preferred)
    background - File indexing, validation, simple tasks (→ Ollama + smaller model)
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================================
# CONFIGURATION
# ============================================================================

PROVIDER_VERSION = "0.1.0"

# Default timeouts (seconds)
DEFAULT_API_TIMEOUT = 300
DEFAULT_OLLAMA_TIMEOUT = 600

# Health check cache TTL (seconds)
DEFAULT_HEALTH_CACHE_TTL = 60


class TaskType(str, Enum):
    """Task classification for provider routing."""
    CRITICAL = "critical"
    BULK = "bulk"
    BACKGROUND = "background"
    QUICK = "quick"


class Provider(str, Enum):
    """Supported LLM providers."""
    CLAUDE_CODE = "claude-code"
    ANTHROPIC = "anthropic"
    AWS_BEDROCK = "aws-bedrock"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


@dataclass
class OllamaServer:
    """Configuration for an Ollama server."""
    name: str
    host: str
    model: str
    priority: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> 'OllamaServer':
        """Create from JSON dict."""
        return cls(
            name=data.get('name', ''),
            host=data.get('host', ''),
            model=data.get('model', ''),
            priority=data.get('priority', 0)
        )

    def to_dict(self) -> dict:
        """Convert to JSON dict."""
        return {
            'name': self.name,
            'host': self.host,
            'model': self.model,
            'priority': self.priority
        }


@dataclass
class ProviderConfig:
    """Provider configuration loaded from project-config.json."""
    ollama_enabled: bool = False
    ollama_failover: bool = True
    ollama_health_check: bool = True

    critical_provider: str = "primary"
    bulk_provider: str = "primary"
    background_provider: str = "primary"
    background_model: str = "same"

    api_fallback_to_ollama: bool = False
    ollama_fallback_to_api: bool = True
    offline_mode: bool = False

    ollama_servers: List[OllamaServer] = field(default_factory=list)

    # Provider chains for different task types
    chains: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'ProviderConfig':
        """Load from project-config.json structure."""
        providers = data.get('providers', {})
        ollama = providers.get('ollama', {})
        routing = providers.get('routing', {})
        chains = providers.get('chains', {})

        # Parse Ollama servers
        servers = [
            OllamaServer.from_dict(s)
            for s in ollama.get('servers', [])
        ]

        # Parse chains - convert to list format
        parsed_chains = {}
        for task_type, chain_str in chains.items():
            if isinstance(chain_str, str):
                parsed_chains[task_type] = [
                    p.strip()
                    for p in chain_str.replace(',', ' ').split()
                    if p.strip()
                ]
            elif isinstance(chain_str, list):
                parsed_chains[task_type] = chain_str

        return cls(
            ollama_enabled=ollama.get('enabled', False),
            ollama_failover=ollama.get('failover', True),
            ollama_health_check=ollama.get('health_check', True),

            critical_provider=routing.get('critical', 'primary'),
            bulk_provider=routing.get('bulk', 'primary'),
            background_provider=routing.get('background', 'primary'),
            background_model=routing.get('background_model', 'same'),

            api_fallback_to_ollama=providers.get('api_fallback_to_ollama', False),
            ollama_fallback_to_api=providers.get('ollama_fallback_to_api', True),
            offline_mode=providers.get('offline_mode', False),

            ollama_servers=servers,
            chains=parsed_chains
        )


@dataclass
class AvailabilityCache:
    """Cached provider availability status."""
    provider: str
    available: bool
    timestamp: float
    metadata: Dict = field(default_factory=dict)

    def is_expired(self, ttl: int) -> bool:
        """Check if cache entry is expired."""
        return (time.time() - self.timestamp) >= ttl

    @classmethod
    def from_dict(cls, data: dict) -> 'AvailabilityCache':
        """Load from cached JSON."""
        return cls(
            provider=data.get('provider', ''),
            available=data.get('available', False),
            timestamp=data.get('timestamp', 0.0),
            metadata={k: v for k, v in data.items()
                     if k not in ('provider', 'available', 'timestamp')}
        )

    def to_dict(self) -> dict:
        """Convert to JSON dict."""
        result = {
            'provider': self.provider,
            'available': self.available,
            'timestamp': self.timestamp
        }
        result.update(self.metadata)
        return result


# ============================================================================
# PROVIDER MANAGER
# ============================================================================


class ProviderManager:
    """Manages multi-provider routing and availability detection."""

    def __init__(
        self,
        config_file: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        health_cache_ttl: int = DEFAULT_HEALTH_CACHE_TTL
    ):
        """
        Initialize the provider manager.

        Args:
            config_file: Path to project-config.json
            cache_dir: Path to cache directory
            health_cache_ttl: TTL for health check cache in seconds
        """
        # Set up paths
        atomic_output_dir = os.environ.get('ATOMIC_OUTPUT_DIR', '.outputs')
        atomic_state_dir = os.environ.get('ATOMIC_STATE_DIR', '.state')

        self.config_file = config_file or Path(atomic_output_dir) / '0-setup' / 'project-config.json'
        self.cache_dir = cache_dir or Path(atomic_state_dir) / 'provider'
        self.health_cache_ttl = health_cache_ttl

        # Initialize state
        self.config = ProviderConfig()
        self.healthy_servers: List[OllamaServer] = []
        self._initialized = False

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def init(self) -> None:
        """Initialize provider manager (lazy initialization)."""
        if self._initialized:
            return

        if self.config_file.exists():
            self._load_config()

        # Preload healthy servers if health check enabled
        if self.config.ollama_enabled and self.config.ollama_health_check:
            self._refresh_healthy_servers()
        else:
            self.healthy_servers = self.config.ollama_servers.copy()

        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from project-config.json."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            self.config = ProviderConfig.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            # Use default config on error
            print(f"Warning: Failed to load config from {self.config_file}: {e}")
            self.config = ProviderConfig()

    # ========================================================================
    # PROVIDER AVAILABILITY DETECTION
    # ========================================================================

    def check_claude_code(self) -> bool:
        """
        Check if Claude Code (subscription) is available.

        Returns:
            True if claude CLI is available and working
        """
        cache = self._get_availability_cache('claude_code')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = False
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True,
                timeout=5
            )
            available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            available = False

        self._save_availability_cache(AvailabilityCache(
            provider='claude-code',
            available=available,
            timestamp=time.time()
        ))

        return available

    def check_anthropic(self) -> bool:
        """
        Check if Anthropic API is available.

        Returns:
            True if ANTHROPIC_API_KEY is set
        """
        cache = self._get_availability_cache('anthropic')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = bool(os.environ.get('ANTHROPIC_API_KEY'))

        self._save_availability_cache(AvailabilityCache(
            provider='anthropic',
            available=available,
            timestamp=time.time(),
            metadata={'key_present': available}
        ))

        return available

    def check_aws_bedrock(self) -> bool:
        """
        Check if AWS Bedrock is available.

        Returns:
            True if AWS credentials are configured
        """
        cache = self._get_availability_cache('aws_bedrock')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = False
        method = 'none'

        # Check for explicit credentials
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
            available = True
            method = 'env_vars'
        else:
            # Check for AWS CLI configured credentials
            try:
                result = subprocess.run(
                    ['aws', 'sts', 'get-caller-identity'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    available = True
                    method = 'aws_cli'
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        self._save_availability_cache(AvailabilityCache(
            provider='aws-bedrock',
            available=available,
            timestamp=time.time(),
            metadata={'method': method}
        ))

        return available

    def check_openai(self) -> bool:
        """
        Check if OpenAI API is available.

        Returns:
            True if OPENAI_API_KEY is set
        """
        cache = self._get_availability_cache('openai')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = bool(os.environ.get('OPENAI_API_KEY'))

        self._save_availability_cache(AvailabilityCache(
            provider='openai',
            available=available,
            timestamp=time.time(),
            metadata={'key_present': available}
        ))

        return available

    def check_google(self) -> bool:
        """
        Check if Google (Gemini) API is available.

        Returns:
            True if GOOGLE_API_KEY is set
        """
        cache = self._get_availability_cache('google')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = bool(os.environ.get('GOOGLE_API_KEY'))

        self._save_availability_cache(AvailabilityCache(
            provider='google',
            available=available,
            timestamp=time.time(),
            metadata={'key_present': available}
        ))

        return available

    def check_azure(self) -> bool:
        """
        Check if Azure OpenAI is available.

        Returns:
            True if Azure credentials are configured
        """
        cache = self._get_availability_cache('azure')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = bool(
            os.environ.get('AZURE_OPENAI_API_KEY') and
            os.environ.get('AZURE_OPENAI_ENDPOINT')
        )

        self._save_availability_cache(AvailabilityCache(
            provider='azure',
            available=available,
            timestamp=time.time(),
            metadata={'key_present': available}
        ))

        return available

    def check_openrouter(self) -> bool:
        """
        Check if OpenRouter is available.

        Returns:
            True if OPENROUTER_API_KEY is set
        """
        cache = self._get_availability_cache('openrouter')
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        available = bool(os.environ.get('OPENROUTER_API_KEY'))

        self._save_availability_cache(AvailabilityCache(
            provider='openrouter',
            available=available,
            timestamp=time.time(),
            metadata={'key_present': available}
        ))

        return available

    def check_ollama(self) -> bool:
        """
        Check if any Ollama server is available.

        Returns:
            True if at least one healthy server exists
        """
        self.init()
        return len(self.healthy_servers) > 0

    def check_availability(self, provider: str) -> bool:
        """
        Check if a specific provider is available.

        Args:
            provider: Provider name (e.g., "anthropic", "ollama")

        Returns:
            True if provider is available
        """
        provider_lower = provider.lower()

        if provider_lower == Provider.CLAUDE_CODE:
            return self.check_claude_code()
        elif provider_lower == Provider.ANTHROPIC:
            return self.check_anthropic()
        elif provider_lower == Provider.AWS_BEDROCK:
            return self.check_aws_bedrock()
        elif provider_lower == Provider.OPENAI:
            return self.check_openai()
        elif provider_lower == Provider.GOOGLE:
            return self.check_google()
        elif provider_lower == Provider.AZURE:
            return self.check_azure()
        elif provider_lower == Provider.OPENROUTER:
            return self.check_openrouter()
        elif provider_lower == Provider.OLLAMA:
            return self.check_ollama()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_available(self, priority_chain: Optional[List[str]] = None) -> List[str]:
        """
        Get list of all available providers in priority order.

        Args:
            priority_chain: Optional custom priority chain

        Returns:
            List of available provider names
        """
        if priority_chain is None:
            priority_chain = [
                'claude-code', 'anthropic', 'aws-bedrock', 'ollama',
                'openai', 'google', 'azure', 'openrouter'
            ]

        available = []
        for provider in priority_chain:
            if self.check_availability(provider):
                available.append(provider)

        return available

    def show_availability(self) -> None:
        """Print availability status for all providers."""
        print("\nProvider Availability:\n")

        providers = [
            ('claude-code', 'Claude Code (Subscription)'),
            ('anthropic', 'Anthropic API'),
            ('aws-bedrock', 'AWS Bedrock'),
            ('ollama', 'Ollama (Local)'),
            ('openai', 'OpenAI API'),
            ('google', 'Google Gemini'),
            ('azure', 'Azure OpenAI'),
            ('openrouter', 'OpenRouter')
        ]

        for provider_id, name in providers:
            status = "✓" if self.check_availability(provider_id) else "✗"
            print(f"  {status} {name}")

        print()

    # ========================================================================
    # HEALTH CHECKING
    # ========================================================================

    def _refresh_healthy_servers(self) -> None:
        """Refresh list of healthy Ollama servers."""
        self.healthy_servers = []

        for server in self.config.ollama_servers:
            if self._check_ollama_health(server.host):
                self.healthy_servers.append(server)

    def _check_ollama_health(self, host: str) -> bool:
        """
        Check health of an Ollama server.

        Args:
            host: Server host (e.g., "localhost:11434")

        Returns:
            True if server is healthy
        """
        cache = self._get_health_cache(host)
        if cache and not cache.is_expired(self.health_cache_ttl):
            return cache.available

        healthy = False
        try:
            # Try to connect to Ollama API
            import urllib.request
            url = f"http://{host}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as response:
                healthy = response.status == 200
        except Exception:
            healthy = False

        self._save_health_cache(host, AvailabilityCache(
            provider=f'ollama-{host}',
            available=healthy,
            timestamp=time.time(),
            metadata={'host': host}
        ))

        return healthy

    def invalidate_health_cache(self) -> None:
        """Invalidate health cache for all servers."""
        for cache_file in self.cache_dir.glob('health_*.json'):
            cache_file.unlink()
        self._refresh_healthy_servers()

    # ========================================================================
    # PROVIDER CHAIN RESOLUTION
    # ========================================================================

    def resolve_chain(self, chain: List[str], context: str = "") -> Optional[str]:
        """
        Resolve the best available provider from a preference chain.

        Args:
            chain: List of provider names in preference order
            context: Optional context string (for logging)

        Returns:
            Provider name or None if none available
        """
        for provider in chain:
            if not provider:
                continue

            if self.check_availability(provider):
                return provider

        return None

    def get_chain(self, task_type: str) -> List[str]:
        """
        Get provider chain for a task type from project config.

        Args:
            task_type: Task type (critical, bulk, quick, background)

        Returns:
            List of provider names in preference order
        """
        self.init()

        # Normalize task type
        task_type = task_type.lower()
        if task_type == 'background':
            task_type = 'quick'

        # Check for task-specific chain
        chain = self.config.chains.get(task_type, [])

        # Fall back to global chain
        if not chain:
            chain = self.config.chains.get('global', [])

        # Ultimate fallback: default chain
        if not chain:
            chain = ['claude-code', 'anthropic', 'aws-bedrock', 'ollama']

        return chain

    def resolve_for_task(self, task_type: str, context: str = "") -> str:
        """
        Resolve best provider for a task type.

        Args:
            task_type: Task type (critical, bulk, quick, background)
            context: Optional context string

        Returns:
            Provider name (defaults to claude-code if none available)
        """
        chain = self.get_chain(task_type)
        provider = self.resolve_chain(chain, context)

        return provider if provider else 'claude-code'

    # ========================================================================
    # PROVIDER SELECTION
    # ========================================================================

    def get_for_task(self, task_type: str) -> str:
        """
        Get the provider for a task type.

        Args:
            task_type: Task type (critical, bulk, background)

        Returns:
            Provider identifier ("primary" or "ollama")
        """
        self.init()

        task_map = {
            'critical': self.config.critical_provider,
            'bulk': self.config.bulk_provider,
            'background': self.config.background_provider
        }

        provider = task_map.get(task_type, 'primary')

        # Check if Ollama is enabled when provider is ollama
        if provider == 'ollama':
            if not self.config.ollama_enabled:
                provider = 'primary'
            elif not self.healthy_servers:
                # No healthy servers - fallback to primary if allowed
                if self.config.ollama_fallback_to_api:
                    provider = 'primary'

        # Check offline mode
        if self.config.offline_mode:
            provider = 'ollama'

        return provider

    def get_ollama_server(self) -> Optional[OllamaServer]:
        """
        Get the best available Ollama server.

        Returns:
            OllamaServer instance or None if no healthy servers
        """
        self.init()

        # Refresh health if needed
        if self.config.ollama_health_check:
            self._refresh_healthy_servers()

        # Return first healthy server (failover order)
        return self.healthy_servers[0] if self.healthy_servers else None

    def get_model(self, task_type: str) -> Optional[str]:
        """
        Get model for task type (handles background model override).

        Args:
            task_type: Task type

        Returns:
            Model name or None
        """
        self.init()

        if task_type == 'background':
            override = self.config.background_model
            if override != 'same' and override:
                return override

        # Return server's configured model
        server = self.get_ollama_server()
        return server.model if server else None

    # ========================================================================
    # INVOCATION
    # ========================================================================

    def invoke(
        self,
        prompt: str,
        output_file: str,
        task_type: str = 'critical',
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        format: Optional[str] = None,
        ollama_host: Optional[str] = None
    ) -> int:
        """
        Invoke an LLM via the appropriate provider.

        This routes through atomic_invoke with --provider, which uses the
        claude-local wrapper for unified model access (ollama/api/max).

        Args:
            prompt: Prompt file path or string
            output_file: Output file path
            task_type: Task type (critical, bulk, background)
            model: Optional model override
            timeout: Optional timeout override
            format: Optional format (e.g., "json")
            ollama_host: Optional Ollama host override

        Returns:
            Exit code (0 for success)
        """
        self.init()

        # Get provider for this task type
        provider = self.get_for_task(task_type)

        # Map internal provider names to wrapper provider names
        if provider == 'primary':
            wrapper_provider = os.environ.get('CLAUDE_PROVIDER', 'max')
        elif provider == 'ollama':
            wrapper_provider = 'ollama'
            # Get Ollama server host if not specified
            if not ollama_host:
                server = self.get_ollama_server()
                if server:
                    ollama_host = f"http://{server.host}"
                    # Get model from server config if not specified
                    if not model:
                        model = server.model
        else:
            wrapper_provider = provider

        # Handle fallback if no Ollama server available
        if wrapper_provider == 'ollama' and not ollama_host:
            if self.config.ollama_fallback_to_api:
                print("WARN: No healthy Ollama servers, falling back to API")
                wrapper_provider = os.environ.get('CLAUDE_PROVIDER', 'max')
            else:
                print("ERROR: No healthy Ollama servers and fallback disabled")
                return 1

        # Set timeout based on provider if not specified
        if timeout is None:
            timeout = (DEFAULT_OLLAMA_TIMEOUT if wrapper_provider == 'ollama'
                      else DEFAULT_API_TIMEOUT)

        # Build atomic_invoke command
        cmd = ['atomic_invoke', prompt, output_file, f"{task_type} task"]
        cmd.append(f'--provider={wrapper_provider}')

        if model:
            cmd.append(f'--model={model}')
        if format:
            cmd.append(f'--format={format}')
        if timeout:
            cmd.append(f'--timeout={timeout}')
        if ollama_host:
            cmd.append(f'--ollama-host={ollama_host}')

        # Execute atomic_invoke
        try:
            result = subprocess.run(cmd)
            return result.returncode
        except FileNotFoundError:
            print(f"ERROR: atomic_invoke command not found")
            return 1

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def status(self) -> None:
        """Print provider status information."""
        self.init()

        print("Provider Configuration:")
        print(f"  Ollama enabled:     {self.config.ollama_enabled}")
        print(f"  Offline mode:       {self.config.offline_mode}")
        print()
        print("Task Routing:")
        print(f"  Critical tasks:     {self.config.critical_provider}")
        print(f"  Bulk tasks:         {self.config.bulk_provider}")
        print(f"  Background tasks:   {self.config.background_provider}")
        print(f"  Background model:   {self.config.background_model}")
        print()

        if self.config.ollama_enabled:
            print("Ollama Servers:")
            for server in self.config.ollama_servers:
                status = "● healthy" if server in self.healthy_servers else "○ unreachable"
                print(f"  {status}  {server.name} ({server.host}) - {server.model}")

    def list_models(self, server: Optional[str] = None) -> List[str]:
        """
        List available models on a server.

        Args:
            server: Optional server host (uses default if not specified)

        Returns:
            List of model names
        """
        if not server:
            ollama_server = self.get_ollama_server()
            if not ollama_server:
                print("No Ollama server available")
                return []
            server = ollama_server.host

        try:
            import urllib.request
            url = f"http://{server}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def invalidate_availability_cache(self) -> None:
        """Invalidate all provider availability cache."""
        for cache_file in self.cache_dir.glob('availability_*.json'):
            cache_file.unlink()

    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================

    def _get_availability_cache(self, provider: str) -> Optional[AvailabilityCache]:
        """Get cached availability status."""
        cache_file = self.cache_dir / f'availability_{provider}.json'

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return AvailabilityCache.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _save_availability_cache(self, cache: AvailabilityCache) -> None:
        """Save availability cache."""
        provider_slug = cache.provider.replace('-', '_')
        cache_file = self.cache_dir / f'availability_{provider_slug}.json'

        with open(cache_file, 'w') as f:
            json.dump(cache.to_dict(), f, indent=2)

    def _get_health_cache(self, host: str) -> Optional[AvailabilityCache]:
        """Get cached health status."""
        host_slug = host.replace(':', '_').replace('/', '_')
        cache_file = self.cache_dir / f'health_{host_slug}.json'

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return AvailabilityCache.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _save_health_cache(self, host: str, cache: AvailabilityCache) -> None:
        """Save health cache."""
        host_slug = host.replace(':', '_').replace('/', '_')
        cache_file = self.cache_dir / f'health_{host_slug}.json'

        with open(cache_file, 'w') as f:
            json.dump(cache.to_dict(), f, indent=2)


# ============================================================================
# CONVENIENCE FUNCTIONS (for bash compatibility)
# ============================================================================

_global_manager: Optional[ProviderManager] = None


def get_manager() -> ProviderManager:
    """Get or create global provider manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ProviderManager()
    return _global_manager


def provider_init() -> None:
    """Initialize global provider manager."""
    get_manager().init()


def provider_check_availability(provider: str) -> bool:
    """Check if a provider is available."""
    return get_manager().check_availability(provider)


def provider_get_available(priority_chain: Optional[List[str]] = None) -> List[str]:
    """Get list of available providers."""
    return get_manager().get_available(priority_chain)


def provider_resolve_for_task(task_type: str, context: str = "") -> str:
    """Resolve best provider for a task type."""
    return get_manager().resolve_for_task(task_type, context)


def provider_status() -> None:
    """Print provider status."""
    get_manager().status()


def provider_show_availability() -> None:
    """Show availability for all providers."""
    get_manager().show_availability()


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """Command-line interface for provider management."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: provider.py <command> [args...]")
        print("\nCommands:")
        print("  status              - Show provider configuration and status")
        print("  availability        - Show availability for all providers")
        print("  check <provider>    - Check if provider is available")
        print("  list-models [host]  - List available models")
        print("  invalidate-cache    - Invalidate all caches")
        sys.exit(1)

    command = sys.argv[1]
    manager = get_manager()

    if command == 'status':
        manager.status()

    elif command == 'availability':
        manager.show_availability()

    elif command == 'check':
        if len(sys.argv) < 3:
            print("Usage: provider.py check <provider>")
            sys.exit(1)
        provider = sys.argv[2]
        available = manager.check_availability(provider)
        print(f"{provider}: {'available' if available else 'unavailable'}")
        sys.exit(0 if available else 1)

    elif command == 'list-models':
        host = sys.argv[2] if len(sys.argv) > 2 else None
        models = manager.list_models(host)
        for model in models:
            print(model)

    elif command == 'invalidate-cache':
        manager.invalidate_availability_cache()
        manager.invalidate_health_cache()
        print("Cache invalidated")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
