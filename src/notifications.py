"""
Notification system for important bot events.

Sends alerts via webhook (Discord, Slack, Telegram, etc.) when
important events occur.
"""

import logging
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NotificationLevel(Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    TRADE = "trade"


class NotificationManager:
    """
    Manage bot notifications.
    
    Sends alerts to configured webhook endpoints for important events.
    """
    
    def __init__(self, webhook_url: str = "", enabled: bool = True):
        """
        Initialize notification manager.
        
        Args:
            webhook_url: Webhook URL to send notifications to
            enabled: Whether notifications are enabled
        """
        self.logger = logging.getLogger("NotificationManager")
        self.webhook_url = webhook_url
        self.enabled = enabled and bool(webhook_url)
        
        if self.enabled:
            self.logger.info(f"Notifications enabled: {self.webhook_url[:30]}...")
        else:
            self.logger.info("Notifications disabled")
    
    async def send_notification(self, title: str, message: str,
                               level: NotificationLevel = NotificationLevel.INFO,
                               fields: Optional[Dict[str, str]] = None) -> bool:
        """
        Send a notification.
        
        Args:
            title: Notification title
            message: Notification message
            level: Severity level
            fields: Optional key-value pairs to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Build payload (Discord webhook format)
            embed = {
                "title": title,
                "description": message,
                "timestamp": datetime.utcnow().isoformat(),
                "color": self._get_color(level)
            }
            
            # Add fields if provided
            if fields:
                embed["fields"] = [
                    {"name": k, "value": str(v), "inline": True}
                    for k, v in fields.items()
                ]
            
            payload = {
                "embeds": [embed]
            }
            
            # Send webhook request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:
                        return True
                    else:
                        self.logger.warning(
                            f"Webhook returned status {response.status}"
                        )
                        return False
        
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False
    
    def _get_color(self, level: NotificationLevel) -> int:
        """Get embed color based on notification level."""
        colors = {
            NotificationLevel.INFO: 0x3498db,      # Blue
            NotificationLevel.WARNING: 0xf39c12,   # Orange
            NotificationLevel.CRITICAL: 0xe74c3c,  # Red
            NotificationLevel.TRADE: 0x2ecc71      # Green
        }
        return colors.get(level, 0x95a5a6)
    
    async def notify_trade_entry(self, symbol: str, direction: str,
                                 size: float, price: float,
                                 divergence: float) -> bool:
        """
        Notify about trade entry.
        
        Args:
            symbol: Trading symbol
            direction: Trade direction
            size: Position size
            price: Entry price
            divergence: Price divergence that triggered trade
            
        Returns:
            True if sent successfully
        """
        return await self.send_notification(
            title=f"🔵 Trade Opened: {symbol} {direction.upper()}",
            message=f"New position opened based on {divergence:.1%} divergence",
            level=NotificationLevel.TRADE,
            fields={
                "Symbol": symbol,
                "Direction": direction,
                "Size": f"${size:.2f}",
                "Entry Price": f"{price:.3f}",
                "Divergence": f"{divergence:.1%}"
            }
        )
    
    async def notify_trade_exit(self, symbol: str, pnl: float,
                                hold_time: int, reason: str) -> bool:
        """
        Notify about trade exit.
        
        Args:
            symbol: Trading symbol
            pnl: Profit/loss
            hold_time: Time held in seconds
            reason: Exit reason
            
        Returns:
            True if sent successfully
        """
        emoji = "🟢" if pnl > 0 else "🔴"
        return await self.send_notification(
            title=f"{emoji} Trade Closed: {symbol}",
            message=f"Position closed with {'profit' if pnl > 0 else 'loss'}",
            level=NotificationLevel.TRADE if pnl > 0 else NotificationLevel.WARNING,
            fields={
                "Symbol": symbol,
                "P&L": f"${pnl:.2f}",
                "Hold Time": f"{hold_time}s",
                "Exit Reason": reason
            }
        )
    
    async def notify_error(self, error_type: str, message: str) -> bool:
        """
        Notify about an error.
        
        Args:
            error_type: Type of error
            message: Error message
            
        Returns:
            True if sent successfully
        """
        return await self.send_notification(
            title=f"⚠️ Error: {error_type}",
            message=message,
            level=NotificationLevel.CRITICAL
        )
    
    async def notify_health_status(self, status: str, issues: list[str]) -> bool:
        """
        Notify about health status change.
        
        Args:
            status: Overall health status
            issues: List of issues
            
        Returns:
            True if sent successfully
        """
        if status == 'healthy':
            return False  # Don't spam with healthy notifications
        
        level = NotificationLevel.CRITICAL if status == 'critical' else NotificationLevel.WARNING
        
        return await self.send_notification(
            title=f"🏥 Health Check: {status.upper()}",
            message="\n".join(f"• {issue}" for issue in issues) if issues else "System degraded",
            level=level
        )
    
    async def notify_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """
        Send daily performance summary.
        
        Args:
            stats: Performance statistics
            
        Returns:
            True if sent successfully
        """
        return await self.send_notification(
            title="📊 Daily Summary",
            message=f"Performance summary for {datetime.now().strftime('%Y-%m-%d')}",
            level=NotificationLevel.INFO,
            fields={
                "Total Trades": str(stats.get('total_trades', 0)),
                "Win Rate": f"{stats.get('win_rate', 0):.1f}%",
                "Total P&L": f"${stats.get('total_pnl', 0):.2f}",
                "Avg P&L": f"${stats.get('avg_pnl', 0):.2f}"
            }
        )
