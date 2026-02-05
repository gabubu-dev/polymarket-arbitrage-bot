#!/bin/bash
# Restart Polymarket Paper Trading Bot with fixes applied

set -e

cd "$(dirname "$0")"

echo "🔧 Polymarket Bot Restart Script"
echo "================================="
echo ""

# Stop any existing bot process
echo "🛑 Stopping existing bot processes..."
pkill -f "bot_paper.py" || echo "  No bot process found"
sleep 2

# Clear old logs to start fresh
echo "🧹 Archiving old logs..."
mkdir -p logs/archive
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
[ -f paper_bot_live.log ] && mv paper_bot_live.log logs/archive/paper_bot_live_${TIMESTAMP}.log
[ -f logs/bot.log ] && mv logs/bot.log logs/archive/bot_${TIMESTAMP}.log
[ -f logs/trades.log ] && mv logs/trades.log logs/archive/trades_${TIMESTAMP}.log
echo "  ✅ Logs archived"

# Show current config
echo ""
echo "📋 Current Configuration:"
echo "  Max Positions: $(jq -r '.trading.max_positions' config.json)"
echo "  Divergence Threshold: $(jq -r '.trading.divergence_threshold' config.json)"
echo "  Min Profit: $(jq -r '.trading.min_profit_threshold' config.json)"
echo "  Position Size: $$(jq -r '.trading.position_size_usd' config.json)"
echo ""

# Start bot
echo "🚀 Starting paper trading bot..."
echo "  Log: paper_bot_live.log"
echo "  Press Ctrl+C to stop the bot"
echo ""
echo "Monitor with: tail -f paper_bot_live.log"
echo "Watch trades: tail -f logs/trades.log"
echo ""

# Run bot
python bot_paper.py 2>&1 | tee paper_bot_live.log
