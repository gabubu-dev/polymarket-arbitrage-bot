"""
Market discovery for real Polymarket prediction markets.

Fetches active markets across all categories (Politics, Sports, Crypto, Economics, Entertainment)
and ranks them by profitability potential.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


@dataclass
class MarketOpportunity:
    """Represents a discovered market opportunity."""
    market_id: str
    condition_id: str
    question: str
    category: str
    end_date: datetime
    volume_24h: float
    liquidity: float
    tokens: List[Dict[str, Any]]
    profitability_score: float
    confidence: float
    best_bid: float
    best_ask: float
    spread: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'market_id': self.market_id,
            'condition_id': self.condition_id,
            'question': self.question,
            'category': self.category,
            'end_date': self.end_date.isoformat() if isinstance(self.end_date, datetime) else self.end_date,
            'volume_24h': self.volume_24h,
            'liquidity': self.liquidity,
            'tokens': self.tokens,
            'profitability_score': self.profitability_score,
            'confidence': self.confidence,
            'best_bid': self.best_bid,
            'best_ask': self.best_ask,
            'spread': self.spread
        }


class PolymarketDiscovery:
    """
    Discovers and ranks active Polymarket prediction markets.
    
    Fetches markets across ALL categories (no restrictions) and ranks them
    by profitability potential based on: profit margin × volume × confidence
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger("PolymarketDiscovery")
        self.config = config
        
        # API endpoints
        self.gamma_api = "https://gamma-api.polymarket.com"
        self.clob_api = "https://clob.polymarket.com"
        
        # Market cache
        self.markets_cache: List[MarketOpportunity] = []
        self.last_refresh: Optional[datetime] = None
        self.refresh_interval = timedelta(hours=1)  # Refresh every hour
        
        # Categories to monitor (ALL categories for profit-first approach)
        self.categories = [
            "politics",
            "sports",
            "crypto",
            "economics",
            "entertainment",
            "business",
            "science",
            "world"
        ]
        
        # Minimum thresholds for quality markets
        self.min_volume_24h = config.get('market_discovery', {}).get('min_volume_24h', 1000.0)
        self.min_liquidity = config.get('market_discovery', {}).get('min_liquidity', 500.0)
        self.max_spread_percent = config.get('market_discovery', {}).get('max_spread_percent', 5.0)
        
        self.logger.info("PolymarketDiscovery initialized - monitoring ALL categories")
    
    def fetch_active_markets(self, force_refresh: bool = False) -> List[MarketOpportunity]:
        """
        Fetch all active Polymarket markets across all categories.
        
        Args:
            force_refresh: Force refresh even if cache is fresh
            
        Returns:
            List of market opportunities sorted by profitability score
        """
        # Check cache freshness
        if not force_refresh and self.last_refresh:
            age = datetime.now() - self.last_refresh
            if age < self.refresh_interval:
                self.logger.info(f"Using cached markets (age: {age.total_seconds():.0f}s)")
                return self.markets_cache
        
        self.logger.info("Fetching active markets from Polymarket Gamma API")
        
        all_markets = []
        
        # Fetch markets for each category
        for category in self.categories:
            try:
                markets = self._fetch_category_markets(category)
                all_markets.extend(markets)
                self.logger.info(f"Found {len(markets)} markets in {category}")
            except Exception as e:
                self.logger.error(f"Error fetching {category} markets: {e}")
        
        # Rank markets by profitability
        ranked_markets = self.rank_by_profitability(all_markets)
        
        # Update cache
        self.markets_cache = ranked_markets
        self.last_refresh = datetime.now()
        
        self.logger.info(
            f"Market discovery complete: {len(ranked_markets)} opportunities found"
        )
        
        return ranked_markets
    
    def _fetch_category_markets(self, category: str) -> List[MarketOpportunity]:
        """Fetch markets for a specific category."""
        try:
            # Query Gamma API for active markets in category
            url = f"{self.gamma_api}/markets"
            params = {
                "tag": category,
                "active": "true",
                "closed": "false",
                "limit": 100
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            raw_markets = response.json()
            
            # Parse markets
            opportunities = []
            for market_data in raw_markets:
                try:
                    opportunity = self._parse_market(market_data, category)
                    if opportunity:
                        opportunities.append(opportunity)
                except Exception as e:
                    self.logger.debug(f"Error parsing market: {e}")
                    continue
            
            return opportunities
            
        except requests.RequestException as e:
            self.logger.error(f"Network error fetching {category} markets: {e}")
            return []
    
    def _parse_market(self, market_data: Dict, category: str) -> Optional[MarketOpportunity]:
        """Parse raw market data into MarketOpportunity."""
        try:
            # Extract basic info
            market_id = market_data.get('id')
            condition_id = market_data.get('conditionId')
            question = market_data.get('question', '')
            
            if not market_id or not question:
                return None
            
            # Get volume and liquidity
            volume_24h = float(market_data.get('volume24hr', 0))
            liquidity = float(market_data.get('liquidity', 0))
            
            # Filter out low-quality markets
            if volume_24h < self.min_volume_24h or liquidity < self.min_liquidity:
                return None
            
            # Get tokens (YES/NO outcomes)
            tokens = market_data.get('tokens', [])
            
            # Get orderbook data to calculate spread
            best_bid, best_ask, spread = self._get_market_spread(market_id)
            
            # Filter by spread
            spread_percent = spread * 100
            if spread_percent > self.max_spread_percent:
                return None
            
            # Parse end date
            end_date_str = market_data.get('endDate')
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')) if end_date_str else datetime.now() + timedelta(days=1)
            
            # Calculate profitability score (will be set by rank_by_profitability)
            profitability_score = 0.0
            
            # Calculate confidence based on liquidity and volume
            confidence = min(1.0, (liquidity / 5000.0) * 0.5 + (volume_24h / 10000.0) * 0.5)
            
            return MarketOpportunity(
                market_id=market_id,
                condition_id=condition_id,
                question=question,
                category=category,
                end_date=end_date,
                volume_24h=volume_24h,
                liquidity=liquidity,
                tokens=tokens,
                profitability_score=profitability_score,
                confidence=confidence,
                best_bid=best_bid,
                best_ask=best_ask,
                spread=spread
            )
            
        except Exception as e:
            self.logger.debug(f"Error parsing market: {e}")
            return None
    
    def _get_market_spread(self, market_id: str) -> tuple[float, float, float]:
        """
        Get best bid/ask and spread for a market.
        
        Returns:
            Tuple of (best_bid, best_ask, spread)
        """
        try:
            # Query orderbook from CLOB API
            url = f"{self.clob_api}/book"
            params = {"token_id": market_id}
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            orderbook = response.json()
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            best_bid = float(bids[0]['price']) if bids else 0.0
            best_ask = float(asks[0]['price']) if asks else 1.0
            spread = best_ask - best_bid
            
            return best_bid, best_ask, spread
            
        except Exception as e:
            self.logger.debug(f"Could not fetch spread for {market_id}: {e}")
            return 0.5, 0.5, 0.0
    
    def rank_by_profitability(self, markets: List[MarketOpportunity]) -> List[MarketOpportunity]:
        """
        Rank markets by profitability potential.
        
        Formula: profitability_score = (profit_margin × volume × confidence) / risk_factor
        
        Args:
            markets: List of market opportunities
            
        Returns:
            Sorted list (highest profitability first)
        """
        for market in markets:
            # Profit margin from spread
            profit_margin = market.spread if market.spread > 0 else 0.01
            
            # Volume factor (normalized)
            volume_factor = min(1.0, market.volume_24h / 50000.0)
            
            # Liquidity factor (normalized)
            liquidity_factor = min(1.0, market.liquidity / 10000.0)
            
            # Time to expiry (markets closer to expiry are riskier)
            time_to_expiry = (market.end_date - datetime.now()).total_seconds()
            time_factor = min(1.0, max(0.1, time_to_expiry / 86400))  # Days until expiry
            
            # Risk factor (inverse of confidence)
            risk_factor = max(0.1, 1.0 - market.confidence)
            
            # Calculate profitability score
            market.profitability_score = (
                profit_margin * 
                volume_factor * 
                liquidity_factor *
                time_factor *
                market.confidence
            ) / risk_factor
        
        # Sort by profitability score (descending)
        markets.sort(key=lambda m: m.profitability_score, reverse=True)
        
        return markets
    
    def filter_by_liquidity(self, markets: List[MarketOpportunity], 
                           min_liquidity: float) -> List[MarketOpportunity]:
        """
        Filter markets by minimum liquidity.
        
        Args:
            markets: List of markets
            min_liquidity: Minimum liquidity in USD
            
        Returns:
            Filtered list
        """
        return [m for m in markets if m.liquidity >= min_liquidity]
    
    def get_top_opportunities(self, n: int = 10) -> List[MarketOpportunity]:
        """
        Get top N market opportunities.
        
        Args:
            n: Number of opportunities to return
            
        Returns:
            Top N markets by profitability score
        """
        if not self.markets_cache:
            self.fetch_active_markets()
        
        return self.markets_cache[:n]
    
    def refresh_market_list(self) -> None:
        """Force refresh of market list."""
        self.logger.info("Force refreshing market list")
        self.fetch_active_markets(force_refresh=True)
    
    def get_market_by_id(self, market_id: str) -> Optional[MarketOpportunity]:
        """Get a specific market by ID."""
        for market in self.markets_cache:
            if market.market_id == market_id:
                return market
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get discovery statistics."""
        if not self.markets_cache:
            return {
                "total_markets": 0,
                "categories": {},
                "avg_profitability": 0.0,
                "avg_volume": 0.0,
                "avg_liquidity": 0.0
            }
        
        # Calculate stats
        category_counts = {}
        for market in self.markets_cache:
            category_counts[market.category] = category_counts.get(market.category, 0) + 1
        
        avg_profitability = sum(m.profitability_score for m in self.markets_cache) / len(self.markets_cache)
        avg_volume = sum(m.volume_24h for m in self.markets_cache) / len(self.markets_cache)
        avg_liquidity = sum(m.liquidity for m in self.markets_cache) / len(self.markets_cache)
        
        return {
            "total_markets": len(self.markets_cache),
            "categories": category_counts,
            "avg_profitability": round(avg_profitability, 4),
            "avg_volume": round(avg_volume, 2),
            "avg_liquidity": round(avg_liquidity, 2),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None
        }
