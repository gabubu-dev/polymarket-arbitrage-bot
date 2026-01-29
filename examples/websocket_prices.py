#!/usr/bin/env python3
"""
Real-time price feed using WebSocket
Shows live price updates for top markets
"""

import asyncio
import websockets
import json
import requests
from datetime import datetime

class PriceTracker:
    def __init__(self):
        self.prices = {}
        self.market_names = {}
    
    def get_top_markets(self, limit=5):
        """Get top markets and their token IDs"""
        response = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={
                "active": "true",
                "limit": limit,
                "order": "volume24hr"
            }
        )
        markets = response.json()
        
        token_ids = []
        for market in markets:
            for token in market.get('tokens', []):
                token_id = token['tokenId']
                token_ids.append(token_id)
                # Store market name for this token
                self.market_names[token_id] = {
                    'question': market['question'][:60],
                    'outcome': token['outcome']
                }
        
        return token_ids
    
    async def connect_and_subscribe(self, token_ids):
        """Connect to WebSocket and subscribe to price updates"""
        uri = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        
        print(f"Connecting to Polymarket WebSocket...")
        print(f"Tracking {len(token_ids)} tokens from top markets\n")
        print("="*80)
        
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
                # Subscribe to markets
                subscribe_msg = {
                    "auth": {},
                    "markets": token_ids,
                    "type": "market"
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                print("✓ Connected and subscribed!")
                print("="*80)
                print("Waiting for price updates...\n")
                
                # Listen for updates
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        self.handle_message(data)
                    except websockets.exceptions.ConnectionClosed:
                        print("\nConnection closed. Reconnecting...")
                        break
                    except Exception as e:
                        print(f"\nError handling message: {e}")
                        
        except Exception as e:
            print(f"\nWebSocket error: {e}")
    
    def handle_message(self, data):
        """Handle incoming WebSocket messages"""
        event_type = data.get('event_type')
        
        if event_type == 'price_change':
            asset_id = data.get('asset_id')
            price = float(data.get('price', 0))
            
            # Get market info
            market_info = self.market_names.get(asset_id, {})
            question = market_info.get('question', 'Unknown Market')
            outcome = market_info.get('outcome', 'Unknown')
            
            # Calculate change
            old_price = self.prices.get(asset_id)
            self.prices[asset_id] = price
            
            change_str = ""
            if old_price and old_price != price:
                pct_change = ((price - old_price) / old_price) * 100
                arrow = "↑" if pct_change > 0 else "↓"
                change_str = f"{arrow} {abs(pct_change):.2f}%"
            
            # Print update
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {question}")
            print(f"          {outcome}: {price*100:.2f}% {change_str}")
            print()
            
        elif event_type == 'book':
            # Order book update
            asset_id = data.get('asset_id')
            market_info = self.market_names.get(asset_id, {})
            
            if 'bids' in data and 'asks' in data:
                best_bid = data['bids'][0] if data['bids'] else None
                best_ask = data['asks'][0] if data['asks'] else None
                
                if best_bid and best_ask:
                    spread = float(best_ask['price']) - float(best_bid['price'])
                    print(f"Book update: {market_info.get('question', 'Unknown')[:50]}")
                    print(f"  Bid: ${best_bid['price']} | Ask: ${best_ask['price']} | Spread: ${spread:.4f}")
                    print()
        
        elif event_type == 'last_trade_price':
            # Last trade update
            asset_id = data.get('asset_id')
            price = float(data.get('price', 0))
            market_info = self.market_names.get(asset_id, {})
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] TRADE: {market_info.get('question', 'Unknown')[:50]}")
            print(f"          {market_info.get('outcome', 'Unknown')} @ {price*100:.2f}%")
            print()
    
    async def run(self):
        """Main run loop"""
        # Get top markets
        print("Fetching top markets...")
        token_ids = self.get_top_markets(limit=5)
        
        if not token_ids:
            print("Failed to fetch markets")
            return
        
        print(f"\nTracking {len(self.market_names)} markets:\n")
        for token_id, info in self.market_names.items():
            print(f"  • {info['question']} ({info['outcome']})")
        print()
        
        # Connect and listen
        while True:
            try:
                await self.connect_and_subscribe(token_ids)
                # If connection closes, wait and retry
                print("\nReconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except KeyboardInterrupt:
                print("\n\nStopped by user")
                break
            except Exception as e:
                print(f"\nError: {e}")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║        POLYMARKET REAL-TIME PRICE TRACKER                  ║
║                                                            ║
║  WebSocket connection to Polymarket CLOB                  ║
║  Press Ctrl+C to stop                                     ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    tracker = PriceTracker()
    
    try:
        asyncio.run(tracker.run())
    except KeyboardInterrupt:
        print("\n\nExiting...")

if __name__ == "__main__":
    main()
