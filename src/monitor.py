"""
Real-time monitoring and health checks.

Monitors bot health, performance metrics, and system status.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class HealthStatus:
    """Health status of the bot."""
    timestamp: datetime
    overall_status: str  # 'healthy', 'degraded', 'critical'
    components: Dict[str, str]  # Component name -> status
    metrics: Dict[str, Any]
    issues: list[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class BotMonitor:
    """
    Monitor bot health and performance.
    
    Tracks key metrics, detects issues, and provides health status reports.
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize monitor.
        
        Args:
            check_interval: Seconds between health checks
        """
        self.logger = logging.getLogger("BotMonitor")
        self.check_interval = check_interval
        
        # Component status tracking
        self.component_status: Dict[str, str] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # Metrics
        self.metrics: Dict[str, Any] = {
            'uptime_seconds': 0,
            'opportunities_detected': 0,
            'trades_executed': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'last_trade_time': None,
            'exchange_latency_ms': {},
            'api_errors': 0,
            'last_error': None
        }
        
        # Health thresholds
        self.thresholds = {
            'max_exchange_latency_ms': 1000,
            'max_time_since_price_update': 30,  # seconds
            'max_api_errors_per_hour': 10,
            'min_balance_usd': 50
        }
        
        self.start_time = datetime.now()
        self.running = False
    
    def update_component_status(self, component: str, status: str) -> None:
        """
        Update component health status.
        
        Args:
            component: Component name
            status: Status ('healthy', 'degraded', 'critical', 'offline')
        """
        self.component_status[component] = status
        self.last_update[component] = datetime.now()
        
        if status in ['critical', 'offline']:
            self.logger.warning(f"Component {component} status: {status}")
    
    def update_metric(self, name: str, value: Any) -> None:
        """
        Update a metric value.
        
        Args:
            name: Metric name
            value: Metric value
        """
        self.metrics[name] = value
    
    def increment_metric(self, name: str, amount: int = 1) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            amount: Amount to increment by
        """
        self.metrics[name] = self.metrics.get(name, 0) + amount
    
    def get_health_status(self) -> HealthStatus:
        """
        Get current health status.
        
        Returns:
            HealthStatus object
        """
        issues = []
        
        # Check component statuses
        for component, status in self.component_status.items():
            if status in ['critical', 'offline']:
                issues.append(f"{component} is {status}")
        
        # Check exchange latency
        for exchange, latency in self.metrics.get('exchange_latency_ms', {}).items():
            if latency > self.thresholds['max_exchange_latency_ms']:
                issues.append(f"{exchange} latency high: {latency}ms")
        
        # Check API errors
        if self.metrics.get('api_errors', 0) > self.thresholds['max_api_errors_per_hour']:
            issues.append(f"High API error rate: {self.metrics['api_errors']}/hour")
        
        # Update uptime
        self.metrics['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
        
        # Determine overall status
        critical_count = sum(1 for s in self.component_status.values() if s == 'critical')
        degraded_count = sum(1 for s in self.component_status.values() if s == 'degraded')
        
        if critical_count > 0 or len(issues) > 0:
            overall_status = 'critical'
        elif degraded_count > 0:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return HealthStatus(
            timestamp=datetime.now(),
            overall_status=overall_status,
            components=self.component_status.copy(),
            metrics=self.metrics.copy(),
            issues=issues
        )
    
    def save_metrics(self, output_path: str = "logs/metrics.json") -> None:
        """
        Save current metrics to file.
        
        Args:
            output_path: Path to save metrics
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        health = self.get_health_status()
        
        with open(output_path, 'w') as f:
            json.dump(health.to_dict(), f, indent=2)
    
    async def start(self) -> None:
        """Start monitoring loop."""
        self.running = True
        self.logger.info("Bot monitor started")
        
        while self.running:
            try:
                # Get health status
                health = self.get_health_status()
                
                # Log critical issues
                if health.overall_status == 'critical':
                    self.logger.error(
                        f"Health check CRITICAL: {', '.join(health.issues)}"
                    )
                elif health.overall_status == 'degraded':
                    self.logger.warning(
                        f"Health check DEGRADED: {', '.join(health.issues)}"
                    )
                
                # Save metrics
                self.save_metrics()
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self) -> None:
        """Stop monitoring."""
        self.running = False
        self.logger.info("Bot monitor stopped")


class PerformanceAnalyzer:
    """
    Analyze trading performance over time.
    
    Provides insights into win rates, profit factors, drawdowns, etc.
    """
    
    def __init__(self, trades_log_path: str = "logs/trades.log"):
        """
        Initialize performance analyzer.
        
        Args:
            trades_log_path: Path to trades log file
        """
        self.logger = logging.getLogger("PerformanceAnalyzer")
        self.trades_log_path = Path(trades_log_path)
    
    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze trading performance from logs.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.trades_log_path.exists():
            return {
                'error': 'Trades log file not found',
                'total_trades': 0
            }
        
        # Parse trades from log
        trades = self._parse_trades_log()
        
        if not trades:
            return {
                'total_trades': 0,
                'message': 'No trades found'
            }
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('pnl', 0) <= 0)
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate profit factor
        total_wins = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        total_losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Average hold time
        hold_times = [t.get('hold_time_seconds', 0) for t in trades if 'hold_time_seconds' in t]
        avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl_per_trade': avg_pnl,
            'profit_factor': profit_factor,
            'avg_hold_time_seconds': avg_hold_time,
            'best_trade': max(t.get('pnl', 0) for t in trades),
            'worst_trade': min(t.get('pnl', 0) for t in trades)
        }
    
    def _parse_trades_log(self) -> list[Dict[str, Any]]:
        """Parse trades from log file."""
        trades = []
        
        try:
            with open(self.trades_log_path, 'r') as f:
                for line in f:
                    if 'EXIT' in line:
                        # Parse exit line to extract trade info
                        # Format: EXIT | {symbol} | PnL: ${pnl} | Hold: {hold_time}s | Reason: {reason}
                        parts = line.split('|')
                        if len(parts) >= 4:
                            trade = {}
                            
                            # Extract symbol
                            if len(parts) > 1:
                                trade['symbol'] = parts[1].strip()
                            
                            # Extract PnL
                            pnl_part = [p for p in parts if 'PnL:' in p]
                            if pnl_part:
                                try:
                                    pnl_str = pnl_part[0].split('$')[1].strip()
                                    trade['pnl'] = float(pnl_str)
                                except (IndexError, ValueError):
                                    pass
                            
                            # Extract hold time
                            hold_part = [p for p in parts if 'Hold:' in p]
                            if hold_part:
                                try:
                                    hold_str = hold_part[0].split(':')[1].strip().replace('s', '')
                                    trade['hold_time_seconds'] = float(hold_str)
                                except (IndexError, ValueError):
                                    pass
                            
                            if 'pnl' in trade:
                                trades.append(trade)
        
        except Exception as e:
            self.logger.error(f"Error parsing trades log: {e}")
        
        return trades
    
    def generate_report(self, output_path: str = "logs/performance_report.txt") -> None:
        """
        Generate performance report and save to file.
        
        Args:
            output_path: Path to save report
        """
        metrics = self.analyze_performance()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("POLYMARKET ARBITRAGE BOT - PERFORMANCE REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("TRADING METRICS\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total Trades:        {metrics.get('total_trades', 0)}\n")
            f.write(f"Winning Trades:      {metrics.get('winning_trades', 0)}\n")
            f.write(f"Losing Trades:       {metrics.get('losing_trades', 0)}\n")
            f.write(f"Win Rate:            {metrics.get('win_rate', 0):.1f}%\n\n")
            
            f.write("PROFITABILITY\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total P&L:           ${metrics.get('total_pnl', 0):.2f}\n")
            f.write(f"Avg P&L per Trade:   ${metrics.get('avg_pnl_per_trade', 0):.2f}\n")
            f.write(f"Profit Factor:       {metrics.get('profit_factor', 0):.2f}\n")
            f.write(f"Best Trade:          ${metrics.get('best_trade', 0):.2f}\n")
            f.write(f"Worst Trade:         ${metrics.get('worst_trade', 0):.2f}\n\n")
            
            f.write("EXECUTION\n")
            f.write("-" * 60 + "\n")
            f.write(f"Avg Hold Time:       {metrics.get('avg_hold_time_seconds', 0):.1f}s\n\n")
            
            f.write("=" * 60 + "\n")
        
        self.logger.info(f"Performance report saved to {output_path}")
