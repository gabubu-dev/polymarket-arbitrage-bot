"""
Tests for configuration management.
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config, TradingConfig


def test_trading_config_defaults():
    """Test TradingConfig default values."""
    config = TradingConfig()
    
    assert config.divergence_threshold == 0.05
    assert config.min_profit_threshold == 0.02
    assert config.position_size_usd == 100.0
    assert config.max_positions == 5


def test_config_load_from_file():
    """Test loading configuration from JSON file."""
    test_config = {
        "trading": {
            "divergence_threshold": 0.08,
            "position_size_usd": 200.0
        },
        "markets": {
            "enabled_symbols": ["BTC/USDT"]
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_config, f)
        temp_path = f.name
    
    try:
        config = Config(temp_path)
        
        assert config.trading.divergence_threshold == 0.08
        assert config.trading.position_size_usd == 200.0
        assert config.markets.enabled_symbols == ["BTC/USDT"]
    finally:
        Path(temp_path).unlink()


def test_config_validation():
    """Test configuration validation."""
    test_config = {
        "trading": {
            "divergence_threshold": 1.5  # Invalid: > 1
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_config, f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="divergence_threshold must be between 0 and 1"):
            Config(temp_path)
    finally:
        Path(temp_path).unlink()
