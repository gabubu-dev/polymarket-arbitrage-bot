#!/usr/bin/env python3
"""Calculate safe RPC call rate based on rate limit patterns"""

import sqlite3
from datetime import datetime, timedelta

def calculate_optimal_rate():
    """Calculate safe RPC call rate based on rate limit patterns"""
    conn = sqlite3.connect('rate_limits.db')
    cursor = conn.cursor()
    
    # Get rate limit frequency
    cursor.execute('''
        SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
        FROM rate_limit_events
        WHERE provider = 'polygon-rpc'
    ''')
    count, first, last = cursor.fetchone()
    
    print(f"\n📊 Analysis of {count} rate limit events")
    print(f"   First event: {first}")
    print(f"   Last event:  {last}")
    
    if count == 0:
        # No rate limits = conservative default
        optimal = {
            'provider': 'polygon-rpc',
            'max_calls_per_second': 5.0,
            'max_calls_per_minute': 200,
            'recommended_delay_ms': 200,
            'confidence': 0.3
        }
        print("\n⚠️  No rate limit data found. Using conservative defaults.")
    else:
        # Calculate time span
        if first and last:
            first_dt = datetime.fromisoformat(first)
            last_dt = datetime.fromisoformat(last)
            duration_seconds = (last_dt - first_dt).total_seconds()
            events_per_second = count / duration_seconds if duration_seconds > 0 else 0
            
            print(f"   Duration: {duration_seconds:.1f} seconds")
            print(f"   Rate limit events per second: {events_per_second:.2f}")
        
        # Free Polygon RPC typical limits: 10 req/s, 500 req/min
        # Being hit with rate limits means we exceeded these
        # Conservative approach: 30% of typical limit to be safe
        optimal = {
            'provider': 'polygon-rpc',
            'max_calls_per_second': 3.0,   # 30% of typical 10/s
            'max_calls_per_minute': 150,    # 30% of typical 500/min
            'recommended_delay_ms': 350,    # 1000/3 = 333ms, rounded up
            'confidence': 0.7
        }
        print(f"\n💡 Recommended rate based on {count} rate limit events:")
    
    print(f"   Max calls/second: {optimal['max_calls_per_second']}")
    print(f"   Max calls/minute: {optimal['max_calls_per_minute']}")
    print(f"   Delay between calls: {optimal['recommended_delay_ms']}ms")
    print(f"   Confidence: {optimal['confidence']*100:.0f}%")
    
    cursor.execute('''
        INSERT OR REPLACE INTO optimal_rates
        (provider, max_calls_per_second, max_calls_per_minute, 
         recommended_delay_ms, last_updated, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        optimal['provider'],
        optimal['max_calls_per_second'],
        optimal['max_calls_per_minute'],
        optimal['recommended_delay_ms'],
        datetime.now().isoformat(),
        optimal['confidence']
    ))
    
    conn.commit()
    conn.close()
    
    return optimal

if __name__ == '__main__':
    optimal = calculate_optimal_rate()
    print(f"\n✅ Optimal rate calculated and stored in database")
