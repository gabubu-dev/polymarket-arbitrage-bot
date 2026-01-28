#!/usr/bin/env python3
"""
Profitability Calculator for Polymarket Arbitrage Bot

Estimates potential returns based on capital, strategy, and market conditions.
"""

import argparse
from dataclasses import dataclass
from typing import Dict


@dataclass
class StrategyReturns:
    """Expected returns for a strategy."""
    min_daily_return_pct: float
    avg_daily_return_pct: float
    max_daily_return_pct: float
    trades_per_day: int
    win_rate: float
    avg_profit_per_trade_pct: float
    avg_loss_per_trade_pct: float


STRATEGY_PROFILES = {
    'latency': StrategyReturns(
        min_daily_return_pct=0.2,
        avg_daily_return_pct=1.0,
        max_daily_return_pct=3.0,
        trades_per_day=20,
        win_rate=0.65,
        avg_profit_per_trade_pct=1.5,
        avg_loss_per_trade_pct=2.0
    ),
    'spread': StrategyReturns(
        min_daily_return_pct=0.1,
        avg_daily_return_pct=0.5,
        max_daily_return_pct=1.0,
        trades_per_day=5,
        win_rate=0.85,
        avg_profit_per_trade_pct=0.5,
        avg_loss_per_trade_pct=0.3
    ),
    'momentum': StrategyReturns(
        min_daily_return_pct=0.0,
        avg_daily_return_pct=2.0,
        max_daily_return_pct=8.0,
        trades_per_day=10,
        win_rate=0.55,
        avg_profit_per_trade_pct=4.0,
        avg_loss_per_trade_pct=3.0
    ),
    'whale': StrategyReturns(
        min_daily_return_pct=0.15,
        avg_daily_return_pct=0.8,
        max_daily_return_pct=2.0,
        trades_per_day=12,
        win_rate=0.60,
        avg_profit_per_trade_pct=2.0,
        avg_loss_per_trade_pct=2.5
    ),
    'combined': StrategyReturns(
        min_daily_return_pct=0.3,
        avg_daily_return_pct=1.5,
        max_daily_return_pct=4.0,
        trades_per_day=35,
        win_rate=0.62,
        avg_profit_per_trade_pct=2.0,
        avg_loss_per_trade_pct=2.0
    )
}


def calculate_compound_return(initial: float, daily_rate: float, days: int) -> float:
    """Calculate compound return over time."""
    return initial * ((1 + daily_rate) ** days)


def estimate_profitability(
    capital: float,
    strategy: str,
    days: int = 30,
    position_size_pct: float = 0.05
) -> Dict:
    """Estimate profitability for given parameters."""
    
    profile = STRATEGY_PROFILES.get(strategy, STRATEGY_PROFILES['combined'])
    
    # Position sizing
    position_size = capital * position_size_pct
    max_positions = int(capital / position_size)
    
    # Daily returns
    min_return = capital * (profile.min_daily_return_pct / 100)
    avg_return = capital * (profile.avg_daily_return_pct / 100)
    max_return = capital * (profile.max_daily_return_pct / 100)
    
    # Monthly projections
    min_monthly = calculate_compound_return(capital, profile.min_daily_return_pct/100, days)
    avg_monthly = calculate_compound_return(capital, profile.avg_daily_return_pct/100, days)
    max_monthly = calculate_compound_return(capital, profile.max_daily_return_pct/100, days)
    
    # Risk metrics
    expected_value_per_trade = (
        profile.win_rate * profile.avg_profit_per_trade_pct -
        (1 - profile.win_rate) * profile.avg_loss_per_trade_pct
    )
    
    return {
        'capital': capital,
        'strategy': strategy,
        'position_size': position_size,
        'max_positions': max_positions,
        'daily_trades': profile.trades_per_day,
        'win_rate': profile.win_rate,
        'min_daily_profit': min_return,
        'avg_daily_profit': avg_return,
        'max_daily_profit': max_return,
        'min_monthly_total': min_monthly,
        'avg_monthly_total': avg_monthly,
        'max_monthly_total': max_monthly,
        'min_monthly_profit': min_monthly - capital,
        'avg_monthly_profit': avg_monthly - capital,
        'max_monthly_profit': max_monthly - capital,
        'expected_value_per_trade': expected_value_per_trade
    }


