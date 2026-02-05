#!/usr/bin/env python3
"""
Wallet Analyzer - Helper script to find and analyze profitable wallets
Usage: python wallet_analyzer.py <wallet_address>
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from polymarket_client import PolymarketClient


class WalletAnalyzer:
    """Analyzes a wallet's trading performance on Polymarket"""
    
    def __init__(self):
        config = {
            "monitoring": {
                "rpc_endpoints": ["https://polygon-rpc.com"],
                "graphql_endpoint": "https://api.polymarket.com/graphql"
            }
        }
        self.client = PolymarketClient(config)
    
    async def analyze(self, wallet_address: str, days: int = 90) -> Dict[str, Any]:
        """Analyze a wallet's performance"""
        print(f"\n🔍 Analyzing wallet: {wallet_address}")
        print("=" * 60)
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get trades
        trades = await self.client.get_user_trades(wallet_address, since)
        print(f"📊 Found {len(trades)} trades in last {days} days")
        
        if not trades:
            return {"error": "No trades found"}
        
        # Analyze trades
        buy_count = sum(1 for t in trades if t.get("side") == "BUY")
        sell_count = sum(1 for t in trades if t.get("side") == "SELL")
        
        total_volume = sum(t.get("amount", 0) for t in trades)
        avg_trade_size = total_volume / len(trades) if trades else 0
        
        # Category analysis
        categories = {}
        for trade in trades:
            cat = trade.get("market", {}).get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        # Monthly activity
        monthly_trades = len(trades) / (days / 30)
        
        # Get current positions
        positions = await self.client.get_user_positions(wallet_address)
        
        result = {
            "address": wallet_address,
            "total_trades": len(trades),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_volume": total_volume,
            "avg_trade_size": avg_trade_size,
            "monthly_trades": monthly_trades,
            "categories": categories,
            "current_positions": len(positions),
            "analysis_date": datetime.utcnow().isoformat()
        }
        
        self._print_summary(result)
        
        return result
    
    def _print_summary(self, result: Dict[str, Any]):
        """Print analysis summary"""
        print(f"\n📈 Trading Summary:")
        print(f"   Total Trades: {result['total_trades']}")
        print(f"   Buys: {result['buy_count']} | Sells: {result['sell_count']}")
        print(f"   Total Volume: ${result['total_volume']:,.2f}")
        print(f"   Avg Trade Size: ${result['avg_trade_size']:,.2f}")
        print(f"   Monthly Trades: {result['monthly_trades']:.1f}")
        print(f"   Current Positions: {result['current_positions']}")
        
        print(f"\n🏷️ Categories:")
        for cat, count in sorted(result['categories'].items(), key=lambda x: -x[1]):
            print(f"   {cat}: {count} trades")
        
        # Recommendations
        print(f"\n✅ Assessment:")
        is_good = True
        
        if result['monthly_trades'] < 5:
            print(f"   ⚠️ Low activity ({result['monthly_trades']:.1f} trades/month)")
            is_good = False
        else:
            print(f"   ✅ Good activity ({result['monthly_trades']:.1f} trades/month)")
        
        if result['avg_trade_size'] < 100:
            print(f"   ⚠️ Small trade sizes (${result['avg_trade_size']:.2f} avg)")
        else:
            print(f"   ✅ Good trade sizes (${result['avg_trade_size']:.2f} avg)")
        
        if len(result['categories']) == 1:
            print(f"   ✅ Focused category specialist")
        elif len(result['categories']) <= 3:
            print(f"   ✅ Balanced category focus")
        else:
            print(f"   ⚠️ Too many categories ({len(result['categories'])})")
        
        if is_good:
            print(f"\n🎯 RECOMMENDATION: Good candidate for copying!")
        else:
            print(f"\n❌ RECOMMENDATION: Not ideal for copying")
    
    async def close(self):
        await self.client.close()


async def discover_top_wallets():
    """Discover top wallets from leaderboard"""
    config = {
        "monitoring": {
            "rpc_endpoints": ["https://polygon-rpc.com"],
            "graphql_endpoint": "https://api.polymarket.com/graphql"
        }
    }
    
    client = PolymarketClient(config)
    
    print("🔍 Discovering top wallets from Polymarket leaderboard...")
    print("=" * 60)
    
    try:
        candidates = await client.discover_profitable_wallets(
            min_monthly_trades=5,
            min_win_rate=0.55,
            lookback_days=90
        )
        
        print(f"\n🎯 Found {len(candidates)} candidate wallets:\n")
        
        for i, wallet in enumerate(candidates[:10], 1):
            print(f"{i}. {wallet['address']}")
            print(f"   Profit: ${wallet['profit']:,.2f}")
            print(f"   Win Rate: {wallet['win_rate']*100:.1f}%")
            print(f"   Monthly Trades: {wallet['monthly_trades']:.1f}")
            print(f"   Categories: {', '.join(wallet['categories'][:3])}")
            print()
        
        # Save to file
        with open("discovered_wallets.json", "w") as f:
            json.dump(candidates[:20], f, indent=2)
        
        print(f"💾 Saved top 20 wallets to discovered_wallets.json")
        
    finally:
        await client.close()


async def main():
    import os
    
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  python wallet_analyzer.py <wallet_address>  - Analyze a specific wallet")
        print(f"  python wallet_analyzer.py --discover         - Discover top wallets")
        print()
        print("Example:")
        print(f"  python wallet_analyzer.py 0x1234...abcd")
        sys.exit(1)
    
    if sys.argv[1] == "--discover":
        await discover_top_wallets()
    else:
        wallet_address = sys.argv[1]
        
        analyzer = WalletAnalyzer()
        try:
            await analyzer.analyze(wallet_address)
        finally:
            await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
