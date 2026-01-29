"""
Telegram Alert System - Simplified for qippu's requirements

Sends:
1. Hourly balance updates
2. New transaction notifications

Disables all other alert types.
"""

import asyncio
import aiohttp
import logging
from typing import Optional
from datetime import datetime, timedelta
from pathlib import Path
import json


class TelegramAlerter:
    """
    Simplified Telegram alerter for qippu.
    
    Only sends:
    - Hourly balance summary
    - New transaction alerts
    """
    
    QIPPU_CHAT_ID = "6559976977"
    TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: str = QIPPU_CHAT_ID,
        data_dir: str = "data"
    ):
        self.logger = logging.getLogger("TelegramAlerter")
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Track last hourly report and known trades
        self.state_file = self.data_dir / "telegram_simple_state.json"
        self.last_hourly_report: Optional[datetime] = None
        self.reported_trade_ids: set = set()
        self._load_state()
        
        self.enabled = bool(self.bot_token)
        
        if not self.enabled:
            self.logger.warning("Telegram alerts DISABLED - No bot token provided")
        else:
            self.logger.info(f"Telegram alerts ENABLED for chat {chat_id}")
    
    def _load_state(self) -> None:
        """Load alert state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    if data.get('last_hourly_report'):
                        self.last_hourly_report = datetime.fromisoformat(data['last_hourly_report'])
                    self.reported_trade_ids = set(data.get('reported_trade_ids', []))
            except Exception as e:
                self.logger.error(f"Error loading state: {e}")
    
    def _save_state(self) -> None:
        """Save alert state."""
        try:
            data = {
                'last_hourly_report': self.last_hourly_report.isoformat() if self.last_hourly_report else None,
                'reported_trade_ids': list(self.reported_trade_ids),
                'updated_at': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send Telegram message."""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.TELEGRAM_API_BASE.format(token=self.bot_token)}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        self.logger.info("✅ Telegram message sent")
                        return True
                    else:
                        self.logger.error(f"❌ Telegram API error: {response.status}")
                        return False
        except Exception as e:
            self.logger.error(f"❌ Error sending message: {e}")
            return False
    
    async def check_and_send_hourly_report(
        self,
        current_balance: float,
        starting_balance: float,
        total_pnl: float,
        win_rate: float,
        total_trades: int
    ) -> bool:
        """
        Send hourly balance report if an hour has passed.
        
        Returns True if report was sent.
        """
        now = datetime.now()
        
        # Check if we should send (every hour)
        if self.last_hourly_report:
            time_since_last = now - self.last_hourly_report
            if time_since_last < timedelta(hours=1):
                return False  # Not time yet
        
        # Send hourly report
        pnl_percent = (total_pnl / starting_balance) * 100 if starting_balance else 0
        pnl_sign = "+" if total_pnl >= 0 else ""
        
        message = (
            f"⏰ <b>Hourly Balance Report</b>\n"
            f"<i>{now.strftime('%Y-%m-%d %H:%M')}</i>\n\n"
            f"💰 <b>Balance:</b> ${current_balance:,.2f}\n"
            f"📊 <b>Total P&L:</b> {pnl_sign}${total_pnl:,.2f} ({pnl_sign}{pnl_percent:.2f}%)\n"
            f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"📈 <b>Total Trades:</b> {total_trades}\n\n"
            f"<i>Next update in 1 hour</i>"
        )
        
        if await self.send_message(message):
            self.last_hourly_report = now
            self._save_state()
            return True
        return False
    
    async def send_transaction_alert(
        self,
        trade_id: str,
        market: str,
        direction: str,
        size: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        strategy: str
    ) -> bool:
        """
        Send alert for a new completed transaction.
        
        Returns True if alert was sent (or already reported).
        """
        # Skip if already reported
        if trade_id in self.reported_trade_ids:
            return True
        
        if not self.enabled:
            # Still track it even if not sending
            self.reported_trade_ids.add(trade_id)
            self._save_state()
            return False
        
        pnl_sign = "+" if pnl >= 0 else ""
        emoji = "🟢" if pnl >= 0 else "🔴"
        
        message = (
            f"{emoji} <b>New Transaction</b>\n\n"
            f"📊 <b>Market:</b> {market[:50]}{'...' if len(market) > 50 else ''}\n"
            f"📈 <b>Direction:</b> {direction.upper()}\n"
            f"💵 <b>Size:</b> ${size:,.2f}\n"
            f"🎯 <b>Entry:</b> ${entry_price:.3f}\n"
            f"🏁 <b>Exit:</b> ${exit_price:.3f}\n"
            f"💰 <b>P&L:</b> {pnl_sign}${pnl:,.2f}\n"
            f"🧠 <b>Strategy:</b> {strategy}\n\n"
            f"<i>{datetime.now().strftime('%H:%M:%S')}</i>"
        )
        
        if await self.send_message(message):
            self.reported_trade_ids.add(trade_id)
            self._save_state()
            return True
        return False
    
    # DISABLED ALERT TYPES - These methods do nothing
    async def send_startup_notification(self, *args, **kwargs) -> bool:
        """DISABLED - No startup alerts."""
        return True
    
    async def send_daily_summary(self, *args, **kwargs) -> bool:
        """DISABLED - Use hourly reports instead."""
        return True
    
    async def send_emergency_alert(self, *args, **kwargs) -> bool:
        """DISABLED - No emergency alerts."""
        return True
    
    async def send_competitive_benchmark(self, *args, **kwargs) -> bool:
        """DISABLED - No competitive alerts."""
        return True
    
    async def send_bot_discovery_alert(self, *args, **kwargs) -> bool:
        """DISABLED - No bot discovery alerts."""
        return True
    
    async def send_strategy_adaptation_alert(self, *args, **kwargs) -> bool:
        """DISABLED - No strategy alerts."""
        return True
    
    async def send_market_opportunity_alert(self, *args, **kwargs) -> bool:
        """DISABLED - No opportunity alerts."""
        return True
    
    async def send_intelligence_summary(self, *args, **kwargs) -> bool:
        """DISABLED - No intelligence alerts."""
        return True
    
    async def check_and_send_threshold_alert(self, *args, **kwargs) -> bool:
        """DISABLED - No threshold alerts."""
        return True
