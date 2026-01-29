"""
Optimized Polymarket API client with caching and retry logic.

Enhanced version with:
- Response caching with TTL
- Exponential backoff retry
- Structured logging
- Metrics collection
- Async optimizations
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging

import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

from cache import AsyncTTLCache, odds_cache, market_cache
from retry_utils import retry, API_RETRY_CONFIG, RetryConfig
from structured_logging import StructuredLogger
from metrics import get_metrics

logger = StructuredLogger("PolymarketClient", logging.getLogger("PolymarketClient"))


class OptimizedPolymarketClient:
    """
    Optimized Polymarket client with caching, retry logic, and metrics.
    
    Features:
    - Response caching with configurable TTL
    - Automatic retry with exponential backoff
    - Structured logging
    - Performance metrics collection
    - Async batch operations
    """
    
    # Configuration constants
    DEFAULT_MARKET_CACHE_TTL = 30.0  # 30 seconds
    DEFAULT_ODDS_CACHE_TTL = 3.0     # 3 seconds
    GAMMA_API_BASE = "https://gamma-api.polymarket.com"
    CLOB_HOST = "https://clob.polymarket.com"
    
    def __init__(
        self,
        api_key: str = "",
        private_key: str = "",
        chain_id: int = 137,
        funder_address: str = "",
        market_cache_ttl: float = DEFAULT_MARKET_CACHE_TTL,
        odds_cache_ttl: float = DEFAULT_ODDS_CACHE_TTL,
        enable_caching: bool = True
    ):
        """
        Initialize optimized Polymarket client.
        
        Args:
            api_key: Polymarket API key
            private_key: Polygon wallet private key
            chain_id: Polygon chain ID (137 for mainnet, 80002 for testnet)
            funder_address: Polymarket Safe proxy address
            market_cache_ttl: Cache TTL for market data (seconds)
            odds_cache_ttl: Cache TTL for odds data (seconds)
            enable_caching: Whether to enable response caching
        """
        self.api_key = api_key
        self.private_key = private_key
        self.chain_id = chain_id
        self.funder_address = funder_address
        self.enable_caching = enable_caching
        
        # Caches
        self._market_cache = AsyncTTLCache(
            default_ttl=market_cache_ttl,
            max_size=500
        ) if enable_caching else None
        self._odds_cache = AsyncTTLCache(
            default_ttl=odds_cache_ttl,
            max_size=2000
        ) if enable_caching else None
        
        # Initialize CLOB client
        self._client: Optional[ClobClient] = None
        self._client_initialized = False
        
        # Metrics
        self._metrics = get_metrics()
        
        logger.info(
            "Polymarket client initialized",
            chain_id=chain_id,
            caching_enabled=enable_caching,
            market_cache_ttl=market_cache_ttl,
            odds_cache_ttl=odds_cache_ttl
        )
    
    async def _ensure_client(self) -> Optional[ClobClient]:
        """Ensure CLOB client is initialized."""
        if self._client_initialized:
            return self._client
        
        if not self.private_key:
            return None
        
        try:
            start_time = time.time()
            
            self._client = ClobClient(
                host=self.CLOB_HOST,
                chain_id=self.chain_id,
                key=self.private_key,
                signature_type=2 if self.funder_address else 0,
                funder=self.funder_address if self.funder_address else None
            )
            
            # Create or derive API credentials
            if self._client:
                api_creds = self._client.create_or_derive_api_creds()
                self._client.set_api_creds(api_creds)
            
            latency_ms = (time.time() - start_time) * 1000
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='init_client',
                latency_ms=latency_ms,
                success=True
            )
            
            self._client_initialized = True
            logger.info("Polymarket CLOB client initialized successfully")
            
        except Exception as e:
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='init_client',
                latency_ms=0,
                success=False,
                error=str(e)
            )
            logger.error(f"Failed to initialize Polymarket client: {e}")
            self._client = None
        
        return self._client
    
    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        retryable_exceptions=(requests.RequestException, ConnectionError, TimeoutError)
    )
    async def get_crypto_markets(
        self,
        asset: str = "BTC",
        timeframe: str = "15"
    ) -> List[Dict[str, Any]]:
        """
        Get active crypto price prediction markets with caching.
        
        Args:
            asset: Crypto asset (BTC, ETH, SOL, XRP, etc.)
            timeframe: Market timeframe in minutes (15, 60, etc.)
            
        Returns:
            List of market dictionaries
        """
        cache_key = f"markets:{asset}:{timeframe}"
        
        # Check cache
        if self.enable_caching and self._market_cache:
            cached = await self._market_cache.aget(cache_key)
            if cached is not None:
                self._metrics.record_api_call(
                    api_name='polymarket',
                    endpoint='get_crypto_markets',
                    latency_ms=0,
                    success=True,
                    cache_hit=True
                )
                return cached
        
        # Fetch from API
        start_time = time.time()
        
        try:
            url = f"{self.GAMMA_API_BASE}/events"
            params = {
                "tag": "crypto",
                "active": "true",
                "closed": "false"
            }
            
            response = await asyncio.to_thread(
                requests.get,
                url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            events = response.json()
            
            # Filter for specific asset and timeframe
            filtered_markets = []
            for event in events:
                question = event.get('question', '').upper()
                
                if asset.upper() in question and f"{timeframe}" in question:
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
                            'volume': float(market.get('volume', 0) or 0),
                            'liquidity': float(market.get('liquidity', 0) or 0)
                        }
                        filtered_markets.append(market_data)
            
            latency_ms = (time.time() - start_time) * 1000
            
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='get_crypto_markets',
                latency_ms=latency_ms,
                success=True
            )
            
            logger.info(
                f"Fetched {len(filtered_markets)} {asset} markets",
                asset=asset,
                timeframe=timeframe,
                latency_ms=latency_ms
            )
            
            # Cache result
            if self.enable_caching and self._market_cache:
                await self._market_cache.aset(cache_key, filtered_markets)
            
            return filtered_markets
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='get_crypto_markets',
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
            logger.error(
                f"Error fetching markets: {e}",
                asset=asset,
                timeframe=timeframe,
                error=str(e)
            )
            raise
    
    @retry(
        max_attempts=3,
        base_delay=0.5,
        max_delay=10.0,
        retryable_exceptions=(Exception,)
    )
    async def get_market_odds(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current odds for a specific market token with caching.
        
        Args:
            token_id: Polymarket token ID
            
        Returns:
            Dictionary with price info or None if unavailable
        """
        cache_key = f"odds:{token_id}"
        
        # Check cache
        if self.enable_caching and self._odds_cache:
            cached = await self._odds_cache.aget(cache_key)
            if cached is not None:
                self._metrics.record_api_call(
                    api_name='polymarket',
                    endpoint='get_market_odds',
                    latency_ms=0,
                    success=True,
                    cache_hit=True
                )
                return cached
        
        # Fetch from API
        client = await self._ensure_client()
        if not client:
            return None
        
        start_time = time.time()
        
        try:
            orderbook = await asyncio.to_thread(client.get_order_book, token_id)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            best_bid = float(bids[0]['price']) if bids else 0.0
            best_ask = float(asks[0]['price']) if asks else 1.0
            
            bid_size = float(bids[0]['size']) if bids else 0.0
            ask_size = float(asks[0]['size']) if asks else 0.0
            
            mid_price = (best_bid + best_ask) / 2 if (bids and asks) else 0.5
            spread = best_ask - best_bid if (bids and asks) else 1.0
            
            result = {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'spread': spread,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'liquidity': bid_size + ask_size,
                'timestamp': datetime.now().isoformat()
            }
            
            latency_ms = (time.time() - start_time) * 1000
            
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='get_market_odds',
                latency_ms=latency_ms,
                success=True
            )
            
            # Cache result
            if self.enable_caching and self._odds_cache:
                await self._odds_cache.aset(cache_key, result)
            
            return result
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='get_market_odds',
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
            logger.error(
                f"Error getting odds for token {token_id}: {e}",
                token_id=token_id,
                error=str(e)
            )
            raise
    
    async def get_batch_odds(
        self,
        token_ids: List[str],
        max_concurrent: int = 10
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get odds for multiple tokens in parallel.
        
        Args:
            token_ids: List of token IDs
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Dictionary mapping token_id to odds data
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_limit(token_id: str) -> tuple[str, Optional[Dict]]:
            async with semaphore:
                try:
                    odds = await self.get_market_odds(token_id)
                    return token_id, odds
                except Exception:
                    return token_id, None
        
        tasks = [fetch_with_limit(tid) for tid in token_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            token_id: result if not isinstance(result, Exception) else None
            for token_id, result in results
        }
    
    @retry(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        retryable_exceptions=(Exception,)
    )
    async def place_market_order(
        self,
        token_id: str,
        side: str,
        amount: float
    ) -> Optional[str]:
        """
        Place a market order with retry logic.
        
        Args:
            token_id: Token ID to trade
            side: 'BUY' or 'SELL'
            amount: Amount in USDC
            
        Returns:
            Order ID if successful, None otherwise
        """
        client = await self._ensure_client()
        if not client:
            logger.error("Cannot place order: client not initialized")
            return None
        
        start_time = time.time()
        
        try:
            order_args = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=BUY if side.upper() == 'BUY' else SELL
            )
            
            signed_order = await asyncio.to_thread(
                client.create_market_order,
                order_args
            )
            
            response = await asyncio.to_thread(
                client.post_order,
                signed_order,
                OrderType.FOK
            )
            
            order_id = response.get('orderID')
            latency_ms = (time.time() - start_time) * 1000
            
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='place_market_order',
                latency_ms=latency_ms,
                success=True
            )
            
            logger.info(
                f"Placed market order: {side} ${amount} for token {token_id}",
                token_id=token_id,
                side=side,
                amount=amount,
                order_id=order_id,
                latency_ms=latency_ms
            )
            
            return order_id
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._metrics.record_api_call(
                api_name='polymarket',
                endpoint='place_market_order',
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
            logger.error(
                f"Error placing market order: {e}",
                token_id=token_id,
                side=side,
                amount=amount,
                error=str(e)
            )
            raise
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions."""
        client = await self._ensure_client()
        if not client:
            return []
        
        try:
            # This would need to be implemented based on actual CLOB client API
            return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    async def get_balance(self) -> float:
        """Get account balance in USDC."""
        client = await self._ensure_client()
        if not client:
            return 0.0
        
        try:
            # This would need to be implemented based on actual CLOB client API
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0.0
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        if self._market_cache:
            asyncio.create_task(self._market_cache.aclear())
        if self._odds_cache:
            asyncio.create_task(self._odds_cache.aclear())
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {}
        if self._market_cache:
            stats['market_cache'] = self._market_cache.get_stats()
        if self._odds_cache:
            stats['odds_cache'] = self._odds_cache.get_stats()
        return stats
