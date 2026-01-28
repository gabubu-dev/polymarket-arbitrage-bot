"""
Sentiment tracking and analysis for prediction markets.

This module analyzes market sentiment through volume trends, price momentum,
and market activity patterns. Integrates with the bot's trading systems.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque


class SentimentTracker:
    """Track and analyze market sentiment indicators."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize sentiment tracker.
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger("SentimentTracker")
        
        # Load config
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                sentiment_config = config.get('sentiment', {})
        except (FileNotFoundError, json.JSONDecodeError):
            sentiment_config = {}
        
        self.volume_threshold = sentiment_config.get('volume_change_threshold', 0.5)
        self.momentum_threshold = sentiment_config.get('momentum_threshold', 0.1)
        self.lookback_hours = sentiment_config.get('lookback_hours', 24)
        
        # Price history cache
        self._price_history: Dict[str, deque] = {}
        self._max_history = 1000
    
    def analyze_market(self, market_slug: str, 
                       current_price: Optional[float] = None,
                       volume_24h: Optional[float] = None) -> Dict[str, Any]:
        """
        Perform comprehensive sentiment analysis on a market.
        
        Args:
            market_slug: Market slug identifier
            current_price: Current market price (fetched if None)
            volume_24h: 24h volume (fetched if None)
            
        Returns:
            Dictionary containing sentiment metrics
        """
        # Get data from cache or fetch
        if current_price is None:
            current_price = self._get_current_price(market_slug)
        
        if volume_24h is None:
            volume_24h = self._get_volume_24h(market_slug)
        
        # Get historical data
        momentum = self.calculate_momentum(market_slug)
        volume_change = self.calculate_volume_change(market_slug, hours=48)
        
        # Determine overall sentiment
        sentiment_score = self._calculate_sentiment_score(momentum, volume_change)
        sentiment_label = self._sentiment_label(sentiment_score)
        
        return {
            'market_slug': market_slug,
            'current_price': current_price,
            'volume_24h': volume_24h,
            'volume_change_24h': volume_change,
            'momentum': momentum,
            'sentiment_score': sentiment_score,
            'overall_sentiment': sentiment_label,
            'analysis_time': datetime.now().isoformat(),
            'indicators': {
                'high_volume': volume_24h > 10000 if volume_24h else False,
                'increasing_volume': volume_change > self.volume_threshold,
                'positive_momentum': momentum > self.momentum_threshold,
                'negative_momentum': momentum < -self.momentum_threshold,
                'strong_signal': abs(sentiment_score) > 0.5
            }
        }
    
    def track_volume_trends(self, market_slug: str, hours: int = 24) -> Dict[str, Any]:
        """
        Track volume trends over time for a market.
        
        Args:
            market_slug: Market slug identifier
            hours: Number of hours to analyze
            
        Returns:
            Volume trend analysis
        """
        # Mock volume data - replace with actual API calls
        import random
        
        hourly_volumes = {}
        now = int(time.time())
        
        for i in range(hours):
            hour = int((now - i * 3600) // 3600)
            hourly_volumes[hour] = random.uniform(1000, 10000)
        
        # Calculate trend
        hours_list = sorted(hourly_volumes.keys())
        if len(hours_list) < 2:
            trend = 'insufficient_data'
        else:
            first_half = sum(hourly_volumes[h] for h in hours_list[:len(hours_list)//2])
            second_half = sum(hourly_volumes[h] for h in hours_list[len(hours_list)//2:])
            
            if second_half > first_half * 1.2:
                trend = 'increasing'
            elif second_half < first_half * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        
        total_volume = sum(hourly_volumes.values())
        
        return {
            'market_slug': market_slug,
            'hours_analyzed': hours,
            'total_volume': total_volume,
            'avg_hourly_volume': total_volume / len(hourly_volumes) if hourly_volumes else 0,
            'trend': trend,
            'hourly_data': [
                {'hour': h, 'volume': hourly_volumes[h]} 
                for h in hours_list
            ]
        }
    
    def calculate_momentum(self, market_slug: str, 
                           price_history: Optional[List[Dict]] = None) -> float:
        """
        Calculate price momentum for a market.
        
        Args:
            market_slug: Market slug identifier
            price_history: Price history (fetched if None)
            
        Returns:
            Momentum value (-1 to 1)
        """
        if price_history is None:
            price_history = self._get_price_history(market_slug)
        
        if len(price_history) < 2:
            return 0.0
        
        # Use recent price history
        recent_prices = price_history[-24:] if len(price_history) > 24 else price_history
        
        if len(recent_prices) < 2:
            return 0.0
        
        # Calculate price change
        first_price = recent_prices[0].get('price', 0.5)
        last_price = recent_prices[-1].get('price', 0.5)
        
        if first_price == 0:
            return 0.0
        
        # Calculate momentum with smoothing
        price_change = (last_price - first_price) / first_price
        
        # Weight by volume if available
        if 'volume' in recent_prices[-1] and recent_prices[-1]['volume'] > 0:
            volume_factor = min(1.0, recent_prices[-1]['volume'] / 10000)
            price_change *= (0.7 + 0.3 * volume_factor)
        
        return max(-1.0, min(1.0, price_change))
    
    def calculate_volume_change(self, market_slug: str, hours: int = 48) -> float:
        """
        Calculate volume change over time period.
        
        Args:
            market_slug: Market slug identifier
            hours: Hours to analyze
            
        Returns:
            Volume change percentage
        """
        trend = self.track_volume_trends(market_slug, hours=hours)
        hourly_data = trend.get('hourly_data', [])
        
        if len(hourly_data) < 2:
            return 0.0
        
        mid = len(hourly_data) // 2
        first_half = sum(d['volume'] for d in hourly_data[:mid])
        second_half = sum(d['volume'] for d in hourly_data[mid:])
        
        if first_half == 0:
            return 0.0
        
        return (second_half - first_half) / first_half
    
    def detect_market_shift(self, market_slug: str, 
                            threshold: float = 0.1) -> Dict[str, Any]:
        """
        Detect significant market sentiment shifts.
        
        Args:
            market_slug: Market slug identifier
            threshold: Minimum change to report
            
        Returns:
            Shift detection results
        """
        current = self.analyze_market(market_slug)
        momentum = current.get('momentum', 0)
        volume_change = current.get('volume_change_24h', 0)
        
        # Detect shift
        shift_detected = abs(momentum) > threshold or abs(volume_change) > threshold * 2
        
        if not shift_detected:
            return {
                'market_slug': market_slug,
                'shift_detected': False,
                'shift_direction': 'none',
                'confidence': 0.0
            }
        
        # Determine direction
        if momentum > 0 and volume_change > 0:
            direction = 'bullish_acceleration'
            confidence = (momentum + volume_change / 2) / 1.5
        elif momentum < 0 and volume_change > 0:
            direction = 'high_volume_selling'
            confidence = (abs(momentum) + volume_change / 2) / 1.5
        elif momentum > 0:
            direction = 'quiet_accumulation'
            confidence = momentum
        elif momentum < 0:
            direction = 'gradual_distribution'
            confidence = abs(momentum)
        else:
            direction = 'volume_spike_neutral'
            confidence = volume_change / 2
        
        return {
            'market_slug': market_slug,
            'shift_detected': True,
            'shift_direction': direction,
            'confidence': min(1.0, confidence),
            'momentum': momentum,
            'volume_change': volume_change,
            'current_sentiment': current.get('overall_sentiment', 'neutral')
        }
    
    def compare_markets(self, market_slugs: List[str]) -> List[Dict[str, Any]]:
        """
        Compare sentiment across multiple markets.
        
        Args:
            market_slugs: List of market slugs to compare
            
        Returns:
            List of sentiment analyses sorted by sentiment score
        """
        analyses = []
        
        for slug in market_slugs:
            analysis = self.analyze_market(slug)
            if 'error' not in analysis:
                analyses.append(analysis)
        
        # Sort by sentiment score
        analyses.sort(key=lambda x: x.get('sentiment_score', 0), reverse=True)
        
        return analyses
    
    def _calculate_sentiment_score(self, momentum: float, volume_change: float) -> float:
        """
        Calculate overall sentiment score from indicators.
        
        Args:
            momentum: Price momentum
            volume_change: Volume change rate
            
        Returns:
            Sentiment score between -1 and 1
        """
        # Weight momentum more heavily than volume
        score = (momentum * 0.7) + (volume_change * 0.3)
        
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, score))
    
    def _sentiment_label(self, score: float) -> str:
        """
        Convert sentiment score to label.
        
        Args:
            score: Sentiment score
            
        Returns:
            Sentiment label
        """
        if score > 0.5:
            return 'strongly_bullish'
        elif score > 0.2:
            return 'bullish'
        elif score > 0.05:
            return 'slightly_bullish'
        elif score < -0.5:
            return 'strongly_bearish'
        elif score < -0.2:
            return 'bearish'
        elif score < -0.05:
            return 'slightly_bearish'
        else:
            return 'neutral'
    
    def _get_current_price(self, market_slug: str) -> float:
        """Get current price for a market (mock implementation)."""
        import random
        random.seed(hash(market_slug))
        price = random.uniform(0.2, 0.8)
        random.seed()
        return price
    
    def _get_volume_24h(self, market_slug: str) -> float:
        """Get 24h volume for a market (mock implementation)."""
        import random
        random.seed(hash(market_slug) + 1)
        volume = random.uniform(5000, 50000)
        random.seed()
        return volume
    
    def _get_price_history(self, market_slug: str) -> List[Dict]:
        """Get price history for a market (mock implementation)."""
        import random
        
        # Check cache first
        if market_slug in self._price_history:
            return list(self._price_history[market_slug])
        
        # Generate mock data
        random.seed(hash(market_slug))
        history = []
        price = 0.5
        now = int(time.time())
        
        for i in range(48):
            price += random.uniform(-0.03, 0.03)
            price = max(0.1, min(0.9, price))
            history.append({
                'timestamp': now - (48 - i) * 3600,
                'price': price,
                'volume': random.uniform(1000, 10000)
            })
        
        random.seed()
        
        # Cache it
        self._price_history[market_slug] = deque(history, maxlen=self._max_history)
        
        return history
    
    def update_price(self, market_slug: str, price: float, volume: float = 0) -> None:
        """
        Update price data for a market.
        
        Args:
            market_slug: Market identifier
            price: Current price
            volume: Trade volume
        """
        if market_slug not in self._price_history:
            self._price_history[market_slug] = deque(maxlen=self._max_history)
        
        self._price_history[market_slug].append({
            'timestamp': int(time.time()),
            'price': price,
            'volume': volume
        })
