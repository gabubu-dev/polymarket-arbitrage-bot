"""
Telegram Bot - Notifications
Handles all Telegram notifications for trades, performance, and alerts
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, time
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram bot for notifications and commands"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Telegram settings
        telegram_config = config.get("telegram", {})
        self.enabled = telegram_config.get("enabled", False)
        self.bot_token = telegram_config.get("bot_token", "")
        self.chat_id = telegram_config.get("chat_id", "")
        
        # Notification settings
        notif_config = telegram_config.get("notifications", {})
        self.notify_on_trade = notif_config.get("on_trade_copy", True)
        self.notify_on_daily = notif_config.get("on_daily_summary", True)
        self.notify_on_unfollow = notif_config.get("on_wallet_unfollow", True)
        self.notify_on_risk = notif_config.get("on_risk_limit_hit", True)
        self.notify_on_performance = notif_config.get("on_performance_alert", True)
        
        # Daily summary time
        summary_time = telegram_config.get("daily_summary_time", "20:00")
        hour, minute = map(int, summary_time.split(":"))
        self.daily_summary_time = time(hour=hour, minute=minute)
        
        # Hourly report settings
        self.hourly_report_enabled = telegram_config.get("hourly_report_enabled", True)
        
        # Bot instance
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        
        # References to other components (set externally)
        self.paper_trader = None
        self.risk_manager = None
        self.wallet_monitor = None
        
        if self.enabled and self.bot_token and self.chat_id:
            try:
                self.application = Application.builder().token(self.bot_token).build()
                self.bot = self.application.bot
                self._setup_handlers()
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.enabled = False
        elif self.enabled:
            logger.warning("Telegram enabled but missing bot_token or chat_id")
            self.enabled = False
    
    def _setup_handlers(self):
        """Setup command handlers"""
        if not self.application:
            return
        
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("wallets", self.cmd_wallets))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
    
    async def start(self):
        """Start the bot"""
        if not self.application:
            return
        
        await self.application.initialize()
        await self.application.start()
        
        # Start polling in background
        asyncio.create_task(self.application.updater.start_polling())
        
        # Send startup message
        await self.send_message("🚀 Polymarket Copy Trading Bot started!")
    
    async def stop(self):
        """Stop the bot"""
        if self.application:
            await self.application.stop()
    
    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Send a message to the configured chat"""
        if not self.enabled or not self.bot:
            return
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message[:4096],  # Telegram message limit
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]):
        """Send notification for a copied trade"""
        if not self.notify_on_trade:
            return
        
        emoji = "🟢" if trade_data.get("side") == "BUY" else "🔴"
        
        message = f"""
{emoji} <b>Trade Copied</b>

<b>Wallet:</b> {trade_data.get('wallet_name', 'Unknown')}
<b>Market:</b> {trade_data.get('market_question', 'Unknown')[:50]}...
<b>Outcome:</b> {trade_data.get('outcome_name', 'Unknown')}
<b>Side:</b> {trade_data.get('side', 'Unknown')}
<b>Size:</b> ${trade_data.get('size', 0):,.2f} USDC
<b>Price:</b> {trade_data.get('price', 0):.4f}
<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        await self.send_message(message)
    
    async def send_daily_summary(
        self,
        portfolio_stats: Dict[str, Any],
        daily_stats: List[Dict[str, Any]]
    ):
        """Send daily performance summary"""
        if not self.notify_on_daily:
            return
        
        emoji = "🟢" if portfolio_stats.get('total_pnl', 0) >= 0 else "🔴"
        
        message = f"""
{emoji} <b>Daily Summary - {datetime.utcnow().strftime('%Y-%m-%d')}</b>

