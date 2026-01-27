"""
Logging configuration for the arbitrage bot.

Provides colored console output and file logging with proper formatting.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import colorlog


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Set up a logger with colored console output and optional file logging.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console: Whether to log to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()
    
    # Console handler with colors
    if console:
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        console_format = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    # File handler without colors
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


class TradeLogger:
    """
    Specialized logger for trade events.
    
    Logs all trade activity to a separate file for analysis and auditing.
    """
    
    def __init__(self, log_file: str = "logs/trades.log"):
        """
        Initialize trade logger.
        
        Args:
            log_file: Path to trade log file
        """
        self.logger = setup_logger(
            "TradeLogger",
            level="INFO",
            log_file=log_file,
            console=False
        )
    
    def log_opportunity(self, symbol: str, exchange_price: float, 
                       polymarket_price: float, divergence: float) -> None:
        """
        Log detected arbitrage opportunity.
        
        Args:
            symbol: Trading symbol
            exchange_price: Current exchange price
            polymarket_price: Current Polymarket price
            divergence: Price divergence percentage
        """
        self.logger.info(
            f"OPPORTUNITY | {symbol} | Exchange: ${exchange_price:.2f} | "
            f"Polymarket: ${polymarket_price:.2f} | Divergence: {divergence:.2%}"
        )
    
    def log_entry(self, symbol: str, side: str, size: float, 
                  price: float, market_id: str) -> None:
        """
        Log trade entry.
        
        Args:
            symbol: Trading symbol
            side: Trade side (BUY/SELL)
            size: Position size in USD
            price: Entry price
            market_id: Polymarket market ID
        """
        self.logger.info(
            f"ENTRY | {symbol} | {side} | Size: ${size:.2f} | "
            f"Price: ${price:.2f} | Market: {market_id}"
        )
    
    def log_exit(self, symbol: str, pnl: float, hold_time_seconds: int, 
                 exit_reason: str) -> None:
        """
        Log trade exit.
        
        Args:
            symbol: Trading symbol
            pnl: Profit/loss in USD
            hold_time_seconds: Time position was held
            exit_reason: Reason for exit (take_profit, stop_loss, market_close, etc.)
        """
        self.logger.info(
            f"EXIT | {symbol} | PnL: ${pnl:.2f} | "
            f"Hold: {hold_time_seconds}s | Reason: {exit_reason}"
        )
    
    def log_error(self, error_type: str, message: str) -> None:
        """
        Log trade execution error.
        
        Args:
            error_type: Type of error
            message: Error message
        """
        self.logger.error(f"ERROR | {error_type} | {message}")
