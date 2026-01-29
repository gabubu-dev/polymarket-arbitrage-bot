#!/usr/bin/env python3
"""
Mock trading mode - generates realistic trading opportunities for testing.
Run alongside the main bot to simulate market activity.
"""

import asyncio
import random
import time
from datetime import datetime
import sys
sys.path.insert(0, 'src')

from paper_trader import PaperTrader
from market_discovery import PolymarketDiscovery
import json

class MockTradingEngine:
    """Generates mock trading opportunities."""
    
    def __init__(self, min_interval=30, max_interval=120):
        self.paper_trader = PaperTrader(
            initial_balance=10000.0,
            data_dir='data',
            enable_realism=True
        )
        self.min_interval = min_interval  # Min seconds between trades
        self.max_interval = max_interval  # Max seconds between trades
        self.running = False
        
        # Load real markets
        config = json.load(open('config.json'))
        self.discovery = PolymarketDiscovery(config)
        self.markets = []
        
    async def load_markets(self):
        """Load real market data."""
        print("🔍 Loading real Polymarket markets...")
        markets = self.discovery.fetch_active_markets(force_refresh=True)
        
        # Get unique questions
        seen = set()
        self.markets = []
        for m in markets:
            if m.question not in seen and m.outcome_prices:
                seen.add(m.question)
                self.markets.append({
                    'question': m.question,
                    'market_id': m.market_id,
                    'yes_price': m.outcome_prices[0] if len(m.outcome_prices) > 0 else 0.5,
                    'no_price': m.outcome_prices[1] if len(m.outcome_prices) > 1 else 0.5,
                    'volume': m.volume_24h,
                    'liquidity': m.liquidity
                })
        
        print(f"✓ Loaded {len(self.markets)} real markets")
        
    async def generate_trade(self):
        """Generate a single mock trade."""
        # Pick random market
        market = random.choice(self.markets[:20])  # Top 20 only
        
        # Determine direction based on current price
        if market['yes_price'] > 0.6:
            direction = random.choice(['up', 'down'])  # Could go either way
            entry = market['yes_price'] + random.uniform(-0.05, 0.02)
        elif market['yes_price'] < 0.4:
            direction = random.choice(['up', 'down'])
            entry = market['yes_price'] + random.uniform(-0.02, 0.05)
        else:
            direction = random.choice(['up', 'down'])
            entry = market['yes_price'] + random.uniform(-0.03, 0.03)
        
        entry = max(0.01, min(0.99, entry))
        
        # Position size based on confidence
        size = random.uniform(100, 500)
        
        # Pick strategy
        strategy = random.choice(['latency', 'momentum', 'whale', 'spread'])
        
        print(f"\n🎯 MOCK OPPORTUNITY DETECTED")
        print(f"   Market: {market['question'][:50]}...")
        print(f"   Direction: {direction.upper()}")
        print(f"   Entry: ${entry:.3f}")
        print(f"   Size: ${size:.2f}")
        print(f"   Strategy: {strategy}")
        
        # Open position
        trade = await self.paper_trader.open_position(
            symbol=f"MOCK-{market['market_id'][:6]}",
            market_id=market['market_id'],
            market_name=market['question'],
            direction=direction,
            size_usd=size,
            requested_price=entry,
            strategy=strategy,
            market_liquidity=market['liquidity'],
            volume_24h=market['volume']
        )
        
        if trade:
            # Simulate time passing
            await asyncio.sleep(random.uniform(2, 8))
            
            # Determine exit (60% win rate target)
            if random.random() < 0.6:
                # Win - 3-15% profit
                exit_price = entry * random.uniform(1.03, 1.15)
                result = "🟢 WIN"
            else:
                # Loss - 2-10% loss
                exit_price = entry * random.uniform(0.90, 0.98)
                result = "🔴 LOSS"
            
            exit_price = max(0.01, min(0.99, exit_price))
            
            closed = await self.paper_trader.close_position(
                trade_id=trade.trade_id,
                exit_price=exit_price,
                reason='mock_profit_target' if result == "🟢 WIN" else 'mock_stop_loss'
            )
            
            if closed:
                pnl = closed.pnl
                print(f"   {result}: ${pnl:+.2f}")
                
                # Show updated stats
                stats = self.paper_trader.get_performance_stats()
                print(f"\n📊 UPDATED STATS")
                print(f"   Balance: ${stats['current_balance']:.2f}")
                print(f"   Total P&L: ${stats['total_pnl']:+.2f}")
                print(f"   Win Rate: {stats['win_rate']:.1f}%")
                print(f"   Total Trades: {stats['total_trades']}")
                
                return True
        
        return False
        
    async def run(self):
        """Main loop - generate trades continuously."""
        self.running = True
        
        await self.load_markets()
        
        print("\n" + "="*60)
        print("🚀 MOCK TRADING ENGINE STARTED")
        print("="*60)
        print(f"\nGenerating trades every {self.min_interval}-{self.max_interval}s")
        print("Target: ~60% win rate")
        print("\nPress Ctrl+C to stop\n")
        
        trade_count = 0
        while self.running:
            try:
                success = await self.generate_trade()
                if success:
                    trade_count += 1
                    print(f"\n✅ Trade #{trade_count} completed")
                
                # Wait before next trade
                wait = random.uniform(self.min_interval, self.max_interval)
                print(f"\n⏱️  Next trade in {wait:.0f} seconds...")
                await asyncio.sleep(wait)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Stopping mock trading...")
                self.running = False
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                await asyncio.sleep(10)
        
        # Final report
        print("\n" + "="*60)
        print(self.paper_trader.generate_report())
        print("="*60)

if __name__ == "__main__":
    engine = MockTradingEngine(min_interval=30, max_interval=120)  # 30-120s between trades
    asyncio.run(engine.run())
