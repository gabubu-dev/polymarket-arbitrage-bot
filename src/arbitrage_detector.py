"""
Arbitrage opportunity detection with spike-based strategy.

Detects price spikes on exchanges and identifies opportunities
to trade on Polymarket's 15-minute markets before odds adjust.
"""

import logging
from typing import Dict, Optional, List, Deque
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque


@dataclass
class PriceSnapshot:
    """Historical price snapshot for velocity calculation."""
    timestamp: datetime
    price: float
    

@dataclass
class ArbitrageOpportunity:
    """
    Represents a detected arbitrage opportunity.
    """
    symbol: str
    exchange: str
    exchange_price: float
    polymarket_market_id: str
    polymarket_odds: float
    divergence: float
    direction: str  # 'up' or 'down'
    confidence: float
    timestamp: datetime
    expected_profit: float


class ArbitrageDetector:
    """
    Detects arbitrage opportunities using spike detection strategy.
    
    Monitors exchange prices for significant spikes and identifies
    opportunities on Polymarket before odds adjust.
    
    Strategy: When crypto price spikes 1-2%+ in <10 seconds,
    bet on corresponding direction on Polymarket's 15-min markets.
    """
    
    def __init__(self, spike_threshold: float = 0.015,
                 min_profit_threshold: float = 0.02,
                 price_history_seconds: int = 30):
        """
        Initialize spike-based arbitrage detector.
        
        Args:
            spike_threshold: Minimum price change % to trigger (e.g., 0.015 = 1.5%)
            min_profit_threshold: Minimum expected profit percentage
            price_history_seconds: How long to track price history for velocity
        """
        self.logger = logging.getLogger("ArbitrageDetector")
        self.spike_threshold = spike_threshold
        self.min_profit_threshold = min_profit_threshold
        self.price_history_window = timedelta(seconds=price_history_seconds)
        
        # Track price history for each symbol
        self.price_history: Dict[str, Deque[PriceSnapshot]] = {}
        
        # Track recent opportunities to avoid duplicates
        self.recent_opportunities: List[ArbitrageOpportunity] = []
        self.opportunity_cooldown = timedelta(seconds=60)  # Longer cooldown for spike strategy
    
    def update_price(self, symbol: str, price: float) -> None:
        """
        Update price history for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            price: Current price
        """
        now = datetime.now()
        
        # Initialize deque if not exists
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=100)
        
        # Add current price
        self.price_history[symbol].append(PriceSnapshot(now, price))
        
        # Clean old entries
        self._cleanup_old_prices(symbol)
    
    def _cleanup_old_prices(self, symbol: str) -> None:
        """Remove price snapshots older than history window."""
        if symbol not in self.price_history:
            return
        
        cutoff = datetime.now() - self.price_history_window
        history = self.price_history[symbol]
        
        # Remove old entries from left
        while history and history[0].timestamp < cutoff:
            history.popleft()
    
    def detect_spike(self, symbol: str, current_price: float,
                    window_seconds: int = 10) -> Optional[Dict[str, Any]]:
        """
        Detect if current price represents a significant spike.
        
        Args:
            symbol: Trading symbol
            current_price: Current price
            window_seconds: Time window to check for spike (default 10s)
            
        Returns:
            Dictionary with spike info if detected, None otherwise
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return None
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Get oldest price within window
        history = self.price_history[symbol]
        baseline_price = None
        
        for snapshot in history:
            if snapshot.timestamp >= cutoff:
                baseline_price = snapshot.price
                break
        
        if baseline_price is None or baseline_price == 0:
            return None
        
        # Calculate price change
        price_change = (current_price - baseline_price) / baseline_price
        
        # Check if spike exceeds threshold
        if abs(price_change) >= self.spike_threshold:
            direction = "up" if price_change > 0 else "down"
            
            self.logger.info(
                f"Spike detected: {symbol} moved {price_change:.2%} in {window_seconds}s "
                f"({baseline_price} -> {current_price}) - Direction: {direction.upper()}"
            )
            
            return {
                'symbol': symbol,
                'direction': direction,
                'price_change_pct': price_change,
                'baseline_price': baseline_price,
                'current_price': current_price,
                'window_seconds': window_seconds,
                'timestamp': now
            }
        
        return None
    
    def detect_opportunity(self, symbol: str, exchange: str,
                          exchange_price: float, 
                          polymarket_market_id: str,
                          polymarket_odds: float,
                          direction: str) -> Optional[ArbitrageOpportunity]:
        """
        Check if current prices represent an arbitrage opportunity.
        
        Strategy: When price spikes on exchange but Polymarket odds
        haven't adjusted yet, there's an arbitrage window.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name
            exchange_price: Current exchange price
            polymarket_market_id: Polymarket market ID or token ID
            polymarket_odds: Current Polymarket mid price (0-1)
            direction: Expected direction ('up' or 'down')
            
        Returns:
            ArbitrageOpportunity if detected, None otherwise
        """
        # First, update price history
        self.update_price(symbol, exchange_price)
        
        # Detect spike
        spike_info = self.detect_spike(symbol, exchange_price, window_seconds=10)
        
        if spike_info is None:
            return None  # No spike detected
        
        # Check if spike direction matches opportunity direction
        if spike_info['direction'] != direction:
            return None  # Spike in wrong direction
        
        # Calculate divergence between spike magnitude and current Polymarket odds
        divergence = self._calculate_spike_divergence(
            spike_info['price_change_pct'], polymarket_odds, direction
        )
        
        # Check if divergence suggests a viable opportunity
        # Minimum divergence should be at least half the spike threshold
        min_divergence = self.spike_threshold * 0.5
        if abs(divergence) < min_divergence:
            return None
        
        # Calculate expected profit
        expected_profit = self._estimate_profit(divergence, polymarket_odds)
        
        if expected_profit < self.min_profit_threshold:
            return None
        
        # Calculate confidence score
        confidence = self._calculate_confidence(divergence, polymarket_odds)
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            symbol=symbol,
            exchange=exchange,
            exchange_price=exchange_price,
            polymarket_market_id=polymarket_market_id,
            polymarket_odds=polymarket_odds,
            divergence=divergence,
            direction=direction,
            confidence=confidence,
            timestamp=datetime.now(),
            expected_profit=expected_profit
        )
        
        # Check if similar opportunity was recently detected (avoid spam)
        if self._is_duplicate_opportunity(opportunity):
            return None
        
        # Add to recent opportunities
        self.recent_opportunities.append(opportunity)
        self._cleanup_old_opportunities()
        
        self.logger.info(
            f"Detected opportunity: {symbol} {direction} | "
            f"Divergence: {divergence:.2%} | Expected profit: {expected_profit:.2%}"
        )
        
        return opportunity
    
    def _calculate_spike_divergence(self, spike_pct: float, 
                                   polymarket_odds: float,
                                   direction: str) -> float:
        """
        Calculate divergence between spike magnitude and Polymarket odds.
        
        Logic:
        - For UP spike: Large positive spike + low YES odds = high divergence
        - For DOWN spike: Large negative spike + low NO odds (high YES) = high divergence
        
        Args:
            spike_pct: Price change percentage (positive or negative)
            polymarket_odds: Current Polymarket mid price for YES outcome (0-1)
            direction: 'up' or 'down'
            
        Returns:
            Divergence score (higher = better opportunity)
        """
        spike_magnitude = abs(spike_pct)
        
        if direction == "up":
            # For UP markets: we want to BUY YES
            # Good opportunity: Large spike + low YES price (cheap to buy)
            # Divergence = spike magnitude * how cheap YES is
            divergence = spike_magnitude * (1.0 - polymarket_odds)
        else:
            # For DOWN markets: we want to BUY NO (or SELL YES)
            # Good opportunity: Large drop + low NO price (high YES price)
            # Divergence = spike magnitude * how cheap NO is
            divergence = spike_magnitude * polymarket_odds
        
        return divergence
    
    def _estimate_profit(self, divergence: float, odds: float) -> float:
        """
        Estimate expected profit from arbitrage opportunity.
        
        Args:
            divergence: Calculated divergence
            odds: Current Polymarket odds
            
        Returns:
            Expected profit percentage
        """
        # Simplified profit estimation
        # Real calculation would factor in:
        # - Polymarket fees (currently 2%)
        # - Slippage
        # - Probability of market moving against us
        # - Time until market resolution
        
        # For a YES position: profit = (1 - entry_odds) if correct
        # Expected profit = divergence * (1 - odds) - fees
        
        fees = 0.02  # 2% Polymarket fee
        expected_profit = abs(divergence) * (1 - odds) - fees
        
        return max(0, expected_profit)
    
    def _calculate_confidence(self, divergence: float, odds: float) -> float:
        """
        Calculate confidence score for the opportunity.
        
        Args:
            divergence: Price divergence
            odds: Polymarket odds
            
        Returns:
            Confidence score (0-1)
        """
        # Higher divergence = higher confidence
        # Odds around 0.5 = lower confidence (uncertain market)
        # Odds very high or low = higher confidence (strong signal)
        
        divergence_score = min(abs(divergence) / 0.2, 1.0)  # Max at 20% divergence
        
        # Odds confidence (U-shaped: high at extremes, low at 0.5)
        odds_confidence = abs(odds - 0.5) * 2
        
        confidence = (divergence_score * 0.7) + (odds_confidence * 0.3)
        
        return confidence
    
    def _is_duplicate_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Check if this opportunity is a duplicate of a recent one.
        
        Args:
            opportunity: Opportunity to check
            
        Returns:
            True if duplicate, False otherwise
        """
        now = datetime.now()
        
        for recent in self.recent_opportunities:
            # Check if same market and within cooldown period
            if (recent.polymarket_market_id == opportunity.polymarket_market_id and
                recent.direction == opportunity.direction and
                (now - recent.timestamp) < self.opportunity_cooldown):
                return True
        
        return False
    
    def _cleanup_old_opportunities(self) -> None:
        """Remove opportunities older than cooldown period."""
        now = datetime.now()
        cutoff = now - (self.opportunity_cooldown * 2)
        
        self.recent_opportunities = [
            opp for opp in self.recent_opportunities
            if opp.timestamp > cutoff
        ]
    
    def get_recent_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Get list of recent opportunities.
        
        Returns:
            List of recent ArbitrageOpportunity objects
        """
        return self.recent_opportunities.copy()
