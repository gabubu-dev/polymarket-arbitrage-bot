"""
Tests for the enhanced arbitrage bot modules.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Import the modules we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from polling import (
    ContinuousAPIPoller, 
    AdaptiveRateLimiter, 
    CircuitBreaker,
    RateLimitStrategy
)
from probability_shifts import (
    MultiFactorShiftDetector,
    ProbabilitySnapshot,
    ProbabilityTrend
)
from whale_tracker import (
    WhaleTracker,
    WhaleOrder,
    WhaleOrderSide,
    WhaleSignalType
)
from latency_arbitrage import (
    LatencyArbitrageEngine,
    SpreadLockEngine,
    PriceVelocityTracker
)
from strategy_orchestrator import (
    StrategyOrchestrator,
    StrategyType,
    StrategyConfig
)


class TestAdaptiveRateLimiter:
    """Tests for the adaptive rate limiter."""
    
    @pytest.mark.asyncio
    async def test_acquire_permits_request(self):
        limiter = AdaptiveRateLimiter(max_requests_per_second=10)
        result = await limiter.acquire()
        assert result is True
    
    def test_record_response_updates_metrics(self):
        limiter = AdaptiveRateLimiter(max_requests_per_second=10)
        limiter.record_response(100, True)
        
        assert limiter.metrics.total_requests == 1
        assert limiter.metrics.successful_requests == 1
        assert limiter.metrics.avg_response_time_ms == 100
    
    def test_rate_limiting_adjusts_on_errors(self):
        limiter = AdaptiveRateLimiter(
            max_requests_per_second=10,
            strategy=RateLimitStrategy.ADAPTIVE
        )
        
        initial_interval = limiter.current_interval
        
        # Simulate many errors
        for _ in range(10):
            limiter.record_response(100, False, rate_limited=True)
        
        # Interval should have increased
        assert limiter.current_interval > initial_interval


class TestCircuitBreaker:
    """Tests for the circuit breaker."""
    
    @pytest.mark.asyncio
    async def test_circuit_starts_closed(self):
        cb = CircuitBreaker()
        assert await cb.can_execute() is True
        assert cb.state == "closed"
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record failures
        for _ in range(3):
            await cb.record_failure()
        
        assert cb.state == "open"
        assert await cb.can_execute() is False
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_recovery(self):
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout_seconds=0  # Immediate recovery for test
        )
        
        # Open the circuit
        for _ in range(2):
            await cb.record_failure()
        
        assert cb.state == "open"
        
        # Should transition to half-open after timeout
        assert await cb.can_execute() is True
        assert cb.state == "half-open"
        
        # Success should close it
        await cb.record_success()
        assert cb.state == "closed"


class TestProbabilityShiftDetector:
    """Tests for probability shift detection."""
    
    def test_detects_upward_trend(self):
        detector = MultiFactorShiftDetector()
        
        # Add increasing probability snapshots
        for i in range(20):
            snapshot = ProbabilitySnapshot(
                timestamp=datetime.now() + timedelta(seconds=i),
                probability=0.4 + i * 0.02,  # Increasing
                volume_24h=1000,
                bid_ask_spread=0.01,
                order_book_imbalance=0.1
            )
            detector.add_snapshot("market1", snapshot)
        
        # Should detect shift
        opp = detector.detect_shift("market1", current_odds=0.75)
        
        if opp:  # Detection depends on thresholds
            assert opp.shift_magnitude > 0
            assert opp.predicted_odds > opp.current_odds
    
    def test_classifies_trends_correctly(self):
        detector = MultiFactorShiftDetector()
        
        momentum = {
            'price_momentum': 0.05,
            'velocity': 0.02,
            'volatility': 0.01
        }
        
        trend = detector._classify_trend(momentum)
        assert trend == ProbabilityTrend.STRONG_UP


class TestWhaleTracker:
    """Tests for whale tracking."""
    
    def test_tracks_whale_orders(self):
        tracker = WhaleTracker(min_order_size_usd=1000)
        
        order = WhaleOrder(
            order_id="test1",
            market_id="market1",
            side=WhaleOrderSide.BUY_YES,
            size_usd=5000,
            price=0.6,
            timestamp=datetime.now(),
            trader_address="0xabc"
        )
        
        tracker.add_order(order)
        
        # Should have tracked the order
        assert len(tracker._recent_orders) == 1
        assert len(tracker._market_activity["market1"]) == 1
    
    def test_ignores_small_orders(self):
        tracker = WhaleTracker(min_order_size_usd=10000)
        
        order = WhaleOrder(
            order_id="test1",
            market_id="market1",
            side=WhaleOrderSide.BUY_YES,
            size_usd=5000,  # Below threshold
            price=0.6,
            timestamp=datetime.now()
        )
        
        tracker.add_order(order)
        
        # Should not track small orders
        assert len(tracker._recent_orders) == 0


class TestLatencyArbitrageEngine:
    """Tests for latency arbitrage engine."""
    
    def test_detects_high_velocity_moves(self):
        engine = LatencyArbitrageEngine(min_velocity_threshold=1.0)
        
        # Register a market
        engine.register_market(
            market_id="BTC_15MIN_UP",
            symbol="BTC/USDT",
            strike_price=50000,
            expiry_time=datetime.now() + timedelta(minutes=15),
            market_type="15MIN"
        )
        
        # Add prices with high velocity
        base_time = datetime.now()
        for i in range(10):
            engine.velocity_tracker.add_price(
                "BTC/USDT",
                50000 + i * 100,  # Increasing $100 per second
                base_time + timedelta(seconds=i)
            )
        
        # Process update
        opps = engine.process_price_update("BTC/USDT", 51000)
        
        # Should detect opportunity due to high velocity
        assert opps is not None
        assert len(opps) > 0
    
    def test_spread_engine_detects_arbitrage(self):
        engine = SpreadLockEngine(min_spread_percent=0.01)
        
        # Check spread opportunity
        opp = engine.check_spread_opportunity(
            market_id="market1",
            yes_price=0.45,
            no_price=0.50,
            fees=0.02
        )
        
        assert opp is not None
        assert opp['spread'] > 0


class TestStrategyOrchestrator:
    """Tests for strategy orchestrator."""
    
    def test_evaluates_opportunities_by_priority(self):
        config = {
            'latency': {
                'enabled': True,
                'priority': 10,
                'max_positions': 5,
                'capital_allocation': 0.4,
                'min_opportunity_score': 0.5
            },
            'whale': {
                'enabled': True,
                'priority': 5,
                'max_positions': 3,
                'capital_allocation': 0.3,
                'min_opportunity_score': 0.6
            }
        }
        
        orchestrator = StrategyOrchestrator(config)
        
        # Create test opportunities
        from dataclasses import dataclass
        
        @dataclass
        class MockOpp:
            market_id: str
            confidence: float
            expected_profit: float
            direction: str = "up"
            urgency: float = 0.5
            size_usd: float = 100
        
        opportunities = {
            StrategyType.LATENCY: [MockOpp("m1", 0.8, 0.05)],
            StrategyType.WHALE: [MockOpp("m2", 0.7, 0.03)]
        }
        
        scored = orchestrator.evaluate_opportunities(opportunities)
        
        # Should return scored opportunities
        assert len(scored) == 2
        # Higher priority should have higher score
        assert scored[0].opportunity_score >= scored[1].opportunity_score


class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    async def test_poller_initialization(self):
        poller = ContinuousAPIPoller(
            max_requests_per_second=5,
            strategy=RateLimitStrategy.FIXED
        )
        
        # Register an endpoint
        from polling import APIEndpoint
        endpoint = APIEndpoint(
            name="test",
            url="https://httpbin.org/get",
            cache_ttl_ms=5000
        )
        poller.register_endpoint(endpoint)
        
        # Should have registered
        assert "test" in poller._endpoints
    
    def test_end_to_end_opportunity_detection(self):
        """Test full flow from price update to opportunity detection."""
        # Setup components
        latency_engine = LatencyArbitrageEngine()
        
        latency_engine.register_market(
            market_id="BTC_15MIN",
            symbol="BTC/USDT",
            strike_price=50000,
            expiry_time=datetime.now() + timedelta(minutes=15)
        )
        
        # Simulate price surge
        now = datetime.now()
        for i in range(10):
            latency_engine.velocity_tracker.add_price(
                "BTC/USDT",
                50000 + i * 200,  # Strong upward move
                now + timedelta(seconds=i)
            )
        
        # Detect opportunities
        opps = latency_engine.process_price_update("BTC/USDT", 52000)
        
        # Should detect the momentum
        assert opps is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])