"""
Real-time monitoring dashboard for the Polymarket arbitrage bot.

Displays live trading statistics, opportunity detection rates,
and performance metrics.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Dashboard")


class BotDashboard:
    """Simple console-based dashboard for bot monitoring."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.running = False
        self.stats = {
            'trades_today': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'open_positions': 0,
            'opportunities_detected': 0,
            'opportunities_executed': 0,
            'execution_rate': 0.0,
            'avg_execution_time_ms': 0.0,
            'active_strategies': []
        }
    
    async def start(self):
        """Start the dashboard."""
        self.running = True
        logger.info("Starting Bot Dashboard")
        
        while self.running:
            self._clear_screen()
            self._load_stats()
            self._render()
            
            await asyncio.sleep(2)
    
    def stop(self):
        """Stop the dashboard."""
        self.running = False
    
    def _clear_screen(self):
        """Clear the console."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _load_stats(self):
        """Load statistics from log files."""
        # Load from trade log
        trade_log = self.log_dir / "trades.log"
        if trade_log.exists():
            self._parse_trade_log(trade_log)
        
        # Load from performance log
        perf_log = self.log_dir / "performance.log"
        if perf_log.exists():
            self._parse_performance_log(perf_log)
    
    def _parse_trade_log(self, log_file: Path):
        """Parse trade log for statistics."""
        today = datetime.now().date()
        trades_today = 0
        wins = 0
        total_pnl = 0.0
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    # Parse log line
                    if 'EXIT' in line:
                        trades_today += 1
                        # Extract PnL
                        if 'PnL:' in line:
                            try:
                                pnl_str = line.split('PnL: $')[1].split()[0]
                                pnl = float(pnl_str)
                                total_pnl += pnl
                                if pnl > 0:
                                    wins += 1
                            except:
                                pass
        except Exception as e:
            logger.error(f"Error parsing trade log: {e}")
        
        self.stats['trades_today'] = trades_today
        self.stats['win_rate'] = (wins / trades_today * 100) if trades_today > 0 else 0
        self.stats['total_pnl'] = total_pnl
    
    def _parse_performance_log(self, log_file: Path):
        """Parse performance log for statistics."""
        # This would parse detailed performance metrics
        pass
    
    def _render(self):
        """Render the dashboard."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("=" * 70)
        print(f"  POLYMARKET ARBITRAGE BOT - DASHBOARD ({now})")
        print("=" * 70)
        print()
        
        # Performance section
        print("  📊 PERFORMANCE TODAY")
        print("  " + "-" * 66)
        print(f"  Trades:        {self.stats['trades_today']:>8}")
        print(f"  Win Rate:      {self.stats['win_rate']:>7.1f}%")
        print(f"  Total P&L:     ${self.stats['total_pnl']:>8.2f}")
        print(f"  Open Positions: {self.stats['open_positions']:>7}")
        print()
        
        # Execution section
        print("  ⚡ EXECUTION METRICS")
        print("  " + "-" * 66)
        print(f"  Opportunities Detected:  {self.stats['opportunities_detected']:>8}")
        print(f"  Opportunities Executed:  {self.stats['opportunities_executed']:>8}")
        print(f"  Execution Rate:          {self.stats['execution_rate']:>7.1f}%")
        print(f"  Avg Execution Time:      {self.stats['avg_execution_time_ms']:>7.1f}ms")
        print()
        
        # Active strategies
        print("  🎯 ACTIVE STRATEGIES")
        print("  " + "-" * 66)
        for strategy in self.stats['active_strategies'] or ['combined']:
            print(f"    ✓ {strategy}")
        print()
        
        # Status
        print("  🟢 BOT STATUS: RUNNING")
        print()
        print("  Press Ctrl+C to exit dashboard (bot continues running)")
        print("=" * 70)


def main():
    """Run the dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Polymarket Bot Dashboard")
    parser.add_argument('--log-dir', default='logs', help='Log directory path')
    args = parser.parse_args()
    
    dashboard = BotDashboard(log_dir=args.log_dir)
    
    try:
        asyncio.run(dashboard.start())
    except KeyboardInterrupt:
        dashboard.stop()
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()