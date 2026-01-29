"""
Paper Trading Module for Polymarket Arbitrage Bot

Simulates trading without real money, tracks virtual balance,
and provides realistic trade simulation with slippage, fees, and latency.
"""

import json
import random
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import statistics


class PaperTradeStatus(Enum):
    """Paper trade status."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    PARTIAL_FILL = "partial_fill"


@dataclass
class PaperTrade:
    """Represents a paper trading position."""
    trade_id: str
    symbol: str
    market_id: str
    market_name: str
    side: str  # 'BUY' or 'SELL'
    direction: str  # 'up' or 'down'
    size_requested: float
    size_filled: float
    entry_price: float
    entry_time: datetime
    status: PaperTradeStatus = PaperTradeStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[float] = None
    fees_paid: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    exit_reason: Optional[str] = None
    strategy: str = "unknown"
    latency_ms: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'market_id': self.market_id,
            'market_name': self.market_name,
            'side': self.side,
            'direction': self.direction,
            'size_requested': self.size_requested,
            'size_filled': self.size_filled,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'status': self.status.value,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'fees_paid': self.fees_paid,
            'slippage': self.slippage,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'exit_reason': self.exit_reason,
            'strategy': self.strategy,
            'latency_ms': self.latency_ms,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperTrade':
        """Create from dictionary."""
        data = data.copy()
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        if data.get('exit_time'):
            data['exit_time'] = datetime.fromisoformat(data['exit_time'])
        data['status'] = PaperTradeStatus(data['status'])
        return cls(**data)


@dataclass
class PaperPortfolio:
    """Virtual portfolio for paper trading."""
    initial_balance: float = 10000.0
    current_balance: float = 10000.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_fees_paid: float = 0.0
    max_balance: float = 10000.0
    min_balance: float = 10000.0
    peak_pnl: float = 0.0
    max_drawdown: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_fees_paid': self.total_fees_paid,
            'max_balance': self.max_balance,
            'min_balance': self.min_balance,
            'peak_pnl': self.peak_pnl,
            'max_drawdown': self.max_drawdown,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaperPortfolio':
        """Create from dictionary."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


