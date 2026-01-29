"""
Health checks and auto-restart logic for the arbitrage bot.

Monitors bot health and manages restart procedures.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger("health")


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Individual health check configuration and state."""
    name: str
    check_fn: Callable[[], tuple[bool, str]]
    interval_seconds: float = 60.0
    timeout_seconds: float = 10.0
    critical: bool = False  # If True, failure triggers restart
    
    # State
    last_check: Optional[datetime] = None
    last_result: bool = True
    last_message: str = ""
    consecutive_failures: int = 0
    total_failures: int = 0
    total_checks: int = 0


@dataclass
class HealthReport:
    """Complete health report."""
    status: HealthStatus
    timestamp: datetime
    checks: Dict[str, Dict[str, Any]]
    overall_message: str
    restart_recommended: bool = False


class HealthMonitor:
    """
    Monitors bot health through configurable health checks.
    
    Features:
    - Periodic health checks
    - Automatic restart on critical failures
    - Health status aggregation
    - Integration with metrics collection
    """
    
    def __init__(
        self,
        check_interval: float = 30.0,
        restart_threshold: int = 3,
        restart_cooldown_seconds: float = 300.0
    ):
        """
        Initialize health monitor.
        
        Args:
            check_interval: Seconds between health check runs
            restart_threshold: Consecutive failures before restart
            restart_cooldown_seconds: Minimum seconds between restarts
        """
        self.check_interval = check_interval
        self.restart_threshold = restart_threshold
        self.restart_cooldown = timedelta(seconds=restart_cooldown_seconds)
        
        self._checks: Dict[str, HealthCheck] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Restart tracking
        self._restart_count = 0
        self._last_restart: Optional[datetime] = None
        self._restart_callback: Optional[Callable[[], None]] = None
        
        # Status tracking
        self._last_report: Optional[HealthReport] = None
        self._status_history: List[tuple[datetime, HealthStatus]] = []
    
    def add_check(self, check: HealthCheck) -> None:
        """
        Add a health check.
        
        Args:
            check: Health check configuration
        """
        self._checks[check.name] = check
        logger.info(f"Added health check: {check.name}")
    
    def on_restart(self, callback: Callable[[], None]) -> None:
        """
        Set callback for restart events.
        
        Args:
            callback: Function to call when restart is triggered
        """
        self._restart_callback = callback
    
    async def start(self) -> None:
        """Start health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitor started")
    
    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitor stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main health monitoring loop."""
        while self._running:
            try:
                await self._run_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _run_checks(self) -> None:
        """Run all health checks."""
        restart_needed = False
        
        for check in self._checks.values():
            try:
                # Run check with timeout
                result, message = await asyncio.wait_for(
                    asyncio.to_thread(check.check_fn),
                    timeout=check.timeout_seconds
                )
                
                check.last_check = datetime.now()
                check.last_result = result
                check.last_message = message
                check.total_checks += 1
                
                if result:
                    check.consecutive_failures = 0
                else:
                    check.consecutive_failures += 1
                    check.total_failures += 1
                    
                    logger.warning(
                        f"Health check '{check.name}' failed: {message} "
                        f"(consecutive: {check.consecutive_failures})"
                    )
                    
                    # Check if restart needed
                    if check.critical and check.consecutive_failures >= self.restart_threshold:
                        restart_needed = True
                        
            except asyncio.TimeoutError:
                check.last_result = False
                check.last_message = "Check timed out"
                check.consecutive_failures += 1
                check.total_failures += 1
                
                logger.warning(f"Health check '{check.name}' timed out")
                
                if check.critical and check.consecutive_failures >= self.restart_threshold:
                    restart_needed = True
                    
            except Exception as e:
                check.last_result = False
                check.last_message = f"Check error: {e}"
                check.consecutive_failures += 1
                check.total_failures += 1
                
                logger.error(f"Health check '{check.name}' error: {e}")
        
        # Generate health report
        self._last_report = self._generate_report()
        self._status_history.append((datetime.now(), self._last_report.status))
        
        # Trim status history
        if len(self._status_history) > 100:
            self._status_history = self._status_history[-100:]
        
        # Trigger restart if needed and allowed
        if restart_needed and self._can_restart():
            await self._trigger_restart()
    
    def _generate_report(self) -> HealthReport:
        """Generate health report from check results."""
        checks_data = {}
        critical_failures = 0
        total_failures = 0
        
        for name, check in self._checks.items():
            checks_data[name] = {
                'status': 'healthy' if check.last_result else 'unhealthy',
                'message': check.last_message,
                'last_check': check.last_check.isoformat() if check.last_check else None,
                'consecutive_failures': check.consecutive_failures,
                'total_failures': check.total_failures,
                'total_checks': check.total_checks,
                'critical': check.critical
            }
            
            if not check.last_result:
                total_failures += 1
                if check.critical:
                    critical_failures += 1
        
        # Determine overall status
        if critical_failures > 0:
            status = HealthStatus.CRITICAL
            message = f"Critical health checks failing: {critical_failures}"
        elif total_failures > len(self._checks) / 2:
            status = HealthStatus.UNHEALTHY
            message = f"Majority of health checks failing: {total_failures}/{len(self._checks)}"
        elif total_failures > 0:
            status = HealthStatus.DEGRADED
            message = f"Some health checks failing: {total_failures}/{len(self._checks)}"
        else:
            status = HealthStatus.HEALTHY
            message = "All systems operational"
        
        restart_recommended = critical_failures > 0 and self._can_restart()
        
        return HealthReport(
            status=status,
            timestamp=datetime.now(),
            checks=checks_data,
            overall_message=message,
            restart_recommended=restart_recommended
        )
    
    def _can_restart(self) -> bool:
        """Check if restart is allowed (cooldown passed)."""
        if self._last_restart is None:
            return True
        
        time_since_restart = datetime.now() - self._last_restart
        return time_since_restart > self.restart_cooldown
    
    async def _trigger_restart(self) -> None:
        """Trigger bot restart."""
        self._restart_count += 1
        self._last_restart = datetime.now()
        
        logger.critical(
            f"Triggering bot restart (restart #{self._restart_count})"
        )
        
        if self._restart_callback:
            try:
                await asyncio.to_thread(self._restart_callback)
            except Exception as e:
                logger.error(f"Restart callback error: {e}")
    
    def get_report(self) -> Optional[HealthReport]:
        """Get latest health report."""
        return self._last_report
    
    def get_status(self) -> HealthStatus:
        """Get current health status."""
        if self._last_report:
            return self._last_report.status
        return HealthStatus.HEALTHY
    
    def is_healthy(self) -> bool:
        """Check if bot is healthy."""
        return self.get_status() in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    
    def get_restart_stats(self) -> Dict[str, Any]:
        """Get restart statistics."""
        return {
            'restart_count': self._restart_count,
            'last_restart': self._last_restart.isoformat() if self._last_restart else None,
            'can_restart_now': self._can_restart()
        }


