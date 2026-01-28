"""
Backtesting framework for arbitrage strategies.

Tests strategies against historical data to evaluate performance
before deploying with real capital.
"""

import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class BacktestTrade:
    """Represents a trade in backtesting."""
    timestamp: datetime
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    size_usd: float
    pnl: float
    hold_time_seconds: float
    exit_reason: str


@dataclass
class BacktestResults:
    """Results from a backtest run."""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_pnl_per_trade: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[BacktestTrade] = field(default_factory=list)
    daily_pnl: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert results to dictionary."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': (self.total_pnl / self.initial_capital) * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_pnl_per_trade': self.avg_pnl_per_trade,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'trades': [
                {
                    'timestamp': t.timestamp.isoformat(),
                    'symbol': t.symbol,
                    'side': t.side,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'pnl': t.pnl,
                    'hold_time_seconds': t.hold_time_seconds,
                    'exit_reason': t.exit_reason
                }
                for t in self.trades
            ]
        }


class Backtester:
    """
    Backtesting engine for arbitrage strategies.
    
    Simulates trading strategy against historical data to evaluate
    performance metrics before live deployment.
    """
    
    def __init__(self, initial_capital: float = 10000.0,
                 position_size_usd: float = 100.0,
                 max_positions: int = 5,
                 divergence_threshold: float = 0.05,
                 stop_loss_pct: float = 0.15,
                 take_profit_pct: float = 0.90):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital in USD
            position_size_usd: Position size per trade
            max_positions: Maximum concurrent positions
            divergence_threshold: Minimum divergence to trigger trade
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
        """
        self.logger = logging.getLogger("Backtester")
        self.initial_capital = initial_capital
        self.position_size_usd = position_size_usd
        self.max_positions = max_positions
        self.divergence_threshold = divergence_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # Trading state
        self.capital = initial_capital
        self.positions: List[Dict] = []
        self.closed_trades: List[BacktestTrade] = []
        self.daily_pnl: Dict[str, float] = {}
        
    def load_historical_data(self, data_path: str) -> pd.DataFrame:
        """
        Load historical price data.
        
        Args:
            data_path: Path to CSV file with columns:
                      timestamp, symbol, exchange_price, polymarket_price
                      
        Returns:
            DataFrame with historical data
        """
        try:
            df = pd.read_csv(data_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            self.logger.info(f"Loaded {len(df)} historical data points")
            return df
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            raise
    
    def run_backtest(self, historical_data: pd.DataFrame) -> BacktestResults:
        """
        Run backtest on historical data.
        
        Args:
            historical_data: DataFrame with price history
            
        Returns:
            BacktestResults object with performance metrics
        """
        self.logger.info("Starting backtest...")
        
        # Reset state
        self.capital = self.initial_capital
        self.positions = []
        self.closed_trades = []
        self.daily_pnl = {}
        
        # Iterate through historical data
        for idx, row in historical_data.iterrows():
            timestamp = row['timestamp']
            symbol = row['symbol']
            exchange_price = row['exchange_price']
            polymarket_price = row['polymarket_price']
            
            # Check for exit conditions on existing positions
            self._check_exits(timestamp, polymarket_price)
            
            # Check for entry signals
            if len(self.positions) < self.max_positions:
                self._check_entry(
                    timestamp, symbol, exchange_price, polymarket_price
                )
        
        # Close any remaining positions at end of backtest
        for position in self.positions:
            self._close_position(
                position,
                historical_data.iloc[-1]['polymarket_price'],
                historical_data.iloc[-1]['timestamp'],
                'backtest_end'
            )
        
        # Calculate results
        results = self._calculate_results(
            historical_data['timestamp'].min(),
            historical_data['timestamp'].max()
        )
        
        self.logger.info(
            f"Backtest complete: {results.total_trades} trades, "
            f"Win rate: {results.win_rate:.1f}%, "
            f"Total P&L: ${results.total_pnl:.2f} ({results.total_pnl/self.initial_capital*100:.1f}%)"
        )
        
        return results
    
    def _check_entry(self, timestamp: datetime, symbol: str,
                    exchange_price: float, polymarket_price: float) -> None:
        """Check for entry signal and open position if detected."""
        # Calculate divergence (simplified)
        divergence = abs(exchange_price - polymarket_price) / exchange_price
        
        if divergence >= self.divergence_threshold:
            # Check if we have enough capital
            if self.capital >= self.position_size_usd:
                # Open position
                position = {
                    'symbol': symbol,
                    'entry_price': polymarket_price,
                    'entry_time': timestamp,
                    'size_usd': self.position_size_usd,
                    'direction': 'up' if exchange_price > polymarket_price else 'down'
                }
                
                self.positions.append(position)
                self.capital -= self.position_size_usd
                
                self.logger.debug(
                    f"Opened position: {symbol} @ {polymarket_price:.3f} "
                    f"(divergence: {divergence:.2%})"
                )
    
    def _check_exits(self, timestamp: datetime, current_price: float) -> None:
        """Check all positions for exit conditions."""
        positions_to_close = []
        
        for position in self.positions:
            entry_price = position['entry_price']
            pnl_pct = (current_price - entry_price) / entry_price
            
            exit_reason = None
            
            # Check stop loss
            if pnl_pct <= -self.stop_loss_pct:
                exit_reason = 'stop_loss'
            
            # Check take profit
            elif pnl_pct >= self.take_profit_pct:
                exit_reason = 'take_profit'
            
            # Check time-based exit (15-minute markets)
            hold_time = (timestamp - position['entry_time']).total_seconds()
            if hold_time >= 900:  # 15 minutes
                exit_reason = 'market_expiration'
            
            if exit_reason:
                positions_to_close.append((position, exit_reason))
        
        # Close positions
        for position, reason in positions_to_close:
            self._close_position(position, current_price, timestamp, reason)
    
    def _close_position(self, position: Dict, exit_price: float,
                       timestamp: datetime, reason: str) -> None:
        """Close a position and record the trade."""
        entry_price = position['entry_price']
        size = position['size_usd']
        
        # Calculate P&L
        pnl = (exit_price - entry_price) * size
        
        # Update capital
        self.capital += size + pnl
        
        # Record trade
        hold_time = (timestamp - position['entry_time']).total_seconds()
        
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol=position['symbol'],
            side='BUY',
            entry_price=entry_price,
            exit_price=exit_price,
            size_usd=size,
            pnl=pnl,
            hold_time_seconds=hold_time,
            exit_reason=reason
        )
        
        self.closed_trades.append(trade)
        
        # Update daily P&L
        date_key = timestamp.date().isoformat()
        self.daily_pnl[date_key] = self.daily_pnl.get(date_key, 0.0) + pnl
        
        # Remove from open positions
        self.positions.remove(position)
        
        self.logger.debug(
            f"Closed position: {position['symbol']} | P&L: ${pnl:.2f} | "
            f"Reason: {reason}"
        )
    
    def _calculate_results(self, start_date: datetime,
                          end_date: datetime) -> BacktestResults:
        """Calculate backtest performance metrics."""
        total_trades = len(self.closed_trades)
        
        if total_trades == 0:
            return BacktestResults(
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=self.capital,
                total_pnl=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_pnl_per_trade=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0
            )
        
        # Calculate metrics
        winning_trades = sum(1 for t in self.closed_trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.closed_trades if t.pnl <= 0)
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = sum(t.pnl for t in self.closed_trades)
        avg_pnl = total_pnl / total_trades
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        return BacktestResults(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_pnl=total_pnl,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_pnl_per_trade=avg_pnl,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=self.closed_trades,
            daily_pnl=self.daily_pnl
        )
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown during backtest."""
        if not self.closed_trades:
            return 0.0
        
        # Build equity curve
        equity = self.initial_capital
        peak = equity
        max_dd = 0.0
        
        for trade in self.closed_trades:
            equity += trade.pnl
            
            if equity > peak:
                peak = equity
            
            drawdown = (peak - equity) / peak
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio of returns."""
        if not self.closed_trades:
            return 0.0
        
        # Calculate daily returns
        if not self.daily_pnl:
            return 0.0
        
        returns = list(self.daily_pnl.values())
        
        if len(returns) < 2:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        std_return = (
            sum((r - avg_return) ** 2 for r in returns) / len(returns)
        ) ** 0.5
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe (assuming 252 trading days)
        sharpe = (avg_return / std_return) * (252 ** 0.5)
        
        return sharpe
    
    def save_results(self, results: BacktestResults, output_path: str) -> None:
        """
        Save backtest results to file.
        
        Args:
            results: BacktestResults object
            output_path: Path to save results JSON
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        
        self.logger.info(f"Saved backtest results to {output_path}")


def generate_sample_data(output_path: str, days: int = 30) -> None:
    """
    Generate sample historical data for backtesting.
    
    Args:
        output_path: Path to save CSV file
        days: Number of days of data to generate
    """
    import random
    
    data = []
    start_date = datetime.now() - timedelta(days=days)
    
    # Generate data points every minute
    for i in range(days * 24 * 60):
        timestamp = start_date + timedelta(minutes=i)
        
        # Simulate BTC price with random walk
        btc_price = 50000 + random.gauss(0, 1000)
        
        # Polymarket price lags and has noise
        pm_price = btc_price + random.gauss(0, 500)
        pm_odds = 0.5 + random.gauss(0, 0.15)
        pm_odds = max(0.01, min(0.99, pm_odds))
        
        data.append({
            'timestamp': timestamp,
            'symbol': 'BTC/USDT',
            'exchange_price': btc_price,
            'polymarket_price': pm_odds
        })
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} sample data points to {output_path}")
