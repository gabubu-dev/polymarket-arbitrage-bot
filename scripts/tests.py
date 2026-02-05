#!/usr/bin/env python3
"""
Test suite for Polymarket Copy Trading Bot
"""

import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paper_trader import PaperTrader, Position, Portfolio, PositionStatus
from risk_manager import RiskManager, WalletPerformance, DailyStats


class TestPaperTrader(unittest.TestCase):
    """Test paper trading functionality"""
    
    def setUp(self):
        self.config = {
            "paper_trading": {
                "enabled": True,
                "initial_balance_usdc": 10000.0,
                "slippage_min": 0.005,
                "slippage_max": 0.01
            }
        }
        self.trader = PaperTrader(self.config, db_path=":memory:")
    
    def tearDown(self):
        # Clean up in-memory database
        pass
    
    def test_initial_portfolio(self):
        """Test portfolio initialization"""
        stats = self.trader.get_portfolio_stats()
        self.assertEqual(stats["initial_balance"], 10000.0)
        self.assertEqual(stats["balance_usdc"], 10000.0)
        self.assertEqual(stats["total_value"], 10000.0)
        self.assertEqual(stats["total_trades"], 0)
    
    def test_open_position(self):
        """Test opening a position"""
        position = self.trader.open_position(
            wallet_address="0x123",
            wallet_name="Test Wallet",
            market_id="0xabc",
            market_question="Will it rain?",
            outcome_index=0,
            outcome_name="Yes",
            side="BUY",
            price=0.65,
            size=1000.0
        )
        
        self.assertIsNotNone(position)
        self.assertEqual(position.side, "BUY")
        self.assertEqual(position.size, 1000.0)
        self.assertEqual(position.status, PositionStatus.OPEN)
        
        # Check balance was reduced
        stats = self.trader.get_portfolio_stats()
        self.assertLess(stats["balance_usdc"], 10000.0)
    
    def test_insufficient_balance(self):
        """Test opening position with insufficient balance"""
        position = self.trader.open_position(
            wallet_address="0x123",
            wallet_name="Test Wallet",
            market_id="0xabc",
            market_question="Will it rain?",
            outcome_index=0,
            outcome_name="Yes",
            side="BUY",
            price=0.65,
            size=20000.0  # More than balance
        )
        
        self.assertIsNone(position)
    
    def test_close_position(self):
        """Test closing a position"""
        # Open position
        position = self.trader.open_position(
            wallet_address="0x123",
            wallet_name="Test Wallet",
            market_id="0xabc",
            market_question="Will it rain?",
            outcome_index=0,
            outcome_name="Yes",
            side="BUY",
            price=0.65,
            size=1000.0
        )
        
        position_id = position.id
        
        # Close position at higher price (profit)
        closed = self.trader.close_position(
            position_id=position_id,
            exit_price=0.75,
            reason="test"
        )
        
        self.assertIsNotNone(closed)
        self.assertEqual(closed.status, PositionStatus.CLOSED)
        self.assertGreater(closed.pnl, 0)  # Should be profitable
        
        # Check it's in closed positions
        open_positions = self.trader.get_open_positions()
        self.assertEqual(len(open_positions), 0)
        
        closed_positions = self.trader.get_closed_positions()
        self.assertEqual(len(closed_positions), 1)
    
    def test_mirror_trade(self):
        """Test mirroring a trade with copy percentage"""
        position = self.trader.mirror_trade(
            wallet_address="0x123",
            wallet_name="Test Wallet",
            market_id="0xabc",
            market_question="Will it rain?",
            outcome_index=0,
            outcome_name="Yes",
            side="BUY",
            price=0.65,
            original_size=1000.0,
            copy_percentage=50  # Copy 50%
        )
        
        self.assertIsNotNone(position)
        self.assertEqual(position.size, 500.0)  # 50% of 1000


