# Polymarket Arbitrage Bot

Automated arbitrage bot that finds and exploits price discrepancies between Polymarket prediction markets and cryptocurrency exchanges.

## Concept

This project is inspired by successful traders who have made hundreds of thousands of dollars by detecting timing gaps between crypto exchange price movements and Polymarket's 15-minute crypto prediction markets.

### How It Works

1. **Monitor Multiple Sources**: Track both Polymarket odds and real-time crypto prices on exchanges (Binance, Coinbase, etc.)
2. **Detect Divergence**: When BTC/ETH makes a significant move on exchanges, Polymarket odds often lag by 30-90 seconds
3. **Execute Trades**: During this window, enter positions at "stale" odds before the market catches up
4. **Risk Management**: Configurable position sizing, stop-losses, and profit targets

## Reference Tweets

- [@the_smart_ape](https://twitter.com/the_smart_ape): "My @Polymarket bot is still running on my Raspberry Pi. 42 trades triggered, 42 wins, 0 losses"
- [@browomo](https://twitter.com/browomo): Detailed analysis of bots making $918,357/month using this strategy
- [@marlowxbt](https://twitter.com/marlowxbt): "One Python bot made $323K by finding the same loophole thousands of times"

## Key Features

- Real-time monitoring of crypto exchange prices via WebSocket
- Polymarket API integration for market data and order execution
- Configurable threshold for price divergence detection
- Position management and automated trade execution
- Logging and analytics for performance tracking
- Raspberry Pi compatible (low resource requirements)

## Technical Stack

- **Language**: Python 3.9+
- **Exchange APIs**: CCXT for unified exchange access
- **Polymarket**: REST API + WebSocket for real-time data
- **Data**: Pandas for analysis, Redis for caching
- **Deployment**: Can run on Raspberry Pi or any Linux server

## Implementation Approach

### Phase 1: Data Collection
```python
# Monitor both sources simultaneously
- Binance/Coinbase WebSocket for BTC/ETH prices
- Polymarket API for 15-minute market odds
- Calculate real-time divergence
```

### Phase 2: Signal Generation
```python
# Detect arbitrage opportunities
- Price moves >X% on exchange
- Polymarket odds haven't adjusted yet
- Window of opportunity detected
```

### Phase 3: Execution
```python
# Execute trades automatically
- Enter position at favorable odds
- Set profit targets (usually market close at $1)
- Implement safety limits and stop-losses
```

### Phase 4: Analytics
```python
# Track performance
- Win rate, profit/loss
- Average hold time
- Market efficiency over time
```

## Risk Considerations

⚠️ **Important Disclaimers:**

- Requires initial capital and API access to both platforms
- Market conditions change; past performance doesn't guarantee future results
- Polymarket has added fees to combat bot activity
- Network latency matters - closer to exchange = better
- Always test with small amounts first

## Getting Started

```bash
# Clone the repository
git clone https://github.com/gabubu-dev/polymarket-arbitrage-bot.git
cd polymarket-arbitrage-bot

# Install dependencies
pip install -r requirements.txt

# Configure your API keys
cp config.example.json config.json
# Edit config.json with your credentials

# Run the bot
python bot.py
```

## Configuration

```json
{
  "exchanges": ["binance", "coinbase"],
  "polymarket_api_key": "YOUR_KEY",
  "divergence_threshold": 0.05,
  "position_size_usd": 100,
  "max_positions": 5,
  "markets": ["BTC_15MIN", "ETH_15MIN"]
}
```

## Monitoring

The bot includes a built-in dashboard for monitoring:
- Active positions
- Win rate and P&L
- Market divergence signals
- Trade history

## Contributing

Contributions welcome! This is an educational project exploring prediction market arbitrage.

## License

MIT License - See LICENSE file for details

## Disclaimer

This software is for educational purposes only. Trading involves risk. The authors are not responsible for any financial losses incurred through use of this software. Always comply with local regulations and platform terms of service.

## Resources

- [Polymarket API Documentation](https://docs.polymarket.com/)
- [CCXT Library](https://github.com/ccxt/ccxt)
- [Prediction Market Arbitrage Research](https://arxiv.org/abs/prediction-markets)

---

**Status**: 🚧 Work in Progress - Contributions welcome!

*Inspired by real-world traders making $300K+ monthly using similar strategies*
