#!/usr/bin/env python3
"""
Monitor paper trading database and send Telegram alerts for new trades.
Uses subprocess to call OpenClaw CLI directly.
"""
import sqlite3
import time
import subprocess
from datetime import datetime

DB_PATH = "paper_trading.db"
CHECK_INTERVAL = 5  # seconds
USER_TELEGRAM_ID = "5766153421"

class TradeAlertMonitor:
    def __init__(self):
        self.seen_positions = set()
        
    def get_positions(self):
        """Get all positions from database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT position_id, symbol, direction, entry_price, size_usd, status, pnl 
                FROM positions 
                ORDER BY entry_time DESC
            """)
            positions = cursor.fetchall()
            conn.close()
            return positions
        except Exception as e:
            print(f"Error reading database: {e}")
            return []
    
    def send_telegram_alert(self, title, message):
        """Send alert via OpenClaw CLI"""
        try:
            full_message = f"**{title}**\n\n{message}"
            
            # Use subprocess to call sessions_spawn with message tool
            cmd = [
                'sessions_spawn',
                '--label', 'polymarket-alert',
                '--task', f'Send this message via Telegram to user {USER_TELEGRAM_ID}: {full_message}'
            ]
            
            # Try the command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Alert sent: {title}")
                return True
            else:
                print(f"❌ Failed to send alert: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending alert: {e}")
            return False
    
    def check_for_new_trades(self):
        """Check for new positions and send alerts"""
        positions = self.get_positions()
        
        for pos in positions:
            pos_id = pos[0]
            symbol = pos[1]
            direction = pos[2]
            entry_price = pos[3]
            size_usd = pos[4]
            status = pos[5]
            pnl = pos[6] if len(pos) > 6 else 0.0
            
            # Check if this is a new position state
            pos_key = f"{pos_id}_{status}"
            
            if pos_key not in self.seen_positions:
                self.seen_positions.add(pos_key)
                
                if status == "open":
                    # Position opened alert
                    emoji = "📈" if direction == "up" else "📉"
                    title = f"{emoji} POSITION OPENED"
                    message = (
                        f"Market: {symbol}\n"
                        f"Direction: {direction.upper()}\n"
                        f"Entry Price: ${entry_price:.3f}\n"
                        f"Size: ${size_usd:.2f}"
                    )
                    self.send_telegram_alert(title, message)
                    
                elif status == "closed":
                    # Position closed alert
                    emoji = "💰" if pnl >= 0 else "📉"
                    title = f"{emoji} POSITION CLOSED"
                    message = (
                        f"Market: {symbol}\n"
                        f"Direction: {direction.upper()}\n"
                        f"Entry Price: ${entry_price:.3f}\n"
                        f"P&L: ${pnl:.2f}"
                    )
                    self.send_telegram_alert(title, message)
    
    def run(self):
        """Main monitoring loop"""
        print(f"🚀 Trade Alert Monitor Started")
        print(f"📊 Monitoring: {DB_PATH}")
        print(f"📱 Sending alerts to Telegram ID: {USER_TELEGRAM_ID}")
        print(f"⏱️  Check interval: {CHECK_INTERVAL}s")
        print()
        
        # Initialize seen positions from existing DB
        print("Loading existing positions...")
        positions = self.get_positions()
        for pos in positions:
            pos_id = pos[0]
            status = pos[5]
            self.seen_positions.add(f"{pos_id}_{status}")
        print(f"Loaded {len(self.seen_positions)} existing position states")
        print("Monitoring for NEW trades...\n")
        
        while True:
            try:
                self.check_for_new_trades()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                print("\n👋 Shutting down trade alert monitor...")
                break
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor = TradeAlertMonitor()
    monitor.run()
