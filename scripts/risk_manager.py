"""
Risk Manager - Risk controls and portfolio management
Handles daily loss limits, auto-unfollow logic, position sizing
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class WalletPerformance:
    """Tracks performance metrics for a copied wallet"""
    address: str
    name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    trade_history: List[Dict[str, Any]] = field(default_factory=list)
    last_trade_time: Optional[datetime] = None
    is_active: bool = True
    unfollow_reason: Optional[str] = None
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    def record_trade(self, trade_pnl: float, trade_data: Dict[str, Any]):
        """Record a trade result"""
        self.total_trades += 1
        self.total_pnl += trade_pnl
        
        if trade_pnl > 0:
            self.winning_trades += 1
        elif trade_pnl < 0:
            self.losing_trades += 1
        
        self.trade_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "pnl": trade_pnl,
            **trade_data
        })
        self.last_trade_time = datetime.utcnow()
        
        # Keep only last 100 trades in memory
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]


class RiskManager:
    """Manages risk controls for copy trading"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Risk settings
        risk_config = config.get("risk_management", {})
        self.daily_loss_limit_percent = risk_config.get("daily_loss_limit_percent", 5.0)
        self.max_position_size_percent = risk_config.get("max_position_size_percent", 5.0)
        self.max_concurrent_positions = risk_config.get("max_concurrent_positions", 10)
        self.min_win_rate_percent = risk_config.get("min_win_rate_percent", 50.0)
        self.min_trades_for_win_rate = risk_config.get("min_trades_for_win_rate", 20)
        self.auto_unfollow_bad_performers = risk_config.get("auto_unfollow_bad_performers", True)
        self.stop_loss_percent = risk_config.get("stop_loss_percent", 10.0)
        self.take_profit_percent = risk_config.get("take_profit_percent", 20.0)
        
        # State tracking
        self.wallet_performance: Dict[str, WalletPerformance] = {}
        self.daily_losses: Dict[str, float] = defaultdict(float)  # date -> loss amount
        self.risk_events: List[Dict[str, Any]] = []
        self.blocked_wallets: Set[str] = set()
        
        # Trading halt state
        self.trading_halted = False
        self.trading_halt_reason: Optional[str] = None
        self.trading_halt_until: Optional[datetime] = None
        
        # Initialize wallet performance tracking
        self._init_wallet_tracking()
        
        logger.info("RiskManager initialized")
    
    def _init_wallet_tracking(self):
        """Initialize tracking for configured wallets"""
        for wallet in self.config.get("target_wallets", []):
            address = wallet["address"].lower()
            self.wallet_performance[address] = WalletPerformance(
                address=address,
                name=wallet.get("name", "Unknown")
            )
    
    def check_trade_allowed(
        self,
        wallet_address: str,
        market_id: str,
        current_balance: float,
        trade_amount: float,
        open_positions_count: int
    ) -> Tuple[bool, str]:
        """
        Check if a trade should be allowed based on risk rules
        
        Returns: (allowed, reason)
        """
        addr_lower = wallet_address.lower()
        
        # Check if trading is halted
        if self.trading_halted:
            if self.trading_halt_until and datetime.utcnow() < self.trading_halt_until:
                return False, f"Trading halted: {self.trading_halt_reason}"
            else:
                # Resume trading
                self.trading_halted = False
                self.trading_halt_reason = None
                self.trading_halt_until = None
        
        # Check if wallet is blocked
        if addr_lower in self.blocked_wallets:
            return False, "Wallet is blocked due to poor performance"
        
        # Check wallet performance
        if addr_lower in self.wallet_performance:
            perf = self.wallet_performance[addr_lower]
            if self.auto_unfollow_bad_performers and perf.total_trades >= self.min_trades_for_win_rate:
                if perf.win_rate < self.min_win_rate_percent:
                    self.blocked_wallets.add(addr_lower)
                    perf.is_active = False
                    perf.unfollow_reason = f"Win rate {perf.win_rate:.1f}% below {self.min_win_rate_percent}%"
                    self._record_risk_event(
                        "AUTO_UNFOLLOW",
                        f"Auto-unfollowed {perf.name} ({wallet_address}): {perf.unfollow_reason}"
                    )
                    return False, perf.unfollow_reason
        
        # Check daily loss limit
        today = datetime.utcnow().date().isoformat()
        daily_loss = self.daily_losses.get(today, 0)
        daily_loss_limit = current_balance * (self.daily_loss_limit_percent / 100)
        
        if daily_loss >= daily_loss_limit:
            self._halt_trading(
                f"Daily loss limit hit: ${daily_loss:.2f} >= ${daily_loss_limit:.2f}",
                hours=24
            )
            return False, "Daily loss limit reached"
        
        # Check position size limit
        max_position_size = current_balance * (self.max_position_size_percent / 100)
        if trade_amount > max_position_size:
            return False, f"Trade size ${trade_amount:.2f} exceeds max position size ${max_position_size:.2f}"
        
        # Check max concurrent positions
        if open_positions_count >= self.max_concurrent_positions:
            return False, f"Max concurrent positions ({self.max_concurrent_positions}) reached"
        
        return True, "Trade allowed"
    
    def calculate_position_size(
        self,
        original_trade_amount: float,
        current_balance: float,
        copy_percentage: float = 100.0
    ) -> float:
        """
        Calculate the position size for a copy trade
        
        Applies copy percentage and caps at max position size
        """
        # Apply copy percentage
        copied_amount = original_trade_amount * (copy_percentage / 100)
        
        # Cap at max position size
        max_position_size = current_balance * (self.max_position_size_percent / 100)
        
        if copied_amount > max_position_size:
            logger.warning(
                f"Capping position size: ${copied_amount:.2f} -> ${max_position_size:.2f} "
                f"({self.max_position_size_percent}% of balance)"
            )
            return max_position_size
        
        return copied_amount
    
    def record_trade_result(
        self,
        wallet_address: str,
        trade_pnl: float,
        trade_data: Dict[str, Any]
    ):
        """Record the result of a trade for performance tracking"""
        addr_lower = wallet_address.lower()
        
        # Update wallet performance
        if addr_lower in self.wallet_performance:
            self.wallet_performance[addr_lower].record_trade(trade_pnl, trade_data)
        
        # Track daily loss
        if trade_pnl < 0:
            today = datetime.utcnow().date().isoformat()
            self.daily_losses[today] += abs(trade_pnl)
    
    def check_position_exit(
        self,
        position: Any,  # Position object from paper_trader
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Check if a position should be exited based on stop loss / take profit
        
        Returns: (should_exit, reason)
        """
        if not position or position.entry_price <= 0:
            return False, ""
        
        if position.side == "LONG":
            # Check stop loss
            loss_percent = ((position.entry_price - current_price) / position.entry_price) * 100
            if loss_percent >= self.stop_loss_percent:
                return True, f"Stop loss hit: -{loss_percent:.1f}%"
            
            # Check take profit
            profit_percent = ((current_price - position.entry_price) / position.entry_price) * 100
            if profit_percent >= self.take_profit_percent:
                return True, f"Take profit hit: +{profit_percent:.1f}%"
        
        else:  # SHORT
            # Check stop loss (price went up)
            loss_percent = ((current_price - position.entry_price) / position.entry_price) * 100
            if loss_percent >= self.stop_loss_percent:
                return True, f"Stop loss hit: -{loss_percent:.1f}%"
            
            # Check take profit (price went down)
            profit_percent = ((position.entry_price - current_price) / position.entry_price) * 100
            if profit_percent >= self.take_profit_percent:
                return True, f"Take profit hit: +{profit_percent:.1f}%"
        
        return False, ""
    
    def _halt_trading(self, reason: str, hours: int = 24):
        """Halt trading for a specified period"""
        self.trading_halted = True
        self.trading_halt_reason = reason
        self.trading_halt_until = datetime.utcnow() + timedelta(hours=hours)
        
        self._record_risk_event("TRADING_HALTED", reason)
        logger.warning(f"Trading halted: {reason}")
    
    def _record_risk_event(self, event_type: str, message: str):
        """Record a risk management event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "message": message
        }
        self.risk_events.append(event)
        
        # Keep only last 1000 events
        if len(self.risk_events) > 1000:
            self.risk_events = self.risk_events[-1000:]
        
        logger.info(f"Risk event: {event_type} - {message}")
    
    def get_wallet_performance(self, wallet_address: str) -> Optional[WalletPerformance]:
        """Get performance data for a wallet"""
        return self.wallet_performance.get(wallet_address.lower())
    
    def get_all_wallet_performance(self) -> List[WalletPerformance]:
        """Get performance data for all wallets"""
        return list(self.wallet_performance.values())
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk management status"""
        today = datetime.utcnow().date().isoformat()
        
        return {
            "trading_halted": self.trading_halted,
            "trading_halt_reason": self.trading_halt_reason,
            "trading_halt_until": self.trading_halt_until.isoformat() if self.trading_halt_until else None,
            "daily_loss": self.daily_losses.get(today, 0),
            "daily_loss_limit_percent": self.daily_loss_limit_percent,
            "blocked_wallets": list(self.blocked_wallets),
            "wallet_count": len(self.wallet_performance),
            "active_wallet_count": sum(1 for p in self.wallet_performance.values() if p.is_active)
        }
    
    def get_recent_risk_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent risk events"""
        return self.risk_events[-limit:]
    
    def manual_block_wallet(self, wallet_address: str, reason: str) -> bool:
        """Manually block a wallet from being copied"""
        addr_lower = wallet_address.lower()
        
        if addr_lower in self.blocked_wallets:
            return False
        
        self.blocked_wallets.add(addr_lower)
        
        if addr_lower in self.wallet_performance:
            self.wallet_performance[addr_lower].is_active = False
            self.wallet_performance[addr_lower].unfollow_reason = reason
        
        self._record_risk_event("MANUAL_BLOCK", f"Manually blocked {wallet_address}: {reason}")
        return True
    
    def unblock_wallet(self, wallet_address: str) -> bool:
        """Unblock a previously blocked wallet"""
        addr_lower = wallet_address.lower()
        
        if addr_lower not in self.blocked_wallets:
            return False
        
        self.blocked_wallets.discard(addr_lower)
        
        if addr_lower in self.wallet_performance:
            self.wallet_performance[addr_lower].is_active = True
            self.wallet_performance[addr_lower].unfollow_reason = None
        
        self._record_risk_event("WALLET_UNBLOCKED", f"Unblocked {wallet_address}")
        return True
    
    def resume_trading(self) -> bool:
        """Manually resume trading if halted"""
        if not self.trading_halted:
            return False
        
        self.trading_halted = False
        self.trading_halt_reason = None
        self.trading_halt_until = None
        
        self._record_risk_event("TRADING_RESUMED", "Trading manually resumed")
        return True
    
    def reset_daily_loss(self):
        """Reset daily loss tracking (call at start of new day)"""
        today = datetime.utcnow().date().isoformat()
        if today in self.daily_losses:
            yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            self.daily_losses[yesterday] = self.daily_losses.pop(today)
        
        logger.info("Daily loss tracking reset for new day")
