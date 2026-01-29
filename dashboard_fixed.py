#!/usr/bin/env python3
"""Dashboard with REAL Polymarket data integration"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import json
import requests
from datetime import datetime, timedelta
import time

app = Flask(__name__, template_folder='templates')
CORS(app)

# Cache for API data
CACHE = {
    'markets': {'data': None, 'timestamp': 0},
    'stats': {'data': None, 'timestamp': 0}
}
CACHE_TTL = 30  # 30 seconds

def get_polymarket_markets(limit=50):
    """Fetch real markets from Gamma API with caching"""
    now = time.time()
    
    # Return cached data if still valid
    if CACHE['markets']['data'] and (now - CACHE['markets']['timestamp']) < CACHE_TTL:
        return CACHE['markets']['data']
    
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"active": "true", "limit": limit}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            markets = response.json()
            CACHE['markets'] = {'data': markets, 'timestamp': now}
            return markets
        else:
            print(f"❌ Gamma API error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching markets: {e}")
        return []

def calculate_arbitrage_opportunities(markets):
    """Find arbitrage opportunities in real markets"""
    opportunities = []
    
    for market in markets:
        try:
            # Skip if no tokens or volume too low
            if 'tokens' not in market or market.get('volumeNum', 0) < 1000:
                continue
            
            tokens = market['tokens']
            if len(tokens) < 2:
                continue
            
            # Get YES and NO prices
            yes_price = None
            no_price = None
            
            for token in tokens:
                outcome = token.get('outcome', '').lower()
                price = float(token.get('price', 0))
                
                if 'yes' in outcome:
                    yes_price = price
                elif 'no' in outcome:
                    no_price = price
            
            # Check for arbitrage (prices should sum to ~$1.00)
            if yes_price and no_price:
                total = yes_price + no_price
                discrepancy = abs(1.0 - total)
                
                # If discrepancy > 2%, it's an opportunity
                if discrepancy > 0.02:
                    profit_pct = discrepancy * 100
                    opportunities.append({
                        'market': market['question'][:50],
                        'yes_price': yes_price,
                        'no_price': no_price,
                        'profit_pct': profit_pct,
                        'volume': market.get('volumeNum', 0)
                    })
        except Exception as e:
            continue
    
    # Sort by profit potential
    opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
    return opportunities[:10]

def get_whale_activity(markets):
    """Extract whale activity from market data"""
    whale_markets = []
    
    for market in markets:
        volume = market.get('volumeNum', 0)
        liquidity = market.get('liquidityNum', 0)
        
        # Consider "whale markets" as those with high volume
        if volume > 50000:  # $50k+ volume
            whale_markets.append({
                'market': market['question'][:40],
                'volume': volume,
                'liquidity': liquidity
            })
    
    # Sort by volume and take top 5
    whale_markets.sort(key=lambda x: x['volume'], reverse=True)
    return whale_markets[:5]

# Mock data for charts (portfolio stays mock for now)
def get_portfolio_chart():
    return {
        "data": [
            {"x": [0, 1, 2, 3, 4, 5], "y": [10000, 10100, 10050, 10200, 10300, 10250], "type": "scatter", "name": "Balance", "line": {"color": "#00ff88"}},
        ],
        "layout": {
            "title": "Portfolio Balance Over Time",
            "xaxis": {"title": "Days"},
            "yaxis": {"title": "Balance ($)"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 50, "r": 50, "t": 50, "b": 50}
        }
    }

def get_trading_chart():
    """Real trading activity chart from market volumes"""
    markets = get_polymarket_markets(20)
    
    if not markets:
        # Fallback to mock data
        return {
            "data": [
                {"x": ["No Data"], "y": [0], "type": "bar", "name": "Volume", "marker": {"color": "#00ff88"}},
            ],
            "layout": {
                "title": "Trading Volume by Market",
                "xaxis": {"title": "Market"},
                "yaxis": {"title": "Volume ($)"},
                "paper_bgcolor": "#1a1a2e",
                "plot_bgcolor": "#16213e",
                "font": {"color": "#eee"},
                "margin": {"l": 50, "r": 50, "t": 50, "b": 100}
            }
        }
    
    # Get top 5 by volume
    markets.sort(key=lambda x: x.get('volumeNum', 0), reverse=True)
    top_markets = markets[:5]
    
    labels = [m['question'][:30] + "..." for m in top_markets]
    volumes = [m.get('volumeNum', 0) for m in top_markets]
    
    return {
        "data": [
            {"x": labels, "y": volumes, "type": "bar", "name": "Volume", "marker": {"color": "#00ff88"}},
        ],
        "layout": {
            "title": "Top Markets by Volume (REAL DATA)",
            "xaxis": {"title": "Market", "tickangle": -45},
            "yaxis": {"title": "Volume ($)"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 50, "r": 50, "t": 50, "b": 150}
        }
    }

def get_whale_chart():
    """Real whale activity chart"""
    markets = get_polymarket_markets(30)
    whale_data = get_whale_activity(markets)
    
    if not whale_data:
        return {
            "data": [
                {"x": ["No Data"], "y": [0], "type": "bar", "name": "Whale Orders", "marker": {"color": "#667eea"}},
            ],
            "layout": {
                "title": "Whale Activity by Market",
                "xaxis": {"title": "Market"},
                "yaxis": {"title": "Volume ($)"},
                "paper_bgcolor": "#1a1a2e",
                "plot_bgcolor": "#16213e",
                "font": {"color": "#eee"},
                "margin": {"l": 50, "r": 50, "t": 50, "b": 100}
            }
        }
    
    labels = [w['market'] for w in whale_data]
    volumes = [w['volume'] for w in whale_data]
    
    return {
        "data": [
            {"x": labels, "y": volumes, "type": "bar", "name": "Whale Volume", "marker": {"color": "#667eea"}},
        ],
        "layout": {
            "title": "Whale Activity (Volume > $50k) - REAL DATA",
            "xaxis": {"title": "Market", "tickangle": -45},
            "yaxis": {"title": "Volume ($)"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 50, "r": 50, "t": 50, "b": 150}
        }
    }

def get_arbitrage_chart():
    """Real arbitrage opportunities chart"""
    markets = get_polymarket_markets(50)
    opportunities = calculate_arbitrage_opportunities(markets)
    
    if not opportunities:
        return {
            "data": [
                {"x": ["No Opportunities"], "y": [0], "type": "bar", "name": "Profit %", "marker": {"color": "#f093fb"}},
            ],
            "layout": {
                "title": "Arbitrage Opportunities",
                "xaxis": {"title": "Opportunity"},
                "yaxis": {"title": "Potential Profit (%)"},
                "paper_bgcolor": "#1a1a2e",
                "plot_bgcolor": "#16213e",
                "font": {"color": "#eee"},
                "margin": {"l": 50, "r": 50, "t": 50, "b": 100}
            }
        }
    
    # Take top 5 opportunities
    top_opps = opportunities[:5]
    labels = [o['market'] for o in top_opps]
    profits = [o['profit_pct'] for o in top_opps]
    
    return {
        "data": [
            {"x": labels, "y": profits, "type": "bar", "name": "Profit %", "marker": {"color": "#f093fb"}},
        ],
        "layout": {
            "title": "Top Arbitrage Opportunities - REAL DATA",
            "xaxis": {"title": "Market", "tickangle": -45},
            "yaxis": {"title": "Potential Profit (%)"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 50, "r": 50, "t": 50, "b": 150}
        }
    }

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/dashboard')
def api_dashboard():
    """Main dashboard stats with REAL market data"""
    markets = get_polymarket_markets(50)
    opportunities = calculate_arbitrage_opportunities(markets)
    
    # Calculate real stats
    total_volume = sum(m.get('volumeNum', 0) for m in markets)
    active_markets = len(markets)
    avg_volume = total_volume / active_markets if active_markets > 0 else 0
    
    return jsonify({
        "status": {
            "bot_running": False,
            "paper_trading": {
                "enabled": True,
                "virtual_balance": 10250,
                "initial_balance": 10000
            },
            "data_source": "LIVE POLYMARKET API ✅"
        },
        "summary": {
            "open_positions": active_markets,
            "total_pnl": 250.00,  # Still mock for paper trading
            "opportunities": len(opportunities),
            "total_market_volume": f"${total_volume:,.0f}",
            "avg_market_volume": f"${avg_volume:,.0f}"
        },
        "performance": {
            "win_rate": 68.5,  # Mock until we have real trades
            "total_trades": 41,
            "wins": 28,
            "losses": 13
        },
        "top_markets": [
            {
                "question": m['question'][:60] + "...",
                "volume": f"${m.get('volumeNum', 0):,.0f}",
                "tokens": len(m.get('tokens', []))
            }
            for m in sorted(markets, key=lambda x: x.get('volumeNum', 0), reverse=True)[:5]
        ]
    })

@app.route('/api/charts/portfolio')
def api_portfolio():
    return jsonify({"chart": json.dumps(get_portfolio_chart())})

@app.route('/api/charts/trading')
def api_trading():
    return jsonify({"chart": json.dumps(get_trading_chart())})

@app.route('/api/charts/whales')
def api_whales():
    return jsonify({"chart": json.dumps(get_whale_chart())})

@app.route('/api/charts/arbitrage')
def api_arbitrage():
    return jsonify({"chart": json.dumps(get_arbitrage_chart())})

if __name__ == '__main__':
    print('=' * 70)
    print('🚀 Dashboard starting with REAL POLYMARKET DATA')
    print('=' * 70)
    print('📊 Data Sources:')
    print('   ✅ Gamma API: https://gamma-api.polymarket.com/markets')
    print('   ✅ Live market volumes, arbitrage detection, whale tracking')
    print('   🔄 Data refreshes every 30 seconds')
    print('')
    print('🌐 Dashboard: http://0.0.0.0:8080')
    print('=' * 70)
    
    # Test API connection on startup
    print('\n🧪 Testing API connection...')
    markets = get_polymarket_markets(5)
    if markets:
        print(f'✅ Connected! Fetched {len(markets)} markets')
        print(f'📈 Sample: {markets[0]["question"][:60]}...')
    else:
        print('⚠️  Warning: Could not fetch markets. Check your connection.')
    
    print('\n🎯 Starting server...\n')
    app.run(host='0.0.0.0', port=8080, debug=False)
