#!/usr/bin/env python3
"""
Quick test of paper trading system with simulated opportunities.
Shows win rate and performance metrics.
"""

import sys
sys.path.insert(0, 'src')

from paper_trader import PaperTrader
import random
import time

def simulate_trading_opportunities(paper_trader, num_trades=20):
    """Simulate finding and executing trading opportunities."""
    
    markets = [
        "Trump vs Harris 2024",
        "Will BTC hit $150k?",
        "AI regulation by 2026",
        "Fed rate decision",
        "Super Bowl winner"
    ]
    
    strategies = ["latency", "momentum", "spread", "whale"]
    
    print(f"\n🎲 Simulating {num_trades} paper trades...\n")
    
    for i in range(num_trades):
        market = random.choice(markets)
        direction = random.choice(["up", "down"])
        strategy = random.choice(strategies)
        
        # Random position size $100-500
        size = random.uniform(100, 500)
        
        # Random entry price 0.45-0.70
        entry_price = random.uniform(0.45, 0.70)
        
        # Open position
        import asyncio
        trade = asyncio.run(paper_trader.open_position(
            symbol=f"{market[:3]}/USDT",
            market_id=f"market_{i}",
            market_name=market,
            direction=direction,
            size_usd=size,
            requested_price=entry_price,
            strategy=strategy
        ))
        
        if trade:
            print(f"  [{i+1}/{num_trades}] Opened: {market} {direction} - ${size:.2f} @ {entry_price:.3f}")
            
            # Simulate some time passing
            time.sleep(0.1)
            
            # Random exit - 60% chance of profit
            if random.random() < 0.6:
                # Profitable exit (5-15% gain)
                exit_price = entry_price * random.uniform(1.05, 1.15)
            else:
                # Loss (5-10% loss)
                exit_price = entry_price * random.uniform(0.90, 0.95)
            
            # Close position
            closed_trade = asyncio.run(paper_trader.close_position(
                trade_id=trade.trade_id,
                exit_price=exit_price,
                reason="simulated_exit"
            ))
            
            if closed_trade:
                pnl = closed_trade.pnl
                emoji = "🟢" if pnl > 0 else "🔴"
                print(f"    {emoji} Closed: P&L ${pnl:+.2f}")
        
        time.sleep(0.05)

def main():
    print("=" * 60)
    print("📊 PAPER TRADING QUICK TEST")
    print("=" * 60)
    
    # Initialize paper trader
    paper_trader = PaperTrader(
        initial_balance=10000.0,
        data_dir="data/test",
        enable_realism=True
    )
    
    print(f"\n✅ Paper Trader initialized")
    print(f"   Starting Balance: ${paper_trader.portfolio.initial_balance:.2f}")
    print(f"   Realism enabled: Slippage, fees, latency simulation")
    
    # Simulate 20 trades
    simulate_trading_opportunities(paper_trader, num_trades=20)
    
    # Get performance report
    print("\n" + "=" * 60)
    print(paper_trader.generate_report())
    print("=" * 60)
    
    # Summary stats
    stats = paper_trader.get_performance_stats()
    pnl_pct = (stats['total_pnl'] / stats['initial_balance']) * 100
    print(f"\n🎯 FINAL RESULTS:")
    print(f"   Balance: ${stats['current_balance']:.2f}")
    print(f"   P&L: ${stats['total_pnl']:+.2f} ({pnl_pct:+.2f}%)")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    print(f"   Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
    print(f"   Total Trades: {stats['total_trades']}")
    
    # Check if profitable
    if stats['total_pnl'] > 0:
        print(f"\n✅ PROFITABLE: +${stats['total_pnl']:.2f}")
    else:
        print(f"\n❌ UNPROFITABLE: ${stats['total_pnl']:.2f}")
    
    print("\n" + "=" * 60)
    print("Test complete! Paper trading system is functional.")
    print("=" * 60)

if __name__ == "__main__":
    main()
