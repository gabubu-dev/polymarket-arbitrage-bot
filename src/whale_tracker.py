"""
Whale movement tracking for Polymarket.

Monitors large orders and smart money movements to detect early signals
before the broader market reacts.
"""

import logging
from typing import Dict, List, Optional, Set, Deque, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import numpy as np


class WhaleOrderSide(Enum):
    """Side of a whale order."""
    BUY_YES = "buy_yes"
    BUY_NO = "buy_no"
    SELL_YES = "sell_yes"
    SELL_NO = "sell_no"


class WhaleSignalType(Enum):
    """Types of whale signals."""
    ACCUMULATION = "accumulation"      # Steady buying over time
    DISTRIBUTION = "distribution"      # Steady selling
    LARGE_ORDER = "large_order"        # Single large order
    ORDER_WALL = "order_wall"          # Large order book wall
    MOMENTUM = "momentum"              # Following momentum
    CONTRARIAN = "contrarian"          # Betting against trend


@dataclass
class WhaleOrder:
    """Represents a whale-sized order."""
    order_id: str
    market_id: str
    side: WhaleOrderSide
    size_usd: float
    price: float
    timestamp: datetime
    trader_address: Optional[str] = None
    is_filled: bool = False
    fill_time: Optional[datetime] = None


@dataclass
class WhaleSignal:
    """Signal generated from whale activity."""
    market_id: str
    signal_type: WhaleSignalType
    direction: str  # 'up' or 'down' (what whales are betting on)
    confidence: float
    total_volume_usd: float
    num_whales: int
    avg_whl_price: float
    timestamp: datetime
    urgency: float  # 0-1, how quickly to act
    details: Dict = field(default_factory=dict)


@dataclass
class WhaleOpportunity:
    """Trading opportunity based on whale activity."""
    market_id: str
    current_odds: float
    whale_target_odds: float
    direction: str
    confidence: float
    expected_profit: float
    follow_whales: bool  # True = follow, False = fade (contrarian)
    entry_deadline: datetime
    whale_addresses: List[str] = field(default_factory=list)


