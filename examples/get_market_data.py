#!/usr/bin/env python3
"""
Get detailed data for a specific market
Usage: python get_market_data.py "market-slug-here"
"""

import requests
import sys
import json

def get_market_by_slug(slug):
    """Get market details by slug"""
    response = requests.get(
        f"https://gamma-api.polymarket.com/markets",
        params={"slug": slug}
    )
    markets = response.json()
    return markets[0] if markets else None

def get_top_holders(condition_id, limit=10):
    """Get top holders"""
    response = requests.get(
        "https://data-api.polymarket.com/holders",
        params={
            "market": condition_id,
            "limit": limit
        }
    )
    return response.json()

def get_recent_trades(condition_id, limit=20):
    """Get recent trades for a market"""
    response = requests.get(
        "https://data-api.polymarket.com/trades",
        params={
            "market": condition_id,
            "limit": limit,
            "takerOnly": "true"
        }
    )
    return response.json()

def display_market(market):
    """Display market details"""
    print("\n" + "="*80)
    print("  MARKET DETAILS")
    print("="*80)
    
    print(f"\nQuestion: {market['question']}")
    print(f"Market ID: {market['id']}")
    print(f"Condition ID: {market['conditionId']}")
    print(f"Slug: {market['slug']}")
    
    print(f"\n📊 Statistics:")
    print(f"  Volume (Total): ${market.get('volume', 0):,.2f}")
    print(f"  Volume (24h): ${market.get('volume24hr', 0):,.2f}")
    print(f"  Liquidity: ${market.get('liquidity', 0):,.2f}")
    
    print(f"\n💰 Current Prices:")
    if 'outcomePrices' in market:
        for i, price in enumerate(market['outcomePrices']):
            outcome = market['outcomes'][i]
            token_id = market['tokens'][i]['tokenId']
            print(f"  {outcome}: {float(price)*100:.1f}% (Token: {token_id})")
    
    if market.get('description'):
        print(f"\n📝 Description:")
        print(f"  {market['description']}")
    
    if market.get('endDate'):
        print(f"\n📅 End Date: {market['endDate']}")

def display_holders(holders):
    """Display top holders"""
    print("\n" + "="*80)
    print("  TOP HOLDERS")
    print("="*80 + "\n")
    
    for outcome_data in holders:
        token_holders = outcome_data.get('holders', [])
        if token_holders:
            print(f"Top Holders:")
            for i, holder in enumerate(token_holders[:10], 1):
                name = holder.get('name') or holder.get('pseudonym', 'Anonymous')
                amount = holder.get('amount', 0)
                print(f"  {i:2d}. {name:30s} {amount:12,.0f} shares")
            print()

def display_trades(trades):
    """Display recent trades"""
    print("\n" + "="*80)
    print("  RECENT TRADES")
    print("="*80 + "\n")
    
    for i, trade in enumerate(trades[:15], 1):
        side = trade['side']
        size = trade['size']
        price = trade['price']
        outcome = trade['outcome']
        trader = trade.get('name') or trade.get('pseudonym', 'Anonymous')
        
        print(f"{i:2d}. {side:4s} {size:10,.2f} @ ${price:.4f} ({outcome}) - {trader}")

def search_markets(query):
    """Search for markets"""
    response = requests.get(
        "https://gamma-api.polymarket.com/search",
        params={
            "query": query,
            "active": "true"
        }
    )
    return [r for r in response.json() if r.get('type') == 'market']

def main():
    if len(sys.argv) < 2:
        print("""
Usage: python get_market_data.py <market-slug-or-search-term>

Examples:
  python get_market_data.py presidential-election-winner-2024
  python get_market_data.py "Trump win"

To find market slugs, visit polymarket.com and copy from URL:
  https://polymarket.com/event/some-event/market-slug-here
                                          ^^^^^^^^^^^^^^^^
""")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    # Try to get market directly by slug
    print(f"Searching for: {query}")
    market = get_market_by_slug(query)
    
    # If not found, search
    if not market:
        print("Not found as slug, searching...")
        results = search_markets(query)
        
        if not results:
            print(f"No markets found matching '{query}'")
            sys.exit(1)
        
        if len(results) > 1:
            print(f"\nFound {len(results)} markets:\n")
            for i, r in enumerate(results[:10], 1):
                print(f"{i}. {r.get('question', r.get('title'))}")
                print(f"   Slug: {r['slug']}\n")
            
            try:
                choice = int(input("Select market (1-10): ")) - 1
                slug = results[choice]['slug']
                market = get_market_by_slug(slug)
            except:
                print("Invalid selection")
                sys.exit(1)
        else:
            market = get_market_by_slug(results[0]['slug'])
    
    if not market:
        print("Failed to load market data")
        sys.exit(1)
    
    # Display market details
    display_market(market)
    
    condition_id = market['conditionId']
    
    # Get and display holders
    try:
        holders = get_top_holders(condition_id)
        display_holders(holders)
    except Exception as e:
        print(f"\nFailed to get holders: {e}")
    
    # Get and display trades
    try:
        trades = get_recent_trades(condition_id)
        display_trades(trades)
    except Exception as e:
        print(f"\nFailed to get trades: {e}")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