class AutoRestarter:
    """
    Manages automatic bot restart with exponential backoff.
    
    Prevents restart loops by implementing backoff strategy.
    """
    
    def __init__(
        self,
        max_restarts: int = 5,
        base_delay: float = 5.0,
        max_delay: float = 300.0
    ):
        """
        Initialize auto restarter.
        
        Args:
            max_restarts: Maximum consecutive restarts before giving up
            base_delay: Initial delay between restarts (seconds)
            max_delay: Maximum delay between restarts (seconds)
        """
        self.max_restarts = max_restarts
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        self._restart_count = 0
        self._last_restart_time: Optional[datetime] = None
        self._restart_history: List[datetime] = []
    
    def record_restart(self) -> None:
        """Record a restart event."""
        now = datetime.now()
        self._restart_count += 1
        self._last_restart_time = now
        self._restart_history.append(now)
        
        # Trim history to last hour
        cutoff = now - timedelta(hours=1)
        self._restart_history = [t for t in self._restart_history if t > cutoff]
    
    def should_restart(self) -> bool:
        """Check if restart should be attempted."""
        # Check if max restarts reached in the last hour
        if len(self._restart_history) >= self.max_restarts:
            logger.critical(
                f"Max restarts ({self.max_restarts}) reached in last hour. "
                "Manual intervention required."
            )
            return False
        
        return True
    
    def get_delay(self) -> float:
        """Get delay before next restart (exponential backoff)."""
        delay = self.base_delay * (2 ** len(self._restart_history))
        return min(delay, self.max_delay)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get restart statistics."""
        return {
            'total_restarts': self._restart_count,
            'recent_restarts': len(self._restart_history),
            'last_restart': self._last_restart_time.isoformat() if self._last_restart_time else None,
            'can_restart': self.should_restart(),
            'next_delay_seconds': self.get_delay() if self.should_restart() else None
        }


# Common health check functions

def create_api_health_check(
    api_client,
    endpoint: str = "/health",
    timeout: float = 5.0
) -> Callable[[], tuple[bool, str]]:
    """
    Create a health check function for an API client.
    
    Args:
        api_client: API client with a health check method
        endpoint: Health check endpoint
        timeout: Timeout in seconds
        
    Returns:
        Health check function
    """
    def check() -> tuple[bool, str]:
        try:
            # This is a simplified check - implement based on actual API
            if hasattr(api_client, 'is_connected') and callable(api_client.is_connected):
                connected = api_client.is_connected()
                return connected, "Connected" if connected else "Not connected"
            return True, "API client available"
        except Exception as e:
            return False, f"API health check failed: {e}"
    
    return check


def create_price_feed_health_check(
    exchange_monitor,
    max_staleness_seconds: float = 60.0
) -> Callable[[], tuple[bool, str]]:
    """
    Create a health check for price feed freshness.
    
    Args:
        exchange_monitor: Exchange monitor instance
        max_staleness_seconds: Maximum acceptable price age
        
    Returns:
        Health check function
    """
    def check() -> tuple[bool, str]:
        try:
            prices = exchange_monitor.get_all_prices()
            if not prices:
                return False, "No price data available"
            
            # Check price freshness
            now = datetime.now()
            stale_prices = []
            
            for symbol, timestamp in getattr(exchange_monitor, 'last_update', {}).items():
                age = (now - timestamp).total_seconds()
                if age > max_staleness_seconds:
                    stale_prices.append(f"{symbol} ({age:.0f}s)")
            
            if stale_prices:
                return False, f"Stale prices: {', '.join(stale_prices)}"
            
            return True, f"All {len(prices)} price feeds fresh"
            
        except Exception as e:
            return False, f"Price feed check failed: {e}"
    
    return check


def create_memory_health_check(
    max_memory_percent: float = 90.0
) -> Callable[[], tuple[bool, str]]:
    """
    Create a health check for memory usage.
    
    Args:
        max_memory_percent: Maximum acceptable memory usage
        
    Returns:
        Health check function
    """
    def check() -> tuple[bool, str]:
        try:
            import psutil
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > max_memory_percent:
                return False, f"Memory usage high: {usage_percent:.1f}%"
            
            return True, f"Memory usage: {usage_percent:.1f}%"
            
        except ImportError:
            return True, "psutil not available, skipping memory check"
        except Exception as e:
            return False, f"Memory check failed: {e}"
    
    return check