class PaperTrader:
    """
    Paper trading simulator for Polymarket.
    
    Simulates trades with realistic conditions:
    - Slippage (0.1-0.5%)
    - Fees (Polymarket fee structure)
    - Order latency (random delays)
    - Partial fills based on volume
    """
    
    # Polymarket fee structure (approximate)
    MAKER_FEE = 0.0  # No maker fee
    TAKER_FEE = 0.002  # 0.2% taker fee
    
    # Simulation parameters
    SLIPPAGE_MIN = 0.001  # 0.1%
    SLIPPAGE_MAX = 0.005  # 0.5%
    LATENCY_MIN_MS = 50
    LATENCY_MAX_MS = 500
    PARTIAL_FILL_THRESHOLD = 0.3  # 30% chance of partial fill for low volume
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        data_dir: str = "data",
        enable_realism: bool = True,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: str = "6559976977"
    ):
        """
        Initialize paper trader.
        
        Args:
            initial_balance: Starting virtual balance in USD
            data_dir: Directory to store paper trade data
            enable_realism: Enable slippage, fees, and latency simulation
            telegram_bot_token: Telegram bot token for alerts
            telegram_chat_id: Telegram chat ID for alerts (default: qippu)
        """
        self.logger = logging.getLogger("PaperTrader")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.trades_file = self.data_dir / "paper_trades.json"
        self.portfolio_file = self.data_dir / "paper_portfolio.json"
        
        self.enable_realism = enable_realism
        
        # Load or create portfolio
        self.portfolio = self._load_portfolio()
        if not self.portfolio:
            self.portfolio = PaperPortfolio(initial_balance=initial_balance)
            self._save_portfolio()
        
        # Load trades
        self.trades: Dict[str, PaperTrade] = {}
        self.closed_trades: List[PaperTrade] = []
        self._load_trades()
        
        # Performance tracking
        self.daily_pnl: Dict[str, float] = {}
        self.equity_curve: List[Dict[str, Any]] = []
        
        # Telegram alerts
        from telegram_alerts import TelegramAlerter
        self.telegram_alerter = TelegramAlerter(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
            data_dir=data_dir
        )
        
        self.logger.info(
            f"Paper Trader initialized | Balance: ${self.portfolio.current_balance:.2f} | "
            f"Realism: {'ON' if enable_realism else 'OFF'} | "
            f"Telegram Alerts: {'ON' if telegram_bot_token else 'OFF'}"
        )
    
    def _load_portfolio(self) -> Optional[PaperPortfolio]:
        """Load portfolio from disk."""
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file, 'r') as f:
                    data = json.load(f)
                    return PaperPortfolio.from_dict(data)
            except Exception as e:
                self.logger.error(f"Error loading portfolio: {e}")
        return None
    
    def _save_portfolio(self) -> None:
        """Save portfolio to disk."""
        try:
            with open(self.portfolio_file, 'w') as f:
                json.dump(self.portfolio.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving portfolio: {e}")
    
    def _load_trades(self) -> None:
        """Load trades from disk."""
        if self.trades_file.exists():
            try:
                with open(self.trades_file, 'r') as f:
                    data = json.load(f)
                    for trade_data in data.get('open_trades', []):
                        trade = PaperTrade.from_dict(trade_data)
                        self.trades[trade.trade_id] = trade
                    for trade_data in data.get('closed_trades', []):
                        trade = PaperTrade.from_dict(trade_data)
                        self.closed_trades.append(trade)
                self.logger.info(
                    f"Loaded {len(self.trades)} open trades, "
                    f"{len(self.closed_trades)} closed trades"
                )
            except Exception as e:
                self.logger.error(f"Error loading trades: {e}")
    
    def _save_trades(self) -> None:
        """Save trades to disk."""
        try:
            data = {
                'open_trades': [t.to_dict() for t in self.trades.values()],
                'closed_trades': [t.to_dict() for t in self.closed_trades[-1000:]]  # Keep last 1000
            }
            with open(self.trades_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving trades: {e}")
    
    def _calculate_slippage(self, size_usd: float, market_liquidity: float = 10000.0) -> float:
        """Calculate realistic slippage based on order size and liquidity."""
        if not self.enable_realism:
            return 0.0
        
        # Larger orders = more slippage
        size_impact = min(size_usd / 1000, 0.5)  # Max 0.5% from size
        liquidity_factor = max(0.5, min(2.0, 10000.0 / market_liquidity))
        
        base_slippage = random.uniform(self.SLIPPAGE_MIN, self.SLIPPAGE_MAX)
        slippage = base_slippage * (1 + size_impact) * liquidity_factor
        
        return min(slippage, 0.02)  # Cap at 2%
    
    def _calculate_latency(self) -> float:
        """Simulate network latency."""
        if not self.enable_realism:
            return random.uniform(10, 50)
        return random.uniform(self.LATENCY_MIN_MS, self.LATENCY_MAX_MS)
    
    def _calculate_fees(self, size_usd: float, is_taker: bool = True) -> float:
        """Calculate trading fees."""
        if not self.enable_realism:
            return 0.0
        
        fee_rate = self.TAKER_FEE if is_taker else self.MAKER_FEE
        return size_usd * fee_rate
    
    def _check_partial_fill(self, size_usd: float, volume_24h: float = 0) -> tuple[bool, float]:
        """Check if order should be partially filled."""
        if not self.enable_realism or volume_24h <= 0:
            return False, size_usd
        
        # Low volume markets more likely to have partial fills
        volume_ratio = size_usd / volume_24h
        if volume_ratio > 0.1 or random.random() < self.PARTIAL_FILL_THRESHOLD:
            fill_ratio = random.uniform(0.5, 0.95)
            return True, size_usd * fill_ratio
        return False, size_usd
    
    async def open_position(
        self,
        symbol: str,
        market_id: str,
        market_name: str,
        direction: str,
        size_usd: float,
        requested_price: float,
        strategy: str = "unknown",
        market_liquidity: float = 10000.0,
        volume_24h: float = 0.0
    ) -> Optional[PaperTrade]:
        """
        Simulate opening a paper trading position.
        
        Args:
            symbol: Trading symbol (e.g., BTC/USDT)
            market_id: Polymarket market ID
            market_name: Human-readable market name
            direction: 'up' or 'down'
            size_usd: Position size in USD
            requested_price: Requested entry price
            strategy: Strategy that triggered the trade
            market_liquidity: Market liquidity for slippage calc
            volume_24h: 24h volume for partial fill calc
            
        Returns:
            PaperTrade object if successful, None otherwise
        """
        # Check if we have enough balance
        if size_usd > self.portfolio.current_balance:
            self.logger.warning(
                f"Insufficient balance: ${size_usd:.2f} requested, "
                f"${self.portfolio.current_balance:.2f} available"
            )
            return None
        
        # Simulate latency
        latency_ms = self._calculate_latency()
        await asyncio.sleep(latency_ms / 1000)
        
        # Calculate slippage
        slippage = self._calculate_slippage(size_usd, market_liquidity)
        
        # Apply slippage (always worse for trader)
        if direction == 'up':
            actual_price = requested_price * (1 + slippage)
        else:
            actual_price = requested_price * (1 - slippage)
        
        # Check for partial fill
        is_partial, filled_size = self._check_partial_fill(size_usd, volume_24h)
        
        # Calculate fees
        fees = self._calculate_fees(filled_size)
        
        # Create trade
        trade_id = f"paper_{symbol}_{direction}_{datetime.now().timestamp()}"
        
        trade = PaperTrade(
            trade_id=trade_id,
            symbol=symbol,
            market_id=market_id,
            market_name=market_name,
            side='BUY',
            direction=direction,
            size_requested=size_usd,
            size_filled=filled_size,
            entry_price=actual_price,
            entry_time=datetime.now(),
            status=PaperTradeStatus.PARTIAL_FILL if is_partial else PaperTradeStatus.OPEN,
            fees_paid=fees,
            slippage=slippage,
            strategy=strategy,
            latency_ms=latency_ms
        )
        
        if is_partial:
            trade.notes.append(f"Partial fill: {filled_size/size_usd:.1%} of requested size")
        
        # Update portfolio
        self.portfolio.current_balance -= filled_size + fees
        self.portfolio.total_fees_paid += fees
        self.portfolio.last_updated = datetime.now()
        
        # Track trade
        self.trades[trade_id] = trade
        
        # Save state
        self._save_portfolio()
        self._save_trades()
        
        self.logger.info(
            f"📊 PAPER TRADE OPEN | {symbol} {direction} | "
            f"Size: ${filled_size:.2f} | Entry: {actual_price:.3f} | "
            f"Slippage: {slippage:.2%} | Fees: ${fees:.2f} | "
            f"Latency: {latency_ms:.0f}ms"
        )
        
        return trade
    
    async def close_position(
        self,
        trade_id: str,
        exit_price: float,
        reason: str = "manual"
    ) -> Optional[PaperTrade]:
        """
        Simulate closing a paper trading position.
        
        Args:
            trade_id: Trade ID to close
            exit_price: Exit price
            reason: Reason for closing
            
        Returns:
            Closed PaperTrade object if successful, None otherwise
        """
        trade = self.trades.get(trade_id)
        if not trade:
            self.logger.error(f"Trade {trade_id} not found")
            return None
        
        # Simulate latency
        latency_ms = self._calculate_latency()
        await asyncio.sleep(latency_ms / 1000)
        
        # Calculate exit slippage
        slippage = self._calculate_slippage(trade.size_filled)
        
        # Apply slippage to exit
        if trade.direction == 'up':
            actual_exit = exit_price * (1 - slippage)
        else:
            actual_exit = exit_price * (1 + slippage)
        
        # Calculate fees
        fees = self._calculate_fees(trade.size_filled)
        
        # Calculate P&L for prediction markets
        # We bought YES shares for 'up' or NO shares for 'down'
        if trade.direction == 'up':
            pnl = (actual_exit - trade.entry_price) * trade.size_filled
        else:
            pnl = (trade.entry_price - actual_exit) * trade.size_filled
        
        pnl_percent = (pnl / trade.size_filled) * 100 if trade.size_filled > 0 else 0
        
        # Update trade
        trade.exit_price = actual_exit
        trade.exit_time = datetime.now()
        trade.pnl = pnl - fees
        trade.pnl_percent = pnl_percent
        trade.exit_reason = reason
        trade.fees_paid += fees
        trade.status = PaperTradeStatus.CLOSED
        trade.latency_ms += latency_ms
        
        # Update portfolio
        self.portfolio.current_balance += trade.size_filled + trade.pnl
        self.portfolio.total_fees_paid += fees
        self.portfolio.total_trades += 1
        
        if trade.pnl > 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1
        
        # Update max/min balance
        self.portfolio.max_balance = max(self.portfolio.max_balance, self.portfolio.current_balance)
        self.portfolio.min_balance = min(self.portfolio.min_balance, self.portfolio.current_balance)
        
        # Update drawdown
        current_pnl = self.portfolio.current_balance - self.portfolio.initial_balance
        self.portfolio.peak_pnl = max(self.portfolio.peak_pnl, current_pnl)
        drawdown = self.portfolio.peak_pnl - current_pnl
        self.portfolio.max_drawdown = max(self.portfolio.max_drawdown, drawdown)
        
        self.portfolio.last_updated = datetime.now()
        
        # Move to closed trades
        self.closed_trades.append(trade)
        del self.trades[trade_id]
        
        # Save state
        self._save_portfolio()
        self._save_trades()
        
        # Record equity point
        self._record_equity()
        
        emoji = "🟢" if trade.pnl > 0 else "🔴"
        self.logger.info(
            f"{emoji} PAPER TRADE CLOSE | {trade.symbol} | "
            f"PnL: ${trade.pnl:.2f} ({pnl_percent:+.2f}%) | "
            f"Entry: {trade.entry_price:.3f} | Exit: {actual_exit:.3f} | "
            f"Reason: {reason}"
        )
        
        # Send transaction alert to Telegram
        if self.telegram_alerter and self.telegram_alerter.enabled:
            asyncio.create_task(self.telegram_alerter.send_transaction_alert(
                trade_id=trade.trade_id,
                market=trade.market_name,
                direction=trade.direction,
                size=trade.size_filled,
                entry_price=trade.entry_price,
                exit_price=actual_exit,
                pnl=trade.pnl,
                strategy=trade.strategy
            ))
        
        # Check for hourly report
        asyncio.create_task(self._check_hourly_report())
        
        return trade
    
    def _record_equity(self) -> None:
        """Record equity curve point."""
        self.equity_curve.append({
            'timestamp': datetime.now().isoformat(),
            'balance': self.portfolio.current_balance,
            'pnl': self.portfolio.current_balance - self.portfolio.initial_balance
        })
    
    async def _check_telegram_alerts(self, previous_balance: float) -> None:
        """
        Check if balance crossed any alert thresholds.
        
        Args:
            previous_balance: Balance before the last trade
        """
        try:
            stats = self.get_performance_stats()
            
            await self.telegram_alerter.check_and_alert(
                current_balance=self.portfolio.current_balance,
                previous_balance=previous_balance,
                total_pnl=stats['total_pnl'],
                win_rate=stats['win_rate'],
                total_trades=stats['total_trades']
            )
        except Exception as e:
            self.logger.error(f"Error checking Telegram alerts: {e}")
    
    async def _check_hourly_report(self) -> None:
        """
        Check if we should send hourly balance report.
        """
        try:
            if self.telegram_alerter and self.telegram_alerter.enabled:
                stats = self.get_performance_stats()
                await self.telegram_alerter.check_and_send_hourly_report(
                    current_balance=self.portfolio.current_balance,
                    starting_balance=self.portfolio.initial_balance,
                    total_pnl=stats['total_pnl'],
                    win_rate=stats['win_rate'],
                    total_trades=stats['total_trades']
                )
        except Exception as e:
            self.logger.error(f"Error checking hourly report: {e}")
    
    def get_open_positions(self) -> List[PaperTrade]:
        """Get all open paper trades."""
        return list(self.trades.values())
    
    def get_closed_positions(self, limit: int = 100) -> List[PaperTrade]:
        """Get closed paper trades."""
        return self.closed_trades[-limit:]
    
    def get_all_trades(self) -> List[PaperTrade]:
        """Get all trades (open and closed)."""
        return list(self.trades.values()) + self.closed_trades
    
    def get_position(self, trade_id: str) -> Optional[PaperTrade]:
        """Get specific position."""
        return self.trades.get(trade_id)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Calculate comprehensive performance statistics."""
        all_trades = self.get_all_trades()
        closed = self.closed_trades
        
        if not all_trades:
            return self._empty_stats()
        
        # Basic stats
        total_trades = len(closed)
        wins = self.portfolio.winning_trades
        losses = self.portfolio.losing_trades
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # P&L stats
        total_pnl = self.portfolio.current_balance - self.portfolio.initial_balance
        pnl_percent = (total_pnl / self.portfolio.initial_balance) * 100
        
        # Trade analysis
        if closed:
            winning_trades = [t for t in closed if t.pnl > 0]
            losing_trades = [t for t in closed if t.pnl < 0]
            
            avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            largest_win = max((t.pnl for t in winning_trades), default=0)
            largest_loss = min((t.pnl for t in losing_trades), default=0)
            
            # Profit factor
            gross_profit = sum(t.pnl for t in winning_trades)
            gross_loss = abs(sum(t.pnl for t in losing_trades))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Expectancy
            expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss) if total_trades > 0 else 0
            
            # Average trade
            avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            # Hold time
            hold_times = []
            for t in closed:
                if t.exit_time and t.entry_time:
                    hold_times.append((t.exit_time - t.entry_time).total_seconds())
            avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
        else:
            avg_win = avg_loss = largest_win = largest_loss = 0
            profit_factor = expectancy = avg_trade_pnl = avg_hold_time = 0
        
        # Sharpe ratio (simplified - assumes risk-free rate of 0)
        if len(closed) >= 2:
            returns = [t.pnl_percent for t in closed if t.pnl_percent is not None]
            if len(returns) > 1:
                try:
                    sharpe = statistics.mean(returns) / (statistics.stdev(returns) or 1)
                    # Annualize (assume daily trades)
                    sharpe = sharpe * (252 ** 0.5)
                except:
                    sharpe = 0
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        return {
            'initial_balance': self.portfolio.initial_balance,
            'current_balance': self.portfolio.current_balance,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'open_positions': len(self.trades),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'avg_trade_pnl': avg_trade_pnl,
            'avg_hold_time_seconds': avg_hold_time,
            'sharpe_ratio': sharpe,
            'max_drawdown': self.portfolio.max_drawdown,
            'max_drawdown_percent': (self.portfolio.max_drawdown / self.portfolio.initial_balance) * 100,
            'total_fees_paid': self.portfolio.total_fees_paid,
            'created_at': self.portfolio.created_at.isoformat(),
            'last_updated': self.portfolio.last_updated.isoformat()
        }
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure."""
        return {
            'initial_balance': self.portfolio.initial_balance,
            'current_balance': self.portfolio.current_balance,
            'total_pnl': 0,
            'pnl_percent': 0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'open_positions': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'profit_factor': 0,
            'expectancy': 0,
            'avg_trade_pnl': 0,
            'avg_hold_time_seconds': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'max_drawdown_percent': 0,
            'total_fees_paid': 0,
            'created_at': self.portfolio.created_at.isoformat(),
            'last_updated': self.portfolio.last_updated.isoformat()
        }
    
    def reset_account(self, new_balance: float = 10000.0) -> None:
        """Reset paper trading account to initial state."""
        self.logger.warning(f"🔄 Resetting paper trading account to ${new_balance:.2f}")
        
        self.portfolio = PaperPortfolio(initial_balance=new_balance)
        self.trades.clear()
        self.closed_trades.clear()
        self.equity_curve.clear()
        
        # Reset Telegram alert thresholds
        self.telegram_alerter.reset_alerts()
        self.telegram_alerter.starting_balance = new_balance
        
        self._save_portfolio()
        self._save_trades()
        
        self.logger.info("✅ Paper trading account reset complete")
    
    async def send_startup_notification(self) -> None:
        """Send Telegram notification that paper trading has started."""
        try:
            await self.telegram_alerter.send_startup_notification(
                initial_balance=self.portfolio.initial_balance
            )
        except Exception as e:
            self.logger.error(f"Error sending startup notification: {e}")
    
    async def send_daily_summary(self) -> None:
        """Send daily performance summary via Telegram."""
        try:
            stats = self.get_performance_stats()
            
            closed = self.closed_trades
            best_trade = max((t.pnl for t in closed), default=0.0)
            worst_trade = min((t.pnl for t in closed), default=0.0)
            
            await self.telegram_alerter.send_daily_summary(
                balance=self.portfolio.current_balance,
                pnl=stats['total_pnl'],
                win_rate=stats['win_rate'],
                total_trades=stats['total_trades'],
                best_trade=best_trade,
                worst_trade=worst_trade
            )
        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive performance report."""
        stats = self.get_performance_stats()
        
        report = []
        report.append("=" * 60)
        report.append("📊 PAPER TRADING PERFORMANCE REPORT")
        report.append("=" * 60)
        report.append("")
        report.append(f"Account Balance: ${stats['current_balance']:.2f}")
        report.append(f"Initial Balance: ${stats['initial_balance']:.2f}")
        report.append(f"Total P&L: ${stats['total_pnl']:.2f} ({stats['pnl_percent']:+.2f}%)")
        report.append("")
        report.append("-" * 40)
        report.append("TRADE STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Trades: {stats['total_trades']}")
        report.append(f"Winning Trades: {stats['wins']}")
        report.append(f"Losing Trades: {stats['losses']}")
        report.append(f"Win Rate: {stats['win_rate']:.1f}%")
        report.append(f"Open Positions: {stats['open_positions']}")
        report.append("")
        report.append("-" * 40)
        report.append("P&L BREAKDOWN")
        report.append("-" * 40)
        report.append(f"Average Win: ${stats['avg_win']:.2f}")
        report.append(f"Average Loss: ${stats['avg_loss']:.2f}")
        report.append(f"Largest Win: ${stats['largest_win']:.2f}")
        report.append(f"Largest Loss: ${stats['largest_loss']:.2f}")
        report.append(f"Average Trade P&L: ${stats['avg_trade_pnl']:.2f}")
        report.append("")
        report.append("-" * 40)
        report.append("RISK METRICS")
        report.append("-" * 40)
        report.append(f"Max Drawdown: ${stats['max_drawdown']:.2f} ({stats['max_drawdown_percent']:.2f}%)")
        report.append(f"Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        report.append(f"Profit Factor: {stats['profit_factor']:.2f}")
        report.append(f"Expectancy: ${stats['expectancy']:.2f}")
        report.append(f"Total Fees Paid: ${stats['total_fees_paid']:.2f}")
        report.append("")
        
        if stats['total_trades'] > 0:
            report.append("-" * 40)
            report.append("RECENT TRADES")
            report.append("-" * 40)
            recent = self.get_closed_positions(10)
            for trade in reversed(recent):
                emoji = "🟢" if trade.pnl > 0 else "🔴"
                report.append(
                    f"{emoji} {trade.symbol} {trade.direction} | "
                    f"${trade.pnl:.2f} | {trade.strategy}"
                )
        
        report.append("")
        report.append("=" * 60)
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def export_trades_csv(self, filepath: str) -> bool:
        """Export trades to CSV format."""
        try:
            import csv
            
            all_trades = self.get_all_trades()
            with open(filepath, 'w', newline='') as f:
                if all_trades:
                    writer = csv.DictWriter(f, fieldnames=all_trades[0].to_dict().keys())
                    writer.writeheader()
                    for trade in all_trades:
                        writer.writerow(trade.to_dict())
            return True
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return False
