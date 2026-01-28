# Quick Start Guide - Web UI

## 🚀 One-Line Start

```bash
cd ui && ./start.sh
```

That's it! The script will:
1. Install all dependencies (first time only)
2. Start the backend on http://127.0.0.1:8000
3. Start the frontend on http://127.0.0.1:3000
4. Open your browser automatically

## 📋 First Time Setup Checklist

1. **Start the UI**: `./start.sh`
2. **Open**: http://127.0.0.1:3000
3. **Go to Configuration tab**
4. **Enter your API keys**:
   - Polymarket credentials
   - Exchange API keys (Binance/Coinbase)
5. **Set trading parameters**:
   - Divergence threshold: 5%
   - Min profit: 2%
   - Position size: $100
6. **Configure risk limits**:
   - Stop loss: 15%
   - Max daily loss: $1000
7. **Save Configuration**
8. **Click "Start Bot"** in Dashboard

## 🎯 What You Can Do

### Dashboard
- Monitor real-time P&L (daily/weekly/all-time)
- See bot status and uptime
- Track open positions
- View system resources

### Configuration
- Update API keys (masked for security)
- Adjust trading parameters
- Set risk management rules
- Enable notifications

### Trades
- View complete trade history
- See entry/exit prices
- Track P&L per trade
- Filter by status

### Logs
- Real-time log viewing
- Color-coded by severity
- Auto-scroll option
- Clear logs button

## 🛑 Stopping

Press `Ctrl+C` in the terminal to stop both services.

## 🔧 Troubleshooting

**Port already in use?**
```bash
# Kill existing processes
lsof -i :8000
lsof -i :3000
```

**Dependencies not installing?**
```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

**Bot won't start?**
- Ensure config.json exists in bot root
- Check API credentials are correct
- View logs in Logs tab

## 📚 Full Documentation

See [README.md](README.md) for complete documentation.
