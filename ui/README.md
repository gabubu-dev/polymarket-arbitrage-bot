# Polymarket Arbitrage Bot - Web UI

A clean, local-only web interface for monitoring and controlling the Polymarket arbitrage bot.

## Features

### 🎯 Dashboard
- Real-time bot status (running/stopped)
- Performance metrics (Daily, Weekly, All-time P&L)
- Win rate and trade statistics
- System resource monitoring (CPU, memory usage)
- Active position tracking

### ⚙️ Configuration
- Easy configuration of API keys (masked for security)
- Trading parameters (thresholds, position sizes)
- Risk management settings (stop loss, max daily loss)
- Exchange API configuration (Binance, Coinbase)
- Notification settings (webhooks)

### 💰 Trades
- Complete trade history
- Entry/exit prices and P&L per trade
- Trade status tracking (open/closed)
- Auto-refreshing table (every 5 seconds)

### 📝 Logs
- Real-time log viewing
- Configurable number of log lines
- Auto-scroll option
- Color-coded log levels (INFO, WARNING, ERROR)
- Log clearing functionality

### 🔒 Security
- **Localhost only** - Binds to 127.0.0.1 (no external access)
- Sensitive values masked in UI (API keys, secrets)
- No authentication needed (local use only)
- Safe configuration updates (masked values preserved)

## Architecture

```
ui/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   └── main.py         # API endpoints
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # React + Tailwind frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Configuration.jsx
│   │   │   ├── Trades.jsx
│   │   │   └── Logs.jsx
│   │   ├── App.jsx        # Main app component
│   │   ├── main.jsx       # React entry point
│   │   └── index.css      # Tailwind styles
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── start.sh               # Startup script
└── README.md             # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8+ (for backend)
- Node.js 18+ and npm (for frontend)
- The polymarket-arbitrage-bot properly configured

### Backend Setup

1. **Create a Python virtual environment** (optional but recommended):
   ```bash
   cd ui/backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install backend dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. **Install frontend dependencies**:
   ```bash
   cd ui/frontend
   npm install
   ```

### Quick Start

Use the provided startup script to run both backend and frontend:

```bash
cd ui
chmod +x start.sh
./start.sh
```

This will:
- Start the FastAPI backend on http://127.0.0.1:8000
- Start the React frontend on http://127.0.0.1:3000
- Open your browser automatically

**Access the UI**: http://127.0.0.1:3000

### Manual Start

If you prefer to start services manually:

**Terminal 1 - Backend**:
```bash
cd ui/backend
python app/main.py
```

**Terminal 2 - Frontend**:
```bash
cd ui/frontend
npm run dev
```

## API Endpoints

### Configuration
- `GET /api/config` - Get current configuration (with masked secrets)
- `POST /api/config` - Update configuration

### Status & Monitoring
- `GET /api/status` - Get bot status and performance metrics
- `GET /api/trades?limit=50` - Get recent trades
- `GET /api/logs?lines=100` - Get recent log lines

### Control
- `POST /api/control/start` - Start the bot
- `POST /api/control/stop` - Stop the bot
- `POST /api/control/restart` - Restart the bot

### Maintenance
- `DELETE /api/logs` - Clear all log files
- `GET /api/health` - Health check

## Usage Guide

### First Time Setup

1. **Start the UI** using `./start.sh`
2. **Navigate to Configuration tab**
3. **Enter your API credentials**:
   - Polymarket API key, secret, and private key
   - Exchange API keys (Binance, Coinbase)
4. **Configure trading parameters**:
   - Divergence threshold (default: 5%)
   - Min profit threshold (default: 2%)
   - Position size and limits
5. **Set risk management**:
   - Stop loss percentage
   - Max daily loss
   - Emergency shutdown threshold
6. **Click "Save Configuration"**
7. **Go to Dashboard** and click **"Start Bot"**

### Monitoring

- **Dashboard**: Overview of bot performance and status
- **Trades**: Detailed view of all trades with P&L
- **Logs**: Real-time bot activity and debug information

### Starting/Stopping the Bot

- Use the **Start/Stop/Restart** buttons in the header
- Bot status updates automatically every 5 seconds
- System resources (CPU/memory) displayed when running

### Configuration Updates

- Configuration can be updated while bot is running
- Restart the bot for changes to take effect
- Masked values (******) are preserved when saving
- To update a masked value, clear it and enter the new value

## Security Notes

### ✅ Security Features

- **Localhost binding only**: Backend binds to 127.0.0.1, not accessible from network
- **Frontend proxy**: All API calls go through localhost
- **No authentication**: Since it's local-only, no password needed
- **Masked secrets**: API keys shown as `***abc123` in UI
- **Safe updates**: Masked values not overwritten on save

### ⚠️ Security Recommendations

1. **Do NOT expose to public internet**
2. **Run on trusted local machine only**
3. **Use firewall** to block external connections if needed
4. **Keep config.json secure** - it contains unmasked secrets
5. **Don't share screenshots** of the Configuration page

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Try running on different port
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Frontend won't start
```bash
# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Bot won't start from UI
1. Check that `config.json` exists in bot root directory
2. Verify API credentials are correct
3. Check logs for error messages
4. Ensure Python dependencies installed in bot root

### Changes not saving
- Check browser console for errors (F12)
- Verify backend is running (http://127.0.0.1:8000/api/health)
- Check file permissions on config.json

## Development

### Backend Development
```bash
cd backend
# Run with auto-reload
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Development
```bash
cd frontend
# Vite dev server with hot reload
npm run dev
```

### Building for Production
```bash
cd frontend
npm run build
# Output will be in frontend/dist/
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **psutil** - System monitoring
- **python-dotenv** - Environment handling

### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client

## License

Same as parent project (MIT).

## Support

For issues or questions:
1. Check the logs in the Logs tab
2. Verify configuration in Configuration tab
3. Review bot logs at `logs/bot.log`
4. Check backend logs in terminal

---

**Built for local development and monitoring only. Not intended for production deployment.**
