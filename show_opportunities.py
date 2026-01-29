#!/usr/bin/env python3
"""
Show real trading opportunities from Polymarket markets.
"""

import sys
sys.path.insert(0, 'src')
from market_discovery import PolymarketDiscovery
import json

def main():
    config = json.load(open('config.json'))
    md = PolymarketDiscovery(config)
    
    print("=" * 70)
    print("📊 POLYMARKET REAL-TIME OPPORTUNITIES")
    print("=" * 70)
    print()
    
    markets = md.fetch_active_markets(force_refresh=True)
    
    print(f"✓ Discovered {len(markets)} active markets")
    print()
    
    # Group by unique questions (remove duplicates)
    seen = set()
    unique_markets = []
    for m in markets:
        if m.question not in seen:
            seen.add(m.question)
            unique_markets.append(m)
    
    print(f"✓ {len(unique_markets)} unique market questions")
    print()
    print("=" * 70)
    print("TOP 10 TRADING OPPORTUNITIES (by profitability score)")
    print("=" * 70)
    print()
    
    for i, m in enumerate(unique_markets[:10], 1):
        print(f"{i}. {m.question}")
        print(f"   Category: {m.category}")
        
        # Show prices
        if m.outcome_prices and len(m.outcome_prices) == 2:
            yes_price = m.outcome_prices[0]
            no_price = m.outcome_prices[1]
            print(f"   Current: YES={yes_price:.1%} / NO={no_price:.1%}")
        
        # Show orderbook
        print(f"   Orderbook: Bid={m.best_bid:.3f} / Ask={m.best_ask:.3f} (spread: {m.spread:.1%})")
        
        # Show metrics
        print(f"   Volume: ${m.volume_24h:,.0f}/day | Liquidity: ${m.liquidity:,.0f}")
        print(f"   Score: {m.profitability_score:.4f} | Confidence: {m.confidence:.1%}")
        
        # Strategy suggestions
        strategies = []
        if m.spread > 0.02:  # 2%+ spread
            strategies.append("Spread arb")
        if m.volume_24h > 10000:
            strategies.append("Momentum")
        if m.liquidity > 50000:
            strategies.append("Whale tracking")
        
        if strategies:
            print(f"   💡 Strategies: {', '.join(strategies)}")
        
        print()
    
    print("=" * 70)
    print("MARKET SUMMARY")
    print("=" * 70)
    
    # Stats
    total_volume = sum(m.volume_24h for m in unique_markets)
    total_liquidity = sum(m.liquidity for m in unique_markets)
    avg_spread = sum(m.spread for m in unique_markets) / len(unique_markets) if unique_markets else 0
    
    print(f"Total 24h Volume: ${total_volume:,.0f}")
    print(f"Total Liquidity: ${total_liquidity:,.0f}")
    print(f"Average Spread: {avg_spread:.2%}")
    print()
    
    # Category breakdown
    categories = {}
    for m in unique_markets:
        categories[m.category] = categories.get(m.category, 0) + 1
    
    print("Markets by category:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count} markets")
    
    print()
    print("=" * 70)
    print("✅ Bot is ready to trade these markets in paper mode")
    print("=" * 70)

if __name__ == "__main__":
    main()
