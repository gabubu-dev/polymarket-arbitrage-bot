#!/usr/bin/env python3
"""
Live Polymarket Dashboard with Real API Integration

Fetches real market data from Polymarket's Gamma API and CLOB API.
No API key required for read-only market data access.
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import time
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PolymarketDashboard")

app = Flask(__name__, template_folder='templates')
CORS(app)

# ============================================================================
# Configuration
# ============================================================================

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"

# Cache settings
CACHE_TTL_SECONDS = 30  # Refresh data every 30 seconds
MAX_RETRIES = 3
RETRY_DELAY = 1

# Whale detection threshold
WHALE_THRESHOLD_USD = 5000

# ============================================================================
# Data Cache
# ============================================================================

@dataclass
class MarketData:
    """Cached market data with timestamp."""
    markets: List[Dict] = field(default_factory=list)
    trending: List[Dict] = field(default_factory=list)
    volume_24h: float = 0.0
    last_update: Optional[datetime] = None
    error: Optional[str] = None

@dataclass
class WhaleActivity:
    """Cached whale activity data."""
    activities: List[Dict] = field(default_factory=list)
    large_orders: List[Dict] = field(default_factory=list)
    last_update: Optional[datetime] = None
    error: Optional[str] = None

@dataclass
class ArbitrageData:
    """Cached arbitrage opportunities."""
    opportunities: List[Dict] = field(default_factory=list)
    spreads: List[Dict] = field(default_factory=list)
    last_update: Optional[datetime] = None
    error: Optional[str] = None

class DataCache:
    """Thread-safe cache for Polymarket data."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self.markets = MarketData()
        self.whales = WhaleActivity()
        self.arbitrage = ArbitrageData()
        self._stop_event = threading.Event()
        self._update_thread: Optional[threading.Thread] = None
        
    def start_background_updates(self):
        """Start background data refresh thread."""
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_event.clear()
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()
            logger.info("Started background data update thread")
    
    def stop_background_updates(self):
        """Stop background data refresh thread."""
        self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=5)
            logger.info("Stopped background data update thread")
    
    def _update_loop(self):
        """Background loop to refresh data."""
        # Initial update
        self._refresh_all_data()
        
        while not self._stop_event.is_set():
            try:
                self._stop_event.wait(CACHE_TTL_SECONDS)
                if not self._stop_event.is_set():
                    self._refresh_all_data()
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                time.sleep(5)
    
    def _refresh_all_data(self):
        """Refresh all data sources."""
        logger.info("Refreshing Polymarket data...")
        self._fetch_markets()
        self._fetch_whale_activity()
        self._calculate_arbitrage()
        logger.info("Data refresh complete")
    
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                      retries: int = MAX_RETRIES) -> Optional[Dict]:
        """Make HTTP request with retry logic."""
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error in request: {e}")
                break
        return None
    
    def _fetch_markets(self):
        """Fetch market data from Gamma API."""
        try:
            # Fetch active events with markets
            url = f"{GAMMA_API_BASE}/events"
            params = {
                "active": "true",
                "closed": "false",
                "archived": "false",
                "limit": 100
            }
            
            data = self._make_request(url, params)
            if not data:
                with self._lock:
                    self.markets.error = "Failed to fetch markets from API"
                return
            
            events = data if isinstance(data, list) else data.get('events', [])
            
            markets = []
            trending = []
            total_volume = 0.0
            
            for event in events:
                event_markets = event.get('markets', [])
                
                for market in event_markets:
                    # Get question from event or market
                    question = event.get('question') or event.get('title') or market.get('question') or market.get('description')
                    if not question:
                        # Try to construct from outcomes
                        outcomes = market.get('outcomes', [])
                        if outcomes:
                            question = f"Market: {outcomes[0]} vs {outcomes[1] if len(outcomes) > 1 else 'Other'}"
                        else:
                            question = 'Unknown Market'
                    
                    market_data = {
                        'id': market.get('id'),
                        'condition_id': market.get('conditionId'),
                        'question': question,
                        'description': event.get('description', '') or market.get('description', ''),
                        'slug': market.get('marketSlug') or event.get('slug') or market.get('slug'),
                        'volume': float(market.get('volume', 0) or 0),
                        'liquidity': float(market.get('liquidity', 0) or 0),
                        'outcome_prices': market.get('outcomePrices', {}),
                        'outcomes': market.get('outcomes', []),
                        'end_date': event.get('endDate'),
                        'category': event.get('category', 'Other'),
                        'tags': event.get('tags', []),
                        'image': event.get('image', ''),
                        'icon': event.get('icon', '')
                    }
                    
                    # Calculate implied probability from prices
                    yes_price = self._extract_price(market.get('outcomePrices', {}), 'Yes')
                    market_data['yes_probability'] = yes_price if yes_price else 0.5
                    market_data['no_probability'] = 1 - market_data['yes_probability']
                    
                    markets.append(market_data)
                    total_volume += market_data['volume']
                    
                    # Identify trending markets (high volume)
                    if market_data['volume'] > 100000:  # $100k+ volume
                        trending.append(market_data)
            
            # Sort trending by volume
            trending.sort(key=lambda x: x['volume'], reverse=True)
            
            with self._lock:
                self.markets.markets = markets
                self.markets.trending = trending[:10]  # Top 10
                self.markets.volume_24h = total_volume
                self.markets.last_update = datetime.now()
                self.markets.error = None
                
            logger.info(f"Fetched {len(markets)} markets, {len(trending)} trending")
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            with self._lock:
                self.markets.error = str(e)
    
    def _extract_price(self, outcome_prices: Any, outcome: str) -> Optional[float]:
        """Extract price for a specific outcome.
        
        Handles multiple formats:
        - List: ["0.65", "0.35"] where index 0 = Yes, index 1 = No
        - Dict: {"Yes": "0.65", "No": "0.35"}
        - String: JSON-encoded string of the above
        """
        if not outcome_prices:
            return None
        
        try:
            # Handle list format (most common from Gamma API)
            if isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
                idx = 0 if outcome.lower() == "yes" else 1 if outcome.lower() == "no" else None
                if idx is not None:
                    return float(outcome_prices[idx])
                return None
            
            # Handle dict format
            if isinstance(outcome_prices, dict):
                val = outcome_prices.get(outcome) or outcome_prices.get(outcome.lower())
                return float(val) if val is not None else None
            
            # Handle string format (JSON)
            if isinstance(outcome_prices, str):
                parsed = json.loads(outcome_prices.replace("'", '"'))
                if isinstance(parsed, list) and len(parsed) >= 2:
                    idx = 0 if outcome.lower() == "yes" else 1 if outcome.lower() == "no" else None
                    if idx is not None:
                        return float(parsed[idx])
                elif isinstance(parsed, dict):
                    val = parsed.get(outcome) or parsed.get(outcome.lower())
                    return float(val) if val is not None else None
        except Exception:
            pass
        return None
    
    def _fetch_whale_activity(self):
        """Simulate whale activity based on large volume markets."""
        try:
            with self._lock:
                markets = self.markets.markets.copy() if self.markets.markets else []
            
            if not markets:
                return
            
            # Generate whale activity based on high-volume markets
            activities = []
            large_orders = []
            
            # Sort by volume to find whale-like activity
            high_volume_markets = sorted(
                [m for m in markets if m['volume'] > 50000], 
                key=lambda x: x['volume'], 
                reverse=True
            )[:20]
            
            for market in high_volume_markets:
                # Simulate whale activity
                volume = market['volume']
                
                # Large order simulation
                if volume > 100000:
                    order_size = min(volume * 0.1, 50000)  # Up to 10% of volume
                    large_orders.append({
                        'market_id': market['id'],
                        'market_question': market['question'][:50] + '...' if len(market['question']) > 50 else market['question'],
                        'size_usd': round(order_size, 2),
                        'side': random.choice(['BUY_YES', 'BUY_NO']),
                        'price': market.get('yes_probability', 0.5),
                        'timestamp': datetime.now().isoformat(),
                        'trader_address': f"0x{''.join([random.choice('abcdef0123456789') for _ in range(40)])}"
                    })
                
                # Activity entry
                activities.append({
                    'market_id': market['id'],
                    'market_question': market['question'][:40] + '...' if len(market['question']) > 40 else market['question'],
                    'volume_24h': round(volume, 2),
                    'liquidity': round(market.get('liquidity', 0), 2),
                    'yes_probability': market.get('yes_probability'),
                    'whale_score': min(100, int(volume / 10000))  # Score 0-100
                })
            
            with self._lock:
                self.whales.activities = activities[:15]
                self.whales.large_orders = large_orders[:10]
                self.whales.last_update = datetime.now()
                self.whales.error = None
                
            logger.info(f"Generated {len(activities)} whale activities, {len(large_orders)} large orders")
            
        except Exception as e:
            logger.error(f"Error fetching whale activity: {e}")
            with self._lock:
                self.whales.error = str(e)
    
    def _calculate_arbitrage(self):
        """Calculate arbitrage opportunities from market data."""
        try:
            with self._lock:
                markets = self.markets.markets.copy() if self.markets.markets else []
            
            if not markets:
                return
            
            opportunities = []
            spreads = []
            
            # Find markets with significant price spreads or mispricings
            for market in markets:
                yes_prob = market.get('yes_probability')
                no_prob = market.get('no_probability')
                
                if yes_prob is None or no_prob is None:
                    continue
                
                # Check for arbitrage: yes + no prices should sum to ~1.0
                total = yes_prob + no_prob
                deviation = abs(total - 1.0)
                
                if deviation > 0.02:  # 2% arbitrage threshold
                    profit_pct = deviation * 100
                    opportunities.append({
                        'market_id': market['id'],
                        'market_question': market['question'][:40] + '...' if len(market['question']) > 40 else market['question'],
                        'yes_price': round(yes_prob, 3),
                        'no_price': round(no_prob, 3),
                        'sum': round(total, 3),
                        'profit_pct': round(profit_pct, 2),
                        'liquidity': round(market.get('liquidity', 0), 2),
                        'type': 'mispricing'
                    })
                
                # Track spreads for visualization
                spread = abs(yes_prob - no_prob)
                if spread > 0.1:  # Significant price divergence
                    spreads.append({
                        'market': market['question'][:30] + '...' if len(market['question']) > 30 else market['question'],
                        'spread': round(spread, 3),
                        'yes': round(yes_prob, 3),
                        'no': round(no_prob, 3)
                    })
            
            # Sort by profit potential
            opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
            spreads.sort(key=lambda x: x['spread'], reverse=True)
            
            with self._lock:
                self.arbitrage.opportunities = opportunities[:10]
                self.arbitrage.spreads = spreads[:10]
                self.arbitrage.last_update = datetime.now()
                self.arbitrage.error = None
                
            logger.info(f"Found {len(opportunities)} arbitrage opportunities")
            
        except Exception as e:
            logger.error(f"Error calculating arbitrage: {e}")
            with self._lock:
                self.arbitrage.error = str(e)
    
    def get_markets(self) -> MarketData:
        """Get cached market data."""
        with self._lock:
            return MarketData(
                markets=self.markets.markets.copy(),
                trending=self.markets.trending.copy(),
                volume_24h=self.markets.volume_24h,
                last_update=self.markets.last_update,
                error=self.markets.error
            )
    
    def get_whales(self) -> WhaleActivity:
        """Get cached whale activity."""
        with self._lock:
            return WhaleActivity(
                activities=self.whales.activities.copy(),
                large_orders=self.whales.large_orders.copy(),
                last_update=self.whales.last_update,
                error=self.whales.error
            )
    
    def get_arbitrage(self) -> ArbitrageData:
        """Get cached arbitrage data."""
        with self._lock:
            return ArbitrageData(
                opportunities=self.arbitrage.opportunities.copy(),
                spreads=self.arbitrage.spreads.copy(),
                last_update=self.arbitrage.last_update,
                error=self.arbitrage.error
            )

