"""Intelligent rate limiter that learns from rate limit errors"""

import time
import asyncio
from collections import deque
from datetime import datetime
import sqlite3
import logging

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """Intelligent rate limiter that learns from rate limit errors"""
    
    def __init__(self, db_path='rate_limits.db', provider='polygon-rpc'):
        self.db_path = db_path
        self.provider = provider
        self.call_history = deque(maxlen=100)
        
        # Load optimal rates from DB
        self.load_optimal_rates()
        
        logger.info(
            f"AdaptiveRateLimiter initialized: {self.max_calls_per_second} calls/sec, "
            f"{self.delay_ms}ms delay"
        )
    
    def load_optimal_rates(self):
        """Load optimal rates from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT max_calls_per_second, recommended_delay_ms
                FROM optimal_rates
                WHERE provider = ?
            ''', (self.provider,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                self.max_calls_per_second = result[0]
                self.delay_ms = result[1]
                logger.info(f"Loaded rates from DB: {self.max_calls_per_second} calls/sec")
            else:
                # VERY Conservative defaults (reduced from 3.0 to 1.0)
                self.max_calls_per_second = 1.0
                self.delay_ms = 1000
                logger.warning("No rates in DB, using conservative defaults: 1.0 calls/sec")
        except Exception as e:
            logger.error(f"Error loading rates: {e}, using conservative defaults")
            self.max_calls_per_second = 1.0
            self.delay_ms = 1000
    
    async def acquire(self):
        """Wait before making next call (if needed)"""
        now = time.time()
        
        # Remove old calls (>1 second ago)
        while self.call_history and now - self.call_history[0] > 1.0:
            self.call_history.popleft()
        
        # Check if we're at limit
        if len(self.call_history) >= self.max_calls_per_second:
            # Wait for oldest call to age out
            wait_time = 1.0 - (now - self.call_history[0])
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Add minimum delay between calls
        if self.call_history:
            time_since_last = now - self.call_history[-1]
            min_delay = self.delay_ms / 1000.0
            if time_since_last < min_delay:
                delay_needed = min_delay - time_since_last
                logger.debug(f"Adding delay of {delay_needed*1000:.0f}ms")
                await asyncio.sleep(delay_needed)
        
        # Record this call
        self.call_history.append(time.time())
    
    def record_rate_limit_error(self, retry_seconds):
        """Learn from rate limit errors"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rate_limit_events
                (timestamp, provider, retry_seconds, error_message)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), self.provider, retry_seconds, 'Rate limited'))
            conn.commit()
            conn.close()
            
            # Reduce rate by 20%
            old_rate = self.max_calls_per_second
            self.max_calls_per_second *= 0.8
            self.delay_ms = int(1000 / self.max_calls_per_second)
            
            logger.warning(
                f"Rate limit hit! Reduced rate from {old_rate:.2f} to "
                f"{self.max_calls_per_second:.2f} calls/sec (delay now {self.delay_ms}ms)"
            )
        except Exception as e:
            logger.error(f"Error recording rate limit: {e}")
    
    def get_stats(self):
        """Get current rate limiter statistics"""
        return {
            'provider': self.provider,
            'max_calls_per_second': self.max_calls_per_second,
            'delay_ms': self.delay_ms,
            'recent_calls': len(self.call_history),
            'calls_in_last_second': len(self.call_history)
        }
