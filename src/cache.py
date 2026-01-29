"""
Caching utilities with TTL support for API responses.

Provides thread-safe and async-safe caching with time-based expiration.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Generic, Optional, TypeVar
from dataclasses import dataclass, field
from collections import OrderedDict
import threading

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A cached value with expiration timestamp."""
    value: T
    expires_at: float
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class TTLCache(Generic[T]):
    """
    Thread-safe cache with time-to-live (TTL) expiration.
    
    Features:
    - Automatic expiration of stale entries
    - LRU eviction when max_size is reached
    - Thread-safe operations
    - Hit/miss statistics
    """
    
    def __init__(
        self,
        default_ttl: float = 60.0,
        max_size: int = 1000,
        cleanup_interval: float = 300.0
    ):
        """
        Initialize TTL cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of entries before LRU eviction
            cleanup_interval: Seconds between automatic cleanup runs
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._last_cleanup = time.time()
    
    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache if present and not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            self._maybe_cleanup()
            
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            
            if time.time() > entry.expires_at:
                # Expired - remove it
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access stats and move to end (LRU)
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(key)
            
            self._hits += 1
            return entry.value
    
    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None
    ) -> None:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        with self._lock:
            self._maybe_cleanup()
            
            # Evict oldest if at capacity and adding new key
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=expires_at
            )
            self._cache.move_to_end(key)
    
    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was found and deleted
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 4),
                'evictions': self._evictions,
                'default_ttl': self.default_ttl
            }
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        now = time.time()
        if now - self._last_cleanup > self.cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now
    
    def _cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry.expires_at
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry (LRU)."""
        if self._cache:
            self._cache.popitem(last=False)
            self._evictions += 1
    
    def keys(self) -> list:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())


class AsyncTTLCache(TTLCache[T]):
    """Async-safe version of TTLCache using asyncio.Lock."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_lock = asyncio.Lock()
    
    async def aget(self, key: str) -> Optional[T]:
        """Async get - delegates to sync get (safe for single-threaded async)."""
        return self.get(key)
    
    async def aset(
        self,
        key: str,
        value: T,
        ttl: Optional[float] = None
    ) -> None:
        """Async set."""
        async with self._async_lock:
            self.set(key, value, ttl)
    
    async def adelete(self, key: str) -> bool:
        """Async delete."""
        async with self._async_lock:
            return self.delete(key)
    
    async def aclear(self) -> None:
        """Async clear."""
        async with self._async_lock:
            self.clear()
    
    async def aget_stats(self) -> Dict[str, Any]:
        """Async get stats."""
        async with self._async_lock:
            return self.get_stats()


def cached(
    ttl: float = 60.0,
    max_size: int = 1000,
    key_func: Optional[Callable] = None
):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl: Time-to-live in seconds
        max_size: Maximum cache size
        key_func: Optional function to generate cache key from arguments
        
    Returns:
        Decorated function
    """
    cache = TTLCache(default_ttl=ttl, max_size=max_size)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        # Attach cache for external access
        wrapper.cache = cache
        return wrapper
    return decorator


def async_cached(
    ttl: float = 60.0,
    max_size: int = 1000,
    key_func: Optional[Callable] = None
):
    """
    Decorator for caching async function results with TTL.
    
    Args:
        ttl: Time-to-live in seconds
        max_size: Maximum cache size
        key_func: Optional function to generate cache key from arguments
        
    Returns:
        Decorated async function
    """
    cache = AsyncTTLCache(default_ttl=ttl, max_size=max_size)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            result = await cache.aget(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.aset(cache_key, result, ttl)
            return result
        
        # Attach cache for external access
        wrapper.cache = cache
        return wrapper
    return decorator


def _generate_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate cache key from function name and arguments."""
    key_parts = [func_name]
    
    # Add positional args
    for arg in args:
        key_parts.append(str(hash(arg)))
    
    # Add keyword args (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={hash(v)}")
    
    return "|".join(key_parts)


# Global caches for common use cases
market_cache = AsyncTTLCache(default_ttl=30.0, max_size=500)  # 30s TTL for market data
price_cache = AsyncTTLCache(default_ttl=5.0, max_size=1000)   # 5s TTL for prices
odds_cache = AsyncTTLCache(default_ttl=3.0, max_size=2000)    # 3s TTL for odds