<b>Portfolio Value:</b> ${portfolio_stats.get('total_value', 0):,.2f} USDC
<b>Total PnL:</b> ${portfolio_stats.get('total_pnl', 0):+,.2f} ({portfolio_stats.get('roi_percent', 0):+.2f}%)
<b>Win Rate:</b> {portfolio_stats.get('win_rate_percent', 0):.1f}%
<b>Trades Today:</b> {portfolio_stats.get('total_trades', 0)}
<b>Open Positions:</b> {portfolio_stats.get('open_positions', 0)}
<b>Max Drawdown:</b> {portfolio_stats.get('max_drawdown_percent', 0):.2f}%
        """.strip()
        
        await self.send_message(message)
    
    async def send_wallet_unfollowed(self, wallet_address: str, reason: str):
        """Send notification when a wallet is unfollowed"""
        if not self.notify_on_unfollow:
            return
        
        message = f"""
⚠️ <b>Wallet Unfollowed</b>

<b>Address:</b> <code>{wallet_address}</code>
<b>Reason:</b> {reason}

This wallet will no longer be copied.
        """.strip()
        
        await self.send_message(message)
    
    async def send_risk_alert(self, event_type: str, message: str, data: Dict[str, Any]):
        """Send risk management alert"""
        if not self.notify_on_risk:
            return
        
        emoji = "🚨" if "LIMIT" in event_type else "⚠️"
        
        msg = f"""
{emoji} <b>Risk Alert: {event_type}</b>

{message}

<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """.strip()
        
        await self.send_message(msg)
    
    async def send_performance_alert(self, wallet_address: str, performance: Dict[str, Any]):
        """Send performance alert for a wallet"""
        if not self.notify_on_performance:
            return
    
    async def send_hourly_report(self, portfolio_stats: Dict[str, Any]):
        """Send hourly balance report (matching old bot format)"""
        if not self.hourly_report_enabled or not self.enabled:
            return
        
        now = datetime.utcnow()
        emoji = "🟢" if portfolio_stats.get('total_pnl', 0) >= 0 else "🔴"
        
        message = f"""
⏰ <b>Hourly Balance Report {now.strftime('%Y-%m-%d %H:%M')}</b>

💰 <b>Balance:</b> ${portfolio_stats.get('total_value', 0):,.2f}
📊 <b>Total P&L:</b> ${portfolio_stats.get('total_pnl', 0):+,.2f} ({portfolio_stats.get('roi_percent', 0):+.2f}%)
🎯 <b>Win Rate:</b> {portfolio_stats.get('win_rate_percent', 0):.1f}%
📈 <b>Total Trades:</b> {portfolio_stats.get('total_trades', 0)}

<i>Next update in 1 hour</i>
        """.strip()
        
        await self.send_message(message)
        
        message = f"""
📊 <b>Performance Alert</b>

<b>Wallet:</b> <code>{wallet_address}</code>
<b>Win Rate:</b> {performance.get('win_rate_percent', 0):.1f}%
<b>Total PnL:</b> ${performance.get('total_pnl', 0):+,.2f}
<b>Trades:</b> {performance.get('total_trades', 0)}

Keep an eye on this wallet's performance.
        """.strip()
        
        await self.send_message(message)
    
    # ==================== Command Handlers ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🚀 <b>Polymarket Copy Trading Bot</b>\n\n"
            "I'm monitoring target wallets and copying their trades in paper trading mode.\n\n"
            "Use /help to see available commands.",
            parse_mode="HTML"
        )
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.risk_manager:
            await update.message.reply_text("Bot is initializing...")
            return
        
        risk_summary = self.risk_manager.get_risk_summary()
        
        status = "🟢 Active" if risk_summary.get('trading_allowed') else "🔴 Paused"
        
        message = f"""
<b>Bot Status:</b> {status}

<b>Daily PnL:</b> {risk_summary.get('daily_pnl_percent', 0):+.2f}%
<b>Loss Limit:</b> {risk_summary.get('daily_loss_limit', 0)}%
<b>Unfollowed Wallets:</b> {risk_summary.get('unfollowed_wallets', 0)}

