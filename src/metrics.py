"""
Metrics collection and monitoring for the arbitrage bot.

Tracks performance, API calls, trades, and system health.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque
import json
from pathlib import Path
import statistics


@dataclass
class APICallMetrics:
    """Metrics for a single API call."""
    api_name: str
    endpoint: str
    latency_ms: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    cache_hit: bool = False
    error: Optional[str] = None


@dataclass
class TradeMetrics:
    """Metrics for a single trade."""
    trade_id: str
    symbol: str
    market_id: str
    direction: str
    entry_price: float
    exit_price: Optional[float] = None
    size_usd: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: Optional[str] = None
    strategy: str = "unknown"
    
    @property
    def duration_seconds(self) -> float:
        """Calculate trade duration in seconds."""
        end = self.exit_time or datetime.now()
        return (end - self.entry_time).total_seconds()
    
    @property
    def is_open(self) -> bool:
        """Check if trade is still open."""
        return self.exit_time is None


@dataclass
class OpportunityMetrics:
    """Metrics for detected opportunities."""
    timestamp: datetime
    symbol: str
    exchange: str
    divergence: float
    expected_profit: float
    confidence: float
    direction: str
    acted_on: bool = False


class MetricsCollector:
    """
    Centralized metrics collection for the arbitrage bot.
    
    Collects and aggregates metrics for:
    - API calls (latency, success rate)
    - Trades (P&L, win rate, duration)
    - Opportunities (detection rate, conversion rate)
    - System health (memory, CPU, uptime)
    """
    
    def __init__(
        self,
        max_history: int = 10000,
        aggregation_window_seconds: float = 300.0
    ):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of events to keep in memory
            aggregation_window_seconds: Time window for aggregation metrics
        """
        self.max_history = max_history
        self.aggregation_window = timedelta(seconds=aggregation_window_seconds)
        
        # Event storage
        self._api_calls: deque = deque(maxlen=max_history)
        self._trades: Dict[str, TradeMetrics] = {}
        self._closed_trades: deque = deque(maxlen=max_history)
        self._opportunities: deque = deque(maxlen=max_history)
        
        # Counters
        self._opportunities_detected = 0
        self._opportunities_acted = 0
        self._api_calls_total = 0
        self._api_calls_failed = 0
        
        # Start time
        self._start_time = datetime.now()
        
        # Alert thresholds
        self._alert_thresholds: Dict[str, Any] = {}
        self._alert_callbacks: List[Callable] = []
    
    def record_api_call(
        self,
        api_name: str,
        endpoint: str,
        latency_ms: float,
        success: bool,
        cache_hit: bool = False,
        error: Optional[str] = None
    ) -> None:
        """
        Record an API call metric.
        
        Args:
            api_name: Name of the API (e.g., 'polymarket', 'binance')
            endpoint: API endpoint called
            latency_ms: Response latency in milliseconds
            success: Whether the call succeeded
            cache_hit: Whether result was from cache
            error: Error message if failed
        """
        metric = APICallMetrics(
            api_name=api_name,
            endpoint=endpoint,
            latency_ms=latency_ms,
            success=success,
            cache_hit=cache_hit,
            error=error
        )
        
        self._api_calls.append(metric)
        self._api_calls_total += 1
        
        if not success:
            self._api_calls_failed += 1
        
        # Check alert thresholds
        self._check_api_alerts(api_name, latency_ms, success)
    
    def record_trade_entry(
        self,
        trade_id: str,
        symbol: str,
        market_id: str,
        direction: str,
        entry_price: float,
        size_usd: float,
        strategy: str = "unknown"
    ) -> None:
        """
        Record a trade entry.
        
        Args:
            trade_id: Unique trade identifier
            symbol: Trading symbol
            market_id: Polymarket market ID
            direction: Trade direction ('up' or 'down')
            entry_price: Entry price
            size_usd: Position size in USD
            strategy: Strategy used for entry
        """
        metric = TradeMetrics(
            trade_id=trade_id,
            symbol=symbol,
            market_id=market_id,
            direction=direction,
            entry_price=entry_price,
            size_usd=size_usd,
            strategy=strategy
        )
        
        self._trades[trade_id] = metric
    
    def record_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str
    ) -> Optional[TradeMetrics]:
        """
        Record a trade exit.
        
        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            exit_reason: Reason for exit
            
        Returns:
            Completed trade metrics or None if trade not found
        """
        trade = self._trades.get(trade_id)
        if not trade:
            return None
        
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.exit_reason = exit_reason
        
        # Calculate P&L
        # For prediction markets: P&L = (exit - entry) * size
        trade.pnl = (exit_price - trade.entry_price) * trade.size_usd
        if trade.entry_price != 0:
            trade.pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
        
        # Move to closed trades
        self._closed_trades.append(trade)
        del self._trades[trade_id]
        
        # Check alert thresholds
        self._check_pnl_alerts(trade)
        
        return trade
    
    def record_opportunity(
        self,
        symbol: str,
        exchange: str,
        divergence: float,
        expected_profit: float,
        confidence: float,
        direction: str,
        acted_on: bool = False
    ) -> None:
        """
        Record a detected arbitrage opportunity.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            divergence: Price divergence detected
            expected_profit: Expected profit percentage
            confidence: Confidence score (0-1)
            direction: Direction ('up' or 'down')
            acted_on: Whether a trade was executed
        """
        metric = OpportunityMetrics(
            symbol=symbol,
            exchange=exchange,
            divergence=divergence,
            expected_profit=expected_profit,
            confidence=confidence,
            direction=direction,
            acted_on=acted_on
        )
        
        self._opportunities.append(metric)
        self._opportunities_detected += 1
        
        if acted_on:
            self._opportunities_acted += 1
    
    def set_alert_threshold(
        self,
        metric_name: str,
        threshold: Any,
        comparator: str = "greater_than"
    ) -> None:
        """
        Set an alert threshold.
        
        Args:
            metric_name: Name of metric to monitor
            threshold: Threshold value
            comparator: Comparison operator ('greater_than', 'less_than', 'equals')
        """
        self._alert_thresholds[metric_name] = {
            'threshold': threshold,
            'comparator': comparator
        }
    
    def add_alert_callback(self, callback: Callable[[str, Any], None]) -> None:
        """
        Add a callback for alert notifications.
        
        Args:
            callback: Function(metric_name, value) to call when alert triggered
        """
        self._alert_callbacks.append(callback)
    
    def _check_api_alerts(
        self,
        api_name: str,
        latency_ms: float,
        success: bool
    ) -> None:
        """Check API-related alert thresholds."""
        # Check latency threshold
        latency_threshold = self._alert_thresholds.get('api_latency_ms')
        if latency_threshold and latency_ms > latency_threshold['threshold']:
            self._trigger_alert('api_latency_ms', latency_ms)
        
        # Check error rate threshold
        if not success:
            error_rate = self._api_calls_failed / self._api_calls_total
            error_threshold = self._alert_thresholds.get('api_error_rate')
            if error_threshold and error_rate > error_threshold['threshold']:
                self._trigger_alert('api_error_rate', error_rate)
    
    def _check_pnl_alerts(self, trade: TradeMetrics) -> None:
        """Check P&L-related alert thresholds."""
        daily_pnl = self.get_daily_pnl()
        
        loss_threshold = self._alert_thresholds.get('daily_loss')
        if loss_threshold and daily_pnl < -loss_threshold['threshold']:
            self._trigger_alert('daily_loss', daily_pnl)
        
        trade_loss_threshold = self._alert_thresholds.get('single_trade_loss')
        if trade_loss_threshold and trade.pnl < -trade_loss_threshold['threshold']:
            self._trigger_alert('single_trade_loss', trade.pnl)
    
    def _trigger_alert(self, metric_name: str, value: Any) -> None:
        """Trigger alert callbacks."""
        for callback in self._alert_callbacks:
            try:
                callback(metric_name, value)
            except Exception as e:
                print(f"Alert callback error: {e}")
    
    def get_api_stats(self, window_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Get API call statistics.
        
        Args:
            window_seconds: Time window for stats (None = all time)
            
        Returns:
            Dictionary with API statistics
        """
        calls = self._get_recent_api_calls(window_seconds)
        
        if not calls:
            return {
                'total_calls': 0,
                'success_rate': 0.0,
                'avg_latency_ms': 0.0,
                'p95_latency_ms': 0.0,
                'p99_latency_ms': 0.0,
                'cache_hit_rate': 0.0
            }
        
        latencies = [c.latency_ms for c in calls]
        successful = [c for c in calls if c.success]
        cache_hits = [c for c in calls if c.cache_hit]
        
        return {
            'total_calls': len(calls),
            'success_rate': len(successful) / len(calls),
            'avg_latency_ms': statistics.mean(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'cache_hit_rate': len(cache_hits) / len(calls) if calls else 0.0
        }
    
    def get_trade_stats(self, window_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Get trade statistics.
        
        Args:
            window_seconds: Time window for stats (None = all time)
            
        Returns:
            Dictionary with trade statistics
        """
        trades = self._get_recent_closed_trades(window_seconds)
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_pnl': 0.0,
                'avg_trade_duration_seconds': 0.0,
                'open_positions': len(self._trades)
            }
        
        winning_trades = [t for t in trades if t.pnl > 0]
        pnls = [t.pnl for t in trades]
        durations = [t.duration_seconds for t in trades]
        
        return {
            'total_trades': len(trades),
            'win_rate': len(winning_trades) / len(trades) if trades else 0.0,
            'total_pnl': sum(pnls),
            'avg_pnl': statistics.mean(pnls),
            'best_trade': max(pnls) if pnls else 0.0,
            'worst_trade': min(pnls) if pnls else 0.0,
            'avg_trade_duration_seconds': statistics.mean(durations) if durations else 0.0,
            'open_positions': len(self._trades)
        }
    
    def get_opportunity_stats(self, window_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Get opportunity detection statistics.
        
        Args:
            window_seconds: Time window for stats (None = all time)
            
        Returns:
            Dictionary with opportunity statistics
        """
        opportunities = self._get_recent_opportunities(window_seconds)
        
        if not opportunities:
            return {
                'total_detected': 0,
                'acted_on': 0,
                'conversion_rate': 0.0,
                'avg_divergence': 0.0,
                'avg_expected_profit': 0.0
            }
        
        acted = [o for o in opportunities if o.acted_on]
        divergences = [o.divergence for o in opportunities]
        profits = [o.expected_profit for o in opportunities]
        
        return {
            'total_detected': len(opportunities),
            'acted_on': len(acted),
            'conversion_rate': len(acted) / len(opportunities) if opportunities else 0.0,
            'avg_divergence': statistics.mean(divergences),
            'avg_expected_profit': statistics.mean(profits)
        }
    
    def get_daily_pnl(self) -> float:
        """Get total P&L for today."""
        today = datetime.now().date()
        daily_pnl = 0.0
        
        for trade in self._closed_trades:
            if trade.exit_time and trade.exit_time.date() == today:
                daily_pnl += trade.pnl
        
        # Include unrealized P&L from open trades
        for trade in self._trades.values():
            # This is approximate - would need current price for accurate calculation
            pass
        
        return daily_pnl
    
    def get_uptime_seconds(self) -> float:
        """Get bot uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all statistics combined."""
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': self.get_uptime_seconds(),
            'api': self.get_api_stats(),
            'trades': self.get_trade_stats(),
            'opportunities': self.get_opportunity_stats(),
            'daily_pnl': self.get_daily_pnl()
        }
    
    def export_to_json(self, filepath: str) -> None:
        """Export all metrics to JSON file."""
        data = {
            'export_time': datetime.now().isoformat(),
            'stats': self.get_all_stats(),
            'trades': [asdict(t) for t in self._closed_trades],
            'opportunities': [asdict(o) for o in self._opportunities]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _get_recent_api_calls(
        self,
        window_seconds: Optional[float]
    ) -> List[APICallMetrics]:
        """Get API calls within time window."""
        if window_seconds is None:
            return list(self._api_calls)
        
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        return [c for c in self._api_calls if c.timestamp > cutoff]
    
    def _get_recent_closed_trades(
        self,
        window_seconds: Optional[float]
    ) -> List[TradeMetrics]:
        """Get closed trades within time window."""
        if window_seconds is None:
            return list(self._closed_trades)
        
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        return [
            t for t in self._closed_trades
            if t.exit_time and t.exit_time > cutoff
        ]
    
    def _get_recent_opportunities(
        self,
        window_seconds: Optional[float]
    ) -> List[OpportunityMetrics]:
        """Get opportunities within time window."""
        if window_seconds is None:
            return list(self._opportunities)
        
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        return [o for o in self._opportunities if o.timestamp > cutoff]
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of a list."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


# Global metrics collector instance
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def reset_metrics() -> None:
    """Reset global metrics collector."""
    global _metrics
    _metrics = MetricsCollector()