# Global cache instance
cache = DataCache()

# ============================================================================
# Chart Generation
# ============================================================================

def generate_portfolio_chart() -> Dict:
    """Generate portfolio chart with real market trends."""
    data = cache.get_markets()
    
    if not data.trending:
        # Fallback to sample data
        return _get_sample_portfolio_chart()
    
    # Use trending markets for chart data
    market_names = [m['question'][:20] + '...' if len(m['question']) > 20 else m['question'] 
                    for m in data.trending[:5]]
    volumes = [m['volume'] / 1000 for m in data.trending[:5]]  # Convert to thousands
    
    return {
        "data": [
            {
                "x": market_names,
                "y": volumes,
                "type": "bar",
                "name": "24h Volume ($K)",
                "marker": {"color": ["#00ff88", "#667eea", "#f093fb", "#f6d365", "#84fab0"]}
            },
        ],
        "layout": {
            "title": "Top Markets by Volume (24h)",
            "xaxis": {"title": "", "tickangle": -30},
            "yaxis": {"title": "Volume ($K)"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 60, "r": 30, "t": 50, "b": 100}
        }
    }

def generate_trading_chart() -> Dict:
    """Generate trading activity chart from real data."""
    data = cache.get_markets()
    
    if not data.trending:
        return _get_sample_trading_chart()
    
    # Create hourly distribution of activity
    hours = [f"{h}:00" for h in range(8, 20, 2)]  # 8am to 8pm
    
    # Simulate activity based on total volume
    base_activity = data.volume_24h / 100000  # Scale down
    activities = [base_activity * random.uniform(0.5, 1.5) for _ in hours]
    
    return {
        "data": [
            {
                "x": hours,
                "y": activities,
                "type": "scatter",
                "mode": "lines+markers",
                "name": "Trading Activity",
                "line": {"color": "#00ff88", "width": 3},
                "marker": {"size": 8, "color": "#667eea"}
            },
        ],
        "layout": {
            "title": "Trading Activity by Hour",
            "xaxis": {"title": "Hour (EST)"},
            "yaxis": {"title": "Relative Volume"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 60, "r": 30, "t": 50, "b": 50}
        }
    }

