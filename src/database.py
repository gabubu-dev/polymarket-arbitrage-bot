"""
Database persistence for paper trading positions.

Stores positions and trading history in SQLite for dashboard access.
"""

import sqlite3
import logging
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path


class TradingDatabase:
    """
    SQLite database for storing trading positions and history.
    
    Used by dashboard to display trading activity.
    """
    
    def __init__(self, db_path: str = "paper_trading.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.logger = logging.getLogger("TradingDatabase")
        self.db_path = db_path
        
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_schema()
        
        self.logger.info(f"Database initialized: {db_path}")
    
    def _init_schema(self) -> None:
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                position_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                market_id TEXT NOT NULL,
                side TEXT NOT NULL,
                direction TEXT NOT NULL,
                size_usd REAL NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL DEFAULT 0.0,
                exit_reason TEXT,
                status TEXT NOT NULL,
                order_id TEXT
            )
        """)
        
        # State table for bot statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Trading statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_pnl REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                open_positions INTEGER NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        self.logger.info("Database schema initialized")
    
    def save_position(self, position) -> bool:
        """
        Save or update a position in the database.
        
        Args:
            position: Position object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO positions (
                    position_id, symbol, market_id, side, direction,
                    size_usd, entry_price, entry_time, exit_price,
                    exit_time, pnl, exit_reason, status, order_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.position_id,
                position.symbol,
                position.market_id,
                position.side,
                position.direction,
                position.size_usd,
                position.entry_price,
                position.entry_time.isoformat(),
                position.exit_price,
                position.exit_time.isoformat() if position.exit_time else None,
                position.pnl,
                position.exit_reason,
                position.status.value,
                position.order_id
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Saved position: {position.position_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving position: {e}", exc_info=True)
            return False
    
    def get_position(self, position_id: str) -> Optional[Dict]:
        """
        Get a position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position dictionary or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM positions WHERE position_id = ?",
                (position_id,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting position: {e}", exc_info=True)
            return None
    
    def get_all_positions(self, status: Optional[str] = None) -> List[Dict]:
        """
        Get all positions, optionally filtered by status.
        
        Args:
            status: Filter by status ('open', 'closed', or None for all)
            
        Returns:
            List of position dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if status:
                cursor.execute(
                    "SELECT * FROM positions WHERE status = ? ORDER BY entry_time DESC",
                    (status,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM positions ORDER BY entry_time DESC"
                )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}", exc_info=True)
            return []
    
    def save_statistics(self, stats: Dict) -> bool:
        """
        Save trading statistics snapshot.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO statistics (
                    timestamp, total_pnl, total_trades, wins, losses,
                    win_rate, open_positions
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                stats.get('total_pnl', 0.0),
                stats.get('total_trades', 0),
                stats.get('wins', 0),
                stats.get('losses', 0),
                stats.get('win_rate', 0.0),
                stats.get('open_positions', 0)
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.debug("Saved statistics snapshot")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving statistics: {e}", exc_info=True)
            return False
    
    def get_latest_statistics(self) -> Optional[Dict]:
        """
        Get the most recent statistics snapshot.
        
        Returns:
            Statistics dictionary or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM statistics ORDER BY timestamp DESC LIMIT 1"
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}", exc_info=True)
            return None
    
    def set_state(self, key: str, value: str) -> bool:
        """
        Set a state value.
        
        Args:
            key: State key
            value: State value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting state: {e}", exc_info=True)
            return False
    
    def get_state(self, key: str) -> Optional[str]:
        """
        Get a state value.
        
        Args:
            key: State key
            
        Returns:
            State value or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM state WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting state: {e}", exc_info=True)
            return None
