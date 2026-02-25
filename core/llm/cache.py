#!/usr/bin/env python3
"""
ATOMIC CLAUDE - LLM Response Cache

Response caching with TTL and disk persistence.
"""

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


_HASH_PREFIX = "sha256_"


class LLMCache:
    """
    LRU cache for LLM responses with TTL and disk persistence.

    Features:
    - In-memory LRU cache with size limit
    - Configurable TTL (default 15 minutes)
    - Optional disk persistence
    - Cache key based on prompt + params hash
    - Automatic expiration and pruning
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 900,  # 15 minutes
        cache_dir: Optional[str] = None,
        enable_disk: bool = False
    ):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries in memory
            ttl_seconds: Time-to-live in seconds (default 15 min)
            cache_dir: Directory for disk persistence
            enable_disk: Enable disk persistence
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_disk = enable_disk

        # In-memory cache (LRU)
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Disk cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(os.environ.get("ATOMIC_STATE_DIR", ".state")) / "llm_cache"

        if self.enable_disk:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response.

        Args:
            key: Cache key (or full prompt for auto-hashing)

        Returns:
            Cached response dict or None if not found/expired
        """
        # Hash key if it's not already a prefixed hash
        if not key.startswith(_HASH_PREFIX):
            key = self._hash_key(key)

        # Check memory cache first
        if key in self._cache:
            response, timestamp = self._cache[key]

            # Check TTL
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end (LRU)
                self._cache.move_to_end(key)
                self._hits += 1
                return response
            else:
                # Expired - remove
                del self._cache[key]

        # Check disk cache
        if self.enable_disk:
            disk_response = self._get_from_disk(key)
            if disk_response:
                # Add to memory cache
                self._put(key, disk_response)
                self._hits += 1
                return disk_response

        self._misses += 1
        return None

    def set(
        self,
        key: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache a response.

        Args:
            key: Cache key (or full prompt for auto-hashing)
            response: Response to cache
            ttl: Optional TTL override (seconds)
        """
        # Hash key if needed
        if not key.startswith(_HASH_PREFIX):
            key = self._hash_key(key)

        # Store in memory
        self._put(key, response)

        # Store on disk
        if self.enable_disk:
            self._save_to_disk(key, response, ttl)

    def invalidate(self, key: str) -> bool:
        """
        Remove entry from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed
        """
        # Hash key if needed
        if not key.startswith(_HASH_PREFIX):
            key = self._hash_key(key)

        # Remove from memory
        existed = key in self._cache
        if existed:
            del self._cache[key]

        # Remove from disk
        if self.enable_disk:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_file.unlink()
                existed = True

        return existed

    def clear(self) -> None:
        """Clear all cached entries."""
        # Clear memory
        self._cache.clear()

        # Clear disk
        if self.enable_disk and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()

        # Reset stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def prune(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries pruned
        """
        pruned = 0
        current_time = time.time()

        # Prune memory cache
        keys_to_remove = []
        for key, (response, timestamp) in self._cache.items():
            if current_time - timestamp >= self.ttl_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            pruned += 1

        # Prune disk cache
        if self.enable_disk and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                    timestamp = data.get("timestamp", 0)
                    if current_time - timestamp >= self.ttl_seconds:
                        cache_file.unlink()
                        pruned += 1
                except Exception as e:
                    logger.debug("Failed to prune cache file %s: %s", cache_file, e)

        return pruned

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics dict
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "total_requests": total,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "disk_enabled": self.enable_disk,
        }

    def save_to_disk(self) -> int:
        """
        Save current memory cache to disk.

        Returns:
            Number of entries saved
        """
        if not self.enable_disk:
            return 0

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        saved = 0

        for key, (response, timestamp) in self._cache.items():
            try:
                self._save_to_disk(key, response, timestamp=timestamp)
                saved += 1
            except Exception as e:
                logger.debug("Failed to save cache entry %s to disk: %s", key[:16], e)

        return saved

    def load_from_disk(self) -> int:
        """
        Load cache from disk into memory.

        Returns:
            Number of entries loaded
        """
        if not self.enable_disk or not self.cache_dir.exists():
            return 0

        loaded = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    data = json.load(f)

                timestamp = data.get("timestamp", 0)

                # Skip expired entries
                if current_time - timestamp >= self.ttl_seconds:
                    continue

                key = cache_file.stem
                response = data.get("response")

                if response and key not in self._cache:
                    self._put(key, response, timestamp=timestamp)
                    loaded += 1

            except Exception as e:
                logger.debug("Failed to load cache file %s: %s", cache_file, e)

        return loaded

    @staticmethod
    def make_cache_key(
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        **kwargs
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model name
            max_tokens: Max tokens
            temperature: Temperature
            **kwargs: Additional parameters

        Returns:
            SHA256 hash as cache key
        """
        # Build cache key components
        components = [
            prompt,
            system_prompt or "",
            model or "",
            str(max_tokens),
            str(temperature),
        ]

        # Add sorted kwargs
        for key in sorted(kwargs.keys()):
            components.append(f"{key}={kwargs[key]}")

        # Hash with prefix for reliable detection
        key_str = "|".join(components)
        return _HASH_PREFIX + hashlib.sha256(key_str.encode()).hexdigest()

    def _hash_key(self, key: str) -> str:
        """Hash a key to a prefixed SHA256 string."""
        return _HASH_PREFIX + hashlib.sha256(key.encode()).hexdigest()

    def _put(
        self,
        key: str,
        response: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> None:
        """
        Put entry in memory cache (with LRU eviction).

        Args:
            key: Cache key
            response: Response to cache
            timestamp: Optional timestamp (default: now)
        """
        if timestamp is None:
            timestamp = time.time()

        # Check if key exists
        if key in self._cache:
            # Move to end
            self._cache.move_to_end(key)
            self._cache[key] = (response, timestamp)
        else:
            # Add new entry
            self._cache[key] = (response, timestamp)

            # Check size limit
            if len(self._cache) > self.max_size:
                # Remove oldest (first) entry
                self._cache.popitem(last=False)
                self._evictions += 1

    def _save_to_disk(
        self,
        key: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> None:
        """
        Save entry to disk.

        Args:
            key: Cache key
            response: Response to save
            ttl: Optional TTL override
            timestamp: Optional timestamp
        """
        if not self.enable_disk:
            return

        if timestamp is None:
            timestamp = time.time()

        from core.utils.file_ops import write_json

        cache_file = self.cache_dir / f"{key}.json"

        data = {
            "key": key,
            "response": response,
            "timestamp": timestamp,
            "ttl": ttl or self.ttl_seconds,
        }

        write_json(cache_file, data)

    def _get_from_disk(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get entry from disk.

        Args:
            key: Cache key

        Returns:
            Response or None
        """
        if not self.enable_disk:
            return None

        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            timestamp = data.get("timestamp", 0)
            ttl = data.get("ttl", self.ttl_seconds)

            # Check TTL
            if time.time() - timestamp >= ttl:
                # Expired - remove
                cache_file.unlink()
                return None

            return data.get("response")

        except Exception as e:
            logger.debug("Failed to read cache file %s: %s", cache_file, e)
            return None
