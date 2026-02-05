# Polymarket Bot Web UI - Deployment Info

## 🌐 Access URLs

**Primary Access (Tailscale IP):**
- Frontend: http://100.89.126.70:3000
- Backend API: http://100.89.126.70:8000
- API Docs: http://100.89.126.70:8000/docs

**Local Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

**Tailscale Hostname:** fedora.tail747dab.ts.net

## 🔄 Service Management

### Check Status
```bash
# Check if services are running
lsof -i :3000    # Frontend
lsof -i :8000    # Backend

# Check PIDs
cat ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend/frontend.pid
cat ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend/backend.pid
```

### Start Services (if stopped)
```bash
# Start backend
cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend
nohup python app/main.py > backend.log 2>&1 &
echo $! > backend.pid

# Wait for backend to be ready
sleep 3

# Start frontend
cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend
nohup npm run dev > frontend.log 2>&1 &
echo $! > frontend.pid
```

### Stop Services
```bash
# Stop frontend
kill $(cat ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend/frontend.pid)

# Stop backend
kill $(cat ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend/backend.pid)
```

### Restart Services
```bash
# Stop both
kill $(cat ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend/frontend.pid)
kill $(cat ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend/backend.pid)

# Wait a moment
sleep 2

# Start backend
cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend
nohup python app/main.py > backend.log 2>&1 &
echo $! > backend.pid

sleep 3

# Start frontend
cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend
nohup npm run dev > frontend.log 2>&1 &
echo $! > frontend.pid
```

### View Logs
```bash
# Backend logs
tail -f ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/backend/backend.log

# Frontend logs
tail -f ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/ui/frontend/frontend.log
```

## 📊 Current Status

**Deployment Date:** 2026-02-04 21:09 EST

**Backend:**
- Process ID: 588149
- Port: 8000
- Status: Running ✓
- Host: 0.0.0.0 (accessible via Tailscale)

**Frontend:**
- Process ID: 588255
- Port: 3000
- Status: Running ✓
- Host: 0.0.0.0 (accessible via Tailscale)

## 🎨 UI Features

The web UI provides:

1. **Dashboard Tab**
   - Real-time P&L tracking (daily/weekly/all-time)
   - Bot status and uptime
   - Open positions monitor
   - System resource usage (CPU, memory)

2. **Configuration Tab**
   - Polymarket API credentials (masked for security)
   - Exchange API keys (Binance, Coinbase)
   - Trading parameters (divergence threshold, min profit, position size)
   - Risk management settings (stop loss, max daily loss)
   - Notification settings

3. **Trades Tab**
   - Complete trade history
   - Entry/exit prices
   - P&L per trade
   - Status filtering

4. **Logs Tab**
   - Real-time log viewing
   - Color-coded by severity
   - Auto-scroll option
   - Clear logs functionality

## 🔧 Configuration

### Modified Files for Tailscale Access

**backend/app/main.py:**
- Changed `host="127.0.0.1"` → `host="0.0.0.0"`
- Added CORS origin: `http://fedora.tail747dab.ts.net:3000`

**frontend/vite.config.js:**
- Changed `host: '127.0.0.1'` → `host: '0.0.0.0'`

**backend/requirements.txt:**
- Upgraded pydantic to >=2.11.0 for Python 3.14 compatibility

## ⚠️ Notes

- UI expects bot configuration at `~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/config.json`
- Backend can start/stop the main bot process
- Logs are stored in `~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/logs/`
- No authentication configured - secured via Tailscale network only

## 🧪 Testing

Services were verified accessible via:
- ✓ Local curl (localhost:3000, localhost:8000)
- ✓ Tailscale IP curl (100.89.126.70:3000, 100.89.126.70:8000)
- ✓ Health check endpoint responding
- ✓ Frontend serving HTML
