# Polymarket Trading Bot with Analytics Dashboard

A unified trading bot for Polymarket prediction markets with automated trading execution, comprehensive analytics, and a web-based dashboard for real-time monitoring.

## Features

### Trading Features
- **Arbitrage Detection**: Detect price divergences between exchanges and Polymarket
- **Position Management**: Automated position entry, exit, and P&L tracking
- **Risk Management**: Stop-loss, take-profit, daily loss limits, emergency shutdown
- **Whale Tracking**: Monitor large orders and smart money movements
- **Probability Shift Detection**: AI-inspired momentum analysis
- **Continuous Polling**: Efficient API feeds with rate limiting and circuit breakers

### Analytics Features
- **Market Visualization**: Interactive Plotly charts for price history, volume, sentiment
- **Sentiment Tracking**: Analyze market sentiment through volume and price momentum
- **Historical Analysis**: Pattern detection, volatility analysis, trend identification
- **Wallet Tracking**: Monitor wallet performance and identify successful strategies
- **Web Dashboard**: Real-time monitoring via Flask web interface

## Architecture

```
polymarket-arbitrage-bot/
├── bot.py                    # Basic trading bot (CLI)
├── bot_enhanced.py           # Enhanced bot with all strategies
├── dashboard.py              # Flask web dashboard server
├── src/
│   ├── arbitrage_detector.py # Arbitrage opportunity detection
│   ├── position_manager.py   # Position management and execution
│   ├── risk_manager.py       # Risk controls
│   ├── polymarket_client.py  # Polymarket API client
│   ├── polling.py            # Continuous API polling
│   ├── probability_shifts.py # Momentum analysis
│   ├── whale_tracker.py      # Whale activity tracking
│   ├── wallet_tracker.py     # Wallet performance analysis
│   ├── sentiment_tracker.py  # Market sentiment analysis
│   ├── historical_analyzer.py # Historical data analysis
│   ├── visualization.py      # Plotly chart generation
│   ├── exchange_monitor.py   # Exchange price monitoring
│   ├── strategy_orchestrator.py # Strategy coordination
│   ├── latency_arbitrage.py  # Latency arbitrage engine
│   ├── utils.py              # Utility functions
│   └── config.py             # Configuration management
├── templates/
│   └── dashboard.html        # Web dashboard template
├── tests/                    # Unit tests
├── config.example.json       # Example configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip
- (Optional) Polymarket API credentials for live trading

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd polymarket-arbitrage-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the bot:
```bash
cp config.example.json config.json
# Edit config.json with your settings and API credentials
```

4. Create necessary directories:
```bash
mkdir -p data logs
```

## Usage

### Running the Trading Bot (CLI Mode)

#### Basic Bot
```bash
python bot.py
```

#### Enhanced Bot with Strategies
```bash
# Run all strategies
python bot_enhanced.py

# Run specific strategy
python bot_enhanced.py --strategy latency      # 15-min market latency arbitrage
python bot_enhanced.py --strategy spread       # Risk-free spread locking
python bot_enhanced.py --strategy momentum     # Probability shift detection
python bot_enhanced.py --strategy whale        # Whale tracking
python bot_enhanced.py --strategy combined     # All strategies (default)
```

#### Production Mode
```bash
# Run with auto-restart
python bot_enhanced.py --production

# Enable health checks
python bot_enhanced.py --health-check-interval 60
```

### Launching the Web Dashboard

#### Quick Start
```bash
# Start dashboard on default port (8080)
python dashboard.py

# Start with custom port
python dashboard.py --port 8080

# Start with mock data for demonstration
python dashboard.py --mock

