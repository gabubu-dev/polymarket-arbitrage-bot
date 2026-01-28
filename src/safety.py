"""
Safety checks and validators.

Pre-flight checks to ensure safe operation and prevent common issues.
"""

import logging
from typing import Tuple, List, Optional
from datetime import datetime, timedelta
import asyncio


class SafetyValidator:
    """
    Perform safety checks before executing trades.
    
    Validates conditions like network connectivity, API health,
    balance sufficiency, and market conditions.
    """
    
    def __init__(self):
        """Initialize safety validator."""
        self.logger = logging.getLogger("SafetyValidator")
        
        # Track check results
        self.last_checks: dict = {}
        self.check_failures: dict = {}
    
    async def validate_pre_trade(self, polymarket_client, exchange_monitor,
                                 position_size: float) -> Tuple[bool, List[str]]:
        """
        Run all pre-trade safety checks.
        
        Args:
            polymarket_client: PolymarketClient instance
            exchange_monitor: ExchangeMonitor instance
            position_size: Intended position size in USD
            
        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        issues = []
        
        # Check 1: Network connectivity
        if not await self._check_network_health(exchange_monitor):
            issues.append("Exchange network connectivity issues")
        
        # Check 2: API health
        if not await self._check_api_health(polymarket_client):
            issues.append("Polymarket API issues")
        
        # Check 3: Balance sufficiency
        if not await self._check_balance(polymarket_client, position_size):
            issues.append("Insufficient balance for position")
        
        # Check 4: Rate limits
        if not self._check_rate_limits():
            issues.append("API rate limits approaching")
        
        # Check 5: Market hours (if applicable)
        if not self._check_market_hours():
            issues.append("Outside trading hours")
        
        # Update check results
        self.last_checks['pre_trade'] = datetime.now()
        
        is_safe = len(issues) == 0
        
        if not is_safe:
            self.logger.warning(f"Pre-trade checks failed: {', '.join(issues)}")
            self._record_failure('pre_trade', issues)
        
        return is_safe, issues
    
    async def _check_network_health(self, exchange_monitor) -> bool:
        """Check if exchange connections are healthy."""
        try:
            # Check if we've received recent price updates
            for exchange_name, monitor in exchange_monitor.monitors.items():
                for symbol in monitor.symbols:
                    last_update = monitor.last_update.get(symbol)
                    
                    if not last_update:
                        self.logger.warning(f"No price data for {exchange_name} {symbol}")
                        return False
                    
                    # Check if update is recent (within 30 seconds)
                    if datetime.now() - last_update > timedelta(seconds=30):
                        self.logger.warning(
                            f"Stale price data for {exchange_name} {symbol}: "
                            f"{(datetime.now() - last_update).total_seconds()}s old"
                        )
                        return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error checking network health: {e}")
            return False
    
    async def _check_api_health(self, polymarket_client) -> bool:
        """Check if Polymarket API is responding."""
        try:
            if not polymarket_client.client:
                self.logger.warning("Polymarket client not initialized")
                return False
            
            # Try a simple API call to verify connectivity
            # In real implementation, make a lightweight API call
            # For now, just check if client exists
            return True
        
        except Exception as e:
            self.logger.error(f"Error checking API health: {e}")
            return False
    
    async def _check_balance(self, polymarket_client, required_amount: float) -> bool:
        """Check if account has sufficient balance."""
        try:
            balance = polymarket_client.get_balance()
            
            # Require at least 1.5x the position size to account for fees
            required_with_buffer = required_amount * 1.5
            
            if balance < required_with_buffer:
                self.logger.warning(
                    f"Insufficient balance: ${balance:.2f} < ${required_with_buffer:.2f}"
                )
                return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error checking balance: {e}")
            return False
    
    def _check_rate_limits(self) -> bool:
        """Check if we're approaching API rate limits."""
        # In real implementation, track API call counts and check against limits
        # For now, return True (pass)
        return True
    
    def _check_market_hours(self) -> bool:
        """Check if current time is within acceptable trading hours."""
        # Crypto markets are 24/7, so this always passes
        # But you could add logic to avoid trading during
        # low liquidity periods or specific blackout times
        return True
    
    def _record_failure(self, check_type: str, issues: List[str]) -> None:
        """Record a failed check."""
        if check_type not in self.check_failures:
            self.check_failures[check_type] = []
        
        self.check_failures[check_type].append({
            'timestamp': datetime.now(),
            'issues': issues
        })
        
        # Keep only last 100 failures
        self.check_failures[check_type] = self.check_failures[check_type][-100:]
    
    def get_failure_history(self, check_type: Optional[str] = None) -> dict:
        """
        Get history of failed checks.
        
        Args:
            check_type: Specific check type, or None for all
            
        Returns:
            Dictionary of failures
        """
        if check_type:
            return {check_type: self.check_failures.get(check_type, [])}
        return self.check_failures.copy()


class CircuitBreaker:
    """
    Circuit breaker to stop trading after repeated failures.
    
    Implements the circuit breaker pattern to prevent cascading failures.
    """
    
    def __init__(self, failure_threshold: int = 5,
                 timeout_seconds: int = 300):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying again
        """
        self.logger = logging.getLogger("CircuitBreaker")
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        
        self.failure_count = 0
        self.state = "closed"  # closed, open, half_open
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
    
    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == "half_open":
            # Success in half-open state closes the circuit
            self.logger.info("Circuit breaker: Success in half-open state, closing circuit")
            self.state = "closed"
            self.failure_count = 0
        
        # Reset failure count on success
        self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self, error: str) -> None:
        """
        Record a failed operation.
        
        Args:
            error: Error description
        """
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold and self.state == "closed":
            # Open the circuit
            self.state = "open"
            self.opened_at = datetime.now()
            self.logger.error(
                f"Circuit breaker OPENED after {self.failure_count} failures. "
                f"Last error: {error}"
            )
    
    def can_attempt(self) -> Tuple[bool, str]:
        """
        Check if an operation can be attempted.
        
        Returns:
            Tuple of (can_attempt, reason)
        """
        if self.state == "closed":
            return True, ""
        
        if self.state == "open":
            # Check if timeout has passed
            if self.opened_at:
                elapsed = (datetime.now() - self.opened_at).total_seconds()
                if elapsed >= self.timeout_seconds:
                    # Try half-open state
                    self.state = "half_open"
                    self.logger.info("Circuit breaker entering half-open state")
                    return True, ""
            
            return False, f"Circuit breaker is open (failures: {self.failure_count})"
        
        if self.state == "half_open":
            # Allow one attempt in half-open state
            return True, ""
        
        return False, "Unknown circuit state"
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.logger.warning("Circuit breaker manually reset")
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
        self.opened_at = None
    
    def get_status(self) -> dict:
        """
        Get current circuit breaker status.
        
        Returns:
            Dictionary with status info
        """
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None
        }
