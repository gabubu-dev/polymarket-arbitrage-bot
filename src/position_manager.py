"""
Position management and trade execution.

Manages open positions, executes trades, and tracks performance.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


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
                 position_size_usd: float = 100.0):
        """
        Initialize position manager.
        
        Args:
            polymarket_client: PolymarketClient instance
            max_positions: Maximum concurrent positions
            position_size_usd: Default position size in USD
        """
        self.logger = logging.getLogger("PositionManager")
        self.polymarket = polymarket_client
        self.max_positions = max_positions
        self.position_size_usd = position_size_usd
        
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
        
        # Calculate P&L
        # For prediction markets: profit = (exit_price - entry_price) * size
        # If we bought at 0.60 and exit at 1.00, we profit 0.40 per share
        pnl = (exit_price - position.entry_price) * position.size_usd
        
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
        
        hold_time = (position.exit_time - position.entry_time).total_seconds()
        
        self.logger.info(
            f"Closed position: {position.symbol} | P&L: ${pnl:.2f} | "
            f"Hold time: {hold_time:.0f}s | Reason: {reason}"
        )
        
        return True
    
    async def check_position_exits(self, risk_manager) -> None:
        """
        Check all open positions for exit conditions.
        
        Args:
            risk_manager: RiskManager instance to check exit rules
        """
        for position_id, position in list(self.positions.items()):
            # Check if position should be closed
            should_exit, exit_price, reason = await risk_manager.should_exit_position(position)
            
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
        
        return {
            'total_pnl': self.total_pnl,
            'total_trades': total_trades,
            'wins': self.win_count,
            'losses': self.loss_count,
            'win_rate': win_rate,
            'open_positions': len(self.positions),
            'avg_pnl_per_trade': self.total_pnl / total_trades if total_trades > 0 else 0
        }
