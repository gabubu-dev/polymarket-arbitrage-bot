"""
Telegram Alert System for Paper Trading

Sends real-time alerts to qippu when balance moves ±10% thresholds.
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import json


class TelegramAlerter:
    """
    Send Telegram alerts for paper trading milestones.
    
    Alerts when balance crosses ±10% thresholds from starting point.
    """
    
    # qippu's Telegram ID
    QIPPU_CHAT_ID = "6559976977"
    
    # Telegram Bot API endpoint
    TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: str = QIPPU_CHAT_ID,
        starting_balance: float = 10000.0,
        data_dir: str = "data"
    ):
        """
        Initialize Telegram alerter.
        
        Args:
            bot_token: Telegram bot token (get from @BotFather)
            chat_id: Telegram chat ID to send alerts to
            starting_balance: Starting balance for threshold calculations
            data_dir: Directory to store alert state
        """
        self.logger = logging.getLogger("TelegramAlerter")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.starting_balance = starting_balance
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "telegram_alerts_state.json"
        
        # Track which thresholds we've alerted on
        self.alerted_thresholds: set[float] = set()
        self._load_state()
        
        # Determine if enabled
        self.enabled = bool(self.bot_token)
        
        if not self.enabled:
            self.logger.warning(
                "Telegram alerts DISABLED - No bot token provided. "
                "Set TELEGRAM_BOT_TOKEN in config to enable."
            )
        else:
            self.logger.info(
                f"Telegram alerts ENABLED for chat {chat_id} | "
                f"Starting balance: ${starting_balance:.2f}"
            )
    
    def _load_state(self) -> None:
        """Load alert state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.alerted_thresholds = set(data.get('alerted_thresholds', []))
                    self.logger.info(
                        f"Loaded alert state: {len(self.alerted_thresholds)} thresholds already sent"
                    )
            except Exception as e:
                self.logger.error(f"Error loading alert state: {e}")
    
    def _save_state(self) -> None:
        """Save alert state to disk."""
        try:
            data = {
                'alerted_thresholds': list(self.alerted_thresholds),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving alert state: {e}")
    
    def _get_threshold_balance(self, percent_change: int) -> float:
        """
        Calculate balance threshold for a percentage change.
        
        Args:
            percent_change: Percentage change (e.g., +10, -10, +20, -20)
            
        Returns:
            Balance threshold
        """
        return self.starting_balance * (1 + percent_change / 100)
    
    def _get_crossed_thresholds(
        self,
        current_balance: float,
        previous_balance: float
    ) -> list[int]:
        """
        Check which thresholds were crossed.
        
        Args:
            current_balance: Current balance
            previous_balance: Previous balance
            
        Returns:
            List of threshold percentages that were crossed
        """
        crossed = []
        
        # Check upward thresholds (+10%, +20%, +30%, ...)
        threshold = 10
        max_threshold = 500  # Check up to +500%
        while threshold <= max_threshold:
            threshold_balance = self._get_threshold_balance(threshold)
            
            if previous_balance < threshold_balance <= current_balance:
                if threshold not in self.alerted_thresholds:
                    crossed.append(threshold)
            
            threshold += 10
        
        # Check downward thresholds (-10%, -20%, -30%, ...)
        threshold = -10
        min_threshold = -90  # Check down to -90%
        while threshold >= min_threshold:
            threshold_balance = self._get_threshold_balance(threshold)
            
            if previous_balance > threshold_balance >= current_balance:
                if threshold not in self.alerted_thresholds:
                    crossed.append(threshold)
            
            threshold -= 10
        
        return crossed
    
    async def check_and_alert(
        self,
        current_balance: float,
        previous_balance: float,
        total_pnl: float,
        win_rate: float,
        total_trades: int
    ) -> bool:
        """
        Check if any thresholds were crossed and send alerts.
        
        Args:
            current_balance: Current balance
            previous_balance: Previous balance before last trade
            total_pnl: Total profit/loss
            win_rate: Win rate percentage
            total_trades: Total number of trades
            
        Returns:
            True if any alerts were sent
        """
        if not self.enabled:
            return False
        
        crossed = self._get_crossed_thresholds(current_balance, previous_balance)
        
        if not crossed:
            return False
        
        # Send alert for each crossed threshold
        alerts_sent = 0
        for threshold in crossed:
            success = await self._send_threshold_alert(
                threshold=threshold,
                current_balance=current_balance,
                total_pnl=total_pnl,
                win_rate=win_rate,
                total_trades=total_trades
            )
            
            if success:
                self.alerted_thresholds.add(threshold)
                alerts_sent += 1
        
        if alerts_sent > 0:
            self._save_state()
        
        return alerts_sent > 0
    
    async def _send_threshold_alert(
        self,
        threshold: int,
        current_balance: float,
        total_pnl: float,
        win_rate: float,
        total_trades: int
    ) -> bool:
        """
        Send Telegram alert for a specific threshold.
        
        Args:
            threshold: Threshold percentage (+10, -10, etc.)
            current_balance: Current balance
            total_pnl: Total P&L
            win_rate: Win rate percentage
            total_trades: Total trades
            
        Returns:
            True if sent successfully
        """
        # Choose emoji based on gain/loss
        if threshold > 0:
            emoji = "🚀" if threshold >= 50 else "📈"
            trend = "GAIN"
        else:
            emoji = "⚠️" if threshold <= -20 else "📉"
            trend = "LOSS"
        
        # Format message
        pnl_sign = "+" if total_pnl >= 0 else ""
        message = (
            f"{emoji} <b>Paper Trading Alert: {threshold:+d}% {trend}</b>\n\n"
            f"💰 <b>Balance:</b> ${current_balance:,.2f} ({threshold:+d}% from start)\n"
            f"📊 <b>P&L:</b> {pnl_sign}${total_pnl:,.2f}\n"
            f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"📈 <b>Total Trades:</b> {total_trades}\n\n"
            f"<i>Started with ${self.starting_balance:,.2f}</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a Telegram message.
        
        Args:
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
            disable_notification: Send silently
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            self.logger.debug("Telegram not enabled, skipping message")
            return False
        
        try:
            url = f"{self.TELEGRAM_API_BASE.format(token=self.bot_token)}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info("✅ Telegram alert sent successfully")
                        return True
                    else:
                        error = await response.text()
                        self.logger.error(
                            f"❌ Telegram API error {response.status}: {error}"
                        )
                        return False
        
        except Exception as e:
            self.logger.error(f"❌ Error sending Telegram message: {e}")
            return False
    
    async def send_startup_notification(self, initial_balance: float) -> bool:
        """
        Send notification when paper trading starts.
        
        Args:
            initial_balance: Starting balance
            
        Returns:
            True if sent successfully
        """
        message = (
            f"🤖 <b>Paper Trading Bot Started</b>\n\n"
            f"💰 <b>Starting Balance:</b> ${initial_balance:,.2f}\n"
            f"🎯 <b>Alert Thresholds:</b> Every ±10%\n"
            f"📊 <b>Mode:</b> Simulation (No Real Money)\n\n"
            f"<i>You'll receive alerts when balance moves ±10%, ±20%, etc.</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_daily_summary(
        self,
        balance: float,
        pnl: float,
        win_rate: float,
        total_trades: int,
        best_trade: float,
        worst_trade: float
    ) -> bool:
        """
        Send daily performance summary.
        
        Args:
            balance: Current balance
            pnl: Total P&L
            win_rate: Win rate percentage
            total_trades: Total trades
            best_trade: Best trade P&L
            worst_trade: Worst trade P&L
            
        Returns:
            True if sent successfully
        """
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_percent = (pnl / self.starting_balance) * 100
        
        message = (
            f"📊 <b>Daily Paper Trading Summary</b>\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d')}</i>\n\n"
            f"💰 <b>Balance:</b> ${balance:,.2f}\n"
            f"📈 <b>Total P&L:</b> {pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_percent:.2f}%)\n"
            f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n"
            f"📊 <b>Trades Today:</b> {total_trades}\n"
            f"🟢 <b>Best Trade:</b> ${best_trade:.2f}\n"
            f"🔴 <b>Worst Trade:</b> ${worst_trade:.2f}\n"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_emergency_alert(self, reason: str, balance: float) -> bool:
        """
        Send emergency alert (e.g., critical loss).
        
        Args:
            reason: Emergency reason
            balance: Current balance
            
        Returns:
            True if sent successfully
        """
        message = (
            f"🚨 <b>EMERGENCY ALERT</b> 🚨\n\n"
            f"⚠️ <b>Reason:</b> {reason}\n"
            f"💰 <b>Current Balance:</b> ${balance:,.2f}\n"
            f"📉 <b>Loss:</b> ${self.starting_balance - balance:,.2f}\n\n"
            f"<i>Paper trading bot may have stopped</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML", disable_notification=False)
    
    def reset_alerts(self) -> None:
        """Reset alert state (when account is reset)."""
        self.logger.info("🔄 Resetting Telegram alert state")
        self.alerted_thresholds.clear()
        self._save_state()
    
    async def send_competitive_benchmark(
        self,
        our_win_rate: float,
        benchmark_data: Dict[str, Any]
    ) -> bool:
        """
        Send competitive benchmarking alert.
        
        Args:
            our_win_rate: Our bot's win rate
            benchmark_data: Benchmark data from TwitterIntelligence
            
        Returns:
            True if sent successfully
        """
        rank = benchmark_data.get('rank', 'Unknown')
        percentile = benchmark_data.get('percentile', 0)
        competitive_bots = benchmark_data.get('competitive_bots', 0)
        better_than = benchmark_data.get('better_than', 0)
        top_bot_win_rate = benchmark_data.get('top_bot_win_rate', 0)
        avg_competitor = benchmark_data.get('avg_competitor_win_rate', 0)
        
        # Choose emoji based on performance
        if percentile >= 80:
            emoji = "🏆"
        elif percentile >= 60:
            emoji = "👍"
        elif percentile >= 40:
            emoji = "📊"
        else:
            emoji = "⚠️"
        
        message = (
            f"{emoji} <b>Competitive Benchmark Report</b>\n\n"
            f"🤖 <b>Our Win Rate:</b> {our_win_rate:.1f}%\n"
            f"📊 <b>Rank:</b> {rank} ({percentile:.0f}th percentile)\n"
            f"🎯 <b>Competitive Bots:</b> {competitive_bots}\n"
            f"✅ <b>Better Than:</b> {better_than} bots\n\n"
            f"🏅 <b>Top Bot:</b> {top_bot_win_rate:.1f}%\n"
            f"📈 <b>Competitor Avg:</b> {avg_competitor:.1f}%\n\n"
            f"<i>Updated from Twitter intelligence</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_bot_discovery_alert(
        self,
        bot_handle: str,
        win_rate: Optional[float],
        strategies: List[str]
    ) -> bool:
        """
        Alert when discovering a new competitive bot.
        
        Args:
            bot_handle: Twitter handle
            win_rate: Bot's win rate (if available)
            strategies: Strategies used by the bot
            
        Returns:
            True if sent successfully
        """
        win_rate_str = f"{win_rate:.1f}%" if win_rate else "Unknown"
        strategies_str = ", ".join(strategies) if strategies else "Unknown"
        
        message = (
            f"🔍 <b>New Bot Discovered</b>\n\n"
            f"👤 <b>Handle:</b> @{bot_handle}\n"
            f"🎯 <b>Win Rate:</b> {win_rate_str}\n"
            f"📊 <b>Strategies:</b> {strategies_str}\n\n"
            f"<i>Analyzing for competitive insights...</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_strategy_adaptation_alert(
        self,
        strategy_name: str,
        reason: str,
        priority_change: str
    ) -> bool:
        """
        Alert when strategy is adapted based on competitive intel.
        
        Args:
            strategy_name: Name of strategy adapted
            reason: Reason for adaptation
            priority_change: Description of priority change
            
        Returns:
            True if sent successfully
        """
        message = (
            f"🔧 <b>Strategy Adaptation</b>\n\n"
            f"📊 <b>Strategy:</b> {strategy_name}\n"
            f"🎯 <b>Change:</b> {priority_change}\n"
            f"💡 <b>Reason:</b> {reason}\n\n"
            f"<i>Auto-optimizing based on market intelligence</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_market_opportunity_alert(
        self,
        market_question: str,
        category: str,
        profitability_score: float,
        volume_24h: float,
        spread: float
    ) -> bool:
        """
        Alert about high-value market opportunity discovered.
        
        Args:
            market_question: Market question
            category: Market category
            profitability_score: Profitability score
            volume_24h: 24h volume
            spread: Market spread
            
        Returns:
            True if sent successfully
        """
        message = (
            f"💎 <b>High-Value Opportunity</b>\n\n"
            f"❓ <b>Market:</b> {market_question[:100]}\n"
            f"📂 <b>Category:</b> {category.title()}\n"
            f"⭐ <b>Score:</b> {profitability_score:.3f}\n"
            f"💰 <b>Volume 24h:</b> ${volume_24h:,.0f}\n"
            f"📊 <b>Spread:</b> {spread*100:.2f}%\n\n"
            f"<i>Real Polymarket market discovered</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")
    
    async def send_intelligence_summary(
        self,
        total_bots: int,
        top_strategies: Dict[str, Any],
        market_stats: Dict[str, Any]
    ) -> bool:
        """
        Send daily intelligence gathering summary.
        
        Args:
            total_bots: Total bots discovered
            top_strategies: Top performing strategies
            market_stats: Market discovery statistics
            
        Returns:
            True if sent successfully
        """
        # Format top strategies
        strategies_text = ""
        for strat, data in list(top_strategies.items())[:3]:
            count = data.get('count', 0)
            avg_win = data.get('avg_win_rate', 0)
            strategies_text += f"  • {strat}: {avg_win:.1f}% avg ({count} bots)\n"
        
        total_markets = market_stats.get('total_markets', 0)
        avg_volume = market_stats.get('avg_volume', 0)
        
        message = (
            f"🧠 <b>Intelligence Summary</b>\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d')}</i>\n\n"
            f"🤖 <b>Bots Tracked:</b> {total_bots}\n"
            f"📊 <b>Markets Discovered:</b> {total_markets}\n"
            f"💰 <b>Avg Market Volume:</b> ${avg_volume:,.0f}\n\n"
            f"🏆 <b>Top Strategies:</b>\n{strategies_text}\n"
            f"<i>Competitive intelligence active</i>"
        )
        
        return await self.send_message(message, parse_mode="HTML")


# Test function
async def test_telegram_alerts():
    """Test Telegram alerts with dummy data."""
    import os
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ Set TELEGRAM_BOT_TOKEN environment variable to test")
        return
    
    alerter = TelegramAlerter(
        bot_token=bot_token,
        starting_balance=10000.0
    )
    
    # Test startup notification
    print("Sending startup notification...")
    await alerter.send_startup_notification(10000.0)
    await asyncio.sleep(1)
    
    # Test threshold alerts
    print("Testing threshold alerts...")
    
    # Simulate +10% threshold
    await alerter.check_and_alert(
        current_balance=11000.0,
        previous_balance=10000.0,
        total_pnl=1000.0,
        win_rate=65.0,
        total_trades=20
    )
    await asyncio.sleep(1)
    
    # Simulate -10% threshold
    await alerter.check_and_alert(
        current_balance=9000.0,
        previous_balance=10000.0,
        total_pnl=-1000.0,
        win_rate=45.0,
        total_trades=25
    )
    await asyncio.sleep(1)
    
    # Test daily summary
    print("Sending daily summary...")
    await alerter.send_daily_summary(
        balance=10500.0,
        pnl=500.0,
        win_rate=60.0,
        total_trades=15,
        best_trade=250.0,
        worst_trade=-150.0
    )
    
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_telegram_alerts())
