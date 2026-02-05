"""
Paper Trader - Paper trading simulation engine
Tracks virtual USDC balance, mirrors trades, calculates virtual PnL
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a virtual trading position"""
    market_id: str
    outcome: str  # YES or NO
    entry_price: float
    shares: float
    side: str  # LONG or SHORT
    opened_at: datetime
    trade_id: str
    
    # Runtime tracking
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    
    def update_price(self, new_price: float):
        """Update position with current market price"""
        self.current_price = new_price
        
        if self.side == "LONG":
            self.unrealized_pnl = (new_price - self.entry_price) * self.shares
            self.unrealized_pnl_percent = ((new_price / self.entry_price) - 1) * 100 if self.entry_price > 0 else 0
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - new_price) * self.shares
            self.unrealized_pnl_percent = ((self.entry_price / new_price) - 1) * 100 if new_price > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_id": self.market_id,
            "outcome": self.outcome,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "shares": self.shares,
            "side": self.side,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "opened_at": self.opened_at.isoformat(),
            "trade_id": self.trade_id
        }


@dataclass
class TradeRecord:
    """Record of a paper trade"""
    id: str
    timestamp: datetime
    original_wallet: str
    market_id: str
    outcome: str
    side: str  # BUY or SELL
    shares: float
    price: float
    amount: float
    fees: float
    slippage: float
    total_cost: float
    
    # PnL tracking (for closed positions)
    realized_pnl: Optional[float] = None
    realized_pnl_percent: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "original_wallet": self.original_wallet,
            "market_id": self.market_id,
            "outcome": self.outcome,
            "side": self.side,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "fees": self.fees,
            "slippage": self.slippage,
            "total_cost": self.total_cost,
            "realized_pnl": self.realized_pnl,
            "realized_pnl_percent": self.realized_pnl_percent
        }


