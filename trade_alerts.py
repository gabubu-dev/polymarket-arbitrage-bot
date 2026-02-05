#!/usr/bin/env python3
"""
Monitor paper trading database and queue Telegram alerts for new trades.
"""
import sqlite3
import time
import json
from datetime import datetime

DB_PATH = "paper_trading.db"
QUEUE_FILE = "/tmp/polymarket_alerts_queue.jsonl"
CHECK_INTERVAL = 5  # seconds

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
    
    def queue_alert(self, alert_data):
        """Write alert to queue file for processing"""
        try:
            with open(QUEUE_FILE, 'a') as f:
                f.write(json.dumps(alert_data) + '\n')
                f.flush()
            print(f"✅ Queued alert: {alert_data['title']}")
            return True
        except Exception as e:
            print(f"❌ Error queuing alert: {e}")
            return False
    
    def check_for_new_trades(self):
        """Check for new positions and queue alerts"""
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
                    alert_data = {
                        "title": f"{emoji} POSITION OPENED",
                        "message": (
                            f"Market: {symbol}\n"
                            f"Direction: {direction.upper()}\n"
                            f"Entry Price: ${entry_price:.3f}\n"
                            f"Size: ${size_usd:.2f}"
                        ),
                        "timestamp": datetime.now().isoformat()
                    }
                    self.queue_alert(alert_data)
                    
                elif status == "closed":
                    # Position closed alert
                    emoji = "💰" if pnl >= 0 else "📉"
                    alert_data = {
                        "title": f"{emoji} POSITION CLOSED",
                        "message": (
                            f"Market: {symbol}\n"
                            f"Direction: {direction.upper()}\n"
                            f"Entry Price: ${entry_price:.3f}\n"
                            f"P&L: ${pnl:.2f}\n"
                            f"Status: CLOSED"
                        ),
                        "timestamp": datetime.now().isoformat()
                    }
                    self.queue_alert(alert_data)
    
    def run(self):
        """Main monitoring loop"""
        print(f"🚀 Trade Alert Monitor Started")
        print(f"📊 Monitoring: {DB_PATH}")
        print(f"📝 Queue file: {QUEUE_FILE}")
        print(f"⏱️  Check interval: {CHECK_INTERVAL}s")
        print()
        
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
