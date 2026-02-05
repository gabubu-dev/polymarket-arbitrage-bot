"""
Position management and trade execution.

Manages open positions, executes trades, and tracks performance.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from database import TradingDatabase


class PositionStatus(Enum):
    """Position status enum."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


@dataclass
class Position:
    """
    Represents an open trading position.
    """
    position_id: str
    symbol: str
    market_id: str
    side: str  # 'BUY' or 'SELL'
    direction: str  # 'up' or 'down'
    size_usd: float
    entry_price: float
    entry_time: datetime
    status: PositionStatus = PositionStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    exit_reason: Optional[str] = None
    order_id: Optional[str] = None


class PositionManager:
    """
    Manages trading positions and executes trades.
    
    Handles position entry, exit, and P&L tracking.
    """
    
    def __init__(self, polymarket_client, max_positions: int = 5,
                 position_size_usd: float = 100.0, db_path: str = "paper_trading.db"):
        """
        Initialize position manager.
        
        Args:
            polymarket_client: PolymarketClient instance
            max_positions: Maximum concurrent positions
            position_size_usd: Default position size in USD
            db_path: Path to SQLite database
        """
        self.logger = logging.getLogger("PositionManager")
        self.polymarket = polymarket_client
        self.max_positions = max_positions
        self.position_size_usd = position_size_usd
        
        # Initialize database
        self.db = TradingDatabase(db_path)
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        
        # Performance metrics
        self.total_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
    
    async def open_position(self, opportunity) -> Optional[Position]:
        """
        Open a new position based on an arbitrage opportunity.
        
        Args:
            opportunity: ArbitrageOpportunity to trade
            
        Returns:
            Position object if successful, None otherwise
        """
        # Check if we can open more positions
        if len(self.get_open_positions()) >= self.max_positions:
            self.logger.warning(
                f"Cannot open position: max positions ({self.max_positions}) reached"
            )
            return None
        
        # Determine trade parameters
        side = "BUY"  # We're buying YES or NO shares
        price = opportunity.polymarket_odds
        
        # Place order on Polymarket
        order_id = await self.polymarket.place_order(
            market_id=opportunity.polymarket_market_id,
            side=side,
            size=self.position_size_usd,
            price=price
        )
        
        if not order_id:
            self.logger.error("Failed to place order")
            return None
        
        # Create position
        position_id = f"{opportunity.symbol}_{opportunity.direction}_{datetime.now().timestamp()}"
        
        position = Position(
            position_id=position_id,
            symbol=opportunity.symbol,
            market_id=opportunity.polymarket_market_id,
            side=side,
            direction=opportunity.direction,
            size_usd=self.position_size_usd,
            entry_price=price,
            entry_time=datetime.now(),
            order_id=order_id
        )
        
        self.positions[position_id] = position
        
        # Save to database
        self.db.save_position(position)
        
        self.logger.info(
            f"Opened position: {position.symbol} {position.direction} @ {price:.3f} "
            f"(size: ${self.position_size_usd})"
        )
        
        return position
    
    async def close_position(self, position_id: str, 
                            exit_price: float,
                            reason: str = "manual") -> bool:
        """
        Close an open position.
        
        Args:
            position_id: Position to close
            exit_price: Exit price
            reason: Reason for closing
            
        Returns:
            True if successful, False otherwise
        """
        position = self.positions.get(position_id)
        
        if not position:
            self.logger.error(f"Position {position_id} not found")
            return False
        
        if position.status != PositionStatus.OPEN:
            self.logger.warning(f"Position {position_id} is not open")
            return False
        
        # Calculate P&L for prediction markets
        # When you buy at odds 0.30 with $50, you get 50/0.30 = 166.67 shares
        # If you sell at 0.40, profit = 166.67 * (0.40 - 0.30) = $16.67
        # Formula: pnl = size_usd * ((exit_price - entry_price) / entry_price)
        
        if position.entry_price > 0:
            shares = position.size_usd / position.entry_price
            pnl = shares * (exit_price - position.entry_price)
        else:
            # Fallback if entry price is somehow 0
            pnl = 0.0
            self.logger.error(f"Position {position_id} has entry_price = 0!")
        
        # Update position
        position.exit_price = exit_price
        position.exit_time = datetime.now()
        position.pnl = pnl
        position.exit_reason = reason
        position.status = PositionStatus.CLOSED
        
        # Update metrics
        self.total_pnl += pnl
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        # Move to closed positions
        self.closed_positions.append(position)
        del self.positions[position_id]
        
        # Save to database
        self.db.save_position(position)
        
        hold_time = (position.exit_time - position.entry_time).total_seconds()
        
        self.logger.info(
            f"Closed position: {position.symbol} | P&L: ${pnl:.2f} | "
            f"Hold time: {hold_time:.0f}s | Reason: {reason}"
        )
        
        return True
    
    async def check_position_exits(self, risk_manager, exchange_monitor=None) -> None:
        """
        Check all open positions for exit conditions.
        
        Args:
            risk_manager: RiskManager instance to check exit rules
            exchange_monitor: Exchange monitor to get current prices
        """
        for position_id, position in list(self.positions.items()):
            # Get current Polymarket odds (not exchange price!)
            current_odds = None
            try:
                odds = self.polymarket.get_market_odds(position.market_id)
                # Use appropriate odds based on position direction
                if position.direction == 'up':
                    current_odds = odds.get('yes', position.entry_price)
                else:
                    current_odds = odds.get('no', position.entry_price)
            except Exception as e:
                self.logger.error(f"Failed to get current odds for {position.market_id}: {e}")
                # Fallback to entry price if can't get current odds
                current_odds = position.entry_price
            
            # Check if position should be closed
            should_exit, exit_price, reason = await risk_manager.should_exit_position(
                position, current_price=current_odds
            )
            
            if should_exit:
                await self.close_position(position_id, exit_price, reason)
    
    def get_open_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of open Position objects
        """
        return list(self.positions.values())
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """
        Get specific position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position object or None
        """
        return self.positions.get(position_id)
    
    def get_performance_stats(self) -> Dict[str, any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        stats = {
            'total_pnl': self.total_pnl,
            'total_trades': total_trades,
            'wins': self.win_count,
            'losses': self.loss_count,
            'win_rate': win_rate,
            'open_positions': len(self.positions),
            'avg_pnl_per_trade': self.total_pnl / total_trades if total_trades > 0 else 0
        }
        
        # Save to database
        self.db.save_statistics(stats)
        
        return stats