class PaperTrader:
    """Paper trading simulation engine"""
    
    # Polymarket fees (approximate)
    TAKER_FEE_RATE = 0.002  # 0.2% taker fee
    
    def __init__(self, config: Dict[str, Any], db_path: str = "paper_trading.db"):
        self.config = config
        self.db_path = db_path
        
        # Paper trading settings
        paper_config = config.get("paper_trading", {})
        self.initial_balance = paper_config.get("initial_balance_usdc", 10000.0)
        self.slippage_min = paper_config.get("slippage_min", 0.005)
        self.slippage_max = paper_config.get("slippage_max", 0.01)
        self.gas_cost_gwei = paper_config.get("gas_cost_gwei", 50)
        self.gas_limit = paper_config.get("gas_limit", 200000)
        
        # State
        self.balance: float = self.initial_balance
        self.positions: Dict[str, Position] = {}  # key = market_id:outcome
        self.trade_history: List[TradeRecord] = []
        self.daily_stats: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_db()
        
        # Load state
        self._load_state()
        
        logger.info(f"PaperTrader initialized with balance: ${self.balance:.2f} USDC")
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                original_wallet TEXT NOT NULL,
                market_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                side TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                fees REAL NOT NULL,
                slippage REAL NOT NULL,
                total_cost REAL NOT NULL,
                realized_pnl REAL,
                realized_pnl_percent REAL
            )
        """)
        
        # Positions table (for current open positions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                market_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                entry_price REAL NOT NULL,
                shares REAL NOT NULL,
                side TEXT NOT NULL,
                opened_at TEXT NOT NULL,
                trade_id TEXT NOT NULL,
                PRIMARY KEY (market_id, outcome)
            )
        """)
        
        # Balance history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS balance_history (
                timestamp TEXT PRIMARY KEY,
                balance REAL NOT NULL,
                total_positions_value REAL NOT NULL,
                total_equity REAL NOT NULL
            )
        """)
        
        # State table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _load_state(self):
        """Load state from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load balance
        cursor.execute("SELECT value FROM state WHERE key = 'balance'")
        row = cursor.fetchone()
        if row:
            self.balance = float(row[0])
        
        # Load positions
        cursor.execute("SELECT * FROM positions")
        for row in cursor.fetchall():
            position = Position(
                market_id=row[0],
                outcome=row[1],
                entry_price=row[2],
                shares=row[3],
                side=row[4],
                opened_at=datetime.fromisoformat(row[5]),
                trade_id=row[6]
            )
            key = f"{position.market_id}:{position.outcome}"
            self.positions[key] = position
        
        # Load recent trade history (last 1000)
        cursor.execute("""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT 1000
        """)
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            trade_dict = dict(zip(columns, row))
            trade = TradeRecord(
                id=trade_dict["id"],
                timestamp=datetime.fromisoformat(trade_dict["timestamp"]),
                original_wallet=trade_dict["original_wallet"],
                market_id=trade_dict["market_id"],
                outcome=trade_dict["outcome"],
                side=trade_dict["side"],
                shares=trade_dict["shares"],
                price=trade_dict["price"],
                amount=trade_dict["amount"],
                fees=trade_dict["fees"],
                slippage=trade_dict["slippage"],
                total_cost=trade_dict["total_cost"],
                realized_pnl=trade_dict.get("realized_pnl"),
                realized_pnl_percent=trade_dict.get("realized_pnl_percent")
            )
            self.trade_history.append(trade)
        
        conn.close()
        logger.info(f"Loaded state: balance=${self.balance:.2f}, positions={len(self.positions)}")
    
    def _save_state(self):
        """Save current state to database"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Save balance
            cursor.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                ("balance", str(self.balance))
            )
            
            # Save positions
            cursor.execute("DELETE FROM positions")
            for position in self.positions.values():
                cursor.execute("""
                    INSERT INTO positions 
                    (market_id, outcome, entry_price, shares, side, opened_at, trade_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    position.market_id,
                    position.outcome,
                    position.entry_price,
                    position.shares,
                    position.side,
                    position.opened_at.isoformat(),
                    position.trade_id
                ))
            
            conn.commit()
            conn.close()
    
    def execute_trade(
        self,
        original_wallet: str,
        market_id: str,
        outcome: str,
        side: str,  # BUY or SELL
        shares: float,
        price: float,
        trade_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[TradeRecord]]:
        """
        Execute a paper trade
        
        Returns: (success, message, trade_record)
        """
        with self._lock:
            # Generate trade ID
            if trade_id is None:
                trade_id = f"{datetime.utcnow().timestamp()}_{market_id[:8]}"
            
            # Calculate costs
            import random
            slippage = random.uniform(self.slippage_min, self.slippage_max)
            
            if side == "BUY":
                executed_price = price * (1 + slippage)
            else:
                executed_price = price * (1 - slippage)
            
            amount = shares * executed_price
            fees = amount * self.TAKER_FEE_RATE
            
            # Gas cost (simulated in USDC equivalent)
            # Assuming MATIC price ~$0.50 and gas costs
            gas_cost_matic = (self.gas_cost_gwei * 1e-9) * self.gas_limit
            gas_cost_usdc = gas_cost_matic * 0.50  # Approximate MATIC price
            
            total_cost = amount + fees + gas_cost_usdc
            
            position_key = f"{market_id}:{outcome}"
            
            if side == "BUY":
                # Check balance
                if total_cost > self.balance:
                    return False, f"Insufficient balance: ${self.balance:.2f} < ${total_cost:.2f}", None
                
                # Update or create position
                if position_key in self.positions:
                    # Add to existing position (average down/up)
                    pos = self.positions[position_key]
                    total_shares = pos.shares + shares
                    avg_price = ((pos.entry_price * pos.shares) + (executed_price * shares)) / total_shares
                    pos.entry_price = avg_price
                    pos.shares = total_shares
                else:
                    # Create new position
                    self.positions[position_key] = Position(
                        market_id=market_id,
                        outcome=outcome,
                        entry_price=executed_price,
                        shares=shares,
                        side="LONG",
                        opened_at=datetime.utcnow(),
                        trade_id=trade_id
                    )
                
                # Deduct from balance
                self.balance -= total_cost
                
            else:  # SELL
                # Check if we have position to sell
                if position_key not in self.positions:
                    return False, f"No position to sell for {market_id}:{outcome}", None
                
                pos = self.positions[position_key]
                
                if shares > pos.shares:
                    return False, f"Insufficient shares: {pos.shares:.4f} < {shares:.4f}", None
                
                # Calculate realized PnL
                if pos.side == "LONG":
                    realized_pnl = (executed_price - pos.entry_price) * shares - fees - gas_cost_usdc
                    realized_pnl_percent = ((executed_price / pos.entry_price) - 1) * 100
                else:
                    realized_pnl = (pos.entry_price - executed_price) * shares - fees - gas_cost_usdc
                    realized_pnl_percent = ((pos.entry_price / executed_price) - 1) * 100
                
                # Update or remove position
                if shares >= pos.shares * 0.999:  # Allow for small floating point errors
                    del self.positions[position_key]
                else:
                    pos.shares -= shares
                
                # Add proceeds to balance (minus fees)
                self.balance += (amount - fees - gas_cost_usdc)
            
            # Create trade record
            trade = TradeRecord(
                id=trade_id,
                timestamp=datetime.utcnow(),
                original_wallet=original_wallet,
                market_id=market_id,
                outcome=outcome,
                side=side,
                shares=shares,
                price=executed_price,
                amount=amount,
                fees=fees,
                slippage=slippage,
                total_cost=total_cost,
                realized_pnl=realized_pnl if side == "SELL" else None,
                realized_pnl_percent=realized_pnl_percent if side == "SELL" else None
            )
            
            # Save to history
            self.trade_history.insert(0, trade)
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades 
                (id, timestamp, original_wallet, market_id, outcome, side, shares, price, amount, fees, slippage, total_cost, realized_pnl, realized_pnl_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id, trade.timestamp.isoformat(), trade.original_wallet,
                trade.market_id, trade.outcome, trade.side, trade.shares,
                trade.price, trade.amount, trade.fees, trade.slippage,
                trade.total_cost, trade.realized_pnl, trade.realized_pnl_percent
            ))
            conn.commit()
            conn.close()
            
            # Save state
            self._save_state()
            
            logger.info(f"Paper trade executed: {side} {shares:.4f} {outcome} @ ${executed_price:.4f} (PnL: ${realized_pnl:.2f})" if side == "SELL" else 
                       f"Paper trade executed: {side} {shares:.4f} {outcome} @ ${executed_price:.4f}")
            
            return True, "Trade executed successfully", trade
    
    def update_position_prices(self, market_prices: Dict[str, float]):
        """Update position prices with current market data"""
        with self._lock:
            for key, position in self.positions.items():
                if position.market_id in market_prices:
                    position.update_price(market_prices[position.market_id])
    
    def get_portfolio_value(self) -> Dict[str, float]:
        """Get current portfolio value breakdown"""
        with self._lock:
            positions_value = sum(
                pos.shares * pos.current_price if pos.current_price > 0 
                else pos.shares * pos.entry_price 
                for pos in self.positions.values()
            )
            
            total_equity = self.balance + positions_value
            
            return {
                "balance": self.balance,
                "positions_value": positions_value,
                "total_equity": total_equity,
                "total_pnl": total_equity - self.initial_balance,
                "total_pnl_percent": ((total_equity / self.initial_balance) - 1) * 100
            }
    
    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        with self._lock:
            return list(self.positions.values())
    
    def get_position(self, market_id: str, outcome: str) -> Optional[Position]:
        """Get a specific position"""
        key = f"{market_id}:{outcome}"
        return self.positions.get(key)
    
    def get_trade_history(
        self, 
        limit: int = 100, 
        offset: int = 0,
        market_id: Optional[str] = None
    ) -> List[TradeRecord]:
        """Get trade history"""
        with self._lock:
            trades = self.trade_history
            if market_id:
                trades = [t for t in trades if t.market_id == market_id]
            return trades[offset:offset + limit]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            portfolio = self.get_portfolio_value()
            
            # Calculate win rate
            closed_trades = [t for t in self.trade_history if t.realized_pnl is not None]
            if closed_trades:
                winning_trades = [t for t in closed_trades if t.realized_pnl and t.realized_pnl > 0]
                win_rate = len(winning_trades) / len(closed_trades) * 100
                avg_pnl = sum(t.realized_pnl or 0 for t in closed_trades) / len(closed_trades)
            else:
                win_rate = 0
                avg_pnl = 0
            
            # Daily PnL
            today = datetime.utcnow().date().isoformat()
            today_trades = [
                t for t in self.trade_history 
                if t.timestamp.date().isoformat() == today and t.realized_pnl is not None
            ]
            daily_pnl = sum(t.realized_pnl or 0 for t in today_trades)
            
            return {
                "initial_balance": self.initial_balance,
                "current_balance": self.balance,
                "total_equity": portfolio["total_equity"],
                "total_pnl": portfolio["total_pnl"],
                "total_pnl_percent": portfolio["total_pnl_percent"],
                "open_positions": len(self.positions),
                "total_trades": len(self.trade_history),
                "closed_trades": len(closed_trades),
                "win_rate_percent": win_rate,
                "average_trade_pnl": avg_pnl,
                "daily_pnl": daily_pnl
            }
    
    def get_portfolio_stats(self) -> Dict[str, Any]:
        """Get portfolio statistics (alias for compatibility with main.py)"""
        stats = self.get_performance_stats()
        portfolio = self.get_portfolio_value()
        
        # Map to expected format
        return {
            "total_value": portfolio["total_equity"],
            "total_pnl": stats["total_pnl"],
            "roi_percent": stats["total_pnl_percent"],
            "win_rate_percent": stats["win_rate_percent"],
            "total_trades": stats["total_trades"],
            "open_positions": stats["open_positions"],
            "closed_trades": stats["closed_trades"],
            "current_balance": stats["current_balance"],
            "daily_pnl": stats["daily_pnl"]
        }
    
    def reset(self, confirm: bool = False):
        """Reset paper trading account"""
        if not confirm:
            logger.warning("Reset not confirmed. Pass confirm=True to reset.")
            return
        
        with self._lock:
            self.balance = self.initial_balance
            self.positions.clear()
            self.trade_history.clear()
            
            # Clear database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trades")
            cursor.execute("DELETE FROM positions")
            cursor.execute("DELETE FROM state")
            conn.commit()
            conn.close()
            
            logger.info("Paper trading account reset")
    
    def export_data(self, filepath: str, format: str = "json"):
        """Export trading data to file"""
        with self._lock:
            data = {
                "stats": self.get_performance_stats(),
                "positions": [p.to_dict() for p in self.positions.values()],
                "trades": [t.to_dict() for t in self.trade_history]
            }
            
            if format == "json":
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                # CSV export for trades
                import csv
                with open(filepath, 'w', newline='') as f:
                    if self.trade_history:
                        writer = csv.DictWriter(f, fieldnames=self.trade_history[0].to_dict().keys())
                        writer.writeheader()
                        for trade in self.trade_history:
                            writer.writerow(trade.to_dict())
            
            logger.info(f"Data exported to {filepath}")
