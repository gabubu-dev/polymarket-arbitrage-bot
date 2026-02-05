#!/usr/bin/env python3
"""Extract rate limit events from log file"""

import re
import sqlite3
from datetime import datetime

def parse_rate_limits(log_file):
    """Extract rate limit events from log file"""
    conn = sqlite3.connect('rate_limits.db')
    cursor = conn.cursor()
    
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Too many requests.*retry in ([0-9ms]+)"
    
    count = 0
    with open(log_file) as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                timestamp = match.group(1)
                retry = match.group(2)
                
                # Parse retry time
                if 'm' in retry:
                    retry_seconds = int(retry.replace('m0s', '').replace('m', '')) * 60
                elif 's' in retry:
                    retry_seconds = int(retry.replace('s', ''))
                else:
                    retry_seconds = 10  # default
                
                cursor.execute('''
                    INSERT INTO rate_limit_events (timestamp, provider, retry_seconds, error_message)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, 'polygon-rpc', retry_seconds, line.strip()))
                count += 1
    
    conn.commit()
    conn.close()
    
    return count

if __name__ == '__main__':
    count = parse_rate_limits('bot.log')
    print(f"✅ Parsed {count} rate limit events from bot.log")