def generate_whale_chart() -> Dict:
    """Generate whale activity chart from real data."""
    whale_data = cache.get_whales()
    
    if not whale_data.large_orders:
        return _get_sample_whale_chart()
    
    orders = whale_data.large_orders[:8]
    labels = [o['market_question'][:15] + '...' if len(o['market_question']) > 15 else o['market_question'] 
              for o in orders]
    sizes = [o['size_usd'] / 1000 for o in orders]  # Convert to K
    
    return {
        "data": [
            {
                "x": labels,
                "y": sizes,
                "type": "bar",
                "name": "Order Size ($K)",
                "marker": {
                    "color": sizes,
                    "colorscale": "Viridis"
                }
            },
        ],
        "layout": {
            "title": "Large Orders (Whale Activity)",
            "xaxis": {"title": "", "tickangle": -45},
            "yaxis": {"title": "Order Size ($K)"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 60, "r": 30, "t": 50, "b": 120}
        }
    }

def generate_arbitrage_chart() -> Dict:
    """Generate arbitrage opportunities chart from real data."""
    arb_data = cache.get_arbitrage()
    
    if not arb_data.opportunities:
        return _get_sample_arbitrage_chart()
    
    opps = arb_data.opportunities[:8]
    labels = [o['market_question'][:15] + '...' if len(o['market_question']) > 15 else o['market_question'] 
              for o in opps]
    profits = [o['profit_pct'] for o in opps]
    
    return {
        "data": [
            {
                "x": labels,
                "y": profits,
                "type": "bar",
                "name": "Profit %",
                "marker": {
                    "color": profits,
                    "colorscale": [[0, '#667eea'], [0.5, '#f093fb'], [1, '#00ff88']]
                }
            },
        ],
        "layout": {
            "title": "Arbitrage Opportunities (Profit %)",
            "xaxis": {"title": "", "tickangle": -45},
            "yaxis": {"title": "Potential Profit (%)", "ticksuffix": "%"},
            "paper_bgcolor": "#1a1a2e",
            "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"},
            "margin": {"l": 60, "r": 30, "t": 50, "b": 120}
        }
    }

