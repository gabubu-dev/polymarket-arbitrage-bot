# Auto-Restart Configuration

## Setup Complete (2026-02-05)

All three components now run as systemd user services with automatic restart on failure.

## Services

### Trading Bot
- **Service:** `polymarket-trading-bot.service`
- **Command:** `python bot_paper.py`
- **Logs:** `bot_paper.log`
- **Auto-restart:** Yes (10s delay)

### Backend API
- **Service:** `polymarket-ui-backend.service`
- **Port:** 8000
- **Command:** `python app/main.py`
- **Logs:** `ui/backend.log`
- **Auto-restart:** Yes (10s delay)

### Frontend UI  
- **Service:** `polymarket-ui-frontend.service`
- **Port:** 3000
- **Command:** `npm run dev`
- **Logs:** `ui/frontend.log`
- **Auto-restart:** Yes (10s delay)

## Management Commands

```bash
# Check status (all services)
systemctl --user status polymarket-trading-bot
systemctl --user status polymarket-ui-backend
systemctl --user status polymarket-ui-frontend

# Or check all at once
systemctl --user status polymarket-*

# Restart manually
systemctl --user restart polymarket-trading-bot
systemctl --user restart polymarket-ui-backend
systemctl --user restart polymarket-ui-frontend

# Stop services
systemctl --user stop polymarket-trading-bot polymarket-ui-backend polymarket-ui-frontend

# View logs
journalctl --user -u polymarket-trading-bot -f
journalctl --user -u polymarket-ui-backend -f
journalctl --user -u polymarket-ui-frontend -f

# Or tail log files directly
tail -f bot_paper.log
tail -f ui/backend.log
tail -f ui/frontend.log
```

## Access

- **Frontend:** http://fedora.tail747dab.ts.net:3000
- **Backend API:** http://fedora.tail747dab.ts.net:8000

## Auto-Restart Behavior

Both services will automatically restart:
- On crash/failure
- After 10 seconds delay
- Indefinitely (no retry limit)
- On system boot (enabled)

## Testing Auto-Restart

```bash
# Kill backend to test restart
kill $(systemctl --user show -p MainPID polymarket-ui-backend | cut -d= -f2)

# Kill frontend to test restart  
kill $(systemctl --user show -p MainPID polymarket-ui-frontend | cut -d= -f2)

# Both should restart within 10 seconds
sleep 15 && systemctl --user status polymarket-ui-*
```

## Troubleshooting

If services fail to start:
```bash
# Check logs
journalctl --user -u polymarket-ui-backend --no-pager -n 50
journalctl --user -u polymarket-ui-frontend --no-pager -n 50

# Verify working directories exist
ls -la /home/Gabe/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend
ls -la /home/Gabe/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend

# Check port conflicts
lsof -i :3000
lsof -i :8000
```
