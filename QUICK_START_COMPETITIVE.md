# Quick Start - Competitive Polymarket Bot

**Version:** 3.0 - Competitive Edition  
**Status:** ✅ Production Ready

---

## 🚀 5-Minute Start

### 1. Verify Installation
```bash
cd ~/gabubu-repos/polymarket-arbitrage-bot
python verify_upgrade.py
```

Expected: "🎉 COMPETITIVE UPGRADE VERIFIED!"

### 2. (Optional) Install Bird CLI for Twitter Intelligence
```bash
npm install -g @steipete/bird
bird whoami  # Verify Twitter authentication
```

### 3. Update Configuration
Edit `config.json` and ensure these sections exist:
```json
{
  "market_discovery": { "enabled": true },
  "twitter_intelligence": { "enabled": true },
  "competitive_intelligence": { "enabled": true },
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "6559976977"
  }
}
```

### 4. Run Paper Trading
```bash
source venv/bin/activate
python bot_enhanced.py --mode paper
```

---

## 📊 What to Expect

### Console Output
- ✅ Market Discovery: "Discovered 47 markets across 5 categories"
- ✅ Twitter Intel: "Found 3 new competitive bots"
- ✅ Strategy Adapt: "Adjusted momentum priority: 5 → 6"
- ✅ Opportunities: "High-value opportunity: 'Will Trump win?' (score: 0.847)"

### Telegram Alerts
- 📈 Balance threshold alerts (±10%, ±20%, etc.)
- 🏆 Competitive benchmarking reports
- 🔍 New bot discoveries
- 🔧 Strategy adaptations
- 💎 High-value market opportunities

### Data Files Created
- `data/competitive_intelligence.json` - Discovered bots and strategies
- `data/telegram_alerts_state.json` - Alert state tracking
- `logs/bot.log` - Detailed activity log

---

## 📚 Documentation

**Start Here:**
1. **COMPETITIVE_UPGRADE.md** - Full upgrade documentation
2. **TASK_COMPLETION_SUMMARY.md** - Technical details & completion report
3. **This file** - Quick start guide

---

## 🔍 Key Features

### Real Markets
- Fetches ACTIVE Polymarket markets
- Categories: Politics, Sports, Crypto, Economics, Entertainment
- Filters by volume (>$1000) and liquidity (>$500)

### Competitive Intelligence
- Discovers successful bots on Twitter
- Tracks win rates and strategies
- Benchmarks your performance
- Auto-adapts strategies

### Profit-First
- Ranks by profitability score
- No category restrictions
- Dynamic position sizing
- High-confidence plays

---

## ⚙️ Configuration Tuning

### More Markets
```json
"market_discovery": {
  "min_volume_24h": 500,      // Lower = more markets
  "min_liquidity": 250,       // Lower = more markets
  "max_spread_percent": 10    // Higher = more markets
}
```

### More Intelligence
```json
"twitter_intelligence": {
  "search_interval_hours": 3,  // Search more frequently
  "search_queries": [
    "polymarket bot",
    "polymarket profits",      // Add more queries
    "prediction market strategy"
  ]
}
```

### More Aggressive Trading
```json
"trading": {
  "position_size_usd": 200,    // Larger positions
  "max_positions": 10          // More concurrent positions
}
```

---

## 🐛 Troubleshooting

### "No markets discovered"
- Check Polymarket API is accessible
- Lower `min_volume_24h` in config
- Review logs: `tail -f logs/bot.log`

### "Bird CLI not found"
- Install: `npm install -g @steipete/bird`
- Or disable: `"twitter_intelligence": { "enabled": false }`

### "No Telegram alerts"
- Verify `telegram.bot_token` in config
- Check chat_id is correct (6559976977)
- Test: `curl https://api.telegram.org/bot<TOKEN>/getMe`

### "Import errors"
```bash
pip install -r requirements.txt
python verify_upgrade.py
```

---

## 📈 Success Metrics

**Day 1:**
- ✅ Bot running with real markets
- ✅ 20-50 markets discovered
- ✅ Twitter intelligence active (if enabled)

**Week 1:**
- ✅ 5-10 competitive bots discovered
- ✅ Strategy adaptations based on intel
- ✅ Profitable trades across categories

**Month 1:**
- ✅ 20+ bots tracked
- ✅ Clear competitive ranking
- ✅ Optimized strategy weights

---

## 💡 Tips

1. **Start with paper trading** - Verify everything works before live trading
2. **Monitor Telegram** - Enable alerts to stay informed
3. **Check intelligence daily** - Review `data/competitive_intelligence.json`
4. **Tune gradually** - Start conservative, increase as you gain confidence
5. **Review logs** - `logs/bot.log` has detailed activity

---

## 🎯 Next Steps

1. ✅ Verify installation (`python verify_upgrade.py`)
2. ✅ Update config.json with your settings
3. ✅ Install bird CLI (optional but recommended)
4. ✅ Run paper trading (`python bot_enhanced.py --mode paper`)
5. ✅ Monitor Telegram for 24 hours
6. ✅ Review competitive intelligence data
7. ✅ Adjust configuration based on results
8. 🚀 **Dominate the prediction markets!**

---

**Questions?** Check COMPETITIVE_UPGRADE.md for detailed documentation.

**Issues?** Review TASK_COMPLETION_SUMMARY.md for technical details.

---

*Built by kimi-for-coding for qippu*  
*2026-01-30 - Version 3.0 Competitive Edition*