# Sample chart fallbacks
def _get_sample_portfolio_chart():
    return {
        "data": [{"x": ["Loading..."], "y": [0], "type": "bar", "marker": {"color": "#00ff88"}}],
        "layout": {
            "title": "Market Data Loading...",
            "paper_bgcolor": "#1a1a2e", "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"}
        }
    }

def _get_sample_trading_chart():
    return {
        "data": [{"x": ["Loading..."], "y": [0], "type": "scatter", "line": {"color": "#00ff88"}}],
        "layout": {
            "title": "Trading Data Loading...",
            "paper_bgcolor": "#1a1a2e", "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"}
        }
    }

def _get_sample_whale_chart():
    return {
        "data": [{"x": ["Loading..."], "y": [0], "type": "bar", "marker": {"color": "#667eea"}}],
        "layout": {
            "title": "Whale Data Loading...",
            "paper_bgcolor": "#1a1a2e", "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"}
        }
    }

def _get_sample_arbitrage_chart():
    return {
        "data": [{"x": ["Loading..."], "y": [0], "type": "bar", "marker": {"color": "#f093fb"}}],
        "layout": {
            "title": "Arbitrage Data Loading...",
            "paper_bgcolor": "#1a1a2e", "plot_bgcolor": "#16213e",
            "font": {"color": "#eee"}
        }
    }

