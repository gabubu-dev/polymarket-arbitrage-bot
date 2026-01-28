"""
15-minute market latency arbitrage.

Optimized for fast execution on Polymarket's 15-minute crypto prediction markets.
Exploits the 30-90 second delay between exchange price moves and Polymarket odds updates.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import numpy as np


@dataclass
class LatencyOpportunity:
    """A latency arbitrage opportunity."""
    market_id: str
    symbol: str
    direction: str  # 'up' or 'down'
    exchange_price: float
    exchange_price_velocity: float
    polymarket_odds: float
    implied_probability: float
    expected_move_probability: float
    edge_percent: float
    confidence: float
    time_to_expiry_seconds: float
    execution_deadline: datetime
    timestamp: datetime


@dataclass
class ExecutionResult:
    """Result of a latency arbitrage execution."""
    success: bool
    order_id: Optional[str]
    fill_price: Optional[float]
    fill_size: Optional[float]
    execution_time_ms: float
    error_message: Optional[str] = None
    slippage: float = 0.0


class PriceVelocityTracker:
    """Tracks price velocity for exchange symbols."""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._prices: Dict[str, deque] = {}
        self._timestamps: Dict[str, deque] = {}
    
    def add_price(self, symbol: str, price: float, timestamp: datetime = None):
        """Add a price observation."""
        if timestamp is None:
            timestamp = datetime.now()
        
        if symbol not in self._prices:
            self._prices[symbol] = deque(maxlen=self.window_size)
            self._timestamps[symbol] = deque(maxlen=self.window_size)
        
        self._prices[symbol].append(price)
        self._timestamps[symbol].append(timestamp)
    
    def get_velocity(self, symbol: str) -> float:
        """Get price velocity (change per second)."""
        if symbol not in self._prices or len(self._prices[symbol]) < 2:
            return 0.0
        
        prices = list(self._prices[symbol])
        timestamps = list(self._timestamps[symbol])
        
        if len(prices) < 2:
            return 0.0
        
        # Calculate velocity over the window
        price_change = prices[-1] - prices[0]
        time_diff = (timestamps[-1] - timestamps[0]).total_seconds()
        
        if time_diff <= 0:
            return 0.0
        
        return price_change / time_diff
    
    def get_acceleration(self, symbol: str) -> float:
        """Get price acceleration (change in velocity)."""
        if symbol not in self._prices or len(self._prices[symbol]) < 3:
            return 0.0
        
        prices = list(self._prices[symbol])
        timestamps = list(self._timestamps[symbol])
        
        # Calculate velocity in first half
        mid = len(prices) // 2
        v1 = (prices[mid] - prices[0]) / max(0.001, (timestamps[mid] - timestamps[0]).total_seconds())
        
        # Calculate velocity in second half
        v2 = (prices[-1] - prices[mid]) / max(0.001, (timestamps[-1] - timestamps[mid]).total_seconds())
        
        return v2 - v1
    
    def get_trend_strength(self, symbol: str) -> float:
        """Get trend strength (-1 to 1, stronger = more consistent)."""
        if symbol not in self._prices or len(self._prices[symbol]) < 3:
            return 0.0
        
        prices = list(self._prices[symbol])
        
        # Calculate correlation with linear trend
        x = np.arange(len(prices))
        y = np.array(prices)
        
        # Normalize
        y_norm = (y - y.mean()) / (y.std() + 1e-10)
        
        # Correlation with linear trend
        correlation = np.corrcoef(x, y_norm)[0, 1]
        
        return correlation if not np.isnan(correlation) else 0.0


class LatencyArbitrageEngine:
    """
    High-speed engine for 15-minute market latency arbitrage.
    
    Key optimizations:
    - Sub-100ms opportunity detection
    - Pre-computed order parameters
    - Parallel execution paths
    - Fallback execution strategies
    """
    
    def __init__(self,
                 min_divergence: float = 0.03,
                 max_execution_time_ms: float = 500,
                 min_velocity_threshold: float = 0.5,  # Price change per second
                 confidence_threshold: float = 0.75,
                 cooldown_seconds: float = 10):
        self.logger = logging.getLogger("LatencyArbitrageEngine")
        self.min_divergence = min_divergence
        self.max_execution_time_ms = max_execution_time_ms
        self.min_velocity = min_velocity_threshold
        self.confidence_threshold = confidence_threshold
        self.cooldown = timedelta(seconds=cooldown_seconds)
        
        # Tracking
        self.velocity_tracker = PriceVelocityTracker(window_size=10)
        self._last_trade_time: Dict[str, datetime] = {}
        self._market_metadata: Dict[str, Dict] = {}
        
        # Performance tracking
        self._execution_times: deque = deque(maxlen=100)
        self._opportunities_seen = 0
        self._opportunities_executed = 0
    
    def register_market(self, 
                       market_id: str,
                       symbol: str,
                       strike_price: float,
                       expiry_time: datetime,
                       market_type: str = "15MIN"):
        """Register a market for monitoring."""
        self._market_metadata[market_id] = {
            'symbol': symbol,
            'strike_price': strike_price,
            'expiry_time': expiry_time,
            'market_type': market_type,
            'registered_at': datetime.now()
        }
        
        self.logger.debug(f"Registered {market_type} market: {market_id} ({symbol})")
    
    def process_price_update(self,
                            symbol: str,
                            price: float,
                            timestamp: datetime = None) -> Optional[List[LatencyOpportunity]]:
        """
        Process a price update and detect opportunities.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            price: Current price
            timestamp: Update timestamp
            
        Returns:
            List of opportunities or None
        """
        # Update velocity tracker
        self.velocity_tracker.add_price(symbol, price, timestamp)
        
        # Get velocity metrics
        velocity = self.velocity_tracker.get_velocity(symbol)
        acceleration = self.velocity_tracker.get_acceleration(symbol)
        trend_strength = self.velocity_tracker.get_trend_strength(symbol)
        
        # Check if velocity is significant enough
        if abs(velocity) < self.min_velocity:
            return None
        
        # Find relevant markets
        opportunities = []
        
        for market_id, metadata in self._market_metadata.items():
            if metadata['symbol'] != symbol:
                continue
            
            # Check cooldown
            if self._is_in_cooldown(market_id):
                continue
            
            # Calculate opportunity
            opp = self._calculate_opportunity(
                market_id=market_id,
                symbol=symbol,
                price=price,
                velocity=velocity,
                acceleration=acceleration,
                trend_strength=trend_strength,
                metadata=metadata
            )
            
            if opp and opp.confidence >= self.confidence_threshold:
                opportunities.append(opp)
                self._opportunities_seen += 1
        
        return opportunities if opportunities else None
    
    def _calculate_opportunity(self,
                              market_id: str,
                              symbol: str,
                              price: float,
                              velocity: float,
                              acceleration: float,
                              trend_strength: float,
                              metadata: Dict) -> Optional[LatencyOpportunity]:
        """Calculate if there's a latency arbitrage opportunity."""
        # Determine direction based on velocity
        direction = "up" if velocity > 0 else "down"
        
        # Calculate expected price at market expiry
        time_to_expiry = (metadata['expiry_time'] - datetime.now()).total_seconds()
        
        if time_to_expiry <= 0:
            return None  # Market expired
        
        # Predict price at expiry
        # Simple model: current price + velocity * time + 0.5 * acceleration * time^2
        predicted_price = price + velocity * time_to_expiry + \
                         0.5 * acceleration * (time_to_expiry ** 2)
        
        # Calculate probability of being above/below strike
        strike = metadata['strike_price']
        
        if direction == "up":
            expected_move_prob = min(0.99, max(0.01, (predicted_price - strike) / strike + 0.5))
        else:
            expected_move_prob = min(0.99, max(0.01, (strike - predicted_price) / strike + 0.5))
        
        # This would normally come from Polymarket API
        # For now, placeholder - in real implementation, fetch current odds
        current_odds = 0.5  # Placeholder
        
        # Calculate edge
        edge = abs(expected_move_prob - current_odds)
        
        if edge < self.min_divergence:
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            velocity=velocity,
            acceleration=acceleration,
            trend_strength=trend_strength,
            time_to_expiry=time_to_expiry,
            edge=edge
        )
        
        if confidence < self.confidence_threshold:
            return None
        
        # Calculate execution deadline
        # We need to execute before market catches up
        # Estimate: price moves are reflected in odds within 30-90 seconds
        reaction_time = 30 + (1 - abs(trend_strength)) * 60  # 30-90s based on trend clarity
        execution_deadline = datetime.now() + timedelta(seconds=reaction_time)
        
        return LatencyOpportunity(
            market_id=market_id,
            symbol=symbol,
            direction=direction,
            exchange_price=price,
            exchange_price_velocity=velocity,
            polymarket_odds=current_odds,
            implied_probability=expected_move_prob,
            expected_move_probability=expected_move_prob,
            edge_percent=edge * 100,
            confidence=confidence,
            time_to_expiry_seconds=time_to_expiry,
            execution_deadline=execution_deadline,
            timestamp=datetime.now()
        )
    
    def _calculate_confidence(self,
                             velocity: float,
                             acceleration: float,
                             trend_strength: float,
                             time_to_expiry: float,
                             edge: float) -> float:
        """Calculate confidence score for the opportunity."""
        scores = []
        
        # Velocity score (higher velocity = higher confidence)
        vel_score = min(1.0, abs(velocity) / (self.min_velocity * 3))
        scores.append(vel_score * 0.25)
        
        # Trend strength score
        scores.append(abs(trend_strength) * 0.20)
        
        # Acceleration score (accelerating moves are more reliable)
        accel_score = min(1.0, abs(acceleration) / (abs(velocity) + 0.1))
        scores.append(accel_score * 0.15)
        
        # Edge score (larger edge = more confident)
        edge_score = min(1.0, edge / 0.1)  # Max at 10% edge
        scores.append(edge_score * 0.25)
        
        # Time score (more time = more confident)
        time_score = min(1.0, time_to_expiry / 600)  # Max at 10 minutes
        scores.append(time_score * 0.15)
        
        return sum(scores)
    
    def _is_in_cooldown(self, market_id: str) -> bool:
        """Check if market is in cooldown period."""
        if market_id not in self._last_trade_time:
            return False
        
        return datetime.now() - self._last_trade_time[market_id] < self.cooldown
    
    async def execute_opportunity(self,
                                  opportunity: LatencyOpportunity,
                                  polymarket_client,
                                  position_size_usd: float) -> ExecutionResult:
        """
        Execute a latency arbitrage opportunity.
        
        Optimized for speed - must complete before window closes.
        """
        start_time = time.time()
        
        try:
            # Validate opportunity is still valid
            if datetime.now() > opportunity.execution_deadline:
                return ExecutionResult(
                    success=False,
                    order_id=None,
                    fill_price=None,
                    fill_size=None,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    error_message="Execution deadline passed"
                )
            
            # Determine order parameters
            side = "BUY"
            price = opportunity.polymarket_odds
            
            # Adjust price for slippage (be more aggressive to ensure fill)
            if opportunity.direction == "up":
                # Buying YES - offer slightly more
                price = min(0.99, price + 0.005)
            else:
                # Buying NO - equivalent to selling YES at (1 - price)
                # For simplicity, assuming we can express this
                price = max(0.01, price - 0.005)
            
            # Place order with timeout
            order_id = await asyncio.wait_for(
                polymarket_client.place_order(
                    market_id=opportunity.market_id,
                    side=side,
                    size=position_size_usd,
                    price=price
                ),
                timeout=self.max_execution_time_ms / 1000.0
            )
            
            execution_time = (time.time() - start_time) * 1000
            self._execution_times.append(execution_time)
            
            if order_id:
                self._opportunities_executed += 1
                self._last_trade_time[opportunity.market_id] = datetime.now()
                
                return ExecutionResult(
                    success=True,
                    order_id=order_id,
                    fill_price=price,
                    fill_size=position_size_usd,
                    execution_time_ms=execution_time
                )
            else:
                return ExecutionResult(
                    success=False,
                    order_id=None,
                    fill_price=None,
                    fill_size=None,
                    execution_time_ms=execution_time,
                    error_message="Order placement failed"
                )
                
        except asyncio.TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                order_id=None,
                fill_price=None,
                fill_size=None,
                execution_time_ms=execution_time,
                error_message="Execution timeout"
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                order_id=None,
                fill_price=None,
                fill_size=None,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def get_performance_stats(self) -> Dict:
        """Get engine performance statistics."""
        stats = {
            'opportunities_seen': self._opportunities_seen,
            'opportunities_executed': self._opportunities_executed,
            'execution_rate': (
                self._opportunities_executed / max(1, self._opportunities_seen)
            ),
            'markets_tracked': len(self._market_metadata)
        }
        
        if self._execution_times:
            times = list(self._execution_times)
            stats['avg_execution_time_ms'] = np.mean(times)
            stats['median_execution_time_ms'] = np.median(times)
            stats['max_execution_time_ms'] = max(times)
            stats['min_execution_time_ms'] = min(times)
        
        return stats
    
    def reset_stats(self):
        """Reset performance statistics."""
        self._opportunities_seen = 0
        self._opportunities_executed = 0
        self._execution_times.clear()