# Enable debug mode
python dashboard.py --debug
```

#### Production Deployment
```bash
# Using Gunicorn (install separately: pip install gunicorn)
gunicorn -w 4 -b 127.0.0.1:8080 dashboard:app
```

Access the dashboard at: http://127.0.0.1:8080

### API Endpoints

The dashboard provides a REST API for accessing data:

- `GET /api/status` - Bot status and components
- `GET /api/positions` - Current positions
- `GET /api/trades?limit=50` - Recent trades
- `GET /api/pnl` - P&L history and performance
- `GET /api/opportunities` - Arbitrage opportunities
- `GET /api/whales` - Whale activity
- `GET /api/market/<slug>` - Market analysis
- `GET /api/wallet/<address>` - Wallet analysis
- `GET /api/dashboard` - Full dashboard data
- `POST /api/update` - Update dashboard with bot data

Chart endpoints:
- `GET /api/charts/portfolio` - Portfolio overview chart
- `GET /api/charts/trading` - Trading activity chart
- `GET /api/charts/whales` - Whale activity chart
- `GET /api/charts/arbitrage` - Arbitrage opportunities chart

## Configuration

Edit `config.json` to customize:

### API Settings
```json
{
  "api": {
    "base_url": "https://clob.polymarket.com",
    "rate_limit": 10,
    "timeout": 30
  }
}
```

### Trading Parameters
```json
{
  "trading": {
    "max_positions": 5,
    "position_size_usd": 100,
    "enabled": false
  },
  "arbitrage": {
    "divergence_threshold": 0.05,
    "min_profit_threshold": 0.02
  }
}
```

### Risk Management
```json
{
  "risk": {
    "stop_loss_percentage": 0.15,
    "take_profit_percentage": 0.90,
    "max_daily_loss_usd": 1000.0,
    "emergency_shutdown_loss_usd": 5000.0
  }
}
```

### Dashboard Settings
```json
{
  "dashboard": {
    "host": "127.0.0.1",
    "port": 8080,
    "refresh_interval": 30,
    "theme": "plotly_dark"
  }
}
```

## Programmatic Usage

### Using Individual Components

```python
from src.polymarket_client import PolymarketClient
from src.sentiment_tracker import SentimentTracker
from src.visualization import MarketVisualizer

# Initialize components
client = PolymarketClient()
tracker = SentimentTracker()
viz = MarketVisualizer()

# Analyze market sentiment
sentiment = tracker.analyze_market("will-bitcoin-reach-100k")
print(f"Sentiment: {sentiment['overall_sentiment']}")

# Create visualization
fig = viz.plot_sentiment_dashboard("market-slug", sentiment, price_data)
fig.show()
```

### Wallet Analysis

```python
from src.wallet_tracker import WalletTracker

tracker = WalletTracker()

# Track wallet performance
performance = tracker.calculate_performance("0x1234...", days=30)
print(f"Win rate: {performance.get('win_rate', 0):.2%}")

# Compare multiple wallets
comparison = tracker.compare_wallets(["0x1234...", "0x5678..."])
```

### Historical Analysis

```python
from src.historical_analyzer import HistoricalAnalyzer

analyzer = HistoricalAnalyzer()

# Analyze market history
analysis = analyzer.analyze_market_history("market-slug", days=30)
print(f"Volatility: {analysis['volatility']:.4f}")

# Find patterns
patterns = analyzer.find_patterns("market-slug")
for pattern in patterns['patterns']:
    print(f"Pattern: {pattern['type']} - {pattern['description']}")
```

### Integrating Dashboard with Bot

```python
import requests

# Update dashboard with bot data
bot_data = {
    'bot_running': True,
    'positions': [...],
    'trades': [...],
    'pnl_history': [...],
    'performance_stats': {...}
}

requests.post('http://127.0.0.1:8080/api/update', json=bot_data)
```

## Docker Deployment

### Using Docker Compose
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Docker Build
```bash
# Build image
docker build -t polymarket-bot .

# Run container
docker run -p 8080:8080 -v $(pwd)/config.json:/app/config.json polymarket-bot
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_arbitrage_detector.py
```

## Development

### Code Style
```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

## Monitoring

### Health Checks
The bot provides health check endpoints for monitoring:
```bash
curl http://127.0.0.1:8080/api/status
```

### Logging
Logs are written to:
- `logs/bot.log` - General bot activity
- `logs/trades.log` - Trade execution log
- `logs/errors.log` - Error log

## Security Notes

1. **API Keys**: Store API keys in `config.json` or environment variables, never commit them
2. **Private Keys**: Use environment variables for private keys: `export POLYMARKET_PRIVATE_KEY=...`
3. **Dashboard**: Use a firewall/reverse proxy if exposing dashboard to the internet
4. **Rate Limits**: Respect Polymarket's API rate limits to avoid bans

## Troubleshooting

### Bot won't start
- Check `config.json` exists and is valid JSON
- Verify API credentials are correct
- Check logs in `logs/errors.log`

### Dashboard shows no data
- Run `python dashboard.py --mock` to test with sample data
- Ensure bot is running and sending updates to `/api/update`
- Check browser console for JavaScript errors

### Rate limit errors
- Increase `rate_limit` in config
- Enable caching with `"enable_caching": true`
- Use adaptive rate limiting strategy

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. Trading prediction markets involves significant risk. Always:
- Do your own research
- Never risk more than you can afford to lose
- Test thoroughly with small amounts before scaling
- Monitor positions actively

The authors are not responsible for any losses incurred through use of this software.

## Acknowledgments

- Polymarket API documentation
- DextersSolab for trading strategy insights
- Community contributors
- Open source prediction market researchers
