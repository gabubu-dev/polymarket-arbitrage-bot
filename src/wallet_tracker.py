"""
Wallet activity tracking and performance analysis.

This module tracks wallet trading activities, calculates performance metrics,
and identifies successful trading strategies. Integrates with the bot's
whale tracking system for comprehensive wallet monitoring.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class WalletTracker:
    """Track and analyze wallet trading activities."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize wallet tracker.
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger("WalletTracker")
        
        # Load tracked addresses from config
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.tracked_addresses = config.get('wallets', {}).get('tracked_addresses', [])
        except (FileNotFoundError, json.JSONDecodeError):
            self.tracked_addresses = []
        
        # Performance cache
        self._performance_cache: Dict[str, Dict] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def track_wallet(self, address: str, days: int = 30) -> Dict[str, Any]:
        """
        Track trading activity for a wallet address.
        
        Args:
            address: Wallet address
            days: Number of days to look back
            
        Returns:
            Wallet activity analysis
        """
        trades = self._fetch_wallet_trades(address, days)
        
        if not trades:
            return {
                'address': address,
                'error': 'No trades found or API access needed',
                'note': 'This feature requires on-chain data access or Polymarket API key'
            }
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_volume = sum(t.get('size', 0) * t.get('price', 0) for t in trades)
        total_profit = sum(t.get('profit', 0) for t in trades)
        
        # Analyze by market
        markets_traded = defaultdict(int)
        for trade in trades:
            market_id = trade.get('market_id', 'unknown')
            markets_traded[market_id] += 1
        
        return {
            'address': address,
            'period_days': days,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'total_volume': total_volume,
            'total_profit': total_profit,
            'roi': total_profit / total_volume if total_volume > 0 else 0,
            'markets_traded': len(markets_traded),
            'most_active_markets': sorted(
                markets_traded.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'analysis_time': datetime.now().isoformat()
        }
    
    def calculate_performance(self, address: str, days: int = 30) -> Dict[str, Any]:
        """
        Calculate detailed performance metrics for a wallet.
        
        Args:
            address: Wallet address
            days: Number of days to analyze
            
        Returns:
            Performance metrics
        """
        # Check cache
        cache_key = f"{address}_{days}"
        cached = self._performance_cache.get(cache_key)
        if cached and datetime.now() - cached['timestamp'] < self._cache_ttl:
            return cached['data']
        
        trades = self._fetch_wallet_trades(address, days)
        
        if not trades:
            return {'error': 'No trades found', 'address': address}
        
        # Group trades by day
        daily_profits = defaultdict(float)
        daily_volumes = defaultdict(float)
        
        for trade in trades:
            timestamp = trade.get('timestamp', 0)
            day = datetime.fromtimestamp(timestamp).date()
            
            daily_profits[day] += trade.get('profit', 0)
            daily_volumes[day] += trade.get('size', 0) * trade.get('price', 0)
        
        # Calculate metrics
        days_active = len(daily_profits)
        avg_daily_profit = sum(daily_profits.values()) / days_active if days_active > 0 else 0
        avg_daily_volume = sum(daily_volumes.values()) / days_active if days_active > 0 else 0
        
        profits_list = list(daily_profits.values())
        best_day = max(daily_profits.items(), key=lambda x: x[1]) if daily_profits else (None, 0)
        worst_day = min(daily_profits.items(), key=lambda x: x[1]) if daily_profits else (None, 0)
        
        # Calculate Sharpe-like ratio
        if len(profits_list) > 1:
            import statistics
            avg_profit = sum(profits_list) / len(profits_list)
            std_dev = statistics.stdev(profits_list)
            sharpe = avg_profit / std_dev if std_dev > 0 else 0
        else:
            sharpe = 0
        
        result = {
            'address': address,
            'period_days': days,
            'days_active': days_active,
            'avg_daily_profit': avg_daily_profit,
            'avg_daily_volume': avg_daily_volume,
            'best_day': {
                'date': str(best_day[0]) if best_day[0] else None,
                'profit': best_day[1]
            },
            'worst_day': {
                'date': str(worst_day[0]) if worst_day[0] else None,
                'profit': worst_day[1]
            },
            'sharpe_ratio': sharpe,
            'consistency_score': self._calculate_consistency(profits_list),
            'total_trades': len(trades)
        }
        
        # Cache result
        self._performance_cache[cache_key] = {
            'data': result,
            'timestamp': datetime.now()
        }
        
        return result
    
    def get_positions(self, address: str) -> List[Dict[str, Any]]:
        """
        Get current open positions for a wallet.
        
        Args:
            address: Wallet address
            
        Returns:
            List of open positions
        """
        # Placeholder - requires on-chain data
        return [{
            'note': 'Position data requires on-chain data access',
            'address': address
        }]
    
    def compare_wallets(self, addresses: List[str], days: int = 30) -> List[Dict[str, Any]]:
        """
        Compare performance of multiple wallets.
        
        Args:
            addresses: List of wallet addresses
            days: Number of days to analyze
            
        Returns:
            Comparative analysis
        """
        results = []
        
        for address in addresses:
            perf = self.calculate_performance(address, days)
            if 'error' not in perf:
                results.append({
                    'address': address,
                    'avg_daily_profit': perf.get('avg_daily_profit', 0),
                    'win_rate': perf.get('win_rate', 0),
                    'sharpe_ratio': perf.get('sharpe_ratio', 0),
                    'days_active': perf.get('days_active', 0),
                    'consistency_score': perf.get('consistency_score', 0)
                })
        
        # Sort by average daily profit
        results.sort(key=lambda x: x['avg_daily_profit'], reverse=True)
        
        return results
    
    def detect_strategies(self, address: str, days: int = 30) -> Dict[str, Any]:
        """
        Attempt to identify trading strategies used by a wallet.
        
        Args:
            address: Wallet address
            days: Number of days to analyze
            
        Returns:
            Identified strategies
        """
        trades = self._fetch_wallet_trades(address, days)
        
        if not trades:
            return {'strategies': [], 'note': 'Insufficient data', 'address': address}
        
        strategies = []
        
        # Analyze trade patterns
        avg_hold_time = self._calculate_avg_hold_time(trades)
        if avg_hold_time < 3600:  # Less than 1 hour
            strategies.append({
                'type': 'scalping',
                'description': 'Quick in-and-out trades',
                'confidence': 'medium'
            })
        elif avg_hold_time > 86400 * 7:  # More than 7 days
            strategies.append({
                'type': 'position_trading',
                'description': 'Long-term positions',
                'confidence': 'medium'
            })
        
        # Check for arbitrage patterns
        if self._has_paired_trades(trades):
            strategies.append({
                'type': 'arbitrage',
                'description': 'Simultaneous opposite positions',
                'confidence': 'high'
            })
        
        # Check for trend following
        if self._follows_trends(trades):
            strategies.append({
                'type': 'trend_following',
                'description': 'Buys into momentum',
                'confidence': 'medium'
            })
        
        return {
            'address': address,
            'strategies': strategies,
            'avg_hold_time_hours': avg_hold_time / 3600 if avg_hold_time else 0,
            'total_trades': len(trades)
        }
    
    def get_top_performers(self, addresses: Optional[List[str]] = None, 
                          days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top performing wallets.
        
        Args:
            addresses: List of addresses to analyze (uses tracked if None)
            days: Analysis period
            limit: Maximum results
            
        Returns:
            Top performing wallets
        """
        if addresses is None:
            addresses = self.tracked_addresses
        
        results = []
        for address in addresses:
            perf = self.calculate_performance(address, days)
            if 'error' not in perf:
                results.append({
                    'address': address,
                    'avg_daily_profit': perf.get('avg_daily_profit', 0),
                    'sharpe_ratio': perf.get('sharpe_ratio', 0),
                    'consistency_score': perf.get('consistency_score', 0),
                    'days_active': perf.get('days_active', 0)
                })
        
        # Sort by combined score
        results.sort(key=lambda x: (
            x['avg_daily_profit'] * 0.5 + 
            x['sharpe_ratio'] * 0.3 + 
            x['consistency_score'] * 0.2
        ), reverse=True)
        
        return results[:limit]
    
    def _fetch_wallet_trades(self, address: str, days: int) -> List[Dict[str, Any]]:
        """
        Fetch trades for a wallet address.
        
        Note: This is a mock implementation. Real implementation would need:
        - Access to Polymarket's trading API
        - On-chain data from Polygon
        - Proper authentication
        
        Args:
            address: Wallet address
            days: Number of days
            
        Returns:
            List of trades
        """
        # Return mock data for demonstration
        import random
        
        trades = []
        now = int(time.time())
        
        # Seed random for consistent results per address
        random.seed(int(address[-8:], 16) if address.startswith('0x') else hash(address))
        
        for i in range(random.randint(10, 50)):
            timestamp = now - random.randint(0, days * 86400)
            
            trades.append({
                'timestamp': timestamp,
                'market_id': f'market_{random.randint(1, 10)}',
                'side': random.choice(['buy', 'sell']),
                'size': random.uniform(10, 1000),
                'price': random.uniform(0.3, 0.7),
                'profit': random.uniform(-50, 100)
            })
        
        random.seed()  # Reset seed
        return sorted(trades, key=lambda x: x['timestamp'])
    
    def _calculate_consistency(self, profits: List[float]) -> float:
        """
        Calculate consistency score (0-1).
        
        Args:
            profits: List of profit values
            
        Returns:
            Consistency score
        """
        if not profits:
            return 0.0
        
        positive_periods = sum(1 for p in profits if p > 0)
        consistency = positive_periods / len(profits)
        
        return consistency
    
    def _calculate_avg_hold_time(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average hold time between entry and exit."""
        if len(trades) < 2:
            return 0
        
        time_diffs = []
        for i in range(1, len(trades)):
            diff = trades[i]['timestamp'] - trades[i-1]['timestamp']
            time_diffs.append(diff)
        
        return sum(time_diffs) / len(time_diffs) if time_diffs else 0
    
    def _has_paired_trades(self, trades: List[Dict[str, Any]]) -> bool:
        """Check if wallet frequently makes paired trades."""
        paired_count = 0
        
        for i in range(len(trades) - 1):
            t1 = trades[i]
            t2 = trades[i + 1]
            
            time_diff = t2['timestamp'] - t1['timestamp']
            
            # If trades are within 5 minutes and opposite sides
            if time_diff < 300 and t1['side'] != t2['side']:
                paired_count += 1
        
        return paired_count > len(trades) * 0.2
    
    def _follows_trends(self, trades: List[Dict[str, Any]]) -> bool:
        """Check if wallet follows price trends."""
        buy_trades = [t for t in trades if t['side'] == 'buy']
        
        if not buy_trades:
            return False
        
        buy_prices = [t['price'] for t in buy_trades]
        
        if len(buy_prices) < 3:
            return False
        
        increasing = sum(1 for i in range(1, len(buy_prices)) if buy_prices[i] > buy_prices[i-1])
        
        return increasing / (len(buy_prices) - 1) > 0.6
