# Quick Start Guide - Enhanced Polymarket Arbitrage Bot

This guide will get you up and running with the enhanced arbitrage bot in under 10 minutes.

## Prerequisites

- Python 3.9 or higher
- $500+ USDC on Polygon network
- API keys for Polymarket and at least one exchange (Binance recommended)
- (Optional) VPS or dedicated server for 24/7 operation

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd polymarket-arbitrage-bot
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp config.example.json config.json
# Edit config.json with your API keys
```

Required API keys:
- **Polymarket**: API key + wallet private key
- **Exchange**: Binance or Coinbase API key

### 3. Fund Your Wallets

- Deposit USDC to your Polymarket wallet on Polygon
- Deposit funds to your exchange account
- Start with small amounts ($100-500) for testing

## Running the Bot

### Quick Start - Single Strategy

```bash
# Latency arbitrage (recommended for beginners)
python bot_enhanced.py --strategy latency

# Risk-free spread locking
python bot_enhanced.py --strategy spread

# Probability shift detection
python bot_enhanced.py --strategy momentum

# Whale tracking
python bot_enhanced.py --strategy whale
```

### Combined Strategy (All Strategies)

```bash
python bot_enhanced.py --strategy combined
```

### Check Expected Profitability

```bash
# See what you could earn
python profitability.py --capital 1000 --strategy combined

# Compare all strategies
python profitability.py --capital 2000 --compare
```

### Monitor Performance

```bash
# In a separate terminal
python dashboard.py
```

## Strategy Selection Guide

| Your Situation | Recommended Strategy | Why |
|----------------|---------------------|-----|
| New to arbitrage | `latency` | Most reliable, clear edge |
| Low risk tolerance | `spread` | Risk-free when executed properly |
| High volatility markets | `momentum` | Captures large moves |
| Following smart money | `whale` | Copy successful traders |
| Maximize profit | `combined` | Diversified approach |

## Production Deployment

### Option 1: Systemd (Linux)

```bash
# Edit the service file with your paths
sudo cp polymarket-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot

# Check status
sudo systemctl status polymarket-bot
sudo journalctl -u polymarket-bot -f
```

### Option 2: Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f polymarket-bot

# With monitoring (Grafana + Prometheus)
docker-compose --profile monitoring up -d
```

### Option 3: Screen/Tmux (Simple)

```bash
# Using screen
screen -S polymarket
python bot_enhanced.py --strategy combined
# Ctrl+A, D to detach

# Reattach
screen -r polymarket
```

## Configuration Tuning

### For Conservative Trading (Lower Risk)

Edit `config.json`:
```json
{
  "trading": {
    "position_size_usd": 50,
    "max_positions": 3
  },
  "risk_management": {
    "max_daily_loss_usd": 200,
    "stop_loss_percentage": 0.10
  }
}
```

### For Aggressive Trading (Higher Returns)

```json
{
  "trading": {
    "position_size_usd": 200,
    "max_positions": 10
  },
  "risk_management": {
    "max_daily_loss_usd": 2000,
    "stop_loss_percentage": 0.20
  }
}
```

## Troubleshooting

### "Rate limit exceeded"

Increase polling intervals in config:
```json
"api_polling": {
  "polymarket_interval_ms": 500,
  "exchange_interval_ms": 200
}
```

### "No opportunities detected"

- Check market volatility (need price movement)
- Lower divergence threshold temporarily
- Verify exchange connection is working

### "Order execution failed"

- Verify sufficient USDC balance
- Check Polymarket wallet is connected
- Ensure you're on Polygon network

### Bot crashes

Check logs:
```bash
tail -f logs/errors.log
tail -f logs/bot.log
```

## Safety Checklist

Before going live:

- [ ] Tested with small amounts ($50-100)
- [ ] Verified all API keys work
- [ ] Confirmed wallet has sufficient USDC + MATIC for gas
- [ ] Set appropriate stop losses
- [ ] Set daily loss limits
- [ ] Started with `--strategy latency` (safest)
- [ ] Monitoring dashboard running
- [ ] Alerts configured (Discord/Telegram)

## Expected First Week

| Day | Expected Activity |
|-----|-------------------|
| 1-2 | Bot learning patterns, few trades |
| 3-4 | Increasing activity as it adapts |
| 5-7 | Full operation, evaluate performance |

## Next Steps

1. **Monitor for 1 week** - Validate performance vs estimates
2. **Adjust position sizing** - Based on actual results
3. **Add more capital** - Scale up gradually
4. **Consider VPS** - For 24/7 operation
5. **Review logs weekly** - Optimize parameters

## Getting Help

- Check `logs/errors.log` for error messages
- Review `README_ENHANCED.md` for detailed docs
- Verify configuration with `config.example.json`

## Disclaimer

Trading involves risk. Start small, never risk more than you can afford to lose, and monitor performance regularly.