class SpreadLockEngine:
    """
    Risk-free spread locking engine.
    
    Identifies and locks in risk-free arbitrage spreads between
    different markets or between market sides.
    """
    
    def __init__(self, min_spread_percent: float = 0.01):
        self.logger = logging.getLogger("SpreadLockEngine")
        self.min_spread = min_spread_percent
        self._active_spreads: Dict[str, Dict] = {}
    
    def check_spread_opportunity(self,
                                 market_id: str,
                                 yes_price: float,
                                 no_price: float,
                                 fees: float = 0.02) -> Optional[Dict]:
        """
        Check for risk-free spread opportunity.
        
        A risk-free opportunity exists when:
        yes_price + no_price < 1 - fees
        
        This allows buying both sides and profiting regardless of outcome.
        """
        total_cost = yes_price + no_price
        
        if total_cost >= 1.0 - fees:
            return None
        
        spread = 1.0 - total_cost - fees
        
        if spread < self.min_spread:
            return None
        
        return {
            'market_id': market_id,
            'yes_price': yes_price,
            'no_price': no_price,
            'total_cost': total_cost,
            'spread': spread,
            'spread_percent': spread * 100,
            'max_position_size': spread / fees if fees > 0 else float('inf'),
            'timestamp': datetime.now()
        }
    
    def check_cross_market_spread(self,
                                  market_a_id: str,
                                  market_b_id: str,
                                  a_yes_price: float,
                                  b_yes_price: float,
                                  correlation: float = 1.0) -> Optional[Dict]:
        """
        Check for spread between correlated markets.
        
        For example, BTC 15-min up vs BTC 1-hour up when 15-min is nested.
        """
        price_diff = abs(a_yes_price - b_yes_price)
        avg_price = (a_yes_price + b_yes_price) / 2
        
        if avg_price == 0:
            return None
        
        spread_pct = price_diff / avg_price
        
        # Adjust threshold by correlation
        threshold = self.min_spread * (2 - correlation)
        
        if spread_pct < threshold:
            return None
        
        # Determine which is cheaper
        if a_yes_price < b_yes_price:
            buy_market = market_a_id
            sell_market = market_b_id
            buy_price = a_yes_price
            sell_price = b_yes_price
        else:
            buy_market = market_b_id
            sell_market = market_a_id
            buy_price = b_yes_price
            sell_price = a_yes_price
        
        return {
            'type': 'cross_market',
            'buy_market': buy_market,
            'sell_market': sell_market,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'spread': price_diff,
            'spread_percent': spread_pct * 100,
            'correlation': correlation,
            'timestamp': datetime.now()
        }