"""
Optimized Polymarket Arbitrage Bot

Main entry point for the arbitrage bot with:
- Performance optimizations (caching, async batch operations)
- Reliability improvements (retry logic, health monitoring)
- Enhanced monitoring (metrics collection, structured logging)
- Health checks and auto-restart

Part of the Ares AI Assistant project.
"""

import asyncio
import signal
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from structured_logging import (
    setup_structured_logger, StructuredLogger, TradeLogger,
    set_request_id, clear_context
)
from optimized_polymarket_client import OptimizedPolymarketClient
from exchange_monitor import MultiExchangeMonitor
from arbitrage_detector import ArbitrageDetector
from position_manager import PositionManager
from risk_manager import RiskManager
from metrics import get_metrics, MetricsCollector
from health import (
    HealthMonitor, HealthCheck, HealthStatus,
    create_price_feed_health_check, create_memory_health_check,
    AutoRestarter
)
from cache import AsyncTTLCache


@dataclass
class BotStats:
    """Bot runtime statistics."""
    opportunities_detected: int = 0
    opportunities_acted: int = 0
    trades_executed: int = 0
    errors_count: int = 0
    start_time: float = 0.0
    
    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.start_time
    
    @property
    def opportunities_per_hour(self) -> float:
        hours = self.uptime_seconds / 3600
        return self.opportunities_detected / hours if hours > 0 else 0


