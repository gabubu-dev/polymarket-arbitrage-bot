#!/usr/bin/env python3
"""
Polymarket Professional Trading Dashboard v2
Enhanced with realistic paper trading, proper position tracking, and interactive UI
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import requests
from datetime import datetime, timedelta
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
import random
import os

app = Flask(__name__, template_folder='templates')
CORS(app)

# ============================================
# CONFIGURATION
# ============================================
PAPER_TRADING_ENABLED = True
REAL_TRADING_ENABLED = False
INITIAL_PAPER_BALANCE = 10000.0
FEE_RATE = 0.002  # 0.2% trading fee

# API Endpoints
GAMMA_API = "https://gamma-api.polymarket.com"

# ============================================
# ENHANCED DATA MODELS
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

@dataclass
class Trade:
    """Represents a single trade (buy or sell)"""
    id: str
    market_id: str
    market_question: str
    side: str  # YES or NO
    action: str  # BUY or SELL
    amount: float  # Number of shares
    price: float  # Price per share
    total_cost: float  # Total amount paid/received
    fee: float  # Trading fee
    timestamp: str
    pnl: float = 0.0  # Profit/loss for closed trades

@dataclass
class Position:
    """Represents an open position (aggregated trades)"""
    market_id: str
    market_question: str
    side: str
    amount: float  # Total shares
    avg_entry_price: float
    current_price: float
    invested: float  # Total cash invested
    current_value: float  # Current market value
    unrealized_pnl: float
    trades: List[str] = field(default_factory=list)  # List of trade IDs

@dataclass
class Portfolio:
    """Complete portfolio state"""
    cash: float
    initial_balance: float
    positions: Dict[str, Position]  # key: "market_id_side"
    trades: List[Trade]
    realized_pnl: float
    
    @property
    def total_value(self) -> float:
        """Total portfolio value = cash + positions value"""
        positions_value = sum(p.current_value for p in self.positions.values())
        return self.cash + positions_value
    
    @property
    def total_pnl(self) -> float:
        """Total P&L = realized + unrealized"""
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return self.realized_pnl + unrealized
    
    @property
    def total_return_pct(self) -> float:
        """Total return percentage"""
        if self.initial_balance == 0:
            return 0
        return ((self.total_value - self.initial_balance) / self.initial_balance) * 100
    
    def get_stats(self) -> dict:
        """Get portfolio statistics"""
        closed_trades = [t for t in self.trades if t.action == 'SELL']
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        
        return {
            'cash': round(self.cash, 2),
            'initial_balance': round(self.initial_balance, 2),
            'total_value': round(self.total_value, 2),
            'invested': round(sum(p.invested for p in self.positions.values()), 2),
            'realized_pnl': round(self.realized_pnl, 2),
            'total_pnl': round(self.total_pnl, 2),
            'total_return_pct': round(self.total_return_pct, 2),
            'position_count': len(self.positions),
            'trade_count': len(self.trades),
            'win_rate': round((len(winning_trades) / len(closed_trades) * 100), 2) if closed_trades else 0
        }

# ============================================
# GLOBAL STATE
# ============================================

class TradingState:
    def __init__(self):
        self.markets_cache = {'data': [], 'timestamp': 0}
        self.portfolio = self._load_portfolio()
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        os.makedirs("data", exist_ok=True)
    
    def _load_portfolio(self) -> Portfolio:
        """Load portfolio from disk or create new"""
        portfolio_path = "data/portfolio.json"
        trades_path = "data/trades.json"
        
        if os.path.exists(portfolio_path):
            try:
                with open(portfolio_path, 'r') as f:
                    data = json.load(f)
                
                # Load positions
                positions = {}
                for key, pos_data in data.get('positions', {}).items():
                    positions[key] = Position(**pos_data)
                
                # Load trades
                trades = []
                if os.path.exists(trades_path):
                    with open(trades_path, 'r') as f:
                        trades_data = json.load(f)
                        trades = [Trade(**t) for t in trades_data]
                
                return Portfolio(
                    cash=data.get('cash', INITIAL_PAPER_BALANCE),
                    initial_balance=data.get('initial_balance', INITIAL_PAPER_BALANCE),
                    positions=positions,
                    trades=trades,
                    realized_pnl=data.get('realized_pnl', 0)
                )
            except Exception as e:
                print(f"Error loading portfolio: {e}")
        
        # Return fresh portfolio
        return Portfolio(
            cash=INITIAL_PAPER_BALANCE,
            initial_balance=INITIAL_PAPER_BALANCE,
            positions={},
            trades=[],
            realized_pnl=0
        )
    
    def save_portfolio(self):
        """Save portfolio state to disk"""
        try:
            # Save portfolio (without trades list for efficiency)
            portfolio_data = {
                'cash': self.portfolio.cash,
                'initial_balance': self.portfolio.initial_balance,
                'positions': {
                    k: asdict(v) for k, v in self.portfolio.positions.items()
                },
                'realized_pnl': self.portfolio.realized_pnl,
                'last_saved': datetime.now().isoformat()
            }
            
            with open("data/portfolio.json", 'w') as f:
                json.dump(portfolio_data, f, indent=2)
            
            # Save trades separately
            trades_data = [asdict(t) for t in self.portfolio.trades]
            with open("data/trades.json", 'w') as f:
                json.dump(trades_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving portfolio: {e}")
    
    def update_position_prices(self):
        """Update all position current prices based on market data"""
        markets = fetch_markets()
        market_prices = {m.id: {'yes': m.yes_price, 'no': m.no_price} for m in markets}
        
        for key, position in self.portfolio.positions.items():
            if position.market_id in market_prices:
                current_price = market_prices[position.market_id][position.side.lower()]
                position.current_price = current_price
                position.current_value = position.amount * current_price
                position.unrealized_pnl = (current_price - position.avg_entry_price) * position.amount

state = TradingState()

# ============================================
# MARKET DATA
# ============================================

def fetch_markets(limit=100) -> List[Market]:
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
                    id=str(m.get('id', '')),
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

def get_market_by_id(market_id: str) -> Optional[Market]:
    """Get a specific market by ID"""
    markets = fetch_markets()
    return next((m for m in markets if m.id == market_id), None)

# ============================================
# PAPER TRADING ENGINE
# ============================================

def buy_position(market_id: str, side: str, amount: float) -> dict:
    """
    Buy shares in a market
    
    Args:
        market_id: The market ID
        side: 'YES' or 'NO'
        amount: Number of shares to buy
    
    Returns:
        dict with success status and trade details
    """
    market = get_market_by_id(market_id)
    if not market:
        return {'success': False, 'error': 'Market not found'}
    
    if amount <= 0:
        return {'success': False, 'error': 'Amount must be positive'}
    
    # Get current price
    price = market.yes_price if side == 'YES' else market.no_price
    
    # Calculate costs
    subtotal = amount * price
    fee = subtotal * FEE_RATE
    total_cost = subtotal + fee
    
    # Check if enough cash
    if total_cost > state.portfolio.cash:
        return {
            'success': False, 
            'error': f'Insufficient funds. Need ${total_cost:.2f}, have ${state.portfolio.cash:.2f}'
        }
    
    # Create trade record
    trade = Trade(
        id=f"trade_{int(time.time())}_{random.randint(1000,9999)}",
        market_id=market_id,
        market_question=market.question,
        side=side,
        action='BUY',
        amount=amount,
        price=price,
        total_cost=total_cost,
        fee=fee,
        timestamp=datetime.now().isoformat()
    )
    
    # Update or create position
    position_key = f"{market_id}_{side}"
    
    if position_key in state.portfolio.positions:
        # Add to existing position
        pos = state.portfolio.positions[position_key]
        total_amount = pos.amount + amount
        total_invested = pos.invested + total_cost
        
        pos.amount = total_amount
        pos.avg_entry_price = total_invested / total_amount
        pos.invested = total_invested
        pos.trades.append(trade.id)
    else:
        # Create new position
        state.portfolio.positions[position_key] = Position(
            market_id=market_id,
            market_question=market.question,
            side=side,
            amount=amount,
            avg_entry_price=total_cost / amount,
            current_price=price,
            invested=total_cost,
            current_value=subtotal,
            unrealized_pnl=-fee,  # Start with negative fee
            trades=[trade.id]
        )
    
    # Update cash and save trade
    state.portfolio.cash -= total_cost
    state.portfolio.trades.append(trade)
    state.save_portfolio()
    
    return {
        'success': True,
        'trade': asdict(trade),
        'portfolio': state.portfolio.get_stats()
    }

def sell_position(position_key: str, amount: Optional[float] = None) -> dict:
    """
    Sell shares from a position
    
    Args:
        position_key: The position key (market_id_side)
        amount: Amount to sell (None = sell all)
    
    Returns:
        dict with success status and trade details
    """
    if position_key not in state.portfolio.positions:
        return {'success': False, 'error': 'Position not found'}
    
    pos = state.portfolio.positions[position_key]
    market = get_market_by_id(pos.market_id)
    
    if not market:
        return {'success': False, 'error': 'Market not found'}
    
    # Determine amount to sell
    sell_amount = amount if amount else pos.amount
    sell_amount = min(sell_amount, pos.amount)
    
    if sell_amount <= 0:
        return {'success': False, 'error': 'Invalid sell amount'}
    
    # Get current price
    current_price = market.yes_price if pos.side == 'YES' else market.no_price
    
    # Calculate proceeds
    gross_proceeds = sell_amount * current_price
    fee = gross_proceeds * FEE_RATE
    net_proceeds = gross_proceeds - fee
    
    # Calculate P&L
    cost_basis = sell_amount * pos.avg_entry_price
    realized_pnl = net_proceeds - cost_basis
    
    # Create trade record
    trade = Trade(
        id=f"trade_{int(time.time())}_{random.randint(1000,9999)}",
        market_id=pos.market_id,
        market_question=pos.market_question,
        side=pos.side,
        action='SELL',
        amount=sell_amount,
        price=current_price,
        total_cost=net_proceeds,
        fee=fee,
        timestamp=datetime.now().isoformat(),
        pnl=realized_pnl
    )
    
    # Update position
    if sell_amount >= pos.amount:
        # Selling entire position
        del state.portfolio.positions[position_key]
    else:
        # Selling partial position
        pos.amount -= sell_amount
        pos.invested = pos.amount * pos.avg_entry_price
        pos.trades.append(trade.id)
    
    # Update portfolio
    state.portfolio.cash += net_proceeds
    state.portfolio.realized_pnl += realized_pnl
    state.portfolio.trades.append(trade)
    state.save_portfolio()
    
    return {
        'success': True,
        'trade': asdict(trade),
        'realized_pnl': round(realized_pnl, 2),
        'portfolio': state.portfolio.get_stats()
    }

# ============================================
# API ROUTES
# ============================================

@app.route('/')
def index():
    return render_template('trading_dashboard_v2.html')

@app.route('/api/markets')
def api_markets():
    """Get all active markets"""
    markets = fetch_markets()
    return jsonify({
        'markets': [asdict(m) for m in markets],
        'count': len(markets)
    })

@app.route('/api/markets/<market_id>')
def api_market_detail(market_id):
    """Get detailed market data"""
    market = get_market_by_id(market_id)
    if not market:
        return jsonify({'error': 'Market not found'}), 404
    
    # Generate realistic order book
    yes_price = market.yes_price
    bids = [{'price': round(max(0.01, yes_price - 0.01*i), 2), 'size': random.randint(100, 5000)} for i in range(1, 6)]
    asks = [{'price': round(min(0.99, yes_price + 0.01*i), 2), 'size': random.randint(100, 5000)} for i in range(1, 6)]
    
    return jsonify({
        'market': asdict(market),
        'orderbook': {'bids': bids, 'asks': asks}
    })

@app.route('/api/portfolio')
def api_portfolio():
    """Get current portfolio state"""
    state.update_position_prices()
    return jsonify(state.portfolio.get_stats())

@app.route('/api/positions')
def api_positions():
    """Get all open positions with current values"""
    state.update_position_prices()
    positions = []
    for key, pos in state.portfolio.positions.items():
        pos_data = asdict(pos)
        pos_data['key'] = key
        positions.append(pos_data)
    return jsonify({'positions': positions})

@app.route('/api/trades')
def api_trades():
    """Get trade history"""
    limit = request.args.get('limit', 50, type=int)
    trades = sorted(state.portfolio.trades, key=lambda x: x.timestamp, reverse=True)[:limit]
    return jsonify({
        'trades': [asdict(t) for t in trades],
        'total': len(state.portfolio.trades)
    })

@app.route('/api/trade/buy', methods=['POST'])
def api_buy():
    """Execute a buy order"""
    data = request.json
    result = buy_position(
        market_id=data.get('market_id'),
        side=data.get('side'),
        amount=float(data.get('amount', 0))
    )
    return jsonify(result)

@app.route('/api/trade/sell', methods=['POST'])
def api_sell():
    """Execute a sell order"""
    data = request.json
    result = sell_position(
        position_key=data.get('position_key'),
        amount=data.get('amount')  # None = sell all
    )
    return jsonify(result)

@app.route('/api/dashboard')
def api_dashboard():
    """Get dashboard overview data"""
    markets = fetch_markets()
    state.update_position_prices()
    
    # Calculate stats
    total_volume = sum(m.volume for m in markets)
    top_markets = sorted(markets, key=lambda x: x.volume, reverse=True)[:10]
    
    # Recent activity
    recent_trades = sorted(
        state.portfolio.trades, 
        key=lambda x: x.timestamp, 
        reverse=True
    )[:5]
    
    return jsonify({
        'markets_count': len(markets),
        'total_volume': total_volume,
        'top_markets': [asdict(m) for m in top_markets[:5]],
        'portfolio': state.portfolio.get_stats(),
        'recent_trades': [asdict(t) for t in recent_trades],
        'paper_trading': PAPER_TRADING_ENABLED,
        'real_trading': REAL_TRADING_ENABLED
    })

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset paper trading account"""
    global state
    state.portfolio = Portfolio(
        cash=INITIAL_PAPER_BALANCE,
        initial_balance=INITIAL_PAPER_BALANCE,
        positions={},
        trades=[],
        realized_pnl=0
    )
    state.save_portfolio()
    return jsonify({'success': True, 'portfolio': state.portfolio.get_stats()})

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print('=' * 70)
    print('🚀 POLYMARKET TRADING DASHBOARD v2')
    print('=' * 70)
    stats = state.portfolio.get_stats()
    print(f"💵 Cash: ${stats['cash']:.2f}")
    print(f"📊 Positions: {stats['position_count']}")
    print(f"💰 Total Value: ${stats['total_value']:.2f}")
    print(f"📈 Total P&L: ${stats['total_pnl']:.2f} ({stats['total_return_pct']:.2f}%)")
    print('=' * 70)
    print('🌐 Dashboard: http://localhost:8080')
    print('=' * 70)
    
    app.run(host='0.0.0.0', port=8080, debug=False)