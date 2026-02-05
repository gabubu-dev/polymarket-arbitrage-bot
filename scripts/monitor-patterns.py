#!/usr/bin/env python3
"""
Pattern detector for Polymarket bots - logs events, alerts on patterns only
Runs frequently (every 10 seconds) but only alerts on significant patterns

Usage: ./monitor-patterns.py
       ./monitor-patterns.py --check  # Check for patterns, print if found
"""

import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Paths
EVENTS_LOG = Path.home() / "Stable" / "polymarket-bot" / "heartbeat-events.jsonl"
ACTIVITY_LOG = Path.home() / "Stable" / "polymarket-bot" / "bot_activity.json"

# Pattern thresholds
CRASH_THRESHOLD = 3  # 3 crashes in 1 minute = alert
ERROR_THRESHOLD = 5  # 5 errors in 1 minute = alert
PNL_THRESHOLD = 50.0  # $50 change = alert


class PatternDetector:
    """Detect patterns in bot events"""
    
    def __init__(self):
        self.events = deque(maxlen=100)  # Keep last 100 events
        self.load_recent_events()
    
    def load_recent_events(self):
        """Load events from last minute"""
        if not EVENTS_LOG.exists():
            return
        
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        
        with open(EVENTS_LOG) as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    event_time = datetime.fromisoformat(event['timestamp'])
                    if event_time > one_minute_ago:
                        self.events.append(event)
                except:
                    continue
    
    def log_event(self, event_type: str, data: dict):
        """Log event to JSONL file"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'data': data
        }
        
        # Append to log
        with open(EVENTS_LOG, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Add to memory
        self.events.append(event)
    
    def check_bot_status(self):
        """Check if bots are running"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            
            primary_running = 'python main.py' in result.stdout
            secondary_running = 'python bot_paper.py' in result.stdout
            
            if not primary_running:
                self.log_event('bot_down', {'bot': 'primary'})
            
            if not secondary_running:
                self.log_event('bot_down', {'bot': 'secondary'})
            
            return primary_running, secondary_running
        except:
            return False, False
    
    def check_rate_limits(self):
        """Check recent logs for rate limit errors"""
        try:
            log_file = Path.home() / "Stable" / "polymarket-bot" / "bot.log"
            
            # Read last 50 lines
            result = subprocess.run(
                ['tail', '-50', str(log_file)],
                capture_output=True,
                text=True
            )
            
            # Count rate limit errors in last minute
            rate_limit_count = result.stdout.count('Too many requests')
            
            if rate_limit_count > 0:
                self.log_event('rate_limit', {'count': rate_limit_count})
            
            return rate_limit_count
        except:
            return 0
    
    def detect_patterns(self) -> dict:
        """Detect patterns in recent events"""
        patterns = {}
        
        # Count events by type in last minute
        event_counts = defaultdict(int)
        bot_crashes = defaultdict(int)
        
        for event in self.events:
            event_counts[event['type']] += 1
            
            if event['type'] == 'bot_down':
                bot_name = event['data'].get('bot', 'unknown')
                bot_crashes[bot_name] += 1
        
        # Pattern 1: Repeated crashes
        for bot, count in bot_crashes.items():
            if count >= CRASH_THRESHOLD:
                patterns['repeated_crashes'] = {
                    'bot': bot,
                    'count': count,
                    'severity': 'critical'
                }
        
        # Pattern 2: High rate limit errors
        rate_limit_count = event_counts.get('rate_limit', 0)
        if rate_limit_count >= ERROR_THRESHOLD:
            patterns['rate_limit_storm'] = {
                'count': rate_limit_count,
                'severity': 'warning'
            }
        
        return patterns
    
    def update_activity_log(self, primary_running, secondary_running):
        """Update bot activity timestamps"""
        activity = {
            'primary': {
                'last_check': datetime.now().isoformat(),
                'status': 'running' if primary_running else 'down'
            },
            'secondary': {
                'last_check': datetime.now().isoformat(),
                'status': 'running' if secondary_running else 'down'
            }
        }
        
        with open(ACTIVITY_LOG, 'w') as f:
            json.dump(activity, f, indent=2)


def main():
    """Main monitoring loop"""
    detector = PatternDetector()
    
    # Check bot status
    primary_running, secondary_running = detector.check_bot_status()
    
    # Check rate limits
    rate_limit_count = detector.check_rate_limits()
    
    # Update activity log for pmstatus
    detector.update_activity_log(primary_running, secondary_running)
    
    # Detect patterns
    patterns = detector.detect_patterns()
    
    # Only print if patterns found (for cron/alert purposes)
    if patterns:
        print(json.dumps(patterns, indent=2))
        return 1  # Exit code 1 = patterns detected
    
    return 0  # Exit code 0 = all good


if __name__ == '__main__':
    import sys
    sys.exit(main())
