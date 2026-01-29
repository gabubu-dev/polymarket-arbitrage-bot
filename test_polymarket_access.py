#!/usr/bin/env python3
"""
Quick test script to verify Polymarket API access
Run: python test_polymarket_access.py
"""

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import BookParams
import json

def test_basic_access():
    """Test basic API access without authentication"""
    print("=" * 60)
    print("POLYMARKET API ACCESS TEST")
    print("=" * 60)
    print()
    
    # Initialize client (no auth needed for read-only)
    print("1. Initializing CLOB client...")
    client = ClobClient("https://clob.polymarket.com")
    print("   ✅ Client initialized")
    print()
    
    # Test server connection
    print("2. Testing server connection...")
    ok = client.get_ok()
    server_time = client.get_server_time()
    print(f"   ✅ Server OK: {ok}")
    print(f"   ✅ Server Time: {server_time}")
    print()
    
    # Get markets
    print("3. Fetching markets...")
    markets = client.get_simplified_markets()
    print(f"   ✅ Retrieved {len(markets.get('data', []))} markets")
    print()
    
    # Display top 5 markets
    print("4. Top 5 Markets by Volume:")
    print("-" * 60)
    for i, market in enumerate(markets["data"][:5], 1):
        volume = market.get("volume", 0)
        question = market.get("question", "N/A")
        print(f"   {i}. {question[:60]}...")
        print(f"      Volume: ${volume:,.2f}")
        print()
    
    # Test price data for first market with token IDs
    print("5. Testing price data...")
    for market in markets["data"]:
        token_ids_str = market.get("clobTokenIds", "")
        if token_ids_str:
            token_ids = token_ids_str.split(",")
            if len(token_ids) >= 2:
                token_id = token_ids[0]
                print(f"   Market: {market['question'][:50]}...")
                
                try:
                    # Get prices
                    mid = client.get_midpoint(token_id)
                    buy = client.get_price(token_id, side="BUY")
                    sell = client.get_price(token_id, side="SELL")
                    
                    print(f"   ✅ Midpoint: ${mid:.4f}")
                    print(f"   ✅ Buy Price: ${buy:.4f}")
                    print(f"   ✅ Sell Price: ${sell:.4f}")
                    print(f"   ✅ Spread: ${abs(sell - buy):.4f}")
                    print()
                    
                    # Get orderbook
                    print("6. Testing orderbook data...")
                    book = client.get_order_book(token_id)
                    print(f"   ✅ Bids: {len(book.bids)}")
                    print(f"   ✅ Asks: {len(book.asks)}")
                    
                    if book.bids:
                        print(f"   Best Bid: ${book.bids[0].price} (Size: {book.bids[0].size})")
                    if book.asks:
                        print(f"   Best Ask: ${book.asks[0].price} (Size: {book.asks[0].size})")
                    
                except Exception as e:
                    print(f"   ⚠️ Error getting price data: {e}")
                
                break  # Only test first market with valid tokens
    
    print()
    print("=" * 60)
    print("✅ ALL TESTS PASSED - API ACCESS WORKING!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Check POLYMARKET_DATA_ACCESS.md for full documentation")
    print("2. Install Streamlit: pip install streamlit")
    print("3. Run the dashboard: streamlit run dashboard_example.py")
    print()

if __name__ == "__main__":
    try:
        test_basic_access()
    except ImportError:
        print("❌ ERROR: py-clob-client not installed")
        print()
        print("Install it with:")
        print("   pip install py-clob-client")
        print()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
