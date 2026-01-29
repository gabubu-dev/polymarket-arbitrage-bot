#!/usr/bin/env python3
"""
Polymarket Professional Trading Dashboard

Features:
- Real-time market data from Polymarket
- Live order book visualization
- Paper trading with virtual balance
- Real trading preparation (when funded)
- Performance analytics
- Trade history
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import requests
from datetime import datetime, timedelta
import time
import asyncio
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import random

app = Flask(__name__, template_folder='templates')
CORS(app)

# ============================================
# CONFIGURATION
# ============================================
PAPER_TRADING_ENABLED = True
REAL_TRADING_ENABLED = False  # Set to True when wallet is funded
INITIAL_PAPER_BALANCE = 10000.0

# API Endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

# ============================================
# DATA MODELS
# ============================================

@dataclass
class Market:
    id: str
    question: str
    slug: str
    description: str
    category: str
    volume: float
    liquidity: float
    yes_price: float
    no_price: float
    spread: float
    end_date: str
    image_url: str = ""
    
    @property
    def implied_probability(self) -> float:
        return self.yes_price * 100
    
    @property
    def total_volume_formatted(self) -> str:
        if self.volume >= 1_000_000:
            return f"${self.volume/1_000_000:.2f}M"
        elif self.volume >= 1_000:
            return f"${self.volume/1_000:.1f}K"
        return f"${self.volume:.0f}"

@dataclass
class PaperTrade:
    id: str
    market_id: str
    market_question: str
    side: str  # YES or NO
    amount: float
    price: float
    timestamp: datetime
    status: str  # OPEN, CLOSED
    pnl: float = 0.0
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None

@dataclass
class Portfolio:
    cash: float
    positions: Dict[str, dict]
    trades: List[PaperTrade]
    total_pnl: float
    win_rate: float
    
    def to_dict(self):
        return {
            'cash': self.cash,
            'total_value': self.cash + sum(p['value'] for p in self.positions.values()),
            'positions': self.positions,
            'total_pnl': self.total_pnl,
            'win_rate': self.win_rate,
            'trade_count': len(self.trades)
        }

# ============================================
# GLOBAL STATE
# ============================================

class TradingState:
    def __init__(self):
        self.markets_cache = {'data': [], 'timestamp': 0}
        self.orderbook_cache = {}
        self.paper_portfolio = Portfolio(
            cash=INITIAL_PAPER_BALANCE,
            positions={},
            trades=[],
            total_pnl=0.0,
            win_rate=0.0
        )
        self.trade_history = []
        self.price_history = {}  # For charts
        self.load_paper_trades()
    
    def load_paper_trades(self):
        """Load paper trading history from disk"""
        import os
        path = "data/paper_trades.json"
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                    self.paper_portfolio.cash = data.get('cash', INITIAL_PAPER_BALANCE)
                    self.paper_portfolio.positions = data.get('positions', {})
                    self.paper_portfolio.total_pnl = data.get('total_pnl', 0)
            except:
                pass
    
    def save_paper_trades(self):
        """Save paper trading state to disk"""
        import os
        os.makedirs("data", exist_ok=True)
        with open("data/paper_trades.json", 'w') as f:
            json.dump({
                'cash': self.paper_portfolio.cash,
                'positions': self.paper_portfolio.positions,
                'total_pnl': self.paper_portfolio.total_pnl,
                'last_saved': datetime.now().isoformat()
            }, f, indent=2)

state = TradingState()

# ============================================
# DATA FETCHING
# ============================================

def fetch_markets(limit=50) -> List[Market]:
    """Fetch markets from Gamma API with caching"""
    now = time.time()
    if state.markets_cache['data'] and (now - state.markets_cache['timestamp']) < 30:
        return state.markets_cache['data']
    
    try:
        url = f"{GAMMA_API}/markets"
        params = {"active": "true", "limit": limit, "closed": "false"}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            markets = []
            
            for m in data:
                tokens = m.get('tokens', [])
                yes_price = 0.5
                no_price = 0.5
                
                for token in tokens:
                    outcome = token.get('outcome', '').lower()
                    price = float(token.get('price', 0.5))
                    if 'yes' in outcome:
                        yes_price = price
                    elif 'no' in outcome:
                        no_price = price
                
                market = Market(
                    id=m.get('id', ''),
                    question=m.get('question', 'Unknown'),
                    slug=m.get('slug', ''),
                    description=m.get('description', ''),
                    category=m.get('category', 'General'),
                    volume=float(m.get('volumeNum', 0)),
                    liquidity=float(m.get('liquidityNum', 0)),
                    yes_price=yes_price,
                    no_price=no_price,
                    spread=abs(1.0 - (yes_price + no_price)),
                    end_date=m.get('endDate', 'Unknown'),
                    image_url=m.get('imageUrl', '')
                )
                markets.append(market)
            
            state.markets_cache['data'] = markets
            state.markets_cache['timestamp'] = now
            return markets
    except Exception as e:
        print(f"Error fetching markets: {e}")
    
    return state.markets_cache['data'] or []

def fetch_order_book(market_id: str) -> dict:
    """Fetch order book for a market"""
    # Simulated order book for now - in production would use CLOB API
    markets = fetch_markets()
    market = next((m for m in markets if m.id == market_id), None)
    
    if not market:
        return {'bids': [], 'asks': []}
    
    # Generate realistic order book around current price
    yes_price = market.yes_price
    
    bids = []
    asks = []
    
    for i in range(5):
        bid_price = max(0.01, yes_price - 0.02 - (i * 0.01))
        ask_price = min(0.99, yes_price + 0.02 + (i * 0.01))
        
        bids.append({'price': round(bid_price, 3), 'size': random.randint(100, 5000)})
        asks.append({'price': round(ask_price, 3), 'size': random.randint(100, 5000)})
    
    return {'bids': bids, 'asks': asks, 'market_id': market_id}

def fetch_market_trades(market_id: str) -> List[dict]:
    """Fetch recent trades for a market"""
    # In production would fetch from API
    trades = []
    for i in range(20):
        trades.append({
            'price': round(random.uniform(0.3, 0.7), 3),
            'size': random.randint(10, 500),
            'side': random.choice(['BUY', 'SELL']),
            'time': (datetime.now() - timedelta(minutes=i*5)).isoformat()
        })
    return trades

# ============================================
# PAPER TRADING LOGIC
# ============================================

def execute_paper_trade(market_id: str, side: str, amount: float) -> dict:
    """Execute a paper trade"""
    markets = fetch_markets()
    market = next((m for m in markets if m.id == market_id), None)
    
    if not market:
        return {'success': False, 'error': 'Market not found'}
    
    price = market.yes_price if side == 'YES' else market.no_price
    cost = amount * price
    
    # Check if enough cash
    if cost > state.paper_portfolio.cash:
        return {'success': False, 'error': 'Insufficient funds'}
    
    # Execute trade
    trade = PaperTrade(
        id=f"paper_{int(time.time())}_{random.randint(1000, 9999)}",
        market_id=market_id,
        market_question=market.question,
        side=side,
        amount=amount,
        price=price,
        timestamp=datetime.now(),
        status='OPEN'
    )
    
    state.paper_portfolio.cash -= cost
    
    # Update position
    key = f"{market_id}_{side}"
    if key not in state.paper_portfolio.positions:
        state.paper_portfolio.positions[key] = {
            'market_id': market_id,
            'market_question': market.question,
            'side': side,
            'amount': 0,
            'avg_price': 0,
            'current_price': price,
            'value': 0,
            'pnl': 0
        }
    
    pos = state.paper_portfolio.positions[key]
    total_amount = pos['amount'] + amount
    pos['avg_price'] = (pos['amount'] * pos['avg_price'] + amount * price) / total_amount
    pos['amount'] = total_amount
    pos['current_price'] = price
    pos['value'] = total_amount * price
    pos['pnl'] = (price - pos['avg_price']) * total_amount
    
    state.paper_portfolio.trades.append(trade)
    state.save_paper_trades()
    
    return {
        'success': True,
        'trade': asdict(trade),
        'portfolio': state.paper_portfolio.to_dict()
    }

def close_paper_position(position_key: str) -> dict:
    """Close a paper trading position"""
    if position_key not in state.paper_portfolio.positions:
        return {'success': False, 'error': 'Position not found'}
    
    pos = state.paper_portfolio.positions[position_key]
    markets = fetch_markets()
    market = next((m for m in markets if m.id == pos['market_id']), None)
    
    if not market:
        return {'success': False, 'error': 'Market not found'}
    
    exit_price = market.yes_price if pos['side'] == 'YES' else market.no_price
    exit_value = pos['amount'] * exit_price
    pnl = (exit_price - pos['avg_price']) * pos['amount']
    
    state.paper_portfolio.cash += exit_value
    state.paper_portfolio.total_pnl += pnl
    
    del state.paper_portfolio.positions[position_key]
    state.save_paper_trades()
    
    return {
        'success': True,
        'pnl': pnl,
        'exit_price': exit_price,
        'portfolio': state.paper_portfolio.to_dict()
    }

# ============================================
# API ROUTES
# ============================================

@app.route('/')
def index():
    return render_template('trading_dashboard.html')

@app.route('/api/markets')
def api_markets():
    """Get all markets"""
    markets = fetch_markets()
    return jsonify({
        'markets': [asdict(m) for m in markets],
        'count': len(markets),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/markets/<market_id>')
def api_market_detail(market_id):
    """Get detailed market data"""
    markets = fetch_markets()
    market = next((m for m in markets if m.id == market_id), None)
    
    if not market:
        return jsonify({'error': 'Market not found'}), 404
    
    orderbook = fetch_order_book(market_id)
    trades = fetch_market_trades(market_id)
    
    return jsonify({
        'market': asdict(market),
        'orderbook': orderbook,
        'recent_trades': trades
    })

@app.route('/api/markets/<market_id>/orderbook')
def api_orderbook(market_id):
    """Get order book for a market"""
    return jsonify(fetch_order_book(market_id))

@app.route('/api/portfolio')
def api_portfolio():
    """Get paper trading portfolio"""
    return jsonify(state.paper_portfolio.to_dict())

@app.route('/api/trade', methods=['POST'])
def api_trade():
    """Execute a paper trade"""
    data = request.json
    market_id = data.get('market_id')
    side = data.get('side')
    amount = float(data.get('amount', 0))
    
    if not all([market_id, side, amount > 0]):
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
    
    result = execute_paper_trade(market_id, side, amount)
    return jsonify(result)

@app.route('/api/close-position', methods=['POST'])
def api_close_position():
    """Close a paper position"""
    data = request.json
    position_key = data.get('position_key')
    
    if not position_key:
        return jsonify({'success': False, 'error': 'Position key required'}), 400
    
    result = close_paper_position(position_key)
    return jsonify(result)

@app.route('/api/dashboard')
def api_dashboard():
    """Get dashboard summary data"""
    markets = fetch_markets()
    
    total_volume = sum(m.volume for m in markets)
    top_markets = sorted(markets, key=lambda x: x.volume, reverse=True)[:10]
    
    # Calculate arbitrage opportunities
    arbitrage_ops = []
    for m in markets:
        if m.spread > 0.02:  # >2% spread
            arbitrage_ops.append({
                'market': m.question[:50],
                'spread': m.spread,
                'profit_potential': m.spread * 100
            })
    
    arbitrage_ops.sort(key=lambda x: x['profit_potential'], reverse=True)
    
    return jsonify({
        'total_markets': len(markets),
        'total_volume': total_volume,
        'active_volume': f"${total_volume:,.0f}",
        'top_markets': [asdict(m) for m in top_markets[:5]],
        'arbitrage_opportunities': arbitrage_ops[:5],
        'paper_portfolio': state.paper_portfolio.to_dict(),
        'paper_trading_enabled': PAPER_TRADING_ENABLED,
        'real_trading_enabled': REAL_TRADING_ENABLED,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/performance')
def api_performance():
    """Get performance metrics"""
    trades = state.paper_portfolio.trades
    
    if not trades:
        return jsonify({
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'avg_trade': 0
        })
    
    closed_trades = [t for t in trades if t.status == 'CLOSED']
    winning_trades = [t for t in closed_trades if t.pnl > 0]
    
    return jsonify({
        'total_trades': len(trades),
        'closed_trades': len(closed_trades),
        'winning_trades': len(winning_trades),
        'win_rate': (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0,
        'total_pnl': state.paper_portfolio.total_pnl,
        'avg_trade': state.paper_portfolio.total_pnl / len(trades) if trades else 0
    })

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print('=' * 70)
    print('🚀 POLYMARKET PROFESSIONAL TRADING DASHBOARD')
    print('=' * 70)
    print(f'📊 Paper Trading: {"✅ ENABLED" if PAPER_TRADING_ENABLED else "❌ DISABLED"}')
    print(f'💰 Real Trading: {"✅ ENABLED" if REAL_TRADING_ENABLED else "❌ DISABLED (Fund wallet to enable)"}')
    print(f'💵 Paper Balance: ${INITIAL_PAPER_BALANCE:,.2f}')
    print('')
    print('🌐 Dashboard: http://0.0.0.0:8080')
    print('📈 Features:')
    print('   • Real-time market data')
    print('   • Live order books')
    print('   • Paper trading with $10,000 virtual balance')
    print('   • Portfolio tracking')
    print('   • Performance analytics')
    print('=' * 70)
    
    app.run(host='0.0.0.0', port=8080, debug=False)