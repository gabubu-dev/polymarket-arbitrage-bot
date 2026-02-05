#!/usr/bin/env python3
"""
Polymarket Arbitrage Bot - Paper Trading Edition

PAPER TRADING ONLY - No real money, no real API calls.
Safe for aggressive testing and pattern discovery.
"""

import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from logger import setup_logger, TradeLogger
from arbitrage_detector import ArbitrageDetector
from position_manager import PositionManager
from risk_manager import RiskManager

# Paper trading imports
from paper_trading import PaperPolymarketClient, PaperExchangeMonitor


class PaperTradingBot:
    """
    Paper trading version of arbitrage bot.
    
    Simulates all market interactions without real API calls.
    Perfect for aggressive testing and pattern discovery.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the paper trading bot."""
        # Load configuration
        self.config = Config(config_path)
        
        # Setup logging
        self.logger = setup_logger(
            "PaperTradingBot",
            level=self.config.logging.level,
            log_file=self.config.logging.log_file
        )
        
        self.trade_logger = TradeLogger()
        
        self.logger.info("=" * 70)
        self.logger.info("🎯 PAPER TRADING MODE - NO REAL TRADES")
        self.logger.info("=" * 70)
        
        # Initialize paper trading components
        self.exchange_monitor = PaperExchangeMonitor()
        self.polymarket = PaperPolymarketClient()
        
        self.detector = ArbitrageDetector(
            spike_threshold=self.config.trading.divergence_threshold,
            min_profit_threshold=self.config.trading.min_profit_threshold,
            price_history_seconds=30
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
        
        # Setup callbacks
        self.exchange_monitor.add_price_callback(self._on_price_update)
        
        # Trading state
        self.running = False
        self.opportunities_detected = 0
        self.positions_opened = 0
        self.start_time = None
        
    async def _on_price_update(self, symbol: str, price: float, timestamp) -> None:
        """
        Callback for exchange price updates.
        
        Checks for arbitrage opportunities when prices move.
        """
        # Get relevant Polymarket markets
        asset = symbol.split('/')[0]  # BTC from BTC/USDT
        
        markets = self.polymarket.get_crypto_markets(asset, "15")
        
        for market in markets:
            market_id = market.get('id')
            odds = self.polymarket.get_market_odds(market_id)
            
            if not odds:
                continue
            
            # Check for "up" opportunity
            opportunity = self.detector.detect_opportunity(
                symbol=symbol,
                exchange="binance",
                exchange_price=price,
                polymarket_market_id=market_id,
                polymarket_odds=odds['yes'],
                direction="up"
            )
            
            if opportunity:
                self.opportunities_detected += 1
                await self._handle_opportunity(opportunity)
            
            # Check for "down" opportunity
            opportunity = self.detector.detect_opportunity(
                symbol=symbol,
                exchange="binance",
                exchange_price=price,
                polymarket_market_id=market_id,
                polymarket_odds=odds['no'],
                direction="down"
            )
            
            if opportunity:
                self.opportunities_detected += 1
                await self._handle_opportunity(opportunity)
    
    async def _handle_opportunity(self, opportunity) -> None:
        """Handle detected arbitrage opportunity."""
        # Log opportunity
        self.logger.info(
            f"🔔 OPPORTUNITY: {opportunity.symbol} {opportunity.direction.upper()} | "
            f"Exchange: ${opportunity.exchange_price:,.2f} | "
            f"Polymarket odds: {opportunity.polymarket_odds:.3f} | "
            f"Divergence: {opportunity.divergence:.2%}"
        )
        
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
            self.logger.warning(f"❌ Cannot open position: {reason}")
            return
        
        # Open position
        position = await self.position_manager.open_position(opportunity)
        
        if position:
            self.positions_opened += 1
            self.trade_logger.log_entry(
                symbol=position.symbol,
                side=position.side,
                size=position.size_usd,
                price=position.entry_price,
                market_id=position.market_id
            )
            
            self.logger.info(
                f"✅ POSITION OPENED #{self.positions_opened}: "
                f"{position.symbol} {position.direction.upper()} @ {position.entry_price:.3f}"
            )
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for position management and stats."""
        iteration = 0
        
        while self.running:
            try:
                iteration += 1
                
                # Check positions for exit conditions (pass exchange monitor for current prices)
                await self.position_manager.check_position_exits(
                    self.risk_manager, 
                    exchange_monitor=self.exchange_monitor
                )
                
                # Log status every 10 iterations (~30 seconds)
                if iteration % 10 == 0:
                    stats = self.position_manager.get_performance_stats()
                    runtime = (datetime.now() - self.start_time).total_seconds() / 60
                    
                    self.logger.info(
                        f"\n📊 STATUS (Runtime: {runtime:.1f} min):\n"
                        f"  Opportunities: {self.opportunities_detected}\n"
                        f"  Positions Opened: {self.positions_opened}\n"
                        f"  Currently Open: {stats['open_positions']}\n"
                        f"  Total Trades: {stats['total_trades']}\n"
                        f"  Win Rate: {stats['win_rate']:.1f}%\n"
                        f"  Total P&L: ${stats['total_pnl']:.2f}\n"
                        f"  Wins/Losses: {stats['wins']}/{stats['losses']}"
                    )
                
                # Wait before next check
                await asyncio.sleep(self.config.markets.refresh_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    async def start(self) -> None:
        """Start the paper trading bot."""
        self.start_time = datetime.now()
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("🚀 STARTING PAPER TRADING BOT")
        self.logger.info("=" * 70)
        self.logger.info(f"Symbols: {self.config.markets.enabled_symbols}")
        self.logger.info(f"Position Size: ${self.config.trading.position_size_usd}")
        self.logger.info(f"Max Positions: {self.config.trading.max_positions}")
        self.logger.info(f"Divergence Threshold: {self.config.trading.divergence_threshold:.1%}")
        self.logger.info(f"Min Profit: {self.config.trading.min_profit_threshold:.1%}")
        self.logger.info("=" * 70 + "\n")
        
        self.running = True
        
        # Start exchange monitors
        await self.exchange_monitor.start_all()
        
        # Start monitoring loop
        await self._monitoring_loop()
    
    async def stop(self) -> None:
        """Stop the paper trading bot."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("🛑 STOPPING PAPER TRADING BOT")
        self.logger.info("=" * 70)
        
        self.running = False
        
        # Stop exchange monitors
        await self.exchange_monitor.stop_all()
        
        # Close all open positions at current market odds
        for position in self.position_manager.get_open_positions():
            # Get current Polymarket odds for proper P&L
            try:
                odds = self.polymarket.get_market_odds(position.market_id)
                if position.direction == 'up':
                    current_odds = odds.get('yes', position.entry_price)
                else:
                    current_odds = odds.get('no', position.entry_price)
            except Exception as e:
                self.logger.error(f"Failed to get shutdown odds for {position.market_id}: {e}")
                current_odds = position.entry_price
            
            await self.position_manager.close_position(
                position.position_id,
                current_odds,
                "shutdown"
            )
        
        # Log final stats
        stats = self.position_manager.get_performance_stats()
        runtime = (datetime.now() - self.start_time).total_seconds() / 60
        
        self.logger.info(
            f"\n📈 FINAL STATISTICS:\n"
            f"  Runtime: {runtime:.1f} minutes\n"
            f"  Opportunities Detected: {self.opportunities_detected}\n"
            f"  Positions Opened: {self.positions_opened}\n"
            f"  Total Trades: {stats['total_trades']}\n"
            f"  Win Rate: {stats['win_rate']:.1f}%\n"
            f"  Total P&L: ${stats['total_pnl']:.2f}\n"
            f"  Wins: {stats['wins']} | Losses: {stats['losses']}\n"
            f"  Avg P&L/Trade: ${stats.get('avg_pnl', 0):.2f}"
        )
        self.logger.info("=" * 70 + "\n")


async def main():
    """Main entry point."""
    # Create bot
    bot = PaperTradingBot()
    
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
        print("\n⚠️  Keyboard interrupt received")
    finally:
        await bot.stop()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🎯 POLYMARKET PAPER TRADING BOT")
    print("=" * 70)
    print("This is a simulation. No real money will be used.")
    print("Press Ctrl+C to stop the bot at any time.")
    print("=" * 70 + "\n")
    
    asyncio.run(main())
