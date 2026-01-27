"""
Tests for risk management logic.
"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_manager import RiskManager
from position_manager import Position, PositionStatus


def test_risk_manager_initialization():
    """Test RiskManager initialization."""
    rm = RiskManager(
        stop_loss_percentage=0.20,
        take_profit_percentage=0.85,
        max_daily_loss_usd=500.0
    )
    
    assert rm.stop_loss_pct == 0.20
    assert rm.take_profit_pct == 0.85
    assert rm.max_daily_loss == 500.0
    assert not rm.emergency_shutdown


def test_stop_loss_trigger():
    """Test stop loss is triggered correctly."""
    rm = RiskManager(stop_loss_percentage=0.15)
    
    position = Position(
        position_id="test_1",
        symbol="BTC/USDT",
        market_id="market_123",
        side="BUY",
        direction="up",
        size_usd=100.0,
        entry_price=0.60,
        entry_time=datetime.now()
    )
    
    # Price drops 20% - should trigger stop loss
    current_price = 0.48
    
    import asyncio
    should_exit, exit_price, reason = asyncio.run(
        rm.should_exit_position(position, current_price)
    )
    
    assert should_exit
    assert reason == "stop_loss"


def test_take_profit_trigger():
    """Test take profit is triggered correctly."""
    rm = RiskManager(take_profit_percentage=0.90)
    
    position = Position(
        position_id="test_1",
        symbol="BTC/USDT",
        market_id="market_123",
        side="BUY",
        direction="up",
        size_usd=100.0,
        entry_price=0.60,
        entry_time=datetime.now()
    )
    
    # Price gains 95% - should trigger take profit
    current_price = 1.17
    
    import asyncio
    should_exit, exit_price, reason = asyncio.run(
        rm.should_exit_position(position, current_price)
    )
    
    assert should_exit
    assert reason == "take_profit"


def test_daily_loss_limit():
    """Test daily loss limit prevents new positions."""
    rm = RiskManager(max_daily_loss_usd=1000.0)
    
    # Simulate losses
    rm.update_daily_pnl(-900.0)
    
    # Should not allow new position
    can_open, reason = rm.can_open_position(200.0)
    
    assert not can_open
    assert reason == "daily_loss_limit_reached"


def test_emergency_shutdown():
    """Test emergency shutdown is triggered on large losses."""
    rm = RiskManager(
        max_daily_loss_usd=1000.0,
        emergency_shutdown_loss_usd=5000.0
    )
    
    # Simulate catastrophic loss
    rm.update_daily_pnl(-5500.0)
    
    assert rm.emergency_shutdown
    
    can_open, reason = rm.can_open_position(100.0)
    assert not can_open
    assert reason == "emergency_shutdown_active"


def test_risk_status_reporting():
    """Test risk status reporting."""
    rm = RiskManager(max_daily_loss_usd=1000.0)
    
    rm.update_daily_pnl(-300.0)
    
    status = rm.get_risk_status()
    
    assert status['daily_pnl'] == -300.0
    assert status['max_daily_loss'] == 1000.0
    assert status['remaining_daily_budget'] == 700.0
    assert not status['emergency_shutdown']
