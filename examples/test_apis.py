#!/usr/bin/env python3
"""
Quick test script to verify Polymarket API access
Run this first to make sure everything works!
"""

import requests
from datetime import datetime

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_gamma_api():
    """Test Gamma API - Market Metadata"""
    print_section("TEST 1: Gamma API - Market Metadata")
    
    try:
        # Get top 5 markets by 24h volume
        response = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={
                "active": "true",
                "limit": 5,
                "order": "volume24hr"
            }
        )
        response.raise_for_status()
        markets = response.json()
        
        print(f"✓ Success! Found {len(markets)} trending markets:\n")
        
        for i, market in enumerate(markets, 1):
            print(f"{i}. {market['question']}")
            
            # Handle volume/liquidity as string or number
            volume = market.get('volume24hr', 0)
            liquidity = market.get('liquidity', 0)
            try:
                volume = float(volume) if volume else 0
                liquidity = float(liquidity) if liquidity else 0
            except:
                volume = 0
                liquidity = 0
            
            print(f"   Volume (24h): ${volume:,.0f}")
            print(f"   Liquidity: ${liquidity:,.0f}")
            
            if 'outcomePrices' in market:
                try:
                    prices = market['outcomePrices']
                    outcomes = market.get('outcomes', [])
                    if isinstance(prices, str):
                        import ast
                        prices = ast.literal_eval(prices)
                    for j, price in enumerate(prices):
                        if j < len(outcomes):
                            outcome = outcomes[j]
                            print(f"   {outcome}: {float(price)*100:.1f}%")
                except Exception as e:
                    print(f"   (Could not parse prices: {e})")
            print()
        
        return True, markets[0]  # Return first market for further tests
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False, None

def test_data_api(condition_id):
    """Test Data API - Top Holders"""
    print_section("TEST 2: Data API - Top Holders")
    
    try:
        response = requests.get(
            "https://data-api.polymarket.com/holders",
            params={
                "market": condition_id,
                "limit": 5
            }
        )
        response.raise_for_status()
        holders = response.json()
        
        print(f"✓ Success! Top holders for market:\n")
        
        for outcome_data in holders:
            token_holders = outcome_data.get('holders', [])
            if token_holders:
                print(f"Top holders:")
                for i, holder in enumerate(token_holders[:3], 1):
                    name = holder.get('name') or holder.get('pseudonym', 'Anonymous')
                    amount = holder.get('amount', 0)
                    print(f"  {i}. {name}: {amount:,.0f} shares")
                print()
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_clob_api(token_id):
    """Test CLOB API - Order Book"""
    print_section("TEST 3: CLOB API - Order Book & Prices")
    
    try:
        # Get last trade price
        response = requests.get(
            "https://clob.polymarket.com/last-trade-price",
            params={"token_id": token_id}
        )
        response.raise_for_status()
        last_trade = response.json()
        
        print(f"✓ Success! Last trade price: ${last_trade.get('price', 'N/A')}\n")
        
        # Get order book
        response = requests.get(
            "https://clob.polymarket.com/book",
            params={"token_id": token_id}
        )
        response.raise_for_status()
        book = response.json()
        
        print("Order Book:")
        print(f"  Best Bid: {book.get('bids', [{}])[0] if book.get('bids') else 'None'}")
        print(f"  Best Ask: {book.get('asks', [{}])[0] if book.get('asks') else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_search_api():
    """Test Gamma API - Get Events"""
    print_section("TEST 4: Get Events")
    
    try:
        # Search endpoint requires auth, so use events endpoint instead
        response = requests.get(
            "https://gamma-api.polymarket.com/events",
            params={
                "limit": 5,
                "active": "true"
            }
        )
        response.raise_for_status()
        events = response.json()
        
        print(f"✓ Success! Found {len(events)} active events:\n")
        
        for i, event in enumerate(events[:5], 1):
            print(f"{i}. {event.get('title')}")
            print(f"   Slug: {event.get('slug')}")
            print(f"   Markets: {len(event.get('markets', []))}")
            print()
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("  POLYMARKET API TEST SUITE")
    print("  Testing all public APIs for data access")
    print("="*60)
    print(f"\nStarted at: {datetime.now()}\n")
    
    results = {}
    
    # Test 1: Gamma API
    results['gamma'], first_market = test_gamma_api()
    
    if first_market:
        condition_id = first_market.get('conditionId')
        token_id = first_market.get('tokens', [{}])[0].get('tokenId')
        
        # Test 2: Data API
        if condition_id:
            results['data'] = test_data_api(condition_id)
        
        # Test 3: CLOB API
        if token_id:
            results['clob'] = test_clob_api(token_id)
    
    # Test 4: Events
    results['events'] = test_search_api()
    
    # Summary
    print_section("TEST SUMMARY")
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name.upper():15s} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("  🎉 ALL TESTS PASSED! APIs are working correctly.")
        print("  You can now start building your dashboard!")
    else:
        print("  ⚠️  Some tests failed. Check the errors above.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
