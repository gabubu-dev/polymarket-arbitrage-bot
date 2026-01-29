#!/usr/bin/env python3
"""
Quick test script to verify Polymarket API access.
Run this to confirm all data sources are working.

Usage:
    python3 test_polymarket_apis.py
"""

import requests
import json
import sys

def test_gamma_api():
    """Test Gamma API (Market Discovery)"""
    print("🧪 Testing Gamma API...")
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"active": "true", "limit": 5}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Gamma API: OK - Got {len(data)} markets")
            if data:
                print(f"   📊 Sample: {data[0]['question'][:60]}...")
            return True
        else:
            print(f"   ❌ Gamma API: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ Gamma API: Error - {e}")
        return False

def test_clob_api():
    """Test CLOB API (Order Book)"""
    print("\n🧪 Testing CLOB API...")
    try:
        url = "https://clob.polymarket.com/time"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            timestamp = int(response.text)
            print(f"   ✅ CLOB API: OK - Server time: {timestamp}")
            
            # Try markets endpoint
            markets_url = "https://clob.polymarket.com/markets"
            response2 = requests.get(markets_url, timeout=10)
            if response2.status_code == 200:
                print(f"   ✅ CLOB Markets: OK")
            return True
        else:
            print(f"   ❌ CLOB API: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ CLOB API: Error - {e}")
        return False

def test_graphql():
    """Test GraphQL Subgraph"""
    print("\n🧪 Testing GraphQL Subgraph...")
    try:
        url = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
        query = {
            "query": "{ _meta { block { number } } }"
        }
        response = requests.post(url, json=query, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            block = data.get('data', {}).get('_meta', {}).get('block', {}).get('number', 'N/A')
            print(f"   ✅ GraphQL: OK - Latest block: {block}")
            return True
        else:
            print(f"   ❌ GraphQL: Failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ GraphQL: Error - {e}")
        return False

def get_top_markets():
    """Get top 5 markets by volume"""
    print("\n📈 Fetching Top Markets by Volume...")
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"active": "true", "limit": 100}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            markets = response.json()
            # Sort by volume
            markets.sort(key=lambda x: x.get('volumeNum', 0), reverse=True)
            
            print("\n   Top 5 Markets:")
            print("   " + "-" * 70)
            for i, m in enumerate(markets[:5], 1):
                volume = m.get('volumeNum', 0)
                question = m['question'][:55]
                print(f"   {i}. {question}...")
                print(f"      Volume: ${volume:,.0f} | Condition: {m.get('conditionId', 'N/A')[:20]}...")
            return True
    except Exception as e:
        print(f"   Error: {e}")
        return False

def main():
    print("=" * 70)
    print("🎯 Polymarket API Test Suite")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Gamma API", test_gamma_api()))
    results.append(("CLOB API", test_clob_api()))
    results.append(("GraphQL", test_graphql()))
    
    # Get sample data
    get_top_markets()
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All APIs working! You're ready to build.")
        return 0
    else:
        print("\n⚠️  Some APIs failed. Check your connection.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
