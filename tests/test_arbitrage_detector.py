"""
Tests for arbitrage detection logic.
"""

import pytest
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity


def test_detector_initialization():
    """Test ArbitrageDetector initialization."""
    detector = ArbitrageDetector(
        divergence_threshold=0.06,
        min_profit_threshold=0.03
    )
    
    assert detector.divergence_threshold == 0.06
    assert detector.min_profit_threshold == 0.03
    assert len(detector.recent_opportunities) == 0


def test_detect_opportunity_insufficient_divergence():
    """Test that small divergence doesn't trigger opportunity."""
    detector = ArbitrageDetector(divergence_threshold=0.10)
    
    opportunity = detector.detect_opportunity(
        symbol="BTC/USDT",
        exchange="binance",
        exchange_price=50000,
        polymarket_market_id="market_123",
        polymarket_odds=0.55,
        direction="up"
    )
    
    # Small divergence should not trigger
    assert opportunity is None


def test_detect_opportunity_valid():
    """Test detection of valid arbitrage opportunity."""
    detector = ArbitrageDetector(
        divergence_threshold=0.05,
        min_profit_threshold=0.01
    )
    
    # Low odds + upward price movement = potential opportunity
    opportunity = detector.detect_opportunity(
        symbol="BTC/USDT",
        exchange="binance",
        exchange_price=50000,
        polymarket_market_id="market_123",
        polymarket_odds=0.20,  # Very low odds
        direction="up"
    )
    
    assert opportunity is not None
    assert opportunity.symbol == "BTC/USDT"
    assert opportunity.direction == "up"
    assert opportunity.divergence > 0


def test_duplicate_opportunity_filtering():
    """Test that duplicate opportunities are filtered out."""
    detector = ArbitrageDetector()
    
    # First detection
    opp1 = detector.detect_opportunity(
        symbol="BTC/USDT",
        exchange="binance",
        exchange_price=50000,
        polymarket_market_id="market_123",
        polymarket_odds=0.20,
        direction="up"
    )
    
    # Immediate duplicate should be filtered
    opp2 = detector.detect_opportunity(
        symbol="BTC/USDT",
        exchange="binance",
        exchange_price=50000,
        polymarket_market_id="market_123",
        polymarket_odds=0.21,
        direction="up"
    )
    
    assert opp1 is not None
    assert opp2 is None  # Duplicate filtered


def test_profit_estimation():
    """Test expected profit calculation."""
    detector = ArbitrageDetector()
    
    divergence = 0.15
    odds = 0.30
    
    profit = detector._estimate_profit(divergence, odds)
    
    # Profit should be positive and account for fees
    assert profit >= 0
    # Should be less than raw divergence due to fees
    assert profit < divergence
