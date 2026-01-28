"""
Polymarket API client for prediction market data and trading.

Interfaces with Polymarket's CLOB API to fetch market data,
place orders, and manage positions.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL


class PolymarketClient:
    """
    Client for interacting with Polymarket prediction markets.
    
    Provides methods to query markets, get current odds, and execute trades.
    """
    
    def __init__(self, api_key: str = "", private_key: str = "", 
                 chain_id: int = 137, funder_address: str = ""):
        """
        Initialize Polymarket client.
        
        Args:
            api_key: Polymarket API key (optional, for Builder Program)
            private_key: Polygon wallet private key for signing transactions
            chain_id: Polygon chain ID (137 for mainnet, 80002 for testnet)
            funder_address: Polymarket Safe proxy address
        """
        self.logger = logging.getLogger("PolymarketClient")
        self.api_key = api_key
        self.private_key = private_key
        self.chain_id = chain_id
        self.funder_address = funder_address
        
        # Gamma API endpoint for market discovery
        self.gamma_api_base = "https://gamma-api.polymarket.com"
        
        # Initialize CLOB client if credentials provided
        self.client: Optional[ClobClient] = None
        if private_key:
            try:
                self.client = ClobClient(
                    host="https://clob.polymarket.com",
                    chain_id=chain_id,
                    key=private_key,
                    signature_type=2 if funder_address else 0,  # 2 for proxy, 0 for EOA
                    funder=funder_address if funder_address else None
                )
                
                # Create or derive API credentials
                if self.client:
                    api_creds = self.client.create_or_derive_api_creds()
                    self.client.set_api_creds(api_creds)
                    
                self.logger.info("Polymarket client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Polymarket client: {e}")
        
        # Cache for market data
        self.markets_cache: Dict[str, Any] = {}
        self.last_cache_update: Optional[datetime] = None
        self.cache_ttl = timedelta(minutes=1)  # Shorter cache for active markets
    
    def get_crypto_markets(self, asset: str = "BTC", 
                           timeframe: str = "15") -> List[Dict[str, Any]]:
        """
        Get active crypto price prediction markets using Gamma API.
        
        Args:
            asset: Crypto asset (BTC, ETH, SOL, XRP, etc.)
            timeframe: Market timeframe in minutes (15, 60, etc.)
            
        Returns:
            List of market dictionaries with id, question, odds, tokens, etc.
        """
        self.logger.info(f"Fetching {asset} {timeframe}-minute markets from Gamma API")
        
        try:
            # Query Gamma API for events tagged with 'crypto'
            url = f"{self.gamma_api_base}/events"
            params = {
                "tag": "crypto",
                "active": "true",
                "closed": "false"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            events = response.json()
            
            # Filter for specific asset and timeframe
            filtered_markets = []
            for event in events:
                question = event.get('question', '').upper()
                
                # Check if this is the right asset and timeframe
                if asset.upper() in question and f"{timeframe}" in question:
                    # Extract relevant market data
                    markets = event.get('markets', [])
                    for market in markets:
                        market_data = {
                            'event_id': event.get('id'),
                            'question': event.get('question'),
                            'market_id': market.get('id'),
                            'condition_id': market.get('condition_id'),
                            'tokens': market.get('tokens', []),
                            'outcome': market.get('outcome'),
                            'end_date': event.get('endDate'),
                            'active': event.get('active', True),
                            'volume': market.get('volume', 0),
                            'liquidity': market.get('liquidity', 0)
                        }
                        filtered_markets.append(market_data)
            
            self.logger.info(f"Found {len(filtered_markets)} active {asset} {timeframe}min markets")
            return filtered_markets
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching markets from Gamma API: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error in get_crypto_markets: {e}")
            return []
    
    def get_market_odds(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current odds for a specific market token.
        
        Args:
            token_id: Polymarket token ID (for YES or NO outcome)
            
        Returns:
            Dictionary with price, liquidity, spread info, or None if unavailable
        """
        if not self.client:
            self.logger.warning("Client not initialized, cannot fetch odds")
            return None
        
        try:
            # Get order book for the token
            orderbook = self.client.get_order_book(token_id)
            
            # Extract best bid/ask from order book
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            best_bid = float(bids[0]['price']) if bids else 0.0
            best_ask = float(asks[0]['price']) if asks else 1.0
            
            bid_size = float(bids[0]['size']) if bids else 0.0
            ask_size = float(asks[0]['size']) if asks else 0.0
            
            # Calculate mid price and spread
            mid_price = (best_bid + best_ask) / 2 if (bids and asks) else 0.5
            spread = best_ask - best_bid if (bids and asks) else 1.0
            
            return {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'spread': spread,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'liquidity': bid_size + ask_size,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting odds for token {token_id}: {e}")
            return None
    
    def calculate_implied_price(self, odds: Dict[str, float], 
                               direction: str) -> float:
        """
        Calculate implied crypto price from market odds.
        
        For a "BTC > $50,000 in 15 minutes" market, high YES odds
        imply BTC is expected to go above $50k.
        
        Args:
            odds: Dictionary with 'yes' and 'no' odds
            direction: 'up' or 'down'
            
        Returns:
            Implied probability of price movement
        """
        if direction == "up":
            return odds.get('yes', 0.5)
        else:
            return odds.get('no', 0.5)
    
    def place_market_order(self, token_id: str, side: str, 
                          amount: float) -> Optional[str]:
        """
        Place a market order on Polymarket (immediate execution).
        
        Args:
            token_id: Token ID to trade
            side: 'BUY' or 'SELL'
            amount: Amount in USDC
            
        Returns:
            Order ID if successful, None otherwise
        """
        if not self.client:
            self.logger.error("Cannot place order: client not initialized")
            return None
        
        try:
            # Create market order
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=BUY if side.upper() == 'BUY' else SELL
            )
            
            # Sign and submit order
            signed_order = self.client.create_market_order(order_args)
            response = self.client.post_order(signed_order, OrderType.FOK)  # Fill or Kill
            
            order_id = response.get('orderID')
            
            self.logger.info(
                f"Placed market order: {side} ${amount} for token {token_id}"
            )
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None
    
    def place_limit_order(self, token_id: str, side: str, 
                         size: float, price: float) -> Optional[str]:
        """
        Place a limit order on Polymarket.
        
        Args:
            token_id: Token ID to trade
            side: 'BUY' or 'SELL'
            size: Number of shares
            price: Limit price (0.01 to 0.99)
            
        Returns:
            Order ID if successful, None otherwise
        """
        if not self.client:
            self.logger.error("Cannot place order: client not initialized")
            return None
        
        try:
            # Create limit order arguments
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=BUY if side.upper() == 'BUY' else SELL
            )
            
            # Sign and submit order
            signed_order = self.client.create_order(order_args)
            response = self.client.post_order(signed_order, OrderType.GTC)  # Good Till Cancelled
            
            order_id = response.get('orderID')
            
            self.logger.info(
                f"Placed limit order: {side} {size} shares @ {price} for token {token_id}"
            )
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Error placing limit order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.cancel_order(order_id)
            self.logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current open positions.
        
        Returns:
            List of position dictionaries
        """
        if not self.client:
            return []
        
        try:
            positions = []
            # In real implementation, query Polymarket for positions
            # positions = self.client.get_positions()
            return positions
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_balance(self) -> float:
        """
        Get account balance in USDC.
        
        Returns:
            Balance in USD
        """
        if not self.client:
            return 0.0
        
        try:
            # In real implementation, fetch balance from client
            # balance = self.client.get_balance()
            balance = 0.0
            return balance
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return 0.0
