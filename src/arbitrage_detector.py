"""
Arbitrage opportunity detection.

Compares exchange prices with Polymarket market odds to identify
profitable arbitrage opportunities.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass


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
    Detects arbitrage opportunities between exchanges and Polymarket.
    
    Monitors price divergences and generates trading signals when
    opportunities exceed configured thresholds.
    """
    
    def __init__(self, divergence_threshold: float = 0.05,
                 min_profit_threshold: float = 0.02):
        """
        Initialize arbitrage detector.
        
        Args:
            divergence_threshold: Minimum price divergence to trigger signal
            min_profit_threshold: Minimum expected profit percentage
        """
        self.logger = logging.getLogger("ArbitrageDetector")
        self.divergence_threshold = divergence_threshold
        self.min_profit_threshold = min_profit_threshold
        
        # Track recent opportunities to avoid duplicates
        self.recent_opportunities: List[ArbitrageOpportunity] = []
        self.opportunity_cooldown = timedelta(seconds=30)
    
    def detect_opportunity(self, symbol: str, exchange: str,
                          exchange_price: float, 
                          polymarket_market_id: str,
                          polymarket_odds: float,
                          direction: str) -> Optional[ArbitrageOpportunity]:
        """
        Check if current prices represent an arbitrage opportunity.
        
        The key insight: When BTC/ETH makes a sharp move on exchanges,
        Polymarket odds often lag by 30-90 seconds. This creates a window
        where we can bet at "stale" odds before the market corrects.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            exchange: Exchange name
            exchange_price: Current exchange price
            polymarket_market_id: Polymarket market ID
            polymarket_odds: Current Polymarket odds (0-1)
            direction: Expected direction ('up' or 'down')
            
        Returns:
            ArbitrageOpportunity if detected, None otherwise
        """
        # Calculate divergence
        # For "up" markets: high exchange momentum + low Polymarket odds = opportunity
        # For "down" markets: low exchange momentum + high Polymarket odds = opportunity
        
        divergence = self._calculate_divergence(
            exchange_price, polymarket_odds, direction
        )
        
        # Check if divergence exceeds threshold
        if abs(divergence) < self.divergence_threshold:
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
    
    def _calculate_divergence(self, exchange_price: float, 
                             polymarket_odds: float,
                             direction: str) -> float:
        """
        Calculate price divergence between exchange and Polymarket.
        
        This is simplified logic. In reality, you'd track recent price movement
        velocity, compare with historical patterns, etc.
        
        Args:
            exchange_price: Current exchange price
            polymarket_odds: Polymarket odds (0-1)
            direction: Expected direction
            
        Returns:
            Divergence value (positive = opportunity)
        """
        # Simplified divergence calculation
        # Real implementation would track:
        # - Price velocity (how fast price is moving)
        # - Historical correlation between exchange moves and Polymarket updates
        # - Time since last significant price change
        
        if direction == "up":
            # If price is rising but odds are low, that's divergence
            return (1.0 - polymarket_odds) * 2  # Scale to make it more intuitive
        else:
            # If price is falling but odds are high, that's divergence
            return polymarket_odds * 2
    
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