Use /portfolio for detailed stats.
        """.strip()
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command"""
        if not self.paper_trader:
            await update.message.reply_text("Portfolio not available yet...")
            return
        
        stats = self.paper_trader.get_portfolio_stats()
        
        emoji = "🟢" if stats.get('total_pnl', 0) >= 0 else "🔴"
        
        message = f"""
{emoji} <b>Portfolio Overview</b>

<b>Balance:</b> ${stats.get('balance_usdc', 0):,.2f} USDC
<b>Positions Value:</b> ${stats.get('positions_value', 0):,.2f} USDC
<b>Total Value:</b> ${stats.get('total_value', 0):,.2f} USDC
<b>Initial:</b> ${stats.get('initial_balance', 0):,.2f} USDC

<b>Total PnL:</b> ${stats.get('total_pnl', 0):+,.2f} ({stats.get('roi_percent', 0):+.2f}%)
<b>Win Rate:</b> {stats.get('win_rate_percent', 0):.1f}%
<b>Total Trades:</b> {stats.get('total_trades', 0)}
<b>Max Drawdown:</b> {stats.get('max_drawdown_percent', 0):.2f}%
        """.strip()
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        if not self.paper_trader:
            await update.message.reply_text("Positions not available yet...")
            return
        
        positions = self.paper_trader.get_open_positions()
        
        if not positions:
            await update.message.reply_text("No open positions.")
            return
        
        message = "<b>Open Positions:</b>\n\n"
        
        for pos in positions[:10]:  # Limit to 10
            emoji = "🟢" if pos.side == "BUY" else "🔴"
            message += f"""
{emoji} <b>{pos.market_question[:40]}...</b>
Side: {pos.side} | Size: ${pos.size:.2f}
Entry: {pos.entry_price:.4f} | Outcome: {pos.outcome_name}
            """.strip() + "\n\n"
        
        if len(positions) > 10:
            message += f"... and {len(positions) - 10} more positions"
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_wallets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /wallets command"""
        if not self.wallet_monitor:
            await update.message.reply_text("Wallet monitor not available...")
            return
        
        stats = self.wallet_monitor.get_wallet_stats()
        
        if not stats:
            await update.message.reply_text("No wallets being monitored.")
            return
        
        message = "<b>Monitored Wallets:</b>\n\n"
        
        for addr, info in list(stats.items())[:10]:
            status = "🟢" if info.get('is_active') else "🔴"
            message += f"""
{status} <b>{info.get('name', addr[:8])}</b>
Address: <code>{addr[:16]}...</code>
Trades: {info.get('total_trades_detected', 0)}
            """.strip() + "\n\n"
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not self.risk_manager:
            await update.message.reply_text("Stats not available yet...")
            return
        
        daily_stats = self.risk_manager.get_daily_stats(days=7)
        
        if not daily_stats:
            await update.message.reply_text("No daily stats available yet.")
            return
        
        message = "<b>Last 7 Days:</b>\n\n"
        
        for day in daily_stats:
            emoji = "🟢" if day.get('pnl', 0) >= 0 else "🔴"
            message += f"""
{emoji} <b>{day.get('date')}</b>
PnL: ${day.get('pnl', 0):+,.2f} ({day.get('pnl_percent', 0):+.2f}%)
Trades: {day.get('trades', 0)} | Win Rate: {day.get('win_rate', 0):.1f}%
            """.strip() + "\n\n"
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        message = """
<b>Available Commands:</b>

/start - Start the bot
/status - Check bot status
/portfolio - View portfolio stats
/positions - View open positions
/wallets - List monitored wallets
/stats - View daily performance stats
/help - Show this help message
        """.strip()
        
        await update.message.reply_text(message, parse_mode="HTML")
    
    # ==================== Scheduled Tasks ====================
    
    async def check_daily_summary(self):
        """Check if it's time for daily summary"""
        now = datetime.utcnow()
        
        if now.time().hour == self.daily_summary_time.hour and \
           now.time().minute == self.daily_summary_time.minute:
            
            if self.paper_trader and self.risk_manager:
                portfolio_stats = self.paper_trader.get_portfolio_stats()
                daily_stats = self.risk_manager.get_daily_stats(days=1)
                await self.send_daily_summary(portfolio_stats, daily_stats)
