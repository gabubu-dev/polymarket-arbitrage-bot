#!/usr/bin/env python3
"""
Example: Run a backtest on historical data.

This script demonstrates how to use the backtesting framework
to test strategies on historical price data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backtester import Backtester, generate_sample_data
import pandas as pd


def main():
    """Run backtest example."""
    print("=" * 60)
    print("POLYMARKET ARBITRAGE BOT - BACKTESTING EXAMPLE")
    print("=" * 60)
    print()
    
    # Step 1: Generate sample data (or load your own)
    data_path = "data/historical_prices.csv"
    
    if not Path(data_path).exists():
        print("Generating sample historical data...")
        Path("data").mkdir(exist_ok=True)
        generate_sample_data(data_path, days=30)
        print(f"✓ Sample data generated: {data_path}")
        print()
    
    # Step 2: Initialize backtester
    print("Initializing backtester...")
    backtester = Backtester(
        initial_capital=10000.0,
        position_size_usd=100.0,
        max_positions=5,
        divergence_threshold=0.05,  # 5% divergence to trigger trade
        stop_loss_pct=0.15,         # 15% stop loss
        take_profit_pct=0.90        # 90% take profit
    )
    print()
    
    # Step 3: Load historical data
    print("Loading historical data...")
    df = backtester.load_historical_data(data_path)
    print(f"✓ Loaded {len(df)} price points")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()
    
    # Step 4: Run backtest
    print("Running backtest...")
    print("-" * 60)
    results = backtester.run_backtest(df)
    print("-" * 60)
    print()
    
    # Step 5: Display results
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"Initial Capital:     ${results.initial_capital:,.2f}")
    print(f"Final Capital:       ${results.final_capital:,.2f}")
    print(f"Total P&L:           ${results.total_pnl:,.2f} ({results.total_pnl/results.initial_capital*100:.1f}%)")
    print()
    print(f"Total Trades:        {results.total_trades}")
    print(f"Winning Trades:      {results.winning_trades}")
    print(f"Losing Trades:       {results.losing_trades}")
    print(f"Win Rate:            {results.win_rate:.1f}%")
    print()
    print(f"Avg P&L per Trade:   ${results.avg_pnl_per_trade:.2f}")
    print(f"Max Drawdown:        {results.max_drawdown:.1%}")
    print(f"Sharpe Ratio:        {results.sharpe_ratio:.2f}")
    print()
    
    # Step 6: Save detailed results
    output_path = "data/backtest_results.json"
    backtester.save_results(results, output_path)
    print(f"✓ Detailed results saved to: {output_path}")
    print()
    
    # Step 7: Show sample trades
    if results.trades:
        print("SAMPLE TRADES (First 5)")
        print("-" * 60)
        for i, trade in enumerate(results.trades[:5], 1):
            print(f"{i}. {trade.symbol} | Entry: ${trade.entry_price:.2f} | "
                  f"Exit: ${trade.exit_price:.2f} | P&L: ${trade.pnl:.2f} | "
                  f"Reason: {trade.exit_reason}")
        
        if len(results.trades) > 5:
            print(f"... and {len(results.trades) - 5} more trades")
        print()
    
    print("=" * 60)
    print("Backtesting complete!")
    print()
    print("Next steps:")
    print("  1. Review the results and adjust parameters")
    print("  2. Try different divergence thresholds")
    print("  3. Test with real historical data from exchanges")
    print("  4. Run paper trading before going live")
    print()


if __name__ == "__main__":
    main()
