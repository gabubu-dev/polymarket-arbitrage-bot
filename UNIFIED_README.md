# Unified Polymarket Trading Bot

Multi-instance Polymarket arbitrage trading system with web dashboard.

## Repository Structure

```
polymarket-arbitrage-bot/
├── bots/
│   ├── primary/          # Primary bot instance (originally ~/Stable/polymarket-bot)
│   │   ├── config.json
│   │   └── paper_trading.db
│   └── secondary/        # Secondary bot instance (original repo bot)
│       ├── bot.py
│       ├── bot_paper.py
│       ├── config.json
│       └── paper_trading.db
├── src/                  # Shared core modules
│   ├── config.py
│   ├── position_manager.py
│   ├── risk_manager.py
│   └── database.py
├── scripts/              # Utility scripts from primary bot
│   ├── main.py          # Primary bot main entry
│   ├── telegram_bot.py  # Telegram integration
│   ├── wallet_analyzer.py
│   ├── rate_limiter.py
│   └── ... (all primary bot scripts)
├── ui/                   # Web dashboard
│   ├── frontend/        # React frontend (port 3000)
│   └── backend/         # FastAPI backend (port 8000)
├── run_bot.py           # Unified launcher
└── README.md
```

## Quick Start

### Run Single Instance

```bash
# Primary bot (paper trading)
./run_bot.py primary --mode paper

# Secondary bot (paper trading)
./run_bot.py secondary --mode paper

# Both bots simultaneously
./run_bot.py both --mode paper
```

### Run Web Dashboard

```bash
# Terminal 1: Backend
cd ui/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd ui/frontend && npm run dev

# Access at: http://localhost:3000
```

## Bot Instances

### Primary Bot
- **Location**: `bots/primary/`
- **Features**: Rate limiting, wallet analysis, Telegram integration
- **Database**: `bots/primary/paper_trading.db`
- **Config**: `bots/primary/config.json`

### Secondary Bot
- **Location**: `bots/secondary/`
- **Features**: Spike-based arbitrage, web dashboard integration
- **Database**: `bots/secondary/paper_trading.db`
- **Config**: `bots/secondary/config.json`

## Current Status

**Both bots running in paper trading mode:**
- Primary: Port 8000 (backend only)
- Secondary: Port 3000/8000 (full UI)
- Dashboard: http://fedora.tail747dab.ts.net:3000

## Configuration

Each bot instance has its own `config.json`:

```json
{
  "paper_trading": true,
  "initial_balance": 100,
  "position_size": 50,
  "divergence_threshold": 0.005,
  "min_profit_threshold": 0.01
}
```

## Scripts

All utility scripts from primary bot available in `scripts/`:

- `main.py` - Primary bot entry point
- `telegram_bot.py` - Telegram integration
- `wallet_analyzer.py` - Wallet analysis
- `rate_limiter.py` - API rate limiting
- `monitor-patterns.py` - Pattern monitoring
- `status-mobile.py` - Mobile status CLI
- And more...

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python scripts/tests.py

# Check health
python scripts/doctor.py
```

## Deployment

See `DEPLOYMENT.md` for production deployment instructions.

## License

MIT
