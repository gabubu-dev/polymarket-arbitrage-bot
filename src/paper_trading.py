"""
Paper trading simulator for testing without real API calls.

Simulates Polymarket and exchange behavior for safe testing.
"""

import logging
import random
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from logger import setup_logger


class PaperPolymarketClient:
    """
    Paper trading version of PolymarketClient.
    
    Simulates market data and order execution without real API calls.
    """
    
    def __init__(self, api_key: str = "", private_key: str = "", 
                 chain_id: int = 137, funder_address: str = ""):
        """Initialize paper trading client."""
        self.logger = setup_logger("PaperPolymarketClient", level="INFO")
        self.logger.info("🎯 PAPER TRADING MODE ACTIVE - No real trades will be executed")
        
        # Simulated markets
        self.markets = self._generate_mock_markets()
        self.orders = {}
        self.positions = {}
        
    def _generate_mock_markets(self) -> List[Dict[str, Any]]:
        """Generate mock market data across ALL categories."""
        markets = []
        
        # CRYPTO MARKETS - Price predictions
        crypto_assets = ['BTC', 'ETH', 'SOL', 'MATIC', 'AVAX', 'DOGE', 'XRP', 'ADA']
        for asset in crypto_assets:
            base_price = {'BTC': 50000, 'ETH': 2500, 'SOL': 100, 'MATIC': 1, 'AVAX': 30, 'DOGE': 0.1, 'XRP': 0.5, 'ADA': 0.5}
            for i in range(2):
                market_id = f"{asset.lower()}_price_{i}"
                markets.append({
                    'id': market_id,
                    'question': f'Will {asset} be above ${base_price[asset] + i*10} in next hour?',
                    'active': True,
                    'tokens': [
                        {'outcome': 'Yes', 'price': 0.50 + random.uniform(-0.2, 0.2)},
                        {'outcome': 'No', 'price': 0.50 + random.uniform(-0.2, 0.2)}
                    ],
                    'asset': asset,
                    'category': 'crypto',
                    'timeframe': '1HR'
                })
        
        # POLITICS MARKETS
        politics_questions = [
            'Will Trump win 2024 election?',
            'Will Biden be president on Jan 1 2025?',
            'Will there be a government shutdown this year?',
            'Will Republicans control the House?',
            'Will Democrats control the Senate?',
            'Will there be a recession in 2024?'
        ]
        for i, q in enumerate(politics_questions):
            markets.append({
                'id': f'politics_{i}',
                'question': q,
                'active': True,
                'tokens': [
                    {'outcome': 'Yes', 'price': 0.50 + random.uniform(-0.3, 0.3)},
                    {'outcome': 'No', 'price': 0.50 + random.uniform(-0.3, 0.3)}
                ],
                'category': 'politics',
                'timeframe': 'LONG'
            })
        
        # SPORTS MARKETS
        sports_questions = [
            'Will Lakers win NBA championship?',
            'Will Tom Brady return to NFL?',
            'Will Messi win Ballon d\'Or?',
            'Will Yankees win World Series?',
            'Will Tyson Fury fight in 2024?'
        ]
        for i, q in enumerate(sports_questions):
            markets.append({
                'id': f'sports_{i}',
                'question': q,
                'active': True,
                'tokens': [
                    {'outcome': 'Yes', 'price': 0.50 + random.uniform(-0.25, 0.25)},
                    {'outcome': 'No', 'price': 0.50 + random.uniform(-0.25, 0.25)}
                ],
                'category': 'sports',
                'timeframe': 'MEDIUM'
            })
        
        # POP CULTURE / SOCIAL MARKETS
        pop_questions = [
            'Will Taylor Swift release new album this year?',
            'Will Kardashians announce new business?',
            'Will Netflix add 10M subscribers?',
            'Will new Marvel movie gross $1B?',
            'Will Twitter rebrand again?'
        ]
        for i, q in enumerate(pop_questions):
            markets.append({
                'id': f'pop_culture_{i}',
                'question': q,
                'active': True,
                'tokens': [
                    {'outcome': 'Yes', 'price': 0.50 + random.uniform(-0.2, 0.2)},
                    {'outcome': 'No', 'price': 0.50 + random.uniform(-0.2, 0.2)}
                ],
                'category': 'pop-culture',
                'timeframe': 'MEDIUM'
            })
        
        # BUSINESS MARKETS
        business_questions = [
            'Will Apple hit $4T market cap?',
            'Will there be a major tech IPO?',
            'Will Tesla open new factory?',
            'Will there be a mega merger?',
            'Will oil hit $100/barrel?'
        ]
        for i, q in enumerate(business_questions):
            markets.append({
                'id': f'business_{i}',
                'question': q,
                'active': True,
                'tokens': [
                    {'outcome': 'Yes', 'price': 0.50 + random.uniform(-0.2, 0.2)},
                    {'outcome': 'No', 'price': 0.50 + random.uniform(-0.2, 0.2)}
                ],
                'category': 'business',
                'timeframe': 'MEDIUM'
            })
        
        self.logger.info(f"Generated {len(markets)} mock markets across all categories")
        return markets
    
    def get_crypto_markets(self, asset: str = "BTC", 
                           timeframe: str = "15") -> List[Dict[str, Any]]:
        """Get simulated crypto markets."""
        filtered = [m for m in self.markets if m.get('asset') == asset.upper()]
        self.logger.info(f"Returning {len(filtered)} {asset} markets")
        return filtered
    
    def get_markets_by_category(self, category: str = None) -> List[Dict[str, Any]]:
        """Get markets by category (crypto, politics, sports, etc.)"""
        if category:
            filtered = [m for m in self.markets if m.get('category') == category]
            self.logger.info(f"Returning {len(filtered)} {category} markets")
            return filtered
        return self.markets
    
    def get_all_active_markets(self) -> List[Dict[str, Any]]:
        """Get ALL active markets across all categories."""
        active = [m for m in self.markets if m.get('active', True)]
        self.logger.info(f"Returning {len(active)} total active markets")
        return active
    
    def get_market_odds(self, market_id: str) -> Optional[Dict[str, float]]:
        """
        Get current odds for a market (simulated).
        
        Returns:
            Dict with 'yes' and 'no' odds, or None if market not found
        """
        market = next((m for m in self.markets if m['id'] == market_id), None)
        
        if not market:
            return None
        
        # Simulate changing odds
        yes_price = market['tokens'][0]['price']
        no_price = market['tokens'][1]['price']
        
        # Add some random variation to simulate market movement
        yes_price += random.uniform(-0.05, 0.05)
        yes_price = max(0.01, min(0.99, yes_price))
        no_price = 1.0 - yes_price
        
        return {'yes': yes_price, 'no': no_price}
    
    async def place_order(self, market_id: str, side: str, 
                         size: float, price: float) -> Optional[str]:
        """
        Simulate placing an order.
        
        Args:
            market_id: Market ID
            side: BUY or SELL
            size: Order size in USD
            price: Limit price
            
        Returns:
            Simulated order ID
        """
        order_id = str(uuid.uuid4())[:8]
        
        self.orders[order_id] = {
            'market_id': market_id,
            'side': side,
            'size': size,
            'price': price,
            'status': 'FILLED',  # Simulate instant fill
            'timestamp': datetime.now()
        }
        
        self.logger.info(
            f"📝 PAPER ORDER: {side} ${size:.2f} @ {price:.3f} "
            f"on market {market_id} (Order ID: {order_id})"
        )
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        return order_id
    
    def get_balance(self) -> float:
        """Return simulated balance."""
        return 100.0  # $100 paper trading balance
    
    async def cancel_order(self, order_id: str) -> bool:
        """Simulate order cancellation."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELLED'
            self.logger.info(f"📝 PAPER ORDER CANCELLED: {order_id}")
            return True
        return False


class PaperExchangeMonitor:
    """
    Paper trading version of exchange monitor.
    
    Generates simulated price movements for crypto assets.
    """
    
    def __init__(self):
        """Initialize paper exchange monitor."""
        self.logger = setup_logger("PaperExchangeMonitor", level="INFO")
        self.logger.info("🎯 PAPER EXCHANGE MONITOR ACTIVE")
        
        # Starting prices
        self.prices = {
            'BTC/USDT': 50000.0,
            'ETH/USDT': 2500.0,
            'BTC/USD': 50000.0,
            'ETH/USD': 2500.0
        }
        
        self.callbacks = []
        self.running = False
        
    def add_price_callback(self, callback):
        """Register a callback for price updates."""
        self.callbacks.append(callback)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        Returns:
            Current price or None if symbol not found
        """
        return self.prices.get(symbol)
    
    async def start_all(self):
        """Start simulated price feed."""
        self.logger.info("🚀 Starting simulated price feed for all symbols...")
        self.running = True
        
        # Log initial prices
        for symbol, price in self.prices.items():
            self.logger.info(f"  {symbol}: ${price:,.2f}")
        
        # Start price generation task
        task = asyncio.create_task(self._generate_prices())
        self.logger.info("✅ Price generation task started")
        
        # Give it a moment to start generating
        await asyncio.sleep(0.1)
    
    async def stop_all(self):
        """Stop simulated price feed."""
        self.logger.info("Stopping simulated price feed...")
        self.running = False
    
    async def _generate_prices(self):
        """Generate simulated price movements."""
        self.logger.info("💹 Price generation loop started")
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                
                for symbol in self.prices.keys():
                    # More aggressive random walk for testing
                    # Increase volatility to 1-2% std dev for more spikes
                    change_pct = random.gauss(0, 0.015)  # 1.5% std dev
                    
                    # More frequent larger moves (simulate news events)
                    if random.random() < 0.15:  # 15% chance of big move
                        change_pct = random.gauss(0, 0.035)  # 3.5% std dev for spikes
                    
                    old_price = self.prices[symbol]
                    new_price = old_price * (1 + change_pct)
                    self.prices[symbol] = new_price
                    
                    # Notify callbacks
                    for callback in self.callbacks:
                        try:
                            await callback(symbol, new_price, datetime.now())
                        except Exception as e:
                            self.logger.error(f"Error in price callback: {e}")
                    
                    # Log all moves for first 5 iterations, then just significant ones
                    if iteration <= 5 or abs(change_pct) > 0.01:  # >1% move
                        self.logger.info(
                            f"💹 {symbol}: ${old_price:,.2f} → ${new_price:,.2f} "
                            f"({change_pct:+.2%})"
                        )
                
                # Update every 1-3 seconds for faster testing
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                self.logger.error(f"Error generating prices: {e}", exc_info=True)
                await asyncio.sleep(5)