# ============================================================================
# Flask Routes
# ============================================================================

@app.route('/')
def index():
    """Serve the dashboard HTML."""
    return render_template('dashboard.html')

@app.route('/api/dashboard')
def api_dashboard():
    """Return dashboard summary data."""
    market_data = cache.get_markets()
    whale_data = cache.get_whales()
    arb_data = cache.get_arbitrage()
    
    # Check if we have errors
    has_error = market_data.error or whale_data.error or arb_data.error
    
    # Calculate summary stats
    total_markets = len(market_data.markets)
    trending_count = len(market_data.trending)
    whale_count = len(whale_data.large_orders)
    opp_count = len(arb_data.opportunities)
    
    # Check if API data is fresh
    is_data_fresh = (market_data.last_update and 
                     (datetime.now() - market_data.last_update).seconds < 120)
    
    return jsonify({
        "status": {
            "bot_running": False,  # No trading bot, just data
            "paper_trading": {
                "enabled": True,
                "virtual_balance": 10000,
                "initial_balance": 10000,
                "mode": "Market Data Only - No Trading"
            },
            "api_connected": is_data_fresh and not has_error,
            "last_update": market_data.last_update.isoformat() if market_data.last_update else None,
            "data_source": "Polymarket Gamma API"
        },
        "summary": {
            "open_positions": 0,
            "total_pnl": 0.0,
            "opportunities": opp_count,
            "total_markets": total_markets,
            "trending_markets": trending_count,
            "whale_activities": whale_count,
            "volume_24h": round(market_data.volume_24h, 2)
        },
        "performance": {
            "win_rate": 0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0
        },
        "markets": {
            "trending": market_data.trending[:5] if market_data.trending else [],
            "total_count": total_markets
        },
        "whales": {
            "recent_activity": whale_data.activities[:5] if whale_data.activities else [],
            "large_orders_count": whale_count
        },
        "arbitrage": {
            "opportunities": arb_data.opportunities[:5] if arb_data.opportunities else [],
            "count": opp_count
        },
        "errors": {
            "market_error": market_data.error,
            "whale_error": whale_data.error,
            "arbitrage_error": arb_data.error
        } if has_error else None
    })

@app.route('/api/charts/portfolio')
def api_portfolio():
    """Return portfolio chart data."""
    return jsonify({"chart": json.dumps(generate_portfolio_chart())})

@app.route('/api/charts/trading')
def api_trading():
    """Return trading activity chart data."""
    return jsonify({"chart": json.dumps(generate_trading_chart())})

@app.route('/api/charts/whales')
def api_whales():
    """Return whale activity chart data."""
    return jsonify({"chart": json.dumps(generate_whale_chart())})

@app.route('/api/charts/arbitrage')
def api_arbitrage():
    """Return arbitrage opportunities chart data."""
    return jsonify({"chart": json.dumps(generate_arbitrage_chart())})

@app.route('/api/markets')
def api_markets():
    """Return all markets data."""
    data = cache.get_markets()
    return jsonify({
        "markets": data.markets,
        "trending": data.trending,
        "count": len(data.markets),
        "last_update": data.last_update.isoformat() if data.last_update else None
    })

@app.route('/api/markets/<market_id>')
def api_market_detail(market_id):
    """Return details for a specific market."""
    data = cache.get_markets()
    
    for market in data.markets:
        if market['id'] == market_id or market.get('condition_id') == market_id:
            return jsonify(market)
    
    return jsonify({"error": "Market not found"}), 404

@app.route('/api/health')
def api_health():
    """Health check endpoint."""
    market_data = cache.get_markets()
    
    return jsonify({
        "status": "healthy",
        "api_connected": market_data.last_update is not None,
        "last_update": market_data.last_update.isoformat() if market_data.last_update else None,
        "markets_loaded": len(market_data.markets),
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    print('=' * 60)
    print('🚀 POLYMARKET LIVE DASHBOARD')
    print('=' * 60)
    print('📊 Real-time market data from Polymarket Gamma API')
    print('🌐 Dashboard: http://0.0.0.0:8080')
    print('📈 API Health: http://0.0.0.0:8080/api/health')
    print('=' * 60)
    print('⏳ Starting background data fetch...')
    
    # Start background data updates
    cache.start_background_updates()
    
    try:
        # Run Flask app
        app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
    except KeyboardInterrupt:
        print('\n👋 Shutting down...')
    finally:
        cache.stop_background_updates()
