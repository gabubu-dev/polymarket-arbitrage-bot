#!/usr/bin/env python3
"""
Polymarket Copy Trading Bot - Main Entry Point

Monitors target wallets for Polymarket trades and executes paper trades
to simulate copy trading performance.
"""

import os
import sys
import json
import asyncio
import logging
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configure logging first
from logging.handlers import RotatingFileHandler

# Import bot modules
from polymarket_client import PolymarketClient
from wallet_monitor import WalletMonitor, TradeEvent, WalletConfig
from paper_trader import PaperTrader
from risk_manager import RiskManager

# Optional Telegram notifications
try:
    from telegram import Bot
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not installed. Telegram notifications disabled.")


logger = logging.getLogger(__name__)


class PolymarketCopyBot:
    """Main copy trading bot orchestrator"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        # Components
        self.client: Optional[PolymarketClient] = None
        self.wallet_monitor: Optional[WalletMonitor] = None
        self.paper_trader: Optional[PaperTrader] = None
        self.risk_manager: Optional[RiskManager] = None
        self.telegram_bot: Optional[Any] = None
        
        # State
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._tasks: list = []
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.trades_copied = 0
        self.errors = 0
    
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return True
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            logger.error("Copy config.example.json to config.json and edit with your settings")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return False
    
    def setup_logging(self):
        """Configure logging"""
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO").upper())
        log_file = log_config.get("file", "bot.log")
        max_size_mb = log_config.get("max_size_mb", 100)
        backup_count = log_config.get("backup_count", 5)
        
        # Root logger setup
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                RotatingFileHandler(
                    log_file,
                    maxBytes=max_size_mb * 1024 * 1024,
                    backupCount=backup_count
                ),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger.info("Logging configured")
    
    async def init_telegram(self):
        """Initialize Telegram bot for notifications"""
        telegram_config = self.config.get("telegram", {})
        
        if not telegram_config.get("enabled", False):
            logger.info("Telegram notifications disabled")
            return
        
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram library not available, notifications disabled")
            return
        
        token = telegram_config.get("bot_token", "")
        if token == "YOUR_BOT_TOKEN_HERE" or not token:
            logger.warning("Telegram bot token not configured")
            return
        
        try:
            self.telegram_bot = Bot(token=token)
            logger.info("Telegram bot initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
    
    async def send_telegram_notification(self, message: str, parse_mode: Optional[str] = None):
        """Send notification via Telegram"""
        if not self.telegram_bot:
            return
        
        if parse_mode is None and TELEGRAM_AVAILABLE:
            parse_mode = ParseMode.MARKDOWN
        
        telegram_config = self.config.get("telegram", {})
        chat_id = telegram_config.get("chat_id", "")
        
        if not chat_id or chat_id == "YOUR_CHAT_ID_HERE":
            return
        
        try:
            await self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
    
    async def on_trade_detected(self, trade: TradeEvent):
        """Callback when a trade is detected from a monitored wallet"""
        logger.info(
            f"Trade detected from {trade.wallet_address[:10]}...: "
            f"{trade.side} {trade.shares:.4f} {trade.outcome} "
            f"@ ${trade.price:.4f} (Market: {trade.market_id[:20]}...)"
        )
        
        # Get wallet config
        wallet_config = self.wallet_monitor.wallets.get(trade.wallet_address.lower())
        if not wallet_config:
            logger.warning(f"No config found for wallet {trade.wallet_address}")
            return
        
        # Check if trade meets minimum size
        if trade.amount < wallet_config.min_trade_size_usdc:
            logger.info(f"Trade below minimum size: ${trade.amount:.2f} < ${wallet_config.min_trade_size_usdc:.2f}")
            return
        
        # Calculate position size based on copy percentage
        original_shares = trade.shares
        copy_percentage = wallet_config.copy_percentage / 100
        copied_shares = original_shares * copy_percentage
        
        # Get current balance
        portfolio = self.paper_trader.get_portfolio_value()
        current_balance = portfolio["balance"]
        
        # Risk check
        open_positions = len(self.paper_trader.get_positions())
        allowed, reason = self.risk_manager.check_trade_allowed(
            wallet_address=trade.wallet_address,
            market_id=trade.market_id,
            current_balance=current_balance,
            trade_amount=copied_shares * trade.price,
            open_positions_count=open_positions
        )
        
        if not allowed:
            logger.warning(f"Trade blocked by risk manager: {reason}")
            await self.send_telegram_notification(
                f"⚠️ *Trade Blocked*\n"
                f"From: `{wallet_config.name}`\n"
                f"Reason: {reason}"
            )
            return
        
        # Calculate final position size with risk limits
        calculated_shares = self.risk_manager.calculate_position_size(
            original_trade_amount=trade.amount,
            current_balance=current_balance,
            copy_percentage=wallet_config.copy_percentage
        )
        final_shares = calculated_shares / trade.price
        
        # Cap at max trade size
        max_amount = wallet_config.max_trade_size_usdc
        if final_shares * trade.price > max_amount:
            final_shares = max_amount / trade.price
            logger.info(f"Capped at max trade size: ${max_amount:.2f}")
        
        # Execute paper trade
        success, message, trade_record = self.paper_trader.execute_trade(
            original_wallet=trade.wallet_address,
            market_id=trade.market_id,
            outcome=trade.outcome,
            side=trade.side,
            shares=final_shares,
            price=trade.price
        )
        
        if success:
            self.trades_copied += 1
            
            # Send notification
            if self.config.get("telegram", {}).get("notifications", {}).get("on_trade_copy", True):
                emoji = "🟢" if trade.side == "BUY" else "🔴"
                await self.send_telegram_notification(
                    f"{emoji} *Trade Copied*\n"
                    f"From: `{wallet_config.name}`\n"
                    f"Action: {trade.side} {final_shares:.4f} {trade.outcome}\n"
                    f"Price: ${trade.price:.4f}\n"
                    f"Amount: ${final_shares * trade.price:.2f} USDC"
                )
        else:
            logger.error(f"Failed to execute paper trade: {message}")
    
    async def daily_summary_task(self):
        """Send daily performance summary"""
        telegram_config = self.config.get("telegram", {})
        if not telegram_config.get("notifications", {}).get("on_daily_summary", True):
            return
        
        summary_time = telegram_config.get("daily_summary_time", "20:00")
        hour, minute = map(int, summary_time.split(":"))
        
        while self.running:
            try:
                now = datetime.utcnow()
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if target < now:
                    target += timedelta(days=1)
                
                wait_seconds = (target - now).total_seconds()
                logger.debug(f"Next daily summary in {wait_seconds/3600:.1f} hours")
                
                # Wait until summary time or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=wait_seconds
                    )
                    return  # Shutdown signaled
                except asyncio.TimeoutError:
                    pass
                
                # Send summary
                await self.send_daily_summary()
                
            except Exception as e:
                logger.error(f"Error in daily summary task: {e}")
                await asyncio.sleep(60)
    
    async def send_daily_summary(self):
        """Send daily performance summary via Telegram"""
        stats = self.paper_trader.get_performance_stats()
        risk_status = self.risk_manager.get_risk_status()
        
        uptime = datetime.utcnow() - self.start_time if self.start_time else timedelta(0)
        
        message = (
            f"📊 *Daily Summary*\n\n"
            f"*Portfolio:*\n"
            f"Balance: `${stats['current_balance']:.2f}`\n"
            f"Equity: `${stats['total_equity']:.2f}`\n"
            f"Total PnL: `${stats['total_pnl']:.2f}` ({stats['total_pnl_percent']:.2f}%)\n"
            f"Daily PnL: `${stats['daily_pnl']:.2f}`\n\n"
            f"*Activity:*\n"
            f"Open Positions: {stats['open_positions']}\n"
            f"Total Trades: {stats['total_trades']}\n"
            f"Win Rate: {stats['win_rate_percent']:.1f}%\n\n"
            f"*Status:*\n"
            f"Uptime: {uptime.days}d {uptime.seconds//3600}h\n"
            f"Trades Copied: {self.trades_copied}\n"
            f"Trading: {'🟢 Active' if not risk_status['trading_halted'] else '🔴 Halted'}"
        )
        
        await self.send_telegram_notification(message)
    
    async def hourly_report_task(self):
        """Background task for hourly balance reports (old bot format)"""
        telegram_config = self.config.get("telegram", {})
        if not telegram_config.get("hourly_report_enabled", True):
            return
        
        # Wait a bit on first start before sending first report
        await asyncio.sleep(60)
        
        while self.running:
            try:
                await self.send_hourly_report()
                
                # Wait 1 hour
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=3600
                    )
                    return
                except asyncio.TimeoutError:
                    pass
                    
            except Exception as e:
                logger.error(f"Error in hourly report task: {e}")
                await asyncio.sleep(60)
    
    async def send_hourly_report(self):
        """Send hourly balance report (matching old bot format)"""
        stats = self.paper_trader.get_portfolio_stats()
        
        emoji = "🟢" if stats.get('total_pnl', 0) >= 0 else "🔴"
        now = datetime.utcnow()
        
        message = (
            f"⏰ Hourly Balance Report {now.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"💰 Balance: ${stats.get('total_value', 0):,.2f}\n"
            f"📊 Total P&L: ${stats.get('total_pnl', 0):+,.2f} ({stats.get('roi_percent', 0):+.2f}%)\n"
            f"🎯 Win Rate: {stats.get('win_rate_percent', 0):.1f}%\n"
            f"📈 Total Trades: {stats.get('total_trades', 0)}\n\n"
            f"<i>Next update in 1 hour</i>"
        )
        
        await self.send_telegram_notification(message, parse_mode="HTML")
    
    async def risk_check_task(self):
        """Periodic risk check and position monitoring"""
        check_interval = 60  # Check every minute
        
        while self.running:
            try:
                # Update position prices and check stop losses
                positions = self.paper_trader.get_positions()
                
                for position in positions:
                    # In a real implementation, fetch current price from Polymarket
                    # For now, we'll skip price updates in the main loop
                    should_exit, reason = self.risk_manager.check_position_exit(
                        position, position.current_price or position.entry_price
                    )
                    
                    if should_exit:
                        logger.info(f"Risk exit triggered for {position.market_id}: {reason}")
                        # Execute closing trade
                        # This would require fetching current market price
                
                # Check for risk events to notify
                risk_status = self.risk_manager.get_risk_status()
                if risk_status['trading_halted'] and risk_status.get('trading_halt_reason'):
                    if self.config.get("telegram", {}).get("notifications", {}).get("on_risk_limit_hit", True):
                        await self.send_telegram_notification(
                            f"🛑 *Trading Halted*\n"
                            f"Reason: {risk_status['trading_halt_reason']}"
                        )
                
                # Wait for next check or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=check_interval
                    )
                    return
                except asyncio.TimeoutError:
                    pass
                    
            except Exception as e:
                logger.error(f"Error in risk check task: {e}")
                await asyncio.sleep(check_interval)
    
    async def run(self):
        """Main bot loop"""
        # Load configuration
        if not self.load_config():
            return 1
        
        # Setup logging
        self.setup_logging()
        
        logger.info("=" * 50)
        logger.info("Polymarket Copy Trading Bot Starting")
        logger.info("=" * 50)
        
        # Initialize Telegram
        await self.init_telegram()
        await self.send_telegram_notification("🤖 *Bot Started*\nPolymarket Copy Trading Bot is now running!")
        
        try:
            # Initialize components
            logger.info("Initializing Polymarket client...")
            self.client = PolymarketClient(self.config)
            
            logger.info("Initializing paper trader...")
            db_path = self.config.get("paper_trading", {}).get("db_path", "paper_trading.db")
            self.paper_trader = PaperTrader(self.config, db_path)
            
            logger.info("Initializing risk manager...")
            self.risk_manager = RiskManager(self.config)
            
            logger.info("Initializing wallet monitor...")
            self.wallet_monitor = WalletMonitor(
                w3=self.client.w3,
                config=self.config,
                callback=self.on_trade_detected,
                rate_limiter=self.client.rate_limiter
            )
            
            # Start monitoring
            await self.wallet_monitor.start()
            
            # Set state
            self.running = True
            self.start_time = datetime.utcnow()
            
            logger.info("Bot is running. Press Ctrl+C to stop.")
            
            # Start background tasks
            self._tasks = [
                asyncio.create_task(self.daily_summary_task()),
                asyncio.create_task(self.hourly_report_task()),
                asyncio.create_task(self.risk_check_task())
            ]
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.exception("Fatal error in main loop")
            await self.send_telegram_notification(f"❌ *Bot Error*\n```\n{str(e)[:200]}\n```")
            return 1
        finally:
            await self.shutdown()
        
        return 0
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down bot...")
        self.running = False
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Stop components
        if self.wallet_monitor:
            await self.wallet_monitor.stop()
        
        if self.client:
            await self.client.close()
        
        await self.send_telegram_notification(
            f"⏹️ *Bot Stopped*\n"
            f"Uptime: {datetime.utcnow() - self.start_time if self.start_time else 'N/A'}\n"
            f"Trades Copied: {self.trades_copied}"
        )
        
        logger.info("Bot shutdown complete")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self._shutdown_event.set()


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Polymarket Copy Trading Bot")
    parser.add_argument(
        "--config", 
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset paper trading account (WARNING: deletes all data!)"
    )
    args = parser.parse_args()
    
    # Create bot instance
    bot = PolymarketCopyBot(config_path=args.config)
    
    # Handle reset
    if args.reset:
        if input("Are you sure you want to reset all paper trading data? (yes/no): ").lower() == "yes":
            if bot.load_config():
                db_path = bot.config.get("paper_trading", {}).get("db_path", "paper_trading.db")
                trader = PaperTrader(bot.config, db_path)
                trader.reset(confirm=True)
                print("Paper trading data reset.")
        return 0
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, bot.signal_handler)
    signal.signal(signal.SIGTERM, bot.signal_handler)
    
    # Run bot
    try:
        exit_code = asyncio.run(bot.run())
        return exit_code
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 0


if __name__ == "__main__":
    sys.exit(main())
