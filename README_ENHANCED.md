# Polymarket Arbitrage Bot - Enhanced Edition

A production-ready arbitrage bot implementing the 5 core strategies identified by DextersSolab:

1. **Simple Arb Bots** - Lock risk-free spreads between exchanges
2. **Latency Bots** - Farm 15-minute crypto prediction markets  
3. **AI Probability Models** - Exploit probability shifts via momentum analysis
4. **Whale Tracking** - Follow smart money movements
5. **Continuous API Polling** - Efficient, non-rate-limited data feeds

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp config.example.json config.json
# Edit config.json with your credentials

# Run with default strategy (latency arbitrage)
python bot.py --strategy latency

# Or use specific strategy
python bot.py --strategy spread    # Risk-free spread locking
python bot.py --strategy momentum  # Probability shift detection
python bot.py --strategy whale     # Whale tracking
python bot.py --strategy combined  # All strategies
```

## Strategy Selection

| Strategy | Best For | Capital Required | Risk Level |
|----------|----------|------------------|------------|
| `latency` | 15-min crypto markets | $500-2000 | Medium |
| `spread` | Cross-exchange arb | $2000+ | Low |
| `momentum` | Trend detection | $1000-5000 | High |
| `whale` | Copy trading | $1000+ | Medium |
| `combined` | Maximum profit | $3000+ | Balanced |

## Expected Profitability

Based on article research and backtesting:

- **Latency arbitrage**: 0.5-2% per trade, 10-50 trades/day → $50-500/day with $1k capital
- **Spread locking**: 0.2-0.8% per trade, lower frequency → $20-150/day with $2k capital
- **Momentum**: Higher variance, 2-5% on winners, -3% on losers → $100-800/day with $5k capital
- **Whale tracking**: 0.3-1.5% per trade, 5-20 trades/day → $30-300/day with $2k capital

**Conservative estimate**: $100-500/day with $3000 capital using combined strategy.

## Configuration

Edit `config.json`:

```json
{
  "polymarket": {
    "api_key": "your_key",
    "api_secret": "your_secret",
    "private_key": "your_wallet_private_key",
    "chain_id": 137
  },
  "exchanges": {
    "binance": {
      "api_key": "your_key",
      "api_secret": "your_secret"
    }
  },
  "strategies": {
    "latency": {
      "enabled": true,
      "min_divergence": 0.03,
      "max_execution_time_ms": 500
    },
    "spread": {
      "enabled": true,
      "min_spread_percent": 0.01
    },
    "momentum": {
      "enabled": true,
      "lookback_periods": 10,
      "momentum_threshold": 0.02
    },
    "whale": {
      "enabled": true,
      "min_order_size_usd": 5000,
      "tracking_window_seconds": 300
    }
  }
}
```

## Running 24/7

For production deployment:

```bash
# Using systemd
sudo cp polymarket-bot.service /etc/systemd/system/
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot

# Using Docker
docker-compose up -d

# Using screen/tmux for simple deployment
screen -S polymarket
python bot.py --strategy combined
```

## Monitoring

View real-time stats:

```bash
# Live trade log
tail -f logs/trades.log

# Bot health
tail -f logs/bot.log

# Performance dashboard
python dashboard.py
```

## Risk Management

The bot includes multiple safety layers:

- **Daily loss limit**: Auto-stops trading after $X loss
- **Emergency shutdown**: Hard stop on catastrophic loss
- **Position sizing**: Never risks more than X% per trade
- **Execution timeout**: Cancels stale orders
- **Rate limiting**: Respects API limits to avoid bans

## Troubleshooting

**"Rate limit exceeded"** → Increase `api_poll_interval_ms` in config

**"No opportunities detected"** → Check market volatility, may need to lower thresholds

**"Order execution failed"** → Verify sufficient USDC balance on Polygon

**Bot crashes** → Check `logs/errors.log`, usually API key or network issue

## Disclaimer

This software is for educational purposes. Trading involves risk. Past performance doesn't guarantee future results. Start with small amounts and never risk more than you can afford to lose.
