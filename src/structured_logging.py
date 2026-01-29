"""
Structured logging with JSON format for easy parsing and analysis.

Provides enhanced logging with metrics, context, and JSON output.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar
import colorlog

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON structured logs.
    
    Output format:
    {
        "timestamp": "2024-01-15T10:30:00.123456",
        "level": "INFO",
        "logger": "bot",
        "message": "Bot started",
        "module": "bot",
        "function": "start",
        "line": 42,
        "request_id": "req-123",
        "correlation_id": "corr-456",
        "extra": { ... }
    }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process,
        }
        
        # Add context variables
        req_id = request_id.get()
        if req_id:
            log_data['request_id'] = req_id
        
        corr_id = correlation_id.get()
        if corr_id:
            log_data['correlation_id'] = corr_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        extra_fields = [
            'symbol', 'market_id', 'exchange', 'direction', 'price',
            'pnl', 'divergence', 'latency_ms', 'api_call', 'cache_hit',
            'position_id', 'trade_id', 'strategy', 'metrics'
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        # Add any custom extra data
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    Structured logger with context and metrics support.
    
    Provides convenient methods for logging with structured data
    and automatic context injection.
    """
    
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self._logger = logger
    
    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Internal log method with extra handling."""
        # Merge extra dict with kwargs
        all_extra = {**(extra or {}), **kwargs}
        
        # Create LogRecord with extra fields
        if all_extra:
            self._logger.log(level, message, extra=all_extra)
        else:
            self._logger.log(level, message)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with full traceback."""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def log_opportunity(
        self,
        symbol: str,
        exchange: str,
        exchange_price: float,
        polymarket_odds: float,
        divergence: float,
        direction: str,
        expected_profit: float,
        confidence: float
    ) -> None:
        """Log arbitrage opportunity detection."""
        self.info(
            f"Arbitrage opportunity detected: {symbol} {direction}",
            symbol=symbol,
            exchange=exchange,
            exchange_price=exchange_price,
            polymarket_odds=polymarket_odds,
            divergence=divergence,
            direction=direction,
            expected_profit=expected_profit,
            confidence=confidence,
            event_type='opportunity_detected'
        )
    
    def log_trade_entry(
        self,
        symbol: str,
        market_id: str,
        side: str,
        direction: str,
        size_usd: float,
        entry_price: float,
        position_id: str,
        strategy: str = "spike"
    ) -> None:
        """Log trade entry."""
        self.info(
            f"Trade entry: {symbol} {side} @ {entry_price:.4f}",
            symbol=symbol,
            market_id=market_id,
            side=side,
            direction=direction,
            size_usd=size_usd,
            entry_price=entry_price,
            position_id=position_id,
            strategy=strategy,
            event_type='trade_entry'
        )
    
    def log_trade_exit(
        self,
        symbol: str,
        position_id: str,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        hold_time_seconds: float,
        exit_reason: str
    ) -> None:
        """Log trade exit."""
        self.info(
            f"Trade exit: {symbol} P&L=${pnl:.2f} ({pnl_pct:.2%})",
            symbol=symbol,
            position_id=position_id,
            exit_price=exit_price,
            pnl=pnl,
            pnl_pct=pnl_pct,
            hold_time_seconds=hold_time_seconds,
            exit_reason=exit_reason,
            event_type='trade_exit'
        )
    
    def log_api_call(
        self,
        api_name: str,
        endpoint: str,
        latency_ms: float,
        success: bool,
        cache_hit: bool = False,
        error: Optional[str] = None
    ) -> None:
        """Log API call metrics."""
        self.debug(
            f"API call: {api_name}.{endpoint} ({latency_ms:.1f}ms)",
            api_call=f"{api_name}.{endpoint}",
            latency_ms=latency_ms,
            success=success,
            cache_hit=cache_hit,
            error=error,
            event_type='api_call'
        )
    
    def log_metrics(self, metrics: Dict[str, Any], **context) -> None:
        """Log performance metrics."""
        self.info(
            "Performance metrics",
            metrics=metrics,
            event_type='metrics',
            **context
        )


def setup_structured_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_file: Optional[str] = None,
    console: bool = True
) -> StructuredLogger:
    """
    Set up a structured logger with console and file handlers.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional plain text log file path
        json_file: Optional JSON structured log file path
        console: Whether to log to console
        
    Returns:
        StructuredLogger instance
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
    
    # Plain text file handler
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
    
    # JSON structured log handler
    if json_file:
        json_path = Path(json_file)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_handler = logging.FileHandler(json_file)
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
    
    return StructuredLogger(name, logger)


class TradeLogger:
    """
    Specialized logger for trade events.
    
    Logs all trade activity to a separate file for analysis and auditing.
    """
    
    def __init__(
        self,
        log_file: str = "logs/trades.log",
        json_file: str = "logs/trades.json"
    ):
        """
        Initialize trade logger.
        
        Args:
            log_file: Path to plain text trade log
            json_file: Path to JSON structured trade log
        """
        self.logger = setup_structured_logger(
            "TradeLogger",
            level="INFO",
            log_file=log_file,
            json_file=json_file,
            console=False
        )
    
    def log_opportunity(self, **kwargs) -> None:
        """Log detected arbitrage opportunity."""
        self.logger.log_opportunity(**kwargs)
    
    def log_entry(self, **kwargs) -> None:
        """Log trade entry."""
        self.logger.log_trade_entry(**kwargs)
    
    def log_exit(self, **kwargs) -> None:
        """Log trade exit."""
        self.logger.log_trade_exit(**kwargs)
    
    def log_error(self, error_type: str, message: str, **kwargs) -> None:
        """Log trade execution error."""
        self.logger.error(
            f"Trade error: {error_type} - {message}",
            error_type=error_type,
            event_type='trade_error',
            **kwargs
        )


def set_request_id(req_id: str) -> None:
    """Set request ID for current context."""
    request_id.set(req_id)


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id.set(corr_id)


def clear_context() -> None:
    """Clear all context variables."""
    request_id.set(None)
    correlation_id.set(None)