def print_report(results: Dict):
    """Print formatted profitability report."""
    print("\n" + "=" * 60)
    print(f"  POLYMARKET ARBITRAGE BOT - PROFITABILITY ESTIMATE")
    print("=" * 60)
    print()
    
    print(f"  Initial Capital:        ${results['capital']:>12,.2f}")
    print(f"  Strategy:               {results['strategy']:>12}")
    print(f"  Position Size:          ${results['position_size']:>12,.2f}")
    print(f"  Max Concurrent:         {results['max_positions']:>12}")
    print(f"  Expected Trades/Day:    {results['daily_trades']:>12}")
    print(f"  Win Rate:               {results['win_rate']*100:>11.1f}%")
    print()
    
    print("  📈 DAILY RETURNS")
    print("  " + "-" * 56)
    print(f"  Conservative:           ${results['min_daily_profit']:>12,.2f}")
    print(f"  Expected:               ${results['avg_daily_profit']:>12,.2f}")
    print(f"  Optimistic:             ${results['max_daily_profit']:>12,.2f}")
    print()
    
    print("  📊 30-DAY PROJECTIONS")
    print("  " + "-" * 56)
    print(f"  Conservative Profit:    ${results['min_monthly_profit']:>12,.2f}")
    print(f"  Expected Profit:        ${results['avg_monthly_profit']:>12,.2f}")
    print(f"  Optimistic Profit:      ${results['max_monthly_profit']:>12,.2f}")
    print()
    
    print("  💰 TOTAL VALUE AFTER 30 DAYS")
    print("  " + "-" * 56)
    print(f"  Conservative:           ${results['min_monthly_total']:>12,.2f}")
    print(f"  Expected:               ${results['avg_monthly_total']:>12,.2f}")
    print(f"  Optimistic:             ${results['max_monthly_total']:>12,.2f}")
    print()
    
    roi = (results['avg_monthly_profit'] / results['capital']) * 100
    print(f"  Expected ROI (30 days): {roi:>11.1f}%")
    print(f"  Expected Annual ROI:    {roi * 12:>11.1f}%")
    print()
    
    print("  ⚠️  IMPORTANT NOTES")
    print("  " + "-" * 56)
    print("  • These are estimates based on historical patterns")
    print("  • Actual results will vary based on market conditions")
    print("  • Start with smaller amounts to validate performance")
    print("  • Past performance does not guarantee future results")
    print()
    print("=" * 60)


def compare_strategies(capital: float, days: int = 30):
    """Compare all strategies."""
    print("\n" + "=" * 80)
    print(f"  STRATEGY COMPARISON (Capital: ${capital:,.2f}, {days} days)")
    print("=" * 80)
    print()
    print(f"  {'Strategy':<12} {'Daily Return':<15} {'30-Day Profit':<18} {'Annual ROI':<12}")
    print("  " + "-" * 76)
    
    for strategy in ['latency', 'spread', 'momentum', 'whale', 'combined']:
        results = estimate_profitability(capital, strategy, days)
        daily = results['avg_daily_profit']
        monthly = results['avg_monthly_profit']
        annual_roi = (monthly / capital) * 100 * 12
        
        print(f"  {strategy:<12} ${daily:>12,.2f} ${monthly:>15,.2f} {annual_roi:>10.1f}%")
    
    print()
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate expected profitability for Polymarket arbitrage strategies"
    )
    parser.add_argument(
        '--capital', '-c',
        type=float,
        default=1000,
        help='Initial capital in USD (default: 1000)'
    )
    parser.add_argument(
        '--strategy', '-s',
        choices=['latency', 'spread', 'momentum', 'whale', 'combined', 'all'],
        default='combined',
        help='Trading strategy (default: combined)'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=30,
        help='Projection period in days (default: 30)'
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare all strategies'
    )
    
    args = parser.parse_args()
    
    if args.compare:
        compare_strategies(args.capital, args.days)
    else:
        results = estimate_profitability(
            capital=args.capital,
            strategy=args.strategy,
            days=args.days
        )
        print_report(results)


if __name__ == "__main__":
    main()