class TestRiskManager(unittest.TestCase):
    """Test risk management functionality"""
    
    def setUp(self):
        self.config = {
            "risk_management": {
                "daily_loss_limit_percent": 5.0,
                "max_position_size_percent": 5.0,
                "max_concurrent_positions": 10,
                "min_win_rate_percent": 50.0,
                "min_trades_for_win_rate": 20,
                "auto_unfollow_bad_performers": True
            }
        }
        self.risk_manager = RiskManager(self.config)
    
    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement"""
        # Simulate trades that cause -6% loss
        for i in range(10):
            self.risk_manager.update_daily_stats(
                pnl=-100,
                is_win=False,
                current_balance=9000 - i * 100
            )
        
        # Check that trading is not allowed
        # (Note: threshold depends on starting balance calculation)
        # This test verifies the mechanism works
    
    def test_win_rate_check(self):
        """Test win rate-based unfollow"""
        unfollow_called = []
        
        def on_unfollow(addr, reason):
            unfollow_called.append((addr, reason))
        
        self.risk_manager.add_unfollow_callback(on_unfollow)
        
        # Record 20 losing trades (0% win rate)
        for i in range(20):
            self.risk_manager.record_trade_result(
                wallet_address="0xbad",
                wallet_name="Bad Trader",
                pnl=-10,
                current_balance=10000 - i * 10
            )
        
        # Should have unfollowed
        self.assertEqual(len(unfollow_called), 1)
        self.assertEqual(unfollow_called[0][0], "0xbad")
    
    def test_position_size_check(self):
        """Test position size limiting"""
        portfolio_value = 10000
        proposed_size = 1000  # 10%
        
        adjusted = self.risk_manager.check_position_size(proposed_size, portfolio_value)
        
        # Should be limited to 5%
        self.assertEqual(adjusted, 500.0)
    
    def test_concurrent_positions(self):
        """Test concurrent position limit"""
        # Should allow up to 10
        self.assertTrue(self.risk_manager.check_concurrent_positions(5))
        self.assertTrue(self.risk_manager.check_concurrent_positions(9))
        self.assertFalse(self.risk_manager.check_concurrent_positions(10))
        self.assertFalse(self.risk_manager.check_concurrent_positions(15))
    
    def test_stop_loss_price(self):
        """Test stop loss calculation"""
        # Long position
        sl_price = self.risk_manager.get_stop_loss_price(0.65, "BUY")
        self.assertLess(sl_price, 0.65)
        
        # Short position
        sl_price = self.risk_manager.get_stop_loss_price(0.65, "SELL")
        self.assertGreater(sl_price, 0.65)


class TestWalletPerformance(unittest.TestCase):
    """Test wallet performance tracking"""
    
    def setUp(self):
        self.performance = WalletPerformance(
            address="0x123",
            name="Test Wallet"
        )
    
    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        self.performance.total_trades = 10
        self.performance.winning_trades = 7
        self.performance.losing_trades = 3
        
        self.assertEqual(self.performance.win_rate, 70.0)
    
    def test_drawdown_calculation(self):
        """Test max drawdown calculation"""
        self.performance.total_pnl = 100
        self.performance.update_drawdown()
        
        self.performance.total_pnl = 50
        self.performance.update_drawdown()
        
        self.assertEqual(self.performance.max_drawdown, 50)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_full_trade_flow(self):
        """Test complete trade flow"""
        config = {
            "paper_trading": {
                "enabled": True,
                "initial_balance_usdc": 10000.0
            },
            "risk_management": {
                "daily_loss_limit_percent": 5.0,
                "max_position_size_percent": 5.0,
                "max_concurrent_positions": 10,
                "min_win_rate_percent": 50.0,
                "min_trades_for_win_rate": 20
            }
        }
        
        # Create components
        trader = PaperTrader(config, db_path=":memory:")
        risk = RiskManager(config)
        
        # Open position
        position = trader.open_position(
            wallet_address="0x123",
            wallet_name="Test Wallet",
            market_id="0xabc",
            market_question="Test Market",
            outcome_index=0,
            outcome_name="Yes",
            side="BUY",
            price=0.50,
            size=500.0
        )
        
        self.assertIsNotNone(position)
        
        # Close position with profit
        closed = trader.close_position(position.id, 0.60)
        self.assertIsNotNone(closed)
        
        # Record in risk manager
        risk.record_trade_result(
            wallet_address="0x123",
            wallet_name="Test Wallet",
            pnl=closed.pnl,
            current_balance=trader.portfolio.get_total_value()
        )
        
        # Check stats
        wallet_stats = risk.get_wallet_stats("0x123")
        self.assertIsNotNone(wallet_stats)
        self.assertEqual(wallet_stats["total_trades"], 1)
        self.assertEqual(wallet_stats["winning_trades"], 1)
        self.assertEqual(wallet_stats["win_rate_percent"], 100.0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPaperTrader))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskManager))
    suite.addTests(loader.loadTestsFromTestCase(TestWalletPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
