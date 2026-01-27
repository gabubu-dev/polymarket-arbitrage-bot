# Quick Start Guide

## Prerequisites

- Python 3.9 or higher
- Polymarket account with API access
- Exchange API keys (Binance, Coinbase, etc.)
- Some capital to trade (start small!)

## Installation

```bash
# Clone the repository
git clone https://github.com/gabubu-dev/polymarket-arbitrage-bot.git
cd polymarket-arbitrage-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example configuration:
```bash
cp config.example.json config.json
```

2. Edit `config.json` with your API credentials:

```json
{
  "polymarket": {
    "api_key": "your_polymarket_api_key",
    "api_secret": "your_polymarket_api_secret",
    "private_key": "your_ethereum_private_key",
    "chain_id": 137
  },
  "exchanges": {
    "binance": {
      "api_key": "your_binance_api_key",
      "api_secret": "your_binance_api_secret",
      "testnet": true
    }
  }
}
```

**Important**: Start with testnet mode enabled to test without risking real funds!

## Running the Bot

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Run the bot
python bot.py
```

You should see output like:
```
2025-01-27 12:00:00 - ArbitrageBot - INFO - Starting Polymarket Arbitrage Bot
2025-01-27 12:00:01 - ArbitrageBot - INFO - Monitoring symbols: ['BTC/USDT', 'ETH/USDT']
2025-01-27 12:00:01 - ExchangeMonitor.binance - INFO - Starting monitor for binance
```

## Testing

Run the test suite to verify everything works:

```bash
pytest tests/ -v
```

## Understanding the Strategy

The bot looks for timing gaps between:
1. **Exchange price movements** - BTC/ETH price changes on Binance/Coinbase
2. **Polymarket market odds** - Prediction market odds on 15-minute crypto markets

When BTC makes a sharp move on an exchange, Polymarket odds often lag by 30-90 seconds. The bot detects this divergence and takes positions at "stale" odds before the market corrects.

### Example Trade Flow

1. BTC price jumps 2% on Binance
2. Bot detects Polymarket "BTC > $50k in 15 min" market still has low odds (0.35)
3. Bot buys YES shares at 0.35
4. Within seconds, other traders update the market to 0.85
5. Bot holds until market resolves (BTC is above $50k) and profits

## Risk Management

The bot includes several safety features:

- **Stop Loss**: Exits if position loses more than 15% (default)
- **Take Profit**: Exits if position gains more than 90% (default)
- **Daily Loss Limit**: Stops trading if daily losses exceed $1,000 (default)
- **Emergency Shutdown**: Hard stop if total losses exceed $5,000
- **Position Limits**: Max 5 concurrent positions by default

Adjust these in `config.json` under `risk_management`.

## Monitoring

The bot logs all activity to:
- **Console**: Color-coded status updates
- **logs/bot.log**: Detailed operational logs
- **logs/trades.log**: All trade entries/exits with P&L

Check your performance:
```bash
tail -f logs/trades.log
```

## Important Notes

1. **Start Small**: Test with minimum position sizes first
2. **Network Latency Matters**: Run the bot on a VPS close to exchange servers
3. **Polymarket Fees**: Currently 2% fee on winning positions
4. **Market Efficiency**: Arbitrage opportunities have decreased as more bots compete
5. **Capital Requirements**: Need funds on both Polymarket and exchanges
6. **Terms of Service**: Ensure your usage complies with platform ToS

## Troubleshooting

### "Client not initialized" error
- Check your Polymarket private key is correctly formatted
- Ensure you have MATIC for gas fees on Polygon network

### No opportunities detected
- Verify exchanges are connected (check logs)
- Lower `divergence_threshold` in config (but be careful!)
- Make sure you're monitoring active 15-minute markets

### Orders not executing
- Check your Polymarket balance
- Verify API permissions are set correctly
- Look for rate limiting messages in logs

## Advanced Usage

### Custom Market Selection

Edit `src/polymarket_client.py` to filter for specific markets:

```python
async def get_crypto_markets(self, asset: str = "BTC", timeframe: str = "15MIN"):
    # Add custom filtering logic here
    pass
```

### Backtesting

Create a backtesting script using historical data:

```python
from src.arbitrage_detector import ArbitrageDetector

detector = ArbitrageDetector()
# Load historical exchange prices and Polymarket odds
# Simulate opportunity detection
```

## Safety Checklist

Before running with real money:

- [ ] Tested on testnet/paper trading
- [ ] Verified all API keys are correct
- [ ] Set conservative position sizes
- [ ] Understood the risks
- [ ] Have stop-loss limits configured
- [ ] Monitoring is set up (alerts/logs)
- [ ] Read and understood platform ToS

## Support

For issues or questions:
- Open an issue on GitHub
- Check logs for detailed error messages
- Review the code - it's well-commented!

## Legal Disclaimer

This software is for educational purposes only. Trading involves significant risk of loss. The authors are not responsible for any financial losses. Always comply with local regulations and platform terms of service.

---

**Happy (safe) trading!**