class WhaleTracker:
    """
    Tracks whale movements on Polymarket.
    
    Identifies:
    - Large orders (>threshold USD)
    - Accumulation/distribution patterns
    - Smart money addresses with track records
    - Order book walls that may move markets
    """
    
    def __init__(self,
                 min_order_size_usd: float = 5000,
                 tracking_window_seconds: int = 300,
                 whale_address_threshold: float = 0.6,  # Win rate threshold
                 follow_threshold: float = 0.6):  # Confidence to follow
        self.logger = logging.getLogger("WhaleTracker")
        self.min_order_size = min_order_size_usd
        self.tracking_window = timedelta(seconds=tracking_window_seconds)
        self.whale_threshold = whale_address_threshold
        self.follow_threshold = follow_threshold
        
        # Data storage
        self._recent_orders: Deque[WhaleOrder] = deque()
        self._whale_addresses: Dict[str, Dict] = {}  # address -> stats
        self._market_activity: Dict[str, List[WhaleOrder]] = defaultdict(list)
        self._order_book_walls: Dict[str, Dict] = {}
        
        # Performance tracking for learning
        self._trade_history: Dict[str, List[Dict]] = defaultdict(list)
    
    def add_order(self, order: WhaleOrder) -> None:
        """Add a new order to tracking."""
        # Only track whale-sized orders
        if order.size_usd < self.min_order_size:
            return
        
        self._recent_orders.append(order)
        self._market_activity[order.market_id].append(order)
        
        # Update whale address stats
        if order.trader_address:
            self._update_whale_stats(order.trader_address, order)
        
        # Cleanup old data
        self._cleanup_old_data()
        
        self.logger.debug(
            f"Whale order: {order.side.value} ${order.size_usd:.0f} @ "
            f"{order.price:.3f} in {order.market_id}"
        )
    
    def add_order_book_snapshot(self,
                                market_id: str,
                                bids: List[Tuple[float, float]],  # (price, size)
                                asks: List[Tuple[float, float]]) -> None:
        """Process order book to identify walls."""
        # Find large walls (clusters of size > threshold)
        yes_wall = self._find_wall(bids, self.min_order_size)
        no_wall = self._find_wall(asks, self.min_order_size)
        
        self._order_book_walls[market_id] = {
            'yes_wall': yes_wall,
            'no_wall': no_wall,
            'timestamp': datetime.now()
        }
    
    def detect_signal(self, market_id: str, current_odds: float) -> Optional[WhaleSignal]:
        """
        Detect whale signal for a market.
        
        Args:
            market_id: Market to analyze
            current_odds: Current market odds
            
        Returns:
            WhaleSignal if detected, None otherwise
        """
        activity = self._market_activity.get(market_id, [])
        
        if not activity:
            return None
        
        # Filter to recent activity
        cutoff = datetime.now() - self.tracking_window
        recent = [o for o in activity if o.timestamp > cutoff]
        
        if not recent:
            return None
        
        # Analyze activity patterns
        signal_type, direction = self._classify_pattern(recent)
        
        if signal_type is None:
            return None
        
        # Calculate metrics
        total_volume = sum(o.size_usd for o in recent)
        unique_whales = len(set(o.trader_address for o in recent if o.trader_address))
        avg_price = np.mean([o.price for o in recent])
        
        # Calculate confidence
        confidence = self._calculate_confidence(recent, signal_type)
        
        # Calculate urgency
        urgency = self._calculate_urgency(recent, signal_type)
        
        signal = WhaleSignal(
            market_id=market_id,
            signal_type=signal_type,
            direction=direction,
            confidence=confidence,
            total_volume_usd=total_volume,
            num_whales=unique_whales,
            avg_whl_price=avg_price,
            timestamp=datetime.now(),
            urgency=urgency,
            details={
                'recent_orders': len(recent),
                'largest_order': max(o.size_usd for o in recent),
                'wall_pressure': self._get_wall_pressure(market_id, direction)
            }
        )
        
        self.logger.info(
            f"Whale signal in {market_id}: {signal_type.value} {direction} "
            f"(confidence: {confidence:.2f}, volume: ${total_volume:.0f})"
        )
        
        return signal
    
    def get_opportunity(self, 
                       signal: WhaleSignal,
                       current_odds: float) -> Optional[WhaleOpportunity]:
        """
        Convert whale signal to trading opportunity.
        
        Args:
            signal: Detected whale signal
            current_odds: Current market odds
            
        Returns:
            WhaleOpportunity if actionable, None otherwise
        """
        if signal.confidence < self.follow_threshold:
            return None
        
        # Determine if we should follow or fade
        follow = self._should_follow(signal)
        
        # Calculate target odds based on whale activity
        if follow:
            # Follow whales - target moves toward whale average
            target_odds = signal.avg_whl_price
        else:
            # Fade whales - contrarian play
            target_odds = 1.0 - signal.avg_whl_price
        
        # Calculate expected profit
        price_diff = abs(target_odds - current_odds)
        fees = 0.02  # Polymarket fee
        expected_profit = price_diff * signal.confidence - fees
        
        if expected_profit <= 0:
            return None
        
        # Get whale addresses for this signal
        activity = self._market_activity.get(signal.market_id, [])
        cutoff = datetime.now() - self.tracking_window
        whale_addrs = list(set(
            o.trader_address for o in activity 
            if o.timestamp > cutoff and o.trader_address
        ))
        
        opportunity = WhaleOpportunity(
            market_id=signal.market_id,
            current_odds=current_odds,
            whale_target_odds=target_odds,
            direction=signal.direction if follow else ('down' if signal.direction == 'up' else 'up'),
            confidence=signal.confidence,
            expected_profit=expected_profit,
            follow_whales=follow,
            entry_deadline=datetime.now() + timedelta(seconds=int(60 * (1 - signal.urgency))),
            whale_addresses=whale_addrs
        )
        
        return opportunity
    
    def _update_whale_stats(self, address: str, order: WhaleOrder) -> None:
        """Update performance stats for a whale address."""
        if address not in self._whale_addresses:
            self._whale_addresses[address] = {
                'total_trades': 0,
                'profitable_trades': 0,
                'total_volume': 0,
                'markets_traded': set(),
                'first_seen': datetime.now()
            }
        
        stats = self._whale_addresses[address]
        stats['total_trades'] += 1
        stats['total_volume'] += order.size_usd
        stats['markets_traded'].add(order.market_id)
    
    def _cleanup_old_data(self) -> None:
        """Remove data older than tracking window."""
        cutoff = datetime.now() - self.tracking_window
        
        # Clean recent orders
        while self._recent_orders and self._recent_orders[0].timestamp < cutoff:
            self._recent_orders.popleft()
        
        # Clean market activity
        for market_id in list(self._market_activity.keys()):
            self._market_activity[market_id] = [
                o for o in self._market_activity[market_id]
                if o.timestamp > cutoff
            ]
    
    def _find_wall(self, 
                  orders: List[Tuple[float, float]],
                  threshold: float) -> Optional[Dict]:
        """Find a price wall in order book."""
        if not orders:
            return None
        
        # Sort by size and find clusters
        sorted_orders = sorted(orders, key=lambda x: x[1], reverse=True)
        
        for price, size in sorted_orders[:3]:  # Check top 3
            if size >= threshold:
                return {'price': price, 'size': size}
        
        return None
    
    def _classify_pattern(self, 
                         orders: List[WhaleOrder]) -> Tuple[Optional[WhaleSignalType], str]:
        """Classify the pattern of whale activity."""
        if len(orders) < 2:
            # Single large order
            side = orders[0].side
            direction = 'up' if side in [WhaleOrderSide.BUY_YES, WhaleOrderSide.SELL_NO] else 'down'
            return WhaleSignalType.LARGE_ORDER, direction
        
        # Analyze sequence
        yes_volume = sum(o.size_usd for o in orders 
                        if o.side in [WhaleOrderSide.BUY_YES, WhaleOrderSide.SELL_NO])
        no_volume = sum(o.size_usd for o in orders 
                       if o.side in [WhaleOrderSide.BUY_NO, WhaleOrderSide.SELL_YES])
        
        # Check for accumulation/distribution
        timestamps = [o.timestamp for o in orders]
        time_span = max(timestamps) - min(timestamps)
        
        if time_span > timedelta(minutes=2):
            # Extended activity
            if yes_volume > no_volume * 2:
                return WhaleSignalType.ACCUMULATION, 'up'
            elif no_volume > yes_volume * 2:
                return WhaleSignalType.DISTRIBUTION, 'down'
        
        # Check for momentum vs contrarian
        prices = [o.price for o in orders]
        price_trend = prices[-1] - prices[0]
        
        volume_imbalance = abs(yes_volume - no_volume) / (yes_volume + no_volume)
        
        if volume_imbalance > 0.7:
            dominant_side = 'up' if yes_volume > no_volume else 'down'
            if (dominant_side == 'up' and price_trend > 0) or \
               (dominant_side == 'down' and price_trend < 0):
                return WhaleSignalType.MOMENTUM, dominant_side
            else:
                return WhaleSignalType.CONTRARIAN, dominant_side
        
        return None, ''
    
    def _calculate_confidence(self,
                             orders: List[WhaleOrder],
                             signal_type: WhaleSignalType) -> float:
        """Calculate confidence score for whale signal."""
        scores = []
        
        # Volume score
        total_volume = sum(o.size_usd for o in orders)
        volume_score = min(1.0, total_volume / (self.min_order_size * 10))
        scores.append(volume_score * 0.3)
        
        # Whale quality score
        known_whales = 0
        for o in orders:
            if o.trader_address and o.trader_address in self._whale_addresses:
                stats = self._whale_addresses[o.trader_address]
                win_rate = stats['profitable_trades'] / max(1, stats['total_trades'])
                if win_rate > self.whale_threshold:
                    known_whales += 1
        
        quality_score = min(1.0, known_whales / max(1, len(orders)))
        scores.append(quality_score * 0.4)
        
        # Consistency score (all orders in same direction)
        sides = [o.side for o in orders]
        yes_count = sum(1 for s in sides if s in [WhaleOrderSide.BUY_YES, WhaleOrderSide.SELL_NO])
        consistency = max(yes_count, len(sides) - yes_count) / len(sides)
        scores.append(consistency * 0.3)
        
        return sum(scores)
    
    def _calculate_urgency(self,
                          orders: List[WhaleOrder],
                          signal_type: WhaleSignalType) -> float:
        """Calculate urgency to act on signal."""
        urgency = 0.0
        
        # Recent activity = more urgent
        now = datetime.now()
        last_order_time = max(o.timestamp for o in orders)
        seconds_since_last = (now - last_order_time).total_seconds()
        recency_score = max(0, 1 - seconds_since_last / 60)  # Decay over 1 minute
        urgency += recency_score * 0.4
        
        # Large orders = more urgent
        max_size = max(o.size_usd for o in orders)
        size_score = min(1.0, max_size / (self.min_order_size * 5))
        urgency += size_score * 0.3
        
        # Signal type factor
        type_scores = {
            WhaleSignalType.LARGE_ORDER: 0.8,
            WhaleSignalType.ACCUMULATION: 0.5,
            WhaleSignalType.DISTRIBUTION: 0.5,
            WhaleSignalType.MOMENTUM: 0.7,
            WhaleSignalType.CONTRARIAN: 0.4,
            WhaleSignalType.ORDER_WALL: 0.6
        }
        urgency += type_scores.get(signal_type, 0.5) * 0.3
        
        return min(1.0, urgency)
    
    def _get_wall_pressure(self, market_id: str, direction: str) -> float:
        """Get order book wall pressure for a direction."""
        walls = self._order_book_walls.get(market_id, {})
        
        if not walls:
            return 0.0
        
        yes_wall = walls.get('yes_wall', {})
        no_wall = walls.get('no_wall', {})
        
        if direction == 'up' and yes_wall:
            return min(1.0, yes_wall.get('size', 0) / (self.min_order_size * 3))
        elif direction == 'down' and no_wall:
            return min(1.0, no_wall.get('size', 0) / (self.min_order_size * 3))
        
        return 0.0
    
    def _should_follow(self, signal: WhaleSignal) -> bool:
        """Determine if we should follow or fade the whales."""
        # Follow momentum and accumulation
        if signal.signal_type in [WhaleSignalType.MOMENTUM, WhaleSignalType.ACCUMULATION]:
            return True
        
        # Fade distribution (they're exiting)
        if signal.signal_type == WhaleSignalType.DISTRIBUTION:
            return False
        
        # Follow large orders if confidence is high
        if signal.signal_type == WhaleSignalType.LARGE_ORDER and signal.confidence > 0.75:
            return True
        
        # Default: follow
        return True
    
    def record_outcome(self,
                      address: str,
                      market_id: str,
                      profit: float,
                      was_profitable: bool) -> None:
        """Record trade outcome for whale tracking."""
        if address in self._whale_addresses:
            self._whale_addresses[address]['total_trades'] += 1
            if was_profitable:
                self._whale_addresses[address]['profitable_trades'] += 1
        
        self._trade_history[market_id].append({
            'timestamp': datetime.now(),
            'whale_address': address,
            'profit': profit,
            'success': was_profitable
        })
    
    def get_top_whales(self, min_trades: int = 5, limit: int = 10) -> List[Dict]:
        """Get top performing whale addresses."""
        results = []
        
        for address, stats in self._whale_addresses.items():
            if stats['total_trades'] >= min_trades:
                win_rate = stats['profitable_trades'] / stats['total_trades']
                results.append({
                    'address': address,
                    'win_rate': win_rate,
                    'total_trades': stats['total_trades'],
                    'total_volume': stats['total_volume'],
                    'markets': len(stats['markets_traded'])
                })
        
        # Sort by win rate
        results.sort(key=lambda x: x['win_rate'], reverse=True)
        return results[:limit]
    
    def get_market_summary(self, market_id: str) -> Dict:
        """Get whale activity summary for a market."""
        activity = self._market_activity.get(market_id, [])
        cutoff = datetime.now() - self.tracking_window
        recent = [o for o in activity if o.timestamp > cutoff]
        
        if not recent:
            return {'active': False}
        
        yes_volume = sum(o.size_usd for o in recent 
                        if o.side in [WhaleOrderSide.BUY_YES, WhaleOrderSide.SELL_NO])
        no_volume = sum(o.size_usd for o in recent 
                       if o.side in [WhaleOrderSide.BUY_NO, WhaleOrderSide.SELL_YES])
        
        return {
            'active': True,
            'whale_count': len(set(o.trader_address for o in recent if o.trader_address)),
            'total_volume_24h': yes_volume + no_volume,
            'yes_volume': yes_volume,
            'no_volume': no_volume,
            'net_bias': (yes_volume - no_volume) / (yes_volume + no_volume) if (yes_volume + no_volume) > 0 else 0,
            'recent_orders': len(recent)
        }