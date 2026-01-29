#!/usr/bin/env python3
"""
Test script for paper trading functionality.

Tests the paper trader module with simulated trades.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from paper_trader import PaperTrader
import logging

logging.basicConfig(level=logging.INFO)


async def test_paper_trading():
    """Test paper trading with simulated trades."""
    print("=" * 60)
    print("🧪 Testing Paper Trading System")
    print("=" * 60)
    print()
    
    # Initialize paper trader
    trader = PaperTrader(
        initial_balance=10000.0,
        data_dir="data",
        enable_realism=True
    )
    
    print(f"✅ Paper trader initialized")
    print(f"   Virtual balance: ${trader.portfolio.current_balance:.2f}")
    print()
    
    # Simulate some trades
    print("📊 Simulating trades...")
    print()
    
    trades = []
    
    # Trade 1: Winning BTC trade
    print("1️⃣  Opening BTC UP position...")
    trade1 = await trader.open_position(
        symbol="BTC/USDT",
        market_id="btc_market_1",
        market_name="Will BTC be above $50,000 in 15 minutes?",
        direction="up",
        size_usd=500,
        requested_price=0.55,
        strategy="latency_arbitrage",
        market_liquidity=50000,
        volume_24h=100000
    )
    
    if trade1:
        trades.append(trade1)
        print(f"   ✓ Opened at {trade1.entry_price:.3f}")
        print(f"   Slippage: {trade1.slippage:.2%}, Fees: ${trade1.fees_paid:.2f}")
        print()
        
        # Wait a bit (simulated)
        await asyncio.sleep(0.1)
        
        # Close with profit
        print("   Closing BTC position with profit...")
        closed1 = await trader.close_position(trade1.trade_id, 0.95, "take_profit")
        if closed1:
            print(f"   ✓ Closed at {closed1.exit_price:.3f}")
            print(f"   P&L: ${closed1.pnl:.2f} ({closed1.pnl_percent:+.2f}%)")
            print()
    
    # Trade 2: Losing ETH trade
    print("2️⃣  Opening ETH DOWN position...")
    trade2 = await trader.open_position(
        symbol="ETH/USDT",
        market_id="eth_market_1",
        market_name="Will ETH be below $3,000 in 15 minutes?",
        direction="down",
        size_usd=300,
        requested_price=0.45,
        strategy="momentum",
        market_liquidity=30000,
        volume_24h=50000
    )
    
    if trade2:
        trades.append(trade2)
        print(f"   ✓ Opened at {trade2.entry_price:.3f}")
        print(f"   Slippage: {trade2.slippage:.2%}, Fees: ${trade2.fees_paid:.2f}")
        print()
        
        await asyncio.sleep(0.1)
        
        # Close with loss
        print("   Closing ETH position with loss...")
        closed2 = await trader.close_position(trade2.trade_id, 0.25, "stop_loss")
        if closed2:
            print(f"   ✓ Closed at {closed2.exit_price:.3f}")
            print(f"   P&L: ${closed2.pnl:.2f} ({closed2.pnl_percent:+.2f}%)")
            print()
    
    # Trade 3: Small winning trade
    print("3️⃣  Opening BTC DOWN position...")
    trade3 = await trader.open_position(
        symbol="BTC/USDT",
        market_id="btc_market_2",
        market_name="Will BTC be below $49,000 in 15 minutes?",
        direction="down",
        size_usd=200,
        requested_price=0.60,
        strategy="spread",
        market_liquidity=40000,
        volume_24h=80000
    )
    
    if trade3:
        trades.append(trade3)
        print(f"   ✓ Opened at {trade3.entry_price:.3f}")
        print()
        
        await asyncio.sleep(0.1)
        
        print("   Closing BTC position with small profit...")
        closed3 = await trader.close_position(trade3.trade_id, 0.75, "take_profit")
        if closed3:
            print(f"   ✓ Closed at {closed3.exit_price:.3f}")
            print(f"   P&L: ${closed3.pnl:.2f} ({closed3.pnl_percent:+.2f}%)")
            print()
    
    # Trade 4: Winning whale-following trade
    print("4️⃣  Opening ETH UP position (whale signal)...")
    trade4 = await trader.open_position(
        symbol="ETH/USDT",
        market_id="eth_market_2",
        market_name="Will ETH be above $3,100 in 15 minutes?",
        direction="up",
        size_usd=400,
        requested_price=0.40,
        strategy="whale_tracking",
        market_liquidity=60000,
        volume_24h=120000
    )
    
    if trade4:
        trades.append(trade4)
        print(f"   ✓ Opened at {trade4.entry_price:.3f}")
        print()
        
        await asyncio.sleep(0.1)
        
        print("   Closing ETH position with profit...")
        closed4 = await trader.close_position(trade4.trade_id, 0.85, "take_profit")
        if closed4:
            print(f"   ✓ Closed at {closed4.exit_price:.3f}")
            print(f"   P&L: ${closed4.pnl:.2f} ({closed4.pnl_percent:+.2f}%)")
            print()
    
    # Trade 5: Leave one open
    print("5️⃣  Opening SOL UP position (leaving open)...")
    trade5 = await trader.open_position(
        symbol="SOL/USDT",
        market_id="sol_market_1",
        market_name="Will SOL be above $100 in 15 minutes?",
        direction="up",
        size_usd=250,
        requested_price=0.50,
        strategy="latency_arbitrage",
        market_liquidity=35000,
        volume_24h=70000
    )
    
    if trade5:
        print(f"   ✓ Opened at {trade5.entry_price:.3f}")
        print(f"   📍 Leaving position open for demonstration")
        print()
    
    # Generate and display report
    print()
    print(trader.generate_report())
    
    # Export to CSV
    csv_path = "data/paper_trades.csv"
    if trader.export_trades_csv(csv_path):
        print(f"✅ Trades exported to {csv_path}")
    
    return trader


async def main():
    """Main test function."""
    try:
        trader = await test_paper_trading()
        
        print()
        print("=" * 60)
        print("✅ Paper Trading Test Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. View trades: cat data/paper_trades.json")
        print("  2. Check CSV: cat data/paper_trades.csv")
        print("  3. Reset account: python bot_enhanced.py --paper-reset")
        print("  4. View report: python bot_enhanced.py --paper-report")
        print("  5. Start bot: python bot_enhanced.py --mode paper")
        print()
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
