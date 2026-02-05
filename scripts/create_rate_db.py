#!/usr/bin/env python3
"""Create rate limit tracking database"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('rate_limits.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    provider TEXT NOT NULL,
    retry_seconds INTEGER,
    error_message TEXT,
    calls_before_limit INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS optimal_rates (
    provider TEXT PRIMARY KEY,
    max_calls_per_second REAL NOT NULL,
    max_calls_per_minute INTEGER NOT NULL,
    recommended_delay_ms INTEGER NOT NULL,
    last_updated TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5
)
''')

conn.commit()
conn.close()

print("✅ Database created successfully at rate_limits.db")
