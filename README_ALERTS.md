# Trade Alerts System

## Quick Start

```bash
cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/

# Start monitoring
./manage_alerts.sh start

# Check status
./manage_alerts.sh status

# View logs
./manage_alerts.sh logs
```

## How It Works

1. **Monitor** (`trade_alerts.py`) watches the database every 5 seconds
2. **Detects** new position opens/closes
3. **Queues** alerts to `/tmp/polymarket_alerts_queue.jsonl`
4. **Sends** via Telegram to user 5766153421

## Processing Queued Alerts

The monitor queues alerts to a file. To send them via Telegram, use the message tool from the main agent:

**Example (from main agent session):**
```python
import json

with open('/tmp/polymarket_alerts_queue.jsonl', 'r') as f:
    for line in f:
        alert = json.loads(line)
        # Send via message tool:
        message(action='send', channel='telegram', target='5766153421',
                message=f"**{alert['title']}**\n\n{alert['message']}")

# Clear queue after sending
open('/tmp/polymarket_alerts_queue.jsonl', 'w').close()
```

**Or via CLI (manual):**
```bash
# View queued alerts
cat /tmp/polymarket_alerts_queue.jsonl | jq -r '"\(.title)\n\(.message)\n"'

# Process manually in OpenClaw session
# (Read queue, send each via message tool, then clear)
```

## Alert Format

**JSON Structure:**
```json
{
  "title": "📈 POSITION OPENED",
  "message": "Market: BTC/USD\nDirection: UP\nEntry Price: $0.327\nSize: $45.50",
  "timestamp": "2026-02-04T22:42:09.401768"
}
```

**Telegram Message:**
```
📈 POSITION OPENED

Market: BTC/USD
Direction: UP
Entry Price: $0.327
Size: $45.50
```

## Files

- `trade_alerts.py` - Main monitor script
- `manage_alerts.sh` - Start/stop/status commands
- `trade_alerts.log` - Monitor output
- `trade_alerts.pid` - Process ID file
- `/tmp/polymarket_alerts_queue.jsonl` - Alert queue (JSONL format)

## Monitoring

```bash
# Check if running
ps aux | grep trade_alerts.py | grep -v grep

# View queue
cat /tmp/polymarket_alerts_queue.jsonl | jq

# Watch in real-time
tail -f trade_alerts.log
```

## Troubleshooting

**Monitor not running:**
```bash
./manage_alerts.sh start
```

**No alerts queued:**
- Check if bot is running and making trades
- View monitor logs: `./manage_alerts.sh logs`
- Check database: `sqlite3 paper_trading.db "SELECT COUNT(*) FROM positions;"`

**Alerts not sending:**
- Queue is write-only by monitor
- Main agent reads queue and sends via message tool
- Queue can be processed manually or via scheduled task
