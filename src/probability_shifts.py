"""
Probability shift detection using momentum analysis.

Implements AI-inspired models to detect and exploit probability shifts
in prediction markets before the crowd adjusts.
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum


class ProbabilityTrend(Enum):
    """Trend direction for probability movements."""
    STRONG_UP = "strong_up"
    UP = "up"
    FLAT = "flat"
    DOWN = "down"
    STRONG_DOWN = "strong_down"
    VOLATILE = "volatile"


@dataclass
class ProbabilitySnapshot:
    """Snapshot of probability at a point in time."""
    timestamp: datetime
    probability: float
    volume_24h: float = 0.0
    bid_ask_spread: float = 0.0
    order_book_imbalance: float = 0.0  # Positive = more bids


@dataclass
class MomentumSignal:
    """Detected momentum signal."""
    market_id: str
    direction: str  # 'up' or 'down'
    confidence: float
    strength: float
    predicted_probability: float
    entry_probability: float
    expected_return: float
    time_horizon_seconds: int
    timestamp: datetime
    factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class ShiftOpportunity:
    """Identified probability shift opportunity."""
    market_id: str
    current_odds: float
    predicted_odds: float
    shift_magnitude: float
    confidence: float
    expected_profit: float
    time_to_capture: timedelta
    entry_time: datetime
    urgency_score: float  # 0-1, higher = act faster


class ProbabilityMomentumAnalyzer:
    """
    Analyzes probability momentum to predict shifts.
    
    Uses techniques similar to those described in the DextersSolab article:
    - Rate of change analysis
    - Volume-weighted momentum
    - Order book imbalance signals
    - Statistical arbitrage detection
    """
    
    def __init__(self,
                 lookback_periods: int = 20,
                 short_window: int = 5,
                 long_window: int = 15,
                 momentum_threshold: float = 0.02,
                 confidence_threshold: float = 0.7):
        self.logger = logging.getLogger("ProbabilityMomentumAnalyzer")
        self.lookback_periods = lookback_periods
        self.short_window = short_window
        self.long_window = long_window
        self.momentum_threshold = momentum_threshold
        self.confidence_threshold = confidence_threshold
        
        # Store historical data per market
        self._history: Dict[str, Deque[ProbabilitySnapshot]] = {}
        self._momentum_cache: Dict[str, Dict] = {}
    
    def add_snapshot(self, market_id: str, snapshot: ProbabilitySnapshot) -> None:
        """Add a probability snapshot for analysis."""
        if market_id not in self._history:
            self._history[market_id] = deque(maxlen=self.lookback_periods * 2)
        
        self._history[market_id].append(snapshot)
        
        # Update momentum cache
        if len(self._history[market_id]) >= self.long_window:
            self._momentum_cache[market_id] = self._calculate_momentum(market_id)
    
    def detect_shift(self, 
                     market_id: str,
                     current_odds: float,
                     external_signals: Optional[Dict] = None) -> Optional[ShiftOpportunity]:
        """
        Detect a probability shift opportunity.
        
        Args:
            market_id: Market identifier
            current_odds: Current market odds
            external_signals: Optional external signals (exchange prices, news, etc.)
            
        Returns:
            ShiftOpportunity if detected, None otherwise
        """
        if market_id not in self._history:
            return None
        
        history = self._history[market_id]
        if len(history) < self.long_window:
            return None
        
        # Calculate momentum indicators
        momentum = self._momentum_cache.get(market_id, {})
        if not momentum:
            return None
        
        # Get trend direction and strength
        trend = self._classify_trend(momentum)
        
        # Skip flat trends
        if trend == ProbabilityTrend.FLAT:
            return None
        
        # Calculate predicted probability based on momentum
        predicted_probability = self._predict_probability(market_id, momentum)
        
        # Calculate shift magnitude
        shift_magnitude = abs(predicted_probability - current_odds)
        
        # Skip if shift is too small
        if shift_magnitude < self.momentum_threshold:
            return None
        
        # Calculate confidence score
        confidence = self._calculate_confidence(market_id, momentum, external_signals)
        
        if confidence < self.confidence_threshold:
            return None
        
        # Calculate expected profit
        expected_profit = self._estimate_profit(
            current_odds, predicted_probability, confidence
        )
        
        # Calculate urgency (how quickly we need to act)
        urgency = self._calculate_urgency(market_id, momentum, shift_magnitude)
        
        # Determine direction
        direction = "up" if predicted_probability > current_odds else "down"
        
        opportunity = ShiftOpportunity(
            market_id=market_id,
            current_odds=current_odds,
            predicted_odds=predicted_probability,
            shift_magnitude=shift_magnitude,
            confidence=confidence,
            expected_profit=expected_profit,
            time_to_capture=timedelta(seconds=int(30 / urgency)),  # Higher urgency = less time
            entry_time=datetime.now(),
            urgency_score=urgency
        )
        
        self.logger.info(
            f"Shift detected in {market_id}: {current_odds:.3f} -> "
            f"{predicted_probability:.3f} (confidence: {confidence:.2f}, "
            f"urgency: {urgency:.2f})"
        )
        
        return opportunity
    
    def _calculate_momentum(self, market_id: str) -> Dict:
        """Calculate momentum indicators for a market."""
        history = list(self._history[market_id])
        probabilities = np.array([s.probability for s in history])
        volumes = np.array([s.volume_24h for s in history])
        
        # Price momentum (rate of change)
        if len(probabilities) >= self.short_window:
            short_ma = np.mean(probabilities[-self.short_window:])
            long_ma = np.mean(probabilities[-self.long_window:]) if len(probabilities) >= self.long_window else np.mean(probabilities)
            price_momentum = (short_ma - long_ma) / long_ma if long_ma > 0 else 0
        else:
            price_momentum = 0
        
        # Volume-weighted momentum
        if len(volumes) >= 2 and volumes[-1] > 0:
            recent_volume = np.mean(volumes[-3:]) if len(volumes) >= 3 else volumes[-1]
            older_volume = np.mean(volumes[-6:-3]) if len(volumes) >= 6 else volumes[0]
            volume_trend = (recent_volume - older_volume) / older_volume if older_volume > 0 else 0
        else:
            volume_trend = 0
        
        # Order book imbalance (recent average)
        imbalances = [s.order_book_imbalance for s in history[-5:] if s.order_book_imbalance != 0]
        avg_imbalance = np.mean(imbalances) if imbalances else 0
        
        # Volatility (standard deviation of recent changes)
        if len(probabilities) >= 5:
            changes = np.diff(probabilities[-5:])
            volatility = np.std(changes)
        else:
            volatility = 0
        
        # Velocity (most recent change)
        velocity = probabilities[-1] - probabilities[-2] if len(probabilities) >= 2 else 0
        
        return {
            'price_momentum': price_momentum,
            'volume_trend': volume_trend,
            'order_book_imbalance': avg_imbalance,
            'volatility': volatility,
            'velocity': velocity,
            'short_ma': short_ma if 'short_ma' in locals() else probabilities[-1],
            'long_ma': long_ma if 'long_ma' in locals() else probabilities[-1]
        }
    
    def _classify_trend(self, momentum: Dict) -> ProbabilityTrend:
        """Classify the current trend based on momentum."""
        price_mom = momentum.get('price_momentum', 0)
        velocity = momentum.get('velocity', 0)
        volatility = momentum.get('volatility', 0)
        
        # High volatility = uncertain
        if volatility > 0.05:
            return ProbabilityTrend.VOLATILE
        
        # Strong trends
        if price_mom > 0.03 and velocity > 0.01:
            return ProbabilityTrend.STRONG_UP
        elif price_mom < -0.03 and velocity < -0.01:
            return ProbabilityTrend.STRONG_DOWN
        
        # Moderate trends
        if price_mom > 0.015:
            return ProbabilityTrend.UP
        elif price_mom < -0.015:
            return ProbabilityTrend.DOWN
        
        return ProbabilityTrend.FLAT
    
    def _predict_probability(self, market_id: str, momentum: Dict) -> float:
        """Predict future probability based on momentum."""
        history = list(self._history[market_id])
        current_prob = history[-1].probability
        
        # Simple linear extrapolation with decay
        velocity = momentum.get('velocity', 0)
        price_momentum = momentum.get('price_momentum', 0)
        
        # Weight velocity higher for short-term predictions
        combined_momentum = velocity * 0.6 + price_momentum * 0.4
        
        # Apply momentum with decay factor
        decay = 0.7  # Momentum decays over time
        predicted_change = combined_momentum * decay
        
        # Clamp prediction to valid probability range
        predicted = current_prob + predicted_change
        return max(0.01, min(0.99, predicted))
    
    def _calculate_confidence(self, 
                             market_id: str,
                             momentum: Dict,
                             external_signals: Optional[Dict]) -> float:
        """Calculate confidence score for the prediction."""
        scores = []
        
        # Momentum consistency score
        velocity = abs(momentum.get('velocity', 0))
        price_momentum = abs(momentum.get('price_momentum', 0))
        momentum_score = min(1.0, (velocity * 10 + price_momentum * 5) / 2)
        scores.append(momentum_score * 0.3)
        
        # Volume confirmation score
        volume_trend = momentum.get('volume_trend', 0)
        volume_score = min(1.0, abs(volume_trend) * 2)
        scores.append(volume_score * 0.2)
        
        # Order book imbalance score
        imbalance = abs(momentum.get('order_book_imbalance', 0))
        imbalance_score = min(1.0, imbalance * 2)
        scores.append(imbalance_score * 0.25)
        
        # External signal confirmation
        if external_signals:
            # Check if external signals align with prediction
            alignment = external_signals.get('alignment', 0)
            scores.append(abs(alignment) * 0.25)
        else:
            scores.append(0.15)  # Neutral if no external data
        
        # Data quality score (based on history length)
        history_len = len(self._history.get(market_id, []))
        quality_score = min(1.0, history_len / self.long_window)
        scores.append(quality_score * 0.1)
        
        return sum(scores)
    
    def _estimate_profit(self,
                        current_odds: float,
                        predicted_odds: float,
                        confidence: float) -> float:
        """Estimate expected profit from the shift."""
        # Profit if prediction is correct
        potential_profit = abs(predicted_odds - current_odds)
        
        # Adjust for confidence and fees
        polymarket_fee = 0.02  # 2% fee
        adjusted_profit = potential_profit * confidence - polymarket_fee
        
        return max(0, adjusted_profit)
    
    def _calculate_urgency(self,
                          market_id: str,
                          momentum: Dict,
                          shift_magnitude: float) -> float:
        """Calculate urgency score (0-1, higher = act faster)."""
        urgency = 0.0
        
        # Higher velocity = more urgent
        velocity = abs(momentum.get('velocity', 0))
        urgency += min(0.4, velocity * 20)
        
        # Larger shifts = more urgent (others will notice)
        urgency += min(0.3, shift_magnitude * 5)
        
        # Volume spike = more urgent
        volume_trend = abs(momentum.get('volume_trend', 0))
        urgency += min(0.2, volume_trend)
        
        # Order book pressure
        imbalance = abs(momentum.get('order_book_imbalance', 0))
        urgency += min(0.1, imbalance)
        
        return min(1.0, urgency)
    
    def get_market_state(self, market_id: str) -> Dict:
        """Get current market state for a market."""
        if market_id not in self._history:
            return {}
        
        history = list(self._history[market_id])
        momentum = self._momentum_cache.get(market_id, {})
        
        return {
            'current_probability': history[-1].probability if history else None,
            'trend': self._classify_trend(momentum).value if momentum else 'unknown',
            'momentum': momentum,
            'data_points': len(history),
            'last_update': history[-1].timestamp if history else None
        }


class MultiFactorShiftDetector(ProbabilityMomentumAnalyzer):
    """
    Enhanced shift detector using multiple factors.
    
    Incorporates:
    - Historical pattern matching
    - Cross-market correlations
    - Time-of-day effects
    - News/sentiment signals
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("MultiFactorShiftDetector")
        
        # Pattern storage
        self._patterns: Dict[str, List[Dict]] = {}
        self._correlations: Dict[Tuple[str, str], float] = {}
    
    def detect_shift(self,
                     market_id: str,
                     current_odds: float,
                     external_signals: Optional[Dict] = None) -> Optional[ShiftOpportunity]:
        """Enhanced shift detection with multi-factor analysis."""
        # Get base opportunity
        opportunity = super().detect_shift(market_id, current_odds, external_signals)
        
        if not opportunity:
            return None
        
        # Enhance confidence with additional factors
        enhanced_confidence = self._apply_additional_factors(
            market_id, opportunity, external_signals
        )
        
        # Update opportunity with enhanced confidence
        opportunity.confidence = enhanced_confidence
        opportunity.expected_profit = self._estimate_profit(
            opportunity.current_odds,
            opportunity.predicted_odds,
            enhanced_confidence
        )
        
        # Only return if still meets threshold
        if opportunity.confidence >= self.confidence_threshold:
            return opportunity
        
        return None
    
    def _apply_additional_factors(self,
                                  market_id: str,
                                  opportunity: ShiftOpportunity,
                                  external_signals: Optional[Dict]) -> float:
        """Apply additional confidence factors."""
        base_confidence = opportunity.confidence
        adjustments = []
        
        # Time-of-day factor (some times are more predictable)
        hour = datetime.now().hour
        if hour in [9, 10, 11, 14, 15, 16]:  # Market hours
            adjustments.append(0.05)
        elif hour in [0, 1, 2, 3, 4, 5]:  # Low volume hours
            adjustments.append(-0.05)
        
        # Pattern matching factor
        pattern_match = self._match_historical_pattern(market_id)
        adjustments.append(pattern_match * 0.1)
        
        # External signal strength
        if external_signals:
            signal_strength = external_signals.get('strength', 0)
            signal_confidence = external_signals.get('confidence', 0)
            adjustments.append(signal_strength * signal_confidence * 0.15)
        
        # Apply adjustments
        adjusted = base_confidence + sum(adjustments)
        return max(0.0, min(1.0, adjusted))
    
    def _match_historical_pattern(self, market_id: str) -> float:
        """Match current pattern against historical successful patterns."""
        if market_id not in self._history or len(self._history[market_id]) < 10:
            return 0.0
        
        # Simplified pattern matching - would use more sophisticated ML in production
        history = list(self._history[market_id])[-10:]
        recent_changes = [h.probability for h in history]
        
        # Check for common reversal patterns
        # Example: Check if we have a "double bottom" or similar
        if len(recent_changes) >= 5:
            # Simple pattern: strong move followed by consolidation
            early_move = abs(recent_changes[-5] - recent_changes[-10])
            recent_volatility = np.std(recent_changes[-5:])
            
            if early_move > 0.05 and recent_volatility < 0.02:
                return 0.3  # Pattern suggests continuation
        
        return 0.0
    
    def record_outcome(self, 
                      market_id: str,
                      entry_time: datetime,
                      actual_outcome: float,
                      profit: float) -> None:
        """Record actual outcome for learning."""
        # Store pattern for future matching
        if market_id not in self._patterns:
            self._patterns[market_id] = []
        
        # Get state at entry time
        if market_id in self._history:
            history = list(self._history[market_id])
            matching_snapshots = [
                h for h in history 
                if abs((h.timestamp - entry_time).total_seconds()) < 60
            ]
            
            if matching_snapshots:
                self._patterns[market_id].append({
                    'timestamp': entry_time,
                    'state': self._momentum_cache.get(market_id, {}),
                    'outcome': actual_outcome,
                    'profit': profit,
                    'success': profit > 0
                })
                
                # Keep only recent patterns
                cutoff = datetime.now() - timedelta(days=7)
                self._patterns[market_id] = [
                    p for p in self._patterns[market_id]
                    if p['timestamp'] > cutoff
                ]