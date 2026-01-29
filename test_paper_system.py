#!/usr/bin/env python3
"""
Test the complete paper trading system.

Tests:
1. Paper trader initialization
2. Opening positions
3. Closing positions
4. Performance tracking
5. Telegram alerts (if configured)
6. Report generation
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from paper_trader import PaperTrader
from telegram_alerts import TelegramAlerter


async def test_paper_trader():
    """Test the paper trading system."""
    print("=" * 70)
    print("PAPER TRADING SYSTEM TEST")
    print("=" * 70)
    print()
    
    # Initialize paper trader
    print("1. Initializing paper trader...")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    trader = PaperTrader(
        initial_balance=10000.0,
        data_dir="data/test",
        enable_realism=True,
        telegram_bot_token=telegram_token,
        telegram_chat_id="6559976977"
    )
    
    print(f"✅ Paper trader initialized")
    print(f"   Balance: ${trader.portfolio.current_balance:.2f}")
    print()
    
    # Test opening positions
    print("2. Testing position opening...")
    
    test_trades = [
        {
            "symbol": "BTC/USDT",
            "market_id": "test-market-1",
            "market_name": "Bitcoin above $45k by Feb 1",
            "direction": "up",
            "size_usd": 500.0,
            "requested_price": 0.65,
            "strategy": "momentum"
        },
        {
            "symbol": "ETH/USDT",
            "market_id": "test-market-2",
            "market_name": "Ethereum above $2.5k by Feb 1",
            "direction": "up",
            "size_usd": 300.0,
            "requested_price": 0.72,
            "strategy": "latency"
        }
    ]
    
    opened_trades = []
    for trade_data in test_trades:
        trade = await trader.open_position(**trade_data)
        if trade:
            opened_trades.append(trade)
            print(f"✅ Opened: {trade.symbol} {trade.direction} - ${trade.size_filled:.2f}")
        else:
            print(f"❌ Failed to open: {trade_data['symbol']}")
    
    print()
    
    # Display open positions
    print("3. Open positions:")
    open_positions = trader.get_open_positions()
    for pos in open_positions:
        print(f"   - {pos.symbol} {pos.direction}: ${pos.size_filled:.2f} @ {pos.entry_price:.3f}")
    print()
    
    # Test closing positions with profit
    print("4. Testing position closing...")
    
    if len(opened_trades) >= 2:
        # Close first trade with profit
        trade1 = opened_trades[0]
        exit_price_profit = trade1.entry_price * 1.15  # 15% profit
        closed1 = await trader.close_position(
            trade1.trade_id,
            exit_price_profit,
            reason="take_profit"
        )
        
        if closed1:
            print(f"✅ Closed (profit): {closed1.symbol} - P&L: ${closed1.pnl:.2f}")
        
        # Small delay for realistic simulation
        await asyncio.sleep(0.5)
        
        # Close second trade with loss
        trade2 = opened_trades[1]
        exit_price_loss = trade2.entry_price * 0.90  # 10% loss
        closed2 = await trader.close_position(
            trade2.trade_id,
            exit_price_loss,
            reason="stop_loss"
        )
        
        if closed2:
            print(f"✅ Closed (loss): {closed2.symbol} - P&L: ${closed2.pnl:.2f}")
    
    print()
    
    # Get performance stats
    print("5. Performance Statistics:")
    stats = trader.get_performance_stats()
    
    print(f"   Current Balance: ${stats['current_balance']:.2f}")
    print(f"   Total P&L: ${stats['total_pnl']:.2f} ({stats['pnl_percent']:+.2f}%)")
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Wins: {stats['wins']} | Losses: {stats['losses']}")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    print(f"   Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: ${stats['max_drawdown']:.2f}")
    print(f"   Total Fees Paid: ${stats['total_fees_paid']:.2f}")
    print()
    
    # Generate report
    print("6. Generating report...")
    report = trader.generate_report()
    print(report)
    print()
    
    # Test Telegram alerts (if configured)
    if telegram_token:
        print("7. Testing Telegram alerts...")
        
        # Send test alert
        await trader.telegram_alerter.send_message(
            "🧪 <b>Test Alert</b>\n\n"
            "Paper trading system test is running successfully!",
            parse_mode="HTML"
        )
        print("✅ Test Telegram alert sent")
        print()
    else:
        print("7. Skipping Telegram alerts (no token configured)")
        print("   Set TELEGRAM_BOT_TOKEN environment variable to test")
        print()
    
    # Test threshold alert simulation
    print("8. Simulating threshold alerts...")
    
    # Simulate hitting +10% threshold
    alerter = trader.telegram_alerter
    if telegram_token:
        await alerter.check_and_alert(
            current_balance=11000.0,
            previous_balance=10000.0,
            total_pnl=1000.0,
            win_rate=65.5,
            total_trades=25
        )
        print("✅ +10% threshold alert simulated")
        await asyncio.sleep(1)
        
        # Simulate hitting -10% threshold
        await alerter.check_and_alert(
            current_balance=9000.0,
            previous_balance=10000.0,
            total_pnl=-1000.0,
            win_rate=45.0,
            total_trades=30
        )
        print("✅ -10% threshold alert simulated")
        print()
    else:
        print("   Skipped (no Telegram token)")
        print()
    
    # Export trades to CSV
    print("9. Exporting trades to CSV...")
    csv_file = "data/test/paper_trades_export.csv"
    success = trader.export_trades_csv(csv_file)
    if success:
        print(f"✅ Trades exported to {csv_file}")
    else:
        print(f"❌ Failed to export trades")
    print()
    
    print("=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Set TELEGRAM_BOT_TOKEN in config.json to enable alerts")
    print("2. Run: python bot_enhanced.py --mode paper")
    print("3. Monitor dashboard: python dashboard.py")
    print("4. View report: python bot_enhanced.py --paper-report")
    print("5. Reset account: python bot_enhanced.py --paper-reset")
    print()


async def test_realistic_scenario():
    """Test a realistic trading scenario with multiple trades."""
    print("=" * 70)
    print("REALISTIC SCENARIO TEST - 20 Trades")
    print("=" * 70)
    print()
    
    trader = PaperTrader(initial_balance=10000.0, data_dir="data/test_realistic")
    
    # Simulate 20 trades with varying outcomes
    trades_data = [
        ("BTC/USDT", 0.65, 0.70, "up", 500),   # Win
        ("ETH/USDT", 0.72, 0.68, "up", 300),   # Loss
        ("SOL/USDT", 0.55, 0.60, "up", 400),   # Win
        ("BTC/USDT", 0.48, 0.52, "up", 600),   # Win
        ("ETH/USDT", 0.80, 0.75, "down", 350), # Loss
        ("BTC/USDT", 0.62, 0.70, "up", 450),   # Win
        ("SOL/USDT", 0.58, 0.54, "up", 300),   # Loss
        ("BTC/USDT", 0.66, 0.71, "up", 500),   # Win
        ("ETH/USDT", 0.74, 0.78, "up", 400),   # Win
        ("BTC/USDT", 0.69, 0.63, "up", 350),   # Loss
        ("SOL/USDT", 0.51, 0.57, "up", 450),   # Win
        ("BTC/USDT", 0.64, 0.69, "up", 500),   # Win
        ("ETH/USDT", 0.71, 0.67, "up", 300),   # Loss
        ("BTC/USDT", 0.67, 0.73, "up", 550),   # Win
        ("SOL/USDT", 0.59, 0.63, "up", 400),   # Win
        ("BTC/USDT", 0.68, 0.72, "up", 500),   # Win
        ("ETH/USDT", 0.76, 0.80, "up", 350),   # Win
        ("BTC/USDT", 0.65, 0.61, "up", 400),   # Loss
        ("SOL/USDT", 0.54, 0.58, "up", 450),   # Win
        ("BTC/USDT", 0.70, 0.75, "up", 500),   # Win
    ]
    
    win_count = 0
    loss_count = 0
    
    for i, (symbol, entry, exit, direction, size) in enumerate(trades_data, 1):
        # Open position
        trade = await trader.open_position(
            symbol=symbol,
            market_id=f"market-{i}",
            market_name=f"Test Market {i}",
            direction=direction,
            size_usd=size,
            requested_price=entry,
            strategy="test"
        )
        
        if trade:
            # Close position
            closed = await trader.close_position(
                trade.trade_id,
                exit,
                reason="test_scenario"
            )
            
            if closed:
                if closed.pnl > 0:
                    win_count += 1
                    emoji = "🟢"
                else:
                    loss_count += 1
                    emoji = "🔴"
                
                print(f"{emoji} Trade {i:2d}: {closed.symbol:10s} - P&L: ${closed.pnl:+7.2f}")
        
        # Small delay
        await asyncio.sleep(0.1)
    
    print()
    stats = trader.get_performance_stats()
    
    print("FINAL RESULTS:")
    print(f"  Initial Balance: ${stats['initial_balance']:.2f}")
    print(f"  Final Balance: ${stats['current_balance']:.2f}")
    print(f"  Total P&L: ${stats['total_pnl']:.2f} ({stats['pnl_percent']:+.2f}%)")
    print(f"  Win Rate: {stats['win_rate']:.1f}% ({win_count}W / {loss_count}L)")
    print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
    print()


if __name__ == "__main__":
    print("\nPaper Trading System Test Suite\n")
    
    # Run main test
    asyncio.run(test_paper_trader())
    
    # Ask if user wants to run realistic scenario
    response = input("\nRun realistic 20-trade scenario? (y/n): ")
    if response.lower() == 'y':
        asyncio.run(test_realistic_scenario())
