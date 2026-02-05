"""
Risk management for trading positions.

Implements stop-loss, take-profit, and other risk controls.
"""

import logging
from typing import Tuple, Optional
from datetime import datetime, timedelta


class RiskManager:
    """
    Manages risk for trading positions.
    
    Implements stop-loss, take-profit, position sizing limits,
    and daily loss limits.
    """
    
    def __init__(self,
                 stop_loss_percentage: float = 0.15,
                 take_profit_percentage: float = 0.90,
                 max_daily_loss_usd: float = 1000.0,
                 emergency_shutdown_loss_usd: float = 5000.0):
        """
        Initialize risk manager.
        
        Args:
            stop_loss_percentage: Stop loss threshold (e.g., 0.15 = 15% loss)
            take_profit_percentage: Take profit threshold (e.g., 0.90 = 90% profit)
            max_daily_loss_usd: Maximum daily loss before stopping trading
            emergency_shutdown_loss_usd: Total loss that triggers emergency shutdown
        """
        self.logger = logging.getLogger("RiskManager")
        self.stop_loss_pct = stop_loss_percentage
        self.take_profit_pct = take_profit_percentage
        self.max_daily_loss = max_daily_loss_usd
        self.emergency_shutdown_loss = emergency_shutdown_loss_usd
        
        # Track daily losses
        self.daily_pnl = 0.0
        self.last_reset = datetime.now().date()
        
        # Emergency shutdown flag
        self.emergency_shutdown = False
    
    async def should_exit_position(self, position,
                                   current_price: Optional[float] = None) -> Tuple[bool, float, str]:
        """
        Check if a position should be exited.
        
        Args:
            position: Position object
            current_price: Current market price (if available)
            
        Returns:
            Tuple of (should_exit, exit_price, reason)
        """
        # For Polymarket, we typically hold until market resolution
        # But we can implement early exit logic based on odds movement
        
        if not current_price:
            # No current price data, can't evaluate
            return False, 0.0, ""
        
        # Calculate unrealized P&L
        unrealized_pnl = current_price - position.entry_price
        pnl_percentage = unrealized_pnl / position.entry_price
        
        # Check stop loss
        if pnl_percentage <= -self.stop_loss_pct:
            self.logger.warning(
                f"Stop loss triggered for {position.position_id}: "
                f"{pnl_percentage:.2%} loss"
            )
            return True, current_price, "stop_loss"
        
        # Check take profit
        if pnl_percentage >= self.take_profit_pct:
            self.logger.info(
                f"Take profit triggered for {position.position_id}: "
                f"{pnl_percentage:.2%} profit"
            )
            return True, current_price, "take_profit"
        
        # Check if market is about to resolve or has expired (15-minute markets)
        # Convert entry_time to datetime if it's a string
        if isinstance(position.entry_time, str):
            from datetime import datetime as dt
            entry_time = dt.fromisoformat(position.entry_time.replace('Z', '+00:00'))
        else:
            entry_time = position.entry_time
        
        time_held = datetime.now() - entry_time
        
        # Force close if position is older than 20 minutes (market definitely expired)
        if time_held > timedelta(minutes=20):
            self.logger.warning(
                f"Force closing expired position {position.position_id}: "
                f"held for {time_held.total_seconds()/60:.1f} minutes"
            )
            return True, current_price, "market_expired"
        
        # Close before market resolution (14.5 minutes)
        if time_held > timedelta(minutes=14, seconds=30):
            self.logger.info(
                f"Closing position before expiration {position.position_id}"
            )
            return True, current_price, "approaching_expiration"
        
        return False, 0.0, ""
    
    def can_open_position(self, position_size: float) -> Tuple[bool, str]:
        """
        Check if we can open a new position given current risk exposure.
        
        Args:
            position_size: Size of proposed position in USD
            
        Returns:
            Tuple of (can_open, reason)
        """
        # Reset daily P&L if new day
        self._reset_daily_pnl_if_needed()
        
        # Check emergency shutdown
        if self.emergency_shutdown:
            return False, "emergency_shutdown_active"
        
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            self.logger.warning(
                f"Daily loss limit reached: ${self.daily_pnl:.2f}"
            )
            return False, "daily_loss_limit_reached"
        
        # Check if new position would exceed remaining daily risk budget
        remaining_budget = self.max_daily_loss + self.daily_pnl
        if position_size > remaining_budget:
            self.logger.warning(
                f"Position size ${position_size} exceeds remaining daily budget ${remaining_budget:.2f}"
            )
            return False, "insufficient_risk_budget"
        
        return True, ""
    
    def update_daily_pnl(self, pnl: float) -> None:
        """
        Update daily P&L tracking.
        
        Args:
            pnl: Profit/loss to add to daily total
        """
        self._reset_daily_pnl_if_needed()
        
        self.daily_pnl += pnl
        
        # Check for emergency shutdown
        if self.daily_pnl <= -self.emergency_shutdown_loss:
            self.logger.critical(
                f"EMERGENCY SHUTDOWN: Total loss ${self.daily_pnl:.2f} "
                f"exceeds limit ${self.emergency_shutdown_loss}"
            )
            self.emergency_shutdown = True
    
    def _reset_daily_pnl_if_needed(self) -> None:
        """Reset daily P&L counter if it's a new day."""
        today = datetime.now().date()
        
        if today > self.last_reset:
            self.logger.info(
                f"Resetting daily P&L (previous: ${self.daily_pnl:.2f})"
            )
            self.daily_pnl = 0.0
            self.last_reset = today
    
    def get_risk_status(self) -> dict:
        """
        Get current risk status.
        
        Returns:
            Dictionary with risk metrics
        """
        self._reset_daily_pnl_if_needed()
        
        remaining_budget = self.max_daily_loss + self.daily_pnl
        
        return {
            'daily_pnl': self.daily_pnl,
            'max_daily_loss': self.max_daily_loss,
            'remaining_daily_budget': remaining_budget,
            'emergency_shutdown': self.emergency_shutdown,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct
        }
    
    def reset_emergency_shutdown(self) -> None:
        """
        Reset emergency shutdown flag.
        
        Should only be called after reviewing and fixing the issue.
        """
        self.logger.warning("Resetting emergency shutdown flag")
        self.emergency_shutdown = False
