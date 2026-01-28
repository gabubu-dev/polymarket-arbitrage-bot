"""
Historical data analysis for prediction markets.

This module provides tools for analyzing historical market performance,
calculating statistics, and identifying patterns. Integrates with bot
for historical backtesting and performance analysis.
"""

import time
import logging
import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque


class HistoricalAnalyzer:
    """Analyze historical market data and identify patterns."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize historical analyzer.
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger("HistoricalAnalyzer")
        
        # Load config
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.data_config = config.get('data', {})
        except (FileNotFoundError, json.JSONDecodeError):
            self.data_config = {}
        
        # Data storage
        self._market_data: Dict[str, deque] = {}
        self._max_data_points = 10000
    
    def analyze_market_history(self, market_slug: str, days: int = 30) -> Dict[str, Any]:
        """
        Perform comprehensive historical analysis on a market.
        
        Args:
            market_slug: Market slug identifier
            days: Number of days to analyze
            
        Returns:
            Historical analysis results
        """
        # Fetch historical data
        prices = self._get_historical_prices(market_slug, days)
        
        if not prices:
            return {
                'market_slug': market_slug,
                'error': 'No price data available',
                'period_days': days
            }
        
        # Extract values
        price_values = [p['price'] for p in prices]
        volumes = [p.get('volume', 0) for p in prices]
        
        # Calculate metrics
        volatility = self.calculate_volatility(price_values)
        avg_volume = statistics.mean(volumes) if volumes else 0
        
        # Price statistics
        price_min = min(price_values)
        price_max = max(price_values)
        price_current = price_values[-1]
        price_start = price_values[0]
        price_change = price_current - price_start
        price_change_pct = (price_change / price_start) if price_start != 0 else 0
        
        # Identify trends
        trend = self._identify_trend(price_values)
        support_resistance = self._find_support_resistance(price_values)
        
        return {
            'market_slug': market_slug,
            'period_days': days,
            'data_points': len(prices),
            'price_statistics': {
                'start': round(price_start, 4),
                'current': round(price_current, 4),
                'min': round(price_min, 4),
                'max': round(price_max, 4),
                'change': round(price_change, 4),
                'change_percent': round(price_change_pct, 4),
                'average': round(statistics.mean(price_values), 4),
                'median': round(statistics.median(price_values), 4),
                'std_dev': round(statistics.stdev(price_values), 4) if len(price_values) > 1 else 0
            },
            'volume_statistics': {
                'average': round(avg_volume, 2),
                'total': round(sum(volumes), 2),
                'max': round(max(volumes), 2) if volumes else 0
            },
            'volatility': round(volatility, 4),
            'trend': trend,
            'support_resistance': support_resistance,
            'analysis_time': datetime.now().isoformat()
        }
    
    def calculate_volatility(self, prices: List[float]) -> float:
        """
        Calculate price volatility using standard deviation of returns.
        
        Args:
            prices: List of price values
            
        Returns:
            Volatility measure
        """
        if len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Standard deviation of returns
        return statistics.stdev(returns) if len(returns) > 1 else 0.0
    
    def calculate_sharpe_ratio(self, returns: List[float], 
                               risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio for a series of returns.
        
        Args:
            returns: List of return values
            risk_free_rate: Risk-free rate (default 0)
            
        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0
        
        avg_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns)
        
        if std_dev == 0:
            return 0.0
        
        return (avg_return - risk_free_rate) / std_dev
    
    def find_patterns(self, market_slug: str, days: int = 30) -> Dict[str, Any]:
        """
        Identify recurring patterns in market data.
        
        Args:
            market_slug: Market slug identifier
            days: Number of days to analyze
            
        Returns:
            Identified patterns
        """
        prices = self._get_historical_prices(market_slug, days)
        
        if len(prices) < 24:
            return {
                'market_slug': market_slug,
                'patterns': [],
                'message': 'Insufficient data'
            }
        
        price_values = [p['price'] for p in prices]
        
        patterns = []
        
        # Look for consistent trends
        if self._is_consistent_uptrend(price_values):
            patterns.append({
                'type': 'consistent_uptrend',
                'description': 'Market showing consistent upward movement',
                'confidence': 'high',
                'suggested_action': 'follow_trend'
            })
        
        if self._is_consistent_downtrend(price_values):
            patterns.append({
                'type': 'consistent_downtrend',
                'description': 'Market showing consistent downward movement',
                'confidence': 'high',
                'suggested_action': 'follow_trend'
            })
        
        # Look for consolidation
        if self._is_consolidating(price_values):
            patterns.append({
                'type': 'consolidation',
                'description': 'Market trading in narrow range',
                'confidence': 'medium',
                'suggested_action': 'wait_for_breakout'
            })
        
        # Look for breakout
        recent_breakout = self._detect_breakout(price_values)
        if recent_breakout:
            patterns.append(recent_breakout)
        
        # Look for support/resistance bounces
        bounce_pattern = self._detect_support_bounce(price_values)
        if bounce_pattern:
            patterns.append(bounce_pattern)
        
        return {
            'market_slug': market_slug,
            'patterns': patterns,
            'analysis_period': f'{days} days',
            'pattern_count': len(patterns)
        }
    
    def compare_market_performance(self, market_slugs: List[str], 
                                    days: int = 30) -> List[Dict[str, Any]]:
        """
        Compare historical performance of multiple markets.
        
        Args:
            market_slugs: List of market slugs
            days: Number of days to analyze
            
        Returns:
            Comparative analysis sorted by performance
        """
        results = []
        
        for slug in market_slugs:
            analysis = self.analyze_market_history(slug, days)
            if 'error' not in analysis:
                results.append({
                    'market_slug': slug,
                    'price_change_pct': analysis['price_statistics']['change_percent'],
                    'volatility': analysis['volatility'],
                    'avg_volume': analysis['volume_statistics']['average'],
                    'trend': analysis['trend'],
                    'current_price': analysis['price_statistics']['current']
                })
        
        # Sort by price change
        results.sort(key=lambda x: x['price_change_pct'], reverse=True)
        
        return results
    
    def get_market_summary(self, market_slug: str) -> Dict[str, Any]:
        """
        Get a quick summary of market history.
        
        Args:
            market_slug: Market slug identifier
            
        Returns:
            Market summary
        """
        # 7-day summary
        week_analysis = self.analyze_market_history(market_slug, days=7)
        
        # 30-day summary
        month_analysis = self.analyze_market_history(market_slug, days=30)
        
        return {
            'market_slug': market_slug,
            'week_performance': {
                'change_pct': week_analysis.get('price_statistics', {}).get('change_percent', 0),
                'trend': week_analysis.get('trend', 'unknown'),
                'volatility': week_analysis.get('volatility', 0)
            },
            'month_performance': {
                'change_pct': month_analysis.get('price_statistics', {}).get('change_percent', 0),
                'trend': month_analysis.get('trend', 'unknown'),
                'volatility': month_analysis.get('volatility', 0)
            },
            'patterns': self.find_patterns(market_slug, days=14).get('patterns', []),
            'last_updated': datetime.now().isoformat()
        }
    
    def _identify_trend(self, prices: List[float]) -> str:
        """
        Identify overall trend in prices.
        
        Args:
            prices: List of price values
            
        Returns:
            Trend description
        """
        if len(prices) < 2:
            return 'unknown'
        
        # Split into thirds and compare
        third = len(prices) // 3
        first_third = statistics.mean(prices[:third])
        last_third = statistics.mean(prices[-third:])
        
        change = (last_third - first_third) / first_third if first_third != 0 else 0
        
        if change > 0.15:
            return 'strong_uptrend'
        elif change > 0.05:
            return 'uptrend'
        elif change < -0.15:
            return 'strong_downtrend'
        elif change < -0.05:
            return 'downtrend'
        else:
            return 'sideways'
    
    def _find_support_resistance(self, prices: List[float]) -> Dict[str, float]:
        """
        Identify support and resistance levels.
        
        Args:
            prices: List of price values
            
        Returns:
            Support and resistance levels
        """
        if not prices:
            return {'support': 0, 'resistance': 0}
        
        sorted_prices = sorted(prices)
        
        # Use quartiles
        if len(sorted_prices) > 3:
            support = statistics.quantiles(sorted_prices, n=4)[0]
            resistance = statistics.quantiles(sorted_prices, n=4)[2]
        else:
            support = min(prices)
            resistance = max(prices)
        
        return {
            'support': round(support, 4),
            'resistance': round(resistance, 4)
        }
    
    def _is_consistent_uptrend(self, prices: List[float], threshold: float = 0.6) -> bool:
        """Check if prices show consistent uptrend."""
        if len(prices) < 10:
            return False
        
        up_moves = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i-1])
        ratio = up_moves / (len(prices) - 1)
        
        return ratio > threshold
    
    def _is_consistent_downtrend(self, prices: List[float], threshold: float = 0.6) -> bool:
        """Check if prices show consistent downtrend."""
        if len(prices) < 10:
            return False
        
        down_moves = sum(1 for i in range(1, len(prices)) if prices[i] < prices[i-1])
        ratio = down_moves / (len(prices) - 1)
        
        return ratio > threshold
    
    def _is_consolidating(self, prices: List[float], threshold: float = 0.05) -> bool:
        """Check if market is consolidating."""
        if len(prices) < 10:
            return False
        
        price_range = max(prices) - min(prices)
        avg_price = statistics.mean(prices)
        
        range_ratio = price_range / avg_price if avg_price != 0 else 1
        
        return range_ratio < threshold
    
    def _detect_breakout(self, prices: List[float]) -> Optional[Dict[str, Any]]:
        """Detect recent breakout from consolidation."""
        if len(prices) < 20:
            return None
        
        # Check if recent prices broke out of earlier range
        earlier_prices = prices[:-10]
        recent_prices = prices[-10:]
        
        earlier_max = max(earlier_prices)
        earlier_min = min(earlier_prices)
        recent_avg = statistics.mean(recent_prices)
        
        if recent_avg > earlier_max * 1.05:
            return {
                'type': 'upward_breakout',
                'description': 'Market broke above previous range',
                'confidence': 'medium',
                'suggested_action': 'buy'
            }
        elif recent_avg < earlier_min * 0.95:
            return {
                'type': 'downward_breakout',
                'description': 'Market broke below previous range',
                'confidence': 'medium',
                'suggested_action': 'sell'
            }
        
        return None
    
    def _detect_support_bounce(self, prices: List[float]) -> Optional[Dict[str, Any]]:
        """Detect bounce off support level."""
        if len(prices) < 15:
            return None
        
        sr = self._find_support_resistance(prices[:-5])
        support = sr['support']
        
        # Check if price bounced off support recently
        recent = prices[-5:]
        touched_support = any(abs(p - support) < 0.02 for p in prices[-10:-5])
        recovered = recent[-1] > support + 0.03
        
        if touched_support and recovered:
            return {
                'type': 'support_bounce',
                'description': f'Price bounced off support level {support:.3f}',
                'confidence': 'medium',
                'suggested_action': 'buy'
            }
        
        return None
    
    def _get_historical_prices(self, market_slug: str, days: int) -> List[Dict[str, Any]]:
        """
        Get historical prices for a market.
        
        Args:
            market_slug: Market identifier
            days: Number of days
            
        Returns:
            List of price data points
        """
        # Check cache first
        if market_slug in self._market_data:
            data = list(self._market_data[market_slug])
            # Filter to requested days
            cutoff = time.time() - days * 86400
            data = [d for d in data if d.get('timestamp', 0) > cutoff]
            if data:
                return data
        
        # Generate mock data
        import random
        random.seed(hash(market_slug))
        
        prices = []
        price = 0.5
        now = int(time.time())
        
        for i in range(days * 24):
            # Random walk with slight trend
            change = random.uniform(-0.02, 0.02)
            price += change
            price = max(0.05, min(0.95, price))
            
            prices.append({
                'timestamp': now - (days * 24 - i) * 3600,
                'price': price,
                'volume': random.uniform(1000, 10000)
            })
        
        random.seed()
        
        # Cache data
        if market_slug not in self._market_data:
            self._market_data[market_slug] = deque(maxlen=self._max_data_points)
        
        for p in prices:
            self._market_data[market_slug].append(p)
        
        return prices
    
    def add_price_point(self, market_slug: str, price: float, 
                        volume: float = 0, timestamp: Optional[int] = None) -> None:
        """
        Add a price point to historical data.
        
        Args:
            market_slug: Market identifier
            price: Price value
            volume: Trade volume
            timestamp: Unix timestamp (now if None)
        """
        if market_slug not in self._market_data:
            self._market_data[market_slug] = deque(maxlen=self._max_data_points)
        
        self._market_data[market_slug].append({
            'timestamp': timestamp or int(time.time()),
            'price': price,
            'volume': volume
        })
