"""
Continuous API polling with intelligent rate limiting and backoff.

Implements non-rate-limited, efficient data feeds for 24/7 operation.
Uses adaptive rate limiting, request batching, and circuit breaker patterns.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import aiohttp
from enum import Enum


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED = "fixed"           # Fixed interval between requests
    ADAPTIVE = "adaptive"     # Adjust based on response times
    EXPONENTIAL = "exp"       # Exponential backoff on errors


@dataclass
class APIEndpoint:
    """Represents an API endpoint configuration."""
    name: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    weight: int = 1           # Request weight for rate limiting
    priority: int = 5         # 1-10, lower = higher priority
    cache_ttl_ms: int = 1000  # Cache time-to-live


@dataclass
class RequestMetrics:
    """Metrics for API requests."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    avg_response_time_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    consecutive_errors: int = 0


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    
    Opens after threshold errors, closes after cooldown.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout_seconds: int = 60,
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.half_open_max_calls = half_open_max_calls
        
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def can_execute(self) -> bool:
        """Check if request can be executed."""
        async with self._lock:
            if self.state == "closed":
                return True
            
            if self.state == "open":
                if self.last_failure_time and \
                   datetime.now() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                    self.half_open_calls = 0
                    return True
                return False
            
            if self.state == "half-open":
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
            
            return True
    
    async def record_success(self):
        """Record successful request."""
        async with self._lock:
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
                self.half_open_calls = 0
    
    async def record_failure(self):
        """Record failed request."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = datetime.now()
            
            if self.state == "half-open":
                self.state = "open"
            elif self.failures >= self.failure_threshold:
                self.state = "open"


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on API response patterns.
    
    Automatically slows down when approaching limits,
    speeds up when there's headroom.
    """
    
    def __init__(self,
                 max_requests_per_second: float = 10.0,
                 strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE,
                 min_interval_ms: float = 50.0,
                 max_interval_ms: float = 5000.0):
        self.max_rps = max_requests_per_second
        self.strategy = strategy
        self.min_interval = min_interval_ms / 1000.0
        self.max_interval = max_interval_ms / 1000.0
        
        self.current_interval = 1.0 / max_requests_per_second
        self.request_times: deque = deque(maxlen=100)
        self.metrics = RequestMetrics()
        self._semaphore = asyncio.Semaphore(int(max_requests_per_second))
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self, weight: int = 1) -> bool:
        """Acquire permission to make a request."""
        async with self._lock:
            now = time.time()
            
            # Enforce minimum interval
            elapsed = now - self._last_request_time
            if elapsed < self.current_interval * weight:
                wait_time = self.current_interval * weight - elapsed
                await asyncio.sleep(wait_time)
            
            self._last_request_time = time.time()
            return True
    
    def record_response(self, 
                       response_time_ms: float,
                       success: bool,
                       rate_limited: bool = False):
        """Record response metrics for adaptive adjustment."""
        self.request_times.append({
            'time': datetime.now(),
            'response_time_ms': response_time_ms,
            'success': success,
            'rate_limited': rate_limited
        })
        
        self.metrics.total_requests += 1
        
        if success:
            self.metrics.successful_requests += 1
            self.metrics.consecutive_errors = 0
        else:
            self.metrics.failed_requests += 1
            self.metrics.consecutive_errors += 1
        
        if rate_limited:
            self.metrics.rate_limit_hits += 1
        
        # Update average response time
        if self.request_times:
            self.metrics.avg_response_time_ms = sum(
                r['response_time_ms'] for r in self.request_times
            ) / len(self.request_times)
        
        # Adjust rate if using adaptive strategy
        if self.strategy == RateLimitStrategy.ADAPTIVE:
            self._adjust_rate()
    
    def _adjust_rate(self):
        """Adjust request rate based on recent performance."""
        recent = list(self.request_times)[-20:]
        
        if not recent:
            return
        
        # Count issues in recent requests
        rate_limits = sum(1 for r in recent if r['rate_limited'])
        errors = sum(1 for r in recent if not r['success'])
        avg_response = sum(r['response_time_ms'] for r in recent) / len(recent)
        
        # Adjust interval based on conditions
        if rate_limits > 2 or errors > 3:
            # Slow down
            self.current_interval = min(
                self.current_interval * 1.5,
                self.max_interval
            )
        elif avg_response < 200 and rate_limits == 0 and errors == 0:
            # Speed up slightly
            self.current_interval = max(
                self.current_interval * 0.95,
                self.min_interval
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current rate limiter metrics."""
        return {
            'current_interval_ms': self.current_interval * 1000,
            'max_rps': self.max_rps,
            'strategy': self.strategy.value,
            'total_requests': self.metrics.total_requests,
            'success_rate': (
                self.metrics.successful_requests / self.metrics.total_requests
                if self.metrics.total_requests > 0 else 1.0
            ),
            'rate_limit_hits': self.metrics.rate_limit_hits,
            'avg_response_time_ms': self.metrics.avg_response_time_ms
        }


class ContinuousAPIPoller:
    """
    Continuous API polling system for 24/7 data feeds.
    
    Features:
    - Intelligent rate limiting
    - Request batching
    - Circuit breaker protection
    - Response caching
    - Priority queuing
    """
    
    def __init__(self,
                 max_requests_per_second: float = 10.0,
                 strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE,
                 enable_caching: bool = True):
        self.logger = logging.getLogger("ContinuousAPIPoller")
        self.rate_limiter = AdaptiveRateLimiter(max_requests_per_second, strategy)
        self.circuit_breaker = CircuitBreaker()
        self.enable_caching = enable_caching
        
        self._endpoints: Dict[str, APIEndpoint] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._cache: Dict[str, tuple] = {}  # key -> (data, timestamp)
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    
    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        """Register an endpoint for polling."""
        self._endpoints[endpoint.name] = endpoint
        self._callbacks[endpoint.name] = []
        self.logger.debug(f"Registered endpoint: {endpoint.name}")
    
    def add_callback(self, endpoint_name: str, 
                    callback: Callable[[Dict], None]) -> None:
        """Add callback for endpoint data updates."""
        if endpoint_name in self._callbacks:
            self._callbacks[endpoint_name].append(callback)
    
    async def start(self) -> None:
        """Start the polling system."""
        self._running = True
        self.logger.info(f"Starting API poller with {len(self._endpoints)} endpoints")
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Start polling tasks for each endpoint
        for endpoint in self._endpoints.values():
            task = asyncio.create_task(self._poll_loop(endpoint))
            self._tasks.append(task)
        
        # Start metrics reporting task
        if self.rate_limiter.strategy == RateLimitStrategy.ADAPTIVE:
            self._tasks.append(asyncio.create_task(self._metrics_loop()))
    
    async def stop(self) -> None:
        """Stop the polling system."""
        self._running = False
        self.logger.info("Stopping API poller")
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close session
        if self._session:
            await self._session.close()
    
    async def _poll_loop(self, endpoint: APIEndpoint) -> None:
        """Main polling loop for an endpoint."""
        while self._running:
            try:
                # Check circuit breaker
                if not await self.circuit_breaker.can_execute():
                    self.logger.warning(f"Circuit open for {endpoint.name}, waiting...")
                    await asyncio.sleep(10)
                    continue
                
                # Acquire rate limit
                await self.rate_limiter.acquire(endpoint.weight)
                
                # Check cache
                cache_key = f"{endpoint.name}:{hash(str(endpoint.params))}"
                if self.enable_caching and cache_key in self._cache:
                    data, timestamp = self._cache[cache_key]
                    age_ms = (datetime.now() - timestamp).total_seconds() * 1000
                    if age_ms < endpoint.cache_ttl_ms:
                        # Use cached data
                        await self._notify_callbacks(endpoint.name, data)
                        await asyncio.sleep(self.rate_limiter.current_interval)
                        continue
                
                # Make request
                start_time = time.time()
                data = await self._make_request(endpoint)
                response_time_ms = (time.time() - start_time) * 1000
                
                # Record metrics
                success = data is not None
                self.rate_limiter.record_response(response_time_ms, success)
                
                if success:
                    await self.circuit_breaker.record_success()
                    
                    # Update cache
                    if self.enable_caching:
                        self._cache[cache_key] = (data, datetime.now())
                    
                    # Notify callbacks
                    await self._notify_callbacks(endpoint.name, data)
                else:
                    await self.circuit_breaker.record_failure()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in poll loop for {endpoint.name}: {e}")
                await self.circuit_breaker.record_failure()
                await asyncio.sleep(5)
    
    async def _make_request(self, endpoint: APIEndpoint) -> Optional[Dict]:
        """Make HTTP request to endpoint."""
        if not self._session:
            return None
        
        try:
            method = getattr(self._session, endpoint.method.lower())
            
            async with method(
                endpoint.url,
                headers=endpoint.headers,
                params=endpoint.params if endpoint.method == "GET" else None,
                json=endpoint.params if endpoint.method == "POST" else None
            ) as response:
                if response.status == 429:  # Rate limited
                    self.rate_limiter.record_response(0, False, True)
                    retry_after = int(response.headers.get('Retry-After', 5))
                    await asyncio.sleep(retry_after)
                    return None
                
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            self.logger.error(f"Request failed for {endpoint.name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error for {endpoint.name}: {e}")
            return None
    
    async def _notify_callbacks(self, endpoint_name: str, data: Dict) -> None:
        """Notify all registered callbacks."""
        callbacks = self._callbacks.get(endpoint_name, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Callback error: {e}")
    
    async def _metrics_loop(self) -> None:
        """Periodically log rate limiter metrics."""
        while self._running:
            await asyncio.sleep(60)
            metrics = self.rate_limiter.get_metrics()
            self.logger.info(f"Rate limiter metrics: {metrics}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive polling metrics."""
        return {
            'rate_limiter': self.rate_limiter.get_metrics(),
            'circuit_breaker_state': self.circuit_breaker.state,
            'endpoints': len(self._endpoints),
            'running': self._running
        }


class BatchedAPIPoller(ContinuousAPIPoller):
    """
    Extended poller with request batching support.
    
    Combines multiple requests into batches for efficiency.
    """
    
    def __init__(self, batch_size: int = 10, batch_interval_ms: int = 50, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.batch_interval = batch_interval_ms / 1000.0
        self._batch_queue: asyncio.Queue = asyncio.Queue()
        self._batch_callbacks: Dict[str, Callable] = {}
    
    async def start(self) -> None:
        """Start poller with batch processing."""
        await super().start()
        self._tasks.append(asyncio.create_task(self._batch_processor()))
    
    async def add_batch_request(self, 
                               endpoint_name: str,
                               params_list: List[Dict],
                               callback: Callable[[List[Dict]], None]) -> None:
        """Add a batch of requests to the queue."""
        await self._batch_queue.put({
            'endpoint': endpoint_name,
            'params': params_list,
            'callback': callback
        })
    
    async def _batch_processor(self) -> None:
        """Process batched requests."""
        while self._running:
            try:
                batch = []
                deadline = time.time() + self.batch_interval
                
                # Collect requests until batch is full or interval expires
                while len(batch) < self.batch_size and time.time() < deadline:
                    try:
                        item = await asyncio.wait_for(
                            self._batch_queue.get(),
                            timeout=0.01
                        )
                        batch.append(item)
                    except asyncio.TimeoutError:
                        continue
                
                if batch:
                    await self._execute_batch(batch)
                
                await asyncio.sleep(0.001)  # Prevent busy-waiting
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Batch processor error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_batch(self, batch: List[Dict]) -> None:
        """Execute a batch of requests concurrently."""
        tasks = []
        for item in batch:
            endpoint = self._endpoints.get(item['endpoint'])
            if endpoint:
                for params in item['params']:
                    task = self._make_request_with_params(endpoint, params)
                    tasks.append((task, item['callback']))
        
        # Execute all requests concurrently
        results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
        
        # Group results by callback
        callback_results: Dict[Callable, List] = {}
        for (task, callback), result in zip(tasks, results):
            if callback not in callback_results:
                callback_results[callback] = []
            if not isinstance(result, Exception):
                callback_results[callback].append(result)
        
        # Notify callbacks
        for callback, data_list in callback_results.items():
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_list)
                else:
                    callback(data_list)
            except Exception as e:
                self.logger.error(f"Batch callback error: {e}")
    
    async def _make_request_with_params(self, 
                                        endpoint: APIEndpoint,
                                        params: Dict) -> Optional[Dict]:
        """Make request with specific parameters."""
        # Create temporary endpoint with modified params
        temp_endpoint = APIEndpoint(
            name=endpoint.name,
            url=endpoint.url,
            method=endpoint.method,
            headers=endpoint.headers,
            params={**endpoint.params, **params},
            weight=endpoint.weight,
            priority=endpoint.priority,
            cache_ttl_ms=endpoint.cache_ttl_ms
        )
        return await self._make_request(temp_endpoint)