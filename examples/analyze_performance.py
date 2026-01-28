#!/usr/bin/env python3
"""
Example: Analyze trading performance.

This script analyzes actual trading performance from logs and
generates detailed reports.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitor import PerformanceAnalyzer


def main():
    """Run performance analysis."""
    print("=" * 60)
    print("POLYMARKET ARBITRAGE BOT - PERFORMANCE ANALYSIS")
    print("=" * 60)
    print()
    
    # Initialize analyzer
    analyzer = PerformanceAnalyzer(trades_log_path="logs/trades.log")
    
    # Analyze performance
    print("Analyzing trading performance...")
    metrics = analyzer.analyze_performance()
    
    if 'error' in metrics:
        print(f"Error: {metrics['error']}")
        return
    
    if metrics['total_trades'] == 0:
        print("No trades found in logs.")
        print("Trade some positions first, then run this analysis again.")
        return
    
    print()
    print("TRADING PERFORMANCE")
    print("=" * 60)
    
    # Overview
    print("\nOVERVIEW")
    print("-" * 60)
    print(f"Total Trades:        {metrics['total_trades']}")
    print(f"Winning Trades:      {metrics['winning_trades']}")
    print(f"Losing Trades:       {metrics['losing_trades']}")
    print(f"Win Rate:            {metrics['win_rate']:.1f}%")
    
    # Profitability
    print("\nPROFITABILITY")
    print("-" * 60)
    total_pnl = metrics['total_pnl']
    pnl_emoji = "📈" if total_pnl > 0 else "📉"
    print(f"{pnl_emoji} Total P&L:         ${total_pnl:.2f}")
    print(f"   Avg P&L/Trade:    ${metrics['avg_pnl_per_trade']:.2f}")
    print(f"   Profit Factor:    {metrics['profit_factor']:.2f}")
    print(f"   Best Trade:       ${metrics['best_trade']:.2f}")
    print(f"   Worst Trade:      ${metrics['worst_trade']:.2f}")
    
    # Execution
    print("\nEXECUTION")
    print("-" * 60)
    print(f"Avg Hold Time:       {metrics['avg_hold_time_seconds']:.1f} seconds")
    
    print()
    print("=" * 60)
    
    # Generate detailed report
    print("\nGenerating detailed report...")
    analyzer.generate_report("logs/performance_report.txt")
    print("✓ Report saved to: logs/performance_report.txt")
    
    # Recommendations
    print("\nRECOMMENDATIONS")
    print("-" * 60)
    
    if metrics['win_rate'] < 50:
        print("⚠️  Win rate below 50% - Consider:")
        print("   • Increasing divergence threshold")
        print("   • Tightening stop loss")
        print("   • Reviewing entry criteria")
    elif metrics['win_rate'] > 70:
        print("✓ Excellent win rate! Consider:")
        print("   • Increasing position size")
        print("   • Adding more trading pairs")
    
    if metrics['profit_factor'] < 1.0:
        print("⚠️  Profit factor below 1.0 - You're losing money!")
        print("   • Review risk management settings")
        print("   • Analyze losing trades for patterns")
    elif metrics['profit_factor'] > 2.0:
        print("✓ Strong profit factor - Strategy is working well")
    
    if metrics['avg_hold_time_seconds'] > 600:
        print("⚠️  Long average hold time - Consider:")
        print("   • Taking profits earlier")
        print("   • Reviewing market selection")
    
    print()


if __name__ == "__main__":
    main()
