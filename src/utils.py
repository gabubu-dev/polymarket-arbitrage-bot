"""
Utility functions for the Polymarket Trading Bot.

This module provides common helper functions used across the toolkit including
configuration management, caching, data formatting, and retry logic.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable
from pathlib import Path
from functools import wraps


class Config:
    """Configuration manager that loads settings from config.json."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Returns:
            Configuration dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Error loading config: {e}, using defaults")
        
        # Return default config if file doesn't exist
        return {
            "api": {
                "base_url": "https://clob.polymarket.com",
                "gamma_api_url": "https://gamma-api.polymarket.com",
                "rate_limit": 10,
                "timeout": 30,
                "retry_attempts": 3
            },
            "arbitrage": {
                "min_profit_threshold": 0.02,
                "max_position_size": 1000
            },
            "data": {
                "cache_enabled": True,
                "cache_ttl": 300,
                "database_path": "data/markets.db"
            },
            "dashboard": {
                "host": "127.0.0.1",
                "port": 8080,
                "refresh_interval": 30,
                "theme": "plotly_dark"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot notation key.
        
        Args:
            key: Configuration key (e.g., 'api.base_url')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by dot notation key.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)


class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl: Time-to-live in seconds
        """
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['value']
            else:
                del self._cache[key]
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


def format_timestamp(timestamp: int) -> str:
    """
    Format Unix timestamp to readable string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted datetime string
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change as decimal (0.1 = 10%)
    """
    if old_value == 0:
        return 0.0
    
    return (new_value - old_value) / old_value


def ensure_data_directory() -> None:
    """Create data directory if it doesn't exist."""
    Path("data").mkdir(exist_ok=True)


def sanitize_market_slug(slug: str) -> str:
    """
    Sanitize market slug for safe file operations.
    
    Args:
        slug: Market slug
        
    Returns:
        Sanitized slug
    """
    # Remove or replace unsafe characters
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    sanitized = slug
    
    for char in unsafe_chars:
        sanitized = sanitized.replace(char, '-')
    
    return sanitized


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO format datetime string.
    
    Args:
        iso_string: ISO format datetime
        
    Returns:
        Datetime object
    """
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    except ValueError:
        return datetime.now()


def calculate_time_ago(timestamp: int) -> str:
    """
    Calculate human-readable time difference.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Human-readable time difference (e.g., '2 hours ago')
    """
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    return "just now"


def retry_on_failure(func: Callable, max_attempts: int = 3, delay: float = 1.0):
    """
    Retry a function on failure with exponential backoff.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        
    Returns:
        Function result
        
    Raises:
        Last exception if all attempts fail
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                sleep_time = delay * (2 ** attempt)
                time.sleep(sleep_time)
    
    raise last_exception


def rate_limit(calls_per_second: float = 10.0):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls_per_second: Maximum calls per second
    """
    min_interval = 1.0 / calls_per_second
    last_call_time = [0.0]  # Use list for mutable closure
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call_time[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            result = func(*args, **kwargs)
            last_call_time[0] = time.time()
            return result
        
        return wrapper
    
    return decorator


def format_usd(amount: float) -> str:
    """
    Format amount as USD string.
    
    Args:
        amount: Dollar amount
        
    Returns:
        Formatted string (e.g., '$1,234.56')
    """
    if amount >= 1000000:
        return f"${amount/1000000:.2f}M"
    elif amount >= 1000:
        return f"${amount/1000:.2f}K"
    else:
        return f"${amount:.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format value as percentage string.
    
    Args:
        value: Decimal value (e.g., 0.15 for 15%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


class CircularBuffer:
    """Fixed-size circular buffer for storing recent values."""
    
    def __init__(self, size: int = 100):
        """
        Initialize circular buffer.
        
        Args:
            size: Maximum buffer size
        """
        self.size = size
        self._buffer = []
        self._index = 0
    
    def append(self, value: Any) -> None:
        """Add value to buffer."""
        if len(self._buffer) < self.size:
            self._buffer.append(value)
        else:
            self._buffer[self._index] = value
        
        self._index = (self._index + 1) % self.size
    
    def get_all(self) -> list:
        """Get all values in order."""
        if len(self._buffer) < self.size:
            return self._buffer.copy()
        
        # Return in chronological order
        return self._buffer[self._index:] + self._buffer[:self._index]
    
    def clear(self) -> None:
        """Clear buffer."""
        self._buffer.clear()
        self._index = 0
