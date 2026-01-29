#!/usr/bin/env python3
"""
Simple market monitor that displays live market data
Good starting point for building a dashboard
"""

import requests
import time
import os
from datetime import datetime

class SimpleMonitor:
    def __init__(self):
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.data_url = "https://data-api.polymarket.com"
        self.clob_url = "https://clob.polymarket.com"
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def get_trending_markets(self, limit=10):
        """Get top markets by 24h volume"""
        response = requests.get(
            f"{self.gamma_url}/markets",
            params={
                "active": "true",
                "limit": limit,
                "order": "volume24hr"
            }
        )
        return response.json()
    
    def get_market_price(self, token_id):
        """Get last trade price for a token"""
        try:
            response = requests.get(
                f"{self.clob_url}/last-trade-price",
                params={"token_id": token_id}
            )
            return response.json().get('price')
        except:
            return None
    
    def format_market_row(self, market, index):
        """Format a market as a table row"""
        question = market.get('question', 'Unknown')[:50]
        volume = market.get('volume24hr', 0)
        liquidity = market.get('liquidity', 0)
        
        # Get prices
        prices = []
        if 'outcomePrices' in market:
            for i, price in enumerate(market['outcomePrices']):
                outcome = market['outcomes'][i]
                prices.append(f"{outcome}: {float(price)*100:.1f}%")
        
        price_str = " | ".join(prices) if prices else "N/A"
        
        return (
            f"{index:2d}. {question:50s} | "
            f"Vol: ${volume/1000:.1f}K | "
            f"Liq: ${liquidity/1000:.1f}K | "
            f"{price_str}"
        )
    
    def display_header(self):
        """Display dashboard header"""
        print("="*120)
        print("  POLYMARKET LIVE MONITOR")
        print("  Press Ctrl+C to exit")
        print("="*120)
        print(f"  Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*120)
        print()
    
    def run(self, refresh_interval=30, num_markets=15):
        """Run the monitor"""
        try:
            while True:
                self.clear_screen()
                self.display_header()
                
                # Fetch markets
                print("📊 Top Markets by 24h Volume:\n")
                markets = self.get_trending_markets(num_markets)
                
                for i, market in enumerate(markets, 1):
                    print(self.format_market_row(market, i))
                
                print(f"\n{'='*120}")
                print(f"Refreshing in {refresh_interval} seconds...")
                
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitor stopped by user.")
        except Exception as e:
            print(f"\n\nError: {e}")

def main():
    monitor = SimpleMonitor()
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║          POLYMARKET SIMPLE MONITOR                         ║
║                                                            ║
║  This will display top markets refreshed every 30s        ║
║  Press Ctrl+C to stop                                     ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    input("Press Enter to start...")
    monitor.run(refresh_interval=30, num_markets=15)

if __name__ == "__main__":
    main()