class OptimizedArbitrageBot:
    """
    Optimized arbitrage bot with enhanced reliability and monitoring.
    
    Key improvements:
    - Async batch operations for better performance
    - Response caching with TTL
    - Exponential backoff retry logic
    - Health monitoring with auto-restart
    - Structured JSON logging
    - Comprehensive metrics collection
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the optimized arbitrage bot.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path)
        
        # Setup structured logging
        self.logger = setup_structured_logger(
            "ArbitrageBot",
            level=self.config.logging.level,
            log_file=self.config.logging.log_file,
            json_file="logs/bot.json"
        )
        
        self.trade_logger = TradeLogger(
            log_file="logs/trades.log",
            json_file="logs/trades.json"
        )
        
        self.logger.info(
            "Initializing Optimized Polymarket Arbitrage Bot",
            version="2.0.0",
            trading_mode=self.config.trading.trading_mode
        )
        
        # Initialize metrics collector
        self.metrics = get_metrics()
        self._setup_alert_thresholds()
        
        # Initialize optimized components
        self.polymarket = OptimizedPolymarketClient(
            api_key=self.config.polymarket.api_key,
            private_key=self.config.polymarket.private_key,
            chain_id=self.config.polymarket.chain_id,
            market_cache_ttl=30.0,
            odds_cache_ttl=3.0,
            enable_caching=True
        )
        
        self.exchange_monitor = MultiExchangeMonitor()
        
        self.detector = ArbitrageDetector(
            spike_threshold=self.config.trading.divergence_threshold,
            min_profit_threshold=self.config.trading.min_profit_threshold
        )
        
        self.risk_manager = RiskManager(
            stop_loss_percentage=self.config.risk_management.stop_loss_percentage,
            take_profit_percentage=self.config.risk_management.take_profit_percentage,
            max_daily_loss_usd=self.config.risk_management.max_daily_loss_usd,
            emergency_shutdown_loss_usd=self.config.risk_management.emergency_shutdown_loss_usd
        )
        
        self.position_manager = PositionManager(
            polymarket_client=self.polymarket,
            max_positions=self.config.trading.max_positions,
            position_size_usd=self.config.trading.position_size_usd
        )
        
        # Setup exchange monitors
        self._setup_exchanges()
        
        # Health monitoring
        self.health_monitor = HealthMonitor(
            check_interval=30.0,
            restart_threshold=3
        )
        self._setup_health_checks()
        
        # Auto restarter
        self.auto_restarter = AutoRestarter(
            max_restarts=5,
            base_delay=5.0
        )
        
        # Runtime state
        self.running = False
        self._tasks: list[asyncio.Task] = []
        self._stats = BotStats()
        
        # Performance optimizations
        self._price_cache: Dict[str, tuple[float, float]] = {}  # symbol -> (price, timestamp)
        self._price_cache_ttl = 1.0  # 1 second TTL for prices
        
        # Rate limiting
        self._last_api_call = 0.0
        self._min_api_interval = 0.1  # Minimum 100ms between API calls
    
    def _setup_exchanges(self) -> None:
        """Setup exchange monitors based on configuration."""
        for exchange_name, exchange_config in self.config.exchanges.items():
            self.logger.info(
                f"Setting up monitor for {exchange_name}",
                exchange=exchange_name
            )
            
            monitor = self.exchange_monitor.add_exchange(
                exchange_name=exchange_name,
                symbols=self.config.markets.enabled_symbols,
                api_key=exchange_config.api_key,
                api_secret=exchange_config.api_secret,
                testnet=exchange_config.testnet
            )
            
            monitor.add_price_callback(self._on_price_update)
    
    def _setup_health_checks(self) -> None:
        """Setup health monitoring checks."""
        # Price feed health check
        price_check = HealthCheck(
            name="price_feeds",
            check_fn=create_price_feed_health_check(
                self.exchange_monitor,
                max_staleness_seconds=60.0
            ),
            interval_seconds=30.0,
            critical=True
        )
        self.health_monitor.add_check(price_check)
        
        # Memory health check
        memory_check = HealthCheck(
            name="memory_usage",
            check_fn=create_memory_health_check(max_memory_percent=90.0),
            interval_seconds=60.0,
            critical=False
        )
        self.health_monitor.add_check(memory_check)
        
        # API connectivity check
        async def check_api():
            try:
                # Quick connectivity test
                markets = await self.polymarket.get_crypto_markets("BTC", "15")
                return len(markets) > 0, f"Found {len(markets)} markets"
            except Exception as e:
                return False, str(e)
        
        api_check = HealthCheck(
            name="api_connectivity",
            check_fn=lambda: asyncio.run(check_api()),
            interval_seconds=60.0,
            critical=True
        )
        self.health_monitor.add_check(api_check)
        
        # Setup restart callback
        self.health_monitor.on_restart(self._on_restart_triggered)
    
    def _setup_alert_thresholds(self) -> None:
        """Setup metric alert thresholds."""
        self.metrics.set_alert_threshold('daily_loss', 1000.0, 'greater_than')
        self.metrics.set_alert_threshold('single_trade_loss', 500.0, 'greater_than')
        self.metrics.set_alert_threshold('api_latency_ms', 5000.0, 'greater_than')
        self.metrics.set_alert_threshold('api_error_rate', 0.2, 'greater_than')
        
        # Add alert callback
        self.metrics.add_alert_callback(self._on_metric_alert)
    
    def _on_metric_alert(self, metric_name: str, value: Any) -> None:
        """Handle metric alert."""
        self.logger.warning(
            f"Alert triggered: {metric_name} = {value}",
            metric_name=metric_name,
            value=value,
            alert_type='threshold_breach'
        )
    
    def _on_restart_triggered(self) -> None:
        """Handle restart triggered by health monitor."""
        if not self.auto_restarter.should_restart():
            self.logger.critical(
                "Restart required but max restarts reached. Manual intervention needed."
            )
            return
        
        delay = self.auto_restarter.get_delay()
        self.logger.warning(f"Restart triggered. Waiting {delay}s before restart...")
        
        time.sleep(delay)
        self.auto_restarter.record_restart()
        
        # Trigger restart by stopping and letting main loop restart
        asyncio.create_task(self.stop())
    
    async def _on_price_update(
        self,
        symbol: str,
        price: float,
        timestamp
    ) -> None:
        """
        Handle exchange price updates.
        
        Args:
            symbol: Trading symbol
            price: Current price
            timestamp: Update timestamp
        """
        # Update local price cache
        self._price_cache[symbol] = (price, time.time())
        
        # Check for opportunities based on symbol
        if symbol in ["BTC/USDT", "BTC/USD"]:
            await self._check_btc_opportunities(price)
        elif symbol in ["ETH/USDT", "ETH/USD"]:
            await self._check_eth_opportunities(price)
    
    async def _check_btc_opportunities(self, exchange_price: float) -> None:
        """Check for BTC arbitrage opportunities."""
        await self._check_opportunities_for_asset(
            "BTC", "15", exchange_price, "BTC/USDT"
        )
    
    async def _check_eth_opportunities(self, exchange_price: float) -> None:
        """Check for ETH arbitrage opportunities."""
        await self._check_opportunities_for_asset(
            "ETH", "15", exchange_price, "ETH/USDT"
        )
    
    async def _check_opportunities_for_asset(
        self,
        asset: str,
        timeframe: str,
        exchange_price: float,
        symbol: str
    ) -> None:
        """
        Check for arbitrage opportunities for a specific asset.
        
        Args:
            asset: Asset symbol (BTC, ETH, etc.)
            timeframe: Market timeframe
            exchange_price: Current exchange price
            symbol: Trading symbol
        """
        try:
            # Get markets
            markets = await self.polymarket.get_crypto_markets(asset, timeframe)
            
            if not markets:
                return
            
            # Extract token IDs for batch odds fetching
            token_ids = []
            market_map = {}
            
            for market in markets:
                tokens = market.get('tokens', [])
                for token in tokens:
                    token_id = token.get('token_id') or token.get('id')
                    if token_id:
                        token_ids.append(token_id)
                        market_map[token_id] = {
                            'market': market,
                            'outcome': token.get('outcome', '').lower()
                        }
            
            # Fetch odds in parallel
            odds_results = await self.polymarket.get_batch_odds(token_ids)
            
            # Check each market for opportunities
            for token_id, odds in odds_results.items():
                if not odds:
                    continue
                
                market_info = market_map.get(token_id, {})
                market = market_info.get('market', {})
                outcome = market_info.get('outcome', '')
                
                direction = "up" if outcome == "yes" else "down"
                
                opportunity = self.detector.detect_opportunity(
                    symbol=symbol,
                    exchange="binance",
                    exchange_price=exchange_price,
                    polymarket_market_id=market.get('market_id', ''),
                    polymarket_odds=odds['mid_price'],
                    direction=direction
                )
                
                if opportunity:
                    self._stats.opportunities_detected += 1
                    self.metrics.record_opportunity(
                        symbol=symbol,
                        exchange="binance",
                        divergence=opportunity.divergence,
                        expected_profit=opportunity.expected_profit,
                        confidence=opportunity.confidence,
                        direction=direction
                    )
                    
                    self.trade_logger.log_opportunity(
                        symbol=symbol,
                        exchange="binance",
                        exchange_price=exchange_price,
                        polymarket_odds=odds['mid_price'],
                        divergence=opportunity.divergence,
                        direction=direction,
                        expected_profit=opportunity.expected_profit,
                        confidence=opportunity.confidence
                    )
                    
                    await self._handle_opportunity(opportunity)
                    
        except Exception as e:
            self.logger.error(
                f"Error checking opportunities for {asset}: {e}",
                asset=asset,
                error=str(e),
                exc_info=True
            )
            self._stats.errors_count += 1
    
    async def _handle_opportunity(self, opportunity) -> None:
        """
        Handle detected arbitrage opportunity.
        
        Args:
            opportunity: ArbitrageOpportunity object
        """
        # Check risk limits
        can_open, reason = self.risk_manager.can_open_position(
            self.config.trading.position_size_usd
        )
        
        if not can_open:
            self.logger.warning(
                f"Cannot open position: {reason}",
                reason=reason,
                opportunity_id=getattr(opportunity, 'id', 'unknown')
            )
            return
        
        # Open position
        position = await self.position_manager.open_position(opportunity)
        
        if position:
            self._stats.opportunities_acted += 1
            self._stats.trades_executed += 1
            
            self.metrics.record_trade_entry(
                trade_id=position.position_id,
                symbol=position.symbol,
                market_id=position.market_id,
                direction=position.direction,
                entry_price=position.entry_price,
                size_usd=position.size_usd,
                strategy="spike"
            )
            
            self.trade_logger.log_trade_entry(
                symbol=position.symbol,
                market_id=position.market_id,
                side=position.side,
                direction=position.direction,
                size_usd=position.size_usd,
                entry_price=position.entry_price,
                position_id=position.position_id,
                strategy="spike"
            )
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for position management."""
        while self.running:
            try:
                # Check positions for exit conditions
                await self.position_manager.check_position_exits(self.risk_manager)
                
                # Log status periodically
                if self._stats.trades_executed > 0 and self._stats.trades_executed % 10 == 0:
                    await self._log_status()
                
                # Wait before next check
                await asyncio.sleep(self.config.markets.refresh_interval_seconds)
                
            except Exception as e:
                self.logger.error(
                    f"Error in monitoring loop: {e}",
                    error=str(e),
                    exc_info=True
                )
                self._stats.errors_count += 1
                await asyncio.sleep(5)
    
    async def _metrics_loop(self) -> None:
        """Periodic metrics logging loop."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Log metrics every minute
                
                if not self.running:
                    break
                
                stats = self.metrics.get_all_stats()
                self.logger.log_metrics(stats)
                
            except Exception as e:
                self.logger.error(f"Error in metrics loop: {e}")
    
    async def _log_status(self) -> None:
        """Log current bot status."""
        stats = self.position_manager.get_performance_stats()
        api_stats = self.metrics.get_api_stats()
        
        self.logger.info(
            "Bot status update",
            uptime_seconds=self._stats.uptime_seconds,
            opportunities_detected=self._stats.opportunities_detected,
            opportunities_per_hour=self._stats.opportunities_per_hour,
            trades_executed=self._stats.trades_executed,
            errors=self._stats.errors_count,
            total_pnl=stats.get('total_pnl', 0),
            win_rate=stats.get('win_rate', 0),
            open_positions=stats.get('open_positions', 0),
            api_avg_latency_ms=api_stats.get('avg_latency_ms', 0),
            api_success_rate=api_stats.get('success_rate', 0),
            cache_hit_rate=api_stats.get('cache_hit_rate', 0)
        )
    
    async def start(self) -> None:
        """Start the optimized arbitrage bot."""
        self.logger.info(
            "Starting Optimized Polymarket Arbitrage Bot",
            symbols=self.config.markets.enabled_symbols,
            position_size=self.config.trading.position_size_usd,
            divergence_threshold=self.config.trading.divergence_threshold
        )
        
        self.running = True
        self._stats.start_time = time.time()
        
        # Start health monitoring
        await self.health_monitor.start()
        
        # Start exchange monitors
        await self.exchange_monitor.start_all()
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._monitoring_loop()),
            asyncio.create_task(self._metrics_loop())
        ]
        
        # Wait for tasks
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
    
    async def stop(self) -> None:
        """Stop the arbitrage bot."""
        self.logger.info("Stopping Optimized Polymarket Arbitrage Bot")
        
        self.running = False
        
        # Stop health monitoring
        await self.health_monitor.stop()
        
        # Stop exchange monitors
        await self.exchange_monitor.stop_all()
        
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close positions
        for position in self.position_manager.get_open_positions():
            await self.position_manager.close_position(
                position.position_id,
                position.entry_price,
                "shutdown"
            )
        
        # Log final stats
        await self._log_status()
        self.logger.info("Bot stopped successfully")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        return {
            'runtime': {
                'uptime_seconds': self._stats.uptime_seconds,
                'opportunities_detected': self._stats.opportunities_detected,
                'opportunities_acted': self._stats.opportunities_acted,
                'trades_executed': self._stats.trades_executed,
                'errors': self._stats.errors_count
            },
            'trading': self.position_manager.get_performance_stats(),
            'api': self.metrics.get_api_stats(),
            'health': self.health_monitor.get_report(),
            'cache': self.polymarket.get_cache_stats()
        }


async def main():
    """Main entry point."""
    # Check for config file
    if not Path("config.json").exists():
        print("Error: config.json not found")
        print("Please copy config.example.json to config.json and configure your API keys")
        sys.exit(1)
    
    # Create bot
    bot = OptimizedArbitrageBot()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(bot.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Start bot with auto-restart
    restart_count = 0
    max_restarts = 5
    
    while restart_count < max_restarts:
        try:
            await bot.start()
            break  # Normal exit
        except Exception as e:
            restart_count += 1
            delay = min(5 * (2 ** restart_count), 300)  # Exponential backoff, max 5 min
            
            print(f"Bot crashed: {e}")
            print(f"Restarting in {delay}s... (attempt {restart_count}/{max_restarts})")
            
            await asyncio.sleep(delay)
            bot = OptimizedArbitrageBot()  # Create fresh instance
    
    if restart_count >= max_restarts:
        print("Max restarts reached. Manual intervention required.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
