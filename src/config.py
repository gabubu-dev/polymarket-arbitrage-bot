"""
Configuration management for the arbitrage bot.

Loads and validates configuration from JSON file or environment variables.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class PolymarketConfig:
    """Polymarket API configuration."""
    api_key: str = ""
    api_secret: str = ""
    private_key: str = ""
    chain_id: int = 137


@dataclass
class ExchangeConfig:
    """Exchange API configuration."""
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = False


@dataclass
class TradingConfig:
    """Trading parameters."""
    divergence_threshold: float = 0.05
    min_profit_threshold: float = 0.02
    position_size_usd: float = 100.0
    max_positions: int = 5
    max_position_size_usd: float = 500.0


@dataclass
class MarketsConfig:
    """Market monitoring configuration."""
    enabled_symbols: list[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    polymarket_market_types: list[str] = field(default_factory=lambda: ["15MIN_UP", "15MIN_DOWN"])
    refresh_interval_seconds: int = 5


@dataclass
class RiskManagementConfig:
    """Risk management parameters."""
    stop_loss_percentage: float = 0.15
    take_profit_percentage: float = 0.90
    max_daily_loss_usd: float = 1000.0
    emergency_shutdown_loss_usd: float = 5000.0


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    log_file: str = "logs/bot.log"
    log_trades: bool = True


@dataclass
class NotificationsConfig:
    """Notification settings."""
    enabled: bool = False
    webhook_url: str = ""


class Config:
    """
    Main configuration class.
    
    Loads configuration from JSON file and provides structured access
    to all bot settings.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = Path(config_path)
        self._raw_config: Dict[str, Any] = {}
        
        # Configuration objects
        self.polymarket = PolymarketConfig()
        self.exchanges: Dict[str, ExchangeConfig] = {}
        self.trading = TradingConfig()
        self.markets = MarketsConfig()
        self.risk_management = RiskManagementConfig()
        self.logging = LoggingConfig()
        self.notifications = NotificationsConfig()
        
        self.load()
    
    def load(self) -> None:
        """Load configuration from file or environment variables."""
        if self.config_path.exists():
            self._load_from_file()
        else:
            self._load_from_env()
        
        self._validate()
    
    def _load_from_file(self) -> None:
        """Load configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            self._raw_config = json.load(f)
        
        # Parse Polymarket config
        if 'polymarket' in self._raw_config:
            pm = self._raw_config['polymarket']
            self.polymarket = PolymarketConfig(**pm)
        
        # Parse exchange configs
        if 'exchanges' in self._raw_config:
            for exchange_name, exchange_data in self._raw_config['exchanges'].items():
                self.exchanges[exchange_name] = ExchangeConfig(**exchange_data)
        
        # Parse trading config
        if 'trading' in self._raw_config:
            self.trading = TradingConfig(**self._raw_config['trading'])
        
        # Parse markets config
        if 'markets' in self._raw_config:
            self.markets = MarketsConfig(**self._raw_config['markets'])
        
        # Parse risk management config
        if 'risk_management' in self._raw_config:
            self.risk_management = RiskManagementConfig(**self._raw_config['risk_management'])
        
        # Parse logging config
        if 'logging' in self._raw_config:
            self.logging = LoggingConfig(**self._raw_config['logging'])
        
        # Parse notifications config
        if 'notifications' in self._raw_config:
            self.notifications = NotificationsConfig(**self._raw_config['notifications'])
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Polymarket
        self.polymarket.api_key = os.getenv('POLYMARKET_API_KEY', '')
        self.polymarket.api_secret = os.getenv('POLYMARKET_API_SECRET', '')
        self.polymarket.private_key = os.getenv('POLYMARKET_PRIVATE_KEY', '')
        
        # Exchanges - Binance
        if os.getenv('BINANCE_API_KEY'):
            self.exchanges['binance'] = ExchangeConfig(
                api_key=os.getenv('BINANCE_API_KEY', ''),
                api_secret=os.getenv('BINANCE_API_SECRET', ''),
                testnet=os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
            )
        
        # Trading parameters from env
        if os.getenv('DIVERGENCE_THRESHOLD'):
            self.trading.divergence_threshold = float(os.getenv('DIVERGENCE_THRESHOLD'))
    
    def _validate(self) -> None:
        """Validate configuration values."""
        if self.trading.divergence_threshold <= 0 or self.trading.divergence_threshold >= 1:
            raise ValueError("divergence_threshold must be between 0 and 1")
        
        if self.trading.position_size_usd <= 0:
            raise ValueError("position_size_usd must be positive")
        
        if self.risk_management.stop_loss_percentage <= 0 or self.risk_management.stop_loss_percentage >= 1:
            raise ValueError("stop_loss_percentage must be between 0 and 1")
        
        if not self.markets.enabled_symbols:
            raise ValueError("At least one symbol must be enabled")
    
    def get_exchange_config(self, exchange_name: str) -> Optional[ExchangeConfig]:
        """
        Get configuration for a specific exchange.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            ExchangeConfig if found, None otherwise
        """
        return self.exchanges.get(exchange_name)
