#!/usr/bin/env python3
"""
Modern web dashboard for Polymarket arbitrage bot.
Serves via FastAPI for Tailscale access.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import sys
import json
from pathlib import Path

sys.path.insert(0, 'src')
from market_discovery import PolymarketDiscovery
from paper_trader import PaperTrader

app = FastAPI(title="Polymarket Bot Dashboard")

# Try to load templates
try:
    templates = Jinja2Templates(directory="templates")
except:
    templates = None

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard view."""
    
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Polymarket Bot Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        async function refreshData() {
            try {
                const [markets, stats] = await Promise.all([
                    fetch('/api/markets').then(r => r.json()),
                    fetch('/api/stats').then(r => r.json())
                ]);
                
                document.getElementById('balance').textContent = '$' + stats.balance.toFixed(2);
                document.getElementById('pnl').textContent = (stats.pnl >= 0 ? '+' : '') + '$' + stats.pnl.toFixed(2);
                document.getElementById('pnl').className = 'text-2xl sm:text-3xl font-bold ' + (stats.pnl >= 0 ? 'text-green-400' : 'text-red-400');
                document.getElementById('winrate').textContent = stats.win_rate.toFixed(1) + '%';
                document.getElementById('trades').textContent = stats.total_trades;
                
                const marketsList = document.getElementById('markets');
                if (markets.error) {
                    marketsList.innerHTML = '<div class="text-red-400">Error loading markets</div>';
                    return;
                }
                
                marketsList.innerHTML = markets.slice(0, 10).map(function(m, i) {
                    const yesPrice = m.outcome_prices && m.outcome_prices[0] ? (m.outcome_prices[0] * 100).toFixed(1) : '0.0';
                    const noPrice = m.outcome_prices && m.outcome_prices[1] ? (m.outcome_prices[1] * 100).toFixed(1) : '0.0';
                    const spread = (m.spread * 100).toFixed(2);
                    const volume = m.volume_24h ? m.volume_24h.toLocaleString() : '0';
                    const score = m.profitability_score ? m.profitability_score.toFixed(3) : '0.000';
                    
                    return '<div class="border-b border-gray-700 py-3 sm:py-4">' +
                        '<div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">' +
                            '<div class="flex-1 min-w-0">' +
                                '<h3 class="font-semibold text-white text-sm sm:text-base truncate">' + (i+1) + '. ' + m.question + '</h3>' +
                                '<div class="mt-2 space-y-1 text-xs sm:text-sm">' +
                                    '<div class="flex flex-wrap gap-x-3 gap-y-1">' +
                                        '<span class="text-gray-400">Current:</span>' +
                                        '<span class="text-green-400">YES: ' + yesPrice + '%</span>' +
                                        '<span class="text-red-400">NO: ' + noPrice + '%</span>' +
                                    '</div>' +
                                    '<div class="flex flex-wrap gap-x-3 gap-y-1">' +
                                        '<span class="text-gray-400">Spread:</span>' +
                                        '<span class="text-blue-400">' + spread + '%</span>' +
                                        '<span class="text-gray-400">Vol:</span>' +
                                        '<span class="text-yellow-400">$' + volume + '</span>' +
                                    '</div>' +
                                '</div>' +
                            '</div>' +
                            '<div class="text-left sm:text-right mt-2 sm:mt-0">' +
                                '<div class="text-xl sm:text-2xl font-bold text-purple-400">' + score + '</div>' +
                                '<div class="text-xs text-gray-400">Score</div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }).join('');
            } catch (e) {
                console.error('Error refreshing data:', e);
            }
        }
        
        setInterval(refreshData, 5000);
        refreshData();
    </script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <div class="container mx-auto px-3 sm:px-4 py-4 sm:py-8 max-w-6xl">
        <div class="mb-4 sm:mb-8">
            <h1 class="text-2xl sm:text-4xl font-bold text-white mb-1 sm:mb-2">📊 Polymarket Trading Bot</h1>
            <p class="text-sm sm:text-base text-gray-400">Paper Trading Mode - Real-time market opportunities</p>
        </div>
        
        <!-- Stats Cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4 mb-4 sm:mb-8">
            <div class="bg-gray-800 rounded-lg p-3 sm:p-6">
                <div class="text-gray-400 text-xs sm:text-sm mb-1">Balance</div>
                <div id="balance" class="text-xl sm:text-3xl font-bold text-green-400">$10,000</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 sm:p-6">
                <div class="text-gray-400 text-xs sm:text-sm mb-1">P&L</div>
                <div id="pnl" class="text-xl sm:text-3xl font-bold text-blue-400">$0.00</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 sm:p-6">
                <div class="text-gray-400 text-xs sm:text-sm mb-1">Win Rate</div>
                <div id="winrate" class="text-xl sm:text-3xl font-bold text-purple-400">0%</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-3 sm:p-6">
                <div class="text-gray-400 text-xs sm:text-sm mb-1">Trades</div>
                <div id="trades" class="text-xl sm:text-3xl font-bold text-yellow-400">0</div>
            </div>
        </div>
        
        <!-- Markets List -->
        <div class="bg-gray-800 rounded-lg p-3 sm:p-6">
            <h2 class="text-lg sm:text-2xl font-bold text-white mb-3 sm:mb-4">🎯 Top Trading Opportunities</h2>
            <div id="markets" class="space-y-2 sm:space-y-4">
                <div class="text-gray-400">Loading markets...</div>
            </div>
        </div>
        
        <div class="mt-4 sm:mt-8 text-center text-gray-500 text-xs sm:text-sm">
            Auto-refreshes every 5 seconds
        </div>
    </div>
</body>
</html>
    """
    
    return HTMLResponse(content=html)

@app.get("/api/markets")
async def get_markets():
    """Get current market opportunities."""
    try:
        config = json.load(open('config.json'))
        md = PolymarketDiscovery(config)
        markets = md.fetch_active_markets(force_refresh=False)
        
        # Get unique markets only
        seen = set()
        unique = []
        for m in markets:
            if m.question not in seen:
                seen.add(m.question)
                unique.append(m.to_dict())
        
        return unique[:20]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """Get paper trading stats."""
    try:
        paper_trader = PaperTrader(
            initial_balance=10000,
            data_dir="data",
            enable_realism=True
        )
        
        stats = paper_trader.get_performance_stats()
        
        return {
            "balance": stats['current_balance'],
            "pnl": stats['total_pnl'],
            "win_rate": stats['win_rate'],
            "total_trades": stats['total_trades'],
            "sharpe": stats.get('sharpe_ratio', 0)
        }
    except Exception as e:
        return {
            "balance": 10000,
            "pnl": 0,
            "win_rate": 0,
            "total_trades": 0,
            "sharpe": 0
        }

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting Polymarket Bot Dashboard")
    print("=" * 60)
    print()
    print("Dashboard will be available at:")
    print("  • Local: http://localhost:8080")
    print("  • Tailscale: http://<tailscale-hostname>:8080")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
