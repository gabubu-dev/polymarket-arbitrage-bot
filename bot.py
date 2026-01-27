#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot

Main entry point for the arbitrage bot.
Monitors exchanges and Polymarket for arbitrage opportunities.
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from logger import setup_logger, TradeLogger
from exchange_monitor import MultiExchangeMonitor
from polymarket_client import PolymarketClient
from arbitrage_detector import ArbitrageDetector
from position_manager import PositionManager
from risk_manager import RiskManager


class ArbitrageBot:
    """
    Main arbitrage bot class.
    
    Coordinates all components to detect and execute arbitrage trades
    between Polymarket and cryptocurrency exchanges.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the arbitrage bot.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path)
        
        # Setup logging
        self.logger = setup_logger(
            "ArbitrageBot",
            level=self.config.logging.level,
            log_file=self.config.logging.log_file
        )
        
        self.trade_logger = TradeLogger()
        
        self.logger.info("Initializing Polymarket Arbitrage Bot")
        
        # Initialize components
        self.exchange_monitor = MultiExchangeMonitor()
        self.polymarket = PolymarketClient(
            api_key=self.config.polymarket.api_key,
            private_key=self.config.polymarket.private_key,
            chain_id=self.config.polymarket.chain_id
        )
        
        self.detector = ArbitrageDetector(
            divergence_threshold=self.config.trading.divergence_threshold,
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
        
        # Running state
        self.running = False
    
    def _setup_exchanges(self) -> None:
        """Setup exchange monitors based on configuration."""
        for exchange_name, exchange_config in self.config.exchanges.items():
            self.logger.info(f"Setting up monitor for {exchange_name}")
            
            monitor = self.exchange_monitor.add_exchange(
                exchange_name=exchange_name,
                symbols=self.config.markets.enabled_symbols,
                api_key=exchange_config.api_key,
                api_secret=exchange_config.api_secret,
                testnet=exchange_config.testnet
            )
            
            # Add price update callback
            monitor.add_price_callback(self._on_price_update)
    
    async def _on_price_update(self, symbol: str, price: float, timestamp) -> None:
        """
        Callback for exchange price updates.
        
        Args:
            symbol: Trading symbol
            price: New price
            timestamp: Update timestamp
        """
        # This is where the magic happens
        # When we get a price update, check Polymarket for arbitrage opportunities
        
        # Get relevant Polymarket markets
        # For now, simplified - in real implementation, maintain a mapping
        # of exchange symbols to Polymarket market IDs
        
        # Example: BTC/USDT price update -> check BTC 15-minute markets
        if symbol in ["BTC/USDT", "BTC/USD"]:
            await self._check_btc_opportunities(price)
        elif symbol in ["ETH/USDT", "ETH/USD"]:
            await self._check_eth_opportunities(price)
    
    async def _check_btc_opportunities(self, exchange_price: float) -> None:
        """
        Check for BTC arbitrage opportunities.
        
        Args:
            exchange_price: Current BTC price on exchange
        """
        # Get BTC 15-minute markets from Polymarket
        markets = await self.polymarket.get_crypto_markets("BTC", "15MIN")
        
        for market in markets:
            market_id = market.get('id')
            odds = self.polymarket.get_market_odds(market_id)
            
            if not odds:
                continue
            
            # Check for "up" opportunity
            opportunity = self.detector.detect_opportunity(
                symbol="BTC/USDT",
                exchange="binance",
                exchange_price=exchange_price,
                polymarket_market_id=market_id,
                polymarket_odds=odds['yes'],
                direction="up"
            )
            
            if opportunity:
                await self._handle_opportunity(opportunity)
            
            # Check for "down" opportunity
            opportunity = self.detector.detect_opportunity(
                symbol="BTC/USDT",
                exchange="binance",
                exchange_price=exchange_price,
                polymarket_market_id=market_id,
                polymarket_odds=odds['no'],
                direction="down"
            )
            
            if opportunity:
                await self._handle_opportunity(opportunity)
    
    async def _check_eth_opportunities(self, exchange_price: float) -> None:
        """
        Check for ETH arbitrage opportunities.
        
        Args:
            exchange_price: Current ETH price on exchange
        """
        # Similar to BTC, but for ETH markets
        markets = await self.polymarket.get_crypto_markets("ETH", "15MIN")
        
        for market in markets:
            market_id = market.get('id')
            odds = self.polymarket.get_market_odds(market_id)
            
            if not odds:
                continue
            
            for direction in ["up", "down"]:
                odds_value = odds['yes'] if direction == "up" else odds['no']
                
                opportunity = self.detector.detect_opportunity(
                    symbol="ETH/USDT",
                    exchange="binance",
                    exchange_price=exchange_price,
                    polymarket_market_id=market_id,
                    polymarket_odds=odds_value,
                    direction=direction
                )
                
                if opportunity:
                    await self._handle_opportunity(opportunity)
    
    async def _handle_opportunity(self, opportunity) -> None:
        """
        Handle detected arbitrage opportunity.
        
        Args:
            opportunity: ArbitrageOpportunity object
        """
        # Log opportunity
        self.trade_logger.log_opportunity(
            symbol=opportunity.symbol,
            exchange_price=opportunity.exchange_price,
            polymarket_price=opportunity.polymarket_odds,
            divergence=opportunity.divergence
        )
        
        # Check risk limits
        can_open, reason = self.risk_manager.can_open_position(
            self.config.trading.position_size_usd
        )
        
        if not can_open:
            self.logger.warning(f"Cannot open position: {reason}")
            return
        
        # Open position
        position = await self.position_manager.open_position(opportunity)
        
        if position:
            self.trade_logger.log_entry(
                symbol=position.symbol,
                side=position.side,
                size=position.size_usd,
                price=position.entry_price,
                market_id=position.market_id
            )
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for position management."""
        while self.running:
            try:
                # Check positions for exit conditions
                await self.position_manager.check_position_exits(self.risk_manager)
                
                # Log status periodically
                if len(self.position_manager.get_open_positions()) > 0:
                    stats = self.position_manager.get_performance_stats()
                    self.logger.info(
                        f"Status: {stats['open_positions']} open | "
                        f"P&L: ${stats['total_pnl']:.2f} | "
                        f"Win rate: {stats['win_rate']:.1f}%"
                    )
                
                # Wait before next check
                await asyncio.sleep(self.config.markets.refresh_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def start(self) -> None:
        """Start the arbitrage bot."""
        self.logger.info("Starting Polymarket Arbitrage Bot")
        self.logger.info(f"Monitoring symbols: {self.config.markets.enabled_symbols}")
        self.logger.info(f"Position size: ${self.config.trading.position_size_usd}")
        self.logger.info(f"Divergence threshold: {self.config.trading.divergence_threshold:.1%}")
        
        self.running = True
        
        # Start exchange monitors
        await self.exchange_monitor.start_all()
        
        # Start monitoring loop
        await self._monitoring_loop()
    
    async def stop(self) -> None:
        """Stop the arbitrage bot."""
        self.logger.info("Stopping Polymarket Arbitrage Bot")
        
        self.running = False
        
        # Stop exchange monitors
        await self.exchange_monitor.stop_all()
        
        # Close all open positions
        for position in self.position_manager.get_open_positions():
            await self.position_manager.close_position(
                position.position_id,
                position.entry_price,
                "shutdown"
            )
        
        # Log final stats
        stats = self.position_manager.get_performance_stats()
        self.logger.info(
            f"Final stats: {stats['total_trades']} trades | "
            f"Win rate: {stats['win_rate']:.1f}% | "
            f"Total P&L: ${stats['total_pnl']:.2f}"
        )


async def main():
    """Main entry point."""
    # Check for config file
    if not Path("config.json").exists():
        print("Error: config.json not found")
        print("Please copy config.example.json to config.json and configure your API keys")
        sys.exit(1)
    
    # Create bot
    bot = ArbitrageBot()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(bot.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Start bot
    try:
        await bot.start()
    except KeyboardInterrupt:
        pass
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
