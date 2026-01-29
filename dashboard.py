#!/usr/bin/env python3
"""
Polymarket Trading Bot - Web Dashboard

A Flask-based web server that serves the Plotly dashboard for monitoring
trading activity, P&L, positions, and market analytics.

Usage:
    python dashboard.py              # Start dashboard server
    python dashboard.py --port 8080  # Start on custom port
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Import bot modules
from visualization import MarketVisualizer
from utils import Config, format_usd, format_percentage

# Try to import optional bot components
try:
    from position_manager import PositionManager
    from risk_manager import RiskManager
    from polymarket_client import PolymarketClient
    from arbitrage_detector import ArbitrageDetector
    from whale_tracker import WhaleTracker
    from wallet_tracker import WalletTracker
    from sentiment_tracker import SentimentTracker
    from historical_analyzer import HistoricalAnalyzer
    BOT_COMPONENTS_AVAILABLE = True
except ImportError as e:
    BOT_COMPONENTS_AVAILABLE = False
    # Create stubs for optional components
    class MockClient:
        pass
    PolymarketClient = MockClient
    ArbitrageDetector = MockClient
    WhaleTracker = MockClient
    WalletTracker = MockClient
    SentimentTracker = MockClient
    HistoricalAnalyzer = MockClient
    RiskManager = MockClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Dashboard")

# Create Flask app
app = Flask(__name__)
CORS(app)

# Global state
dashboard_state = {
    'bot_running': False,
    'positions': [],
    'trades': [],
    'pnl_history': [],
    'opportunities': [],
    'whale_activity': [],
    'market_data': {},
    'performance_stats': {},
    'risk_status': {},
    'last_update': None,
    'paper_trading': {
        'enabled': False,
        'virtual_balance': 10000.0,
        'initial_balance': 10000.0
    }
}

# Initialize components
config = Config("config.json")
visualizer = MarketVisualizer(config_path="config.json")

# Initialize bot components if available
if BOT_COMPONENTS_AVAILABLE:
    try:
        poly_client = PolymarketClient()
        arbitrage_detector = ArbitrageDetector()
        whale_tracker = WhaleTracker()
        wallet_tracker = WalletTracker()
        sentiment_tracker = SentimentTracker()
        historical_analyzer = HistoricalAnalyzer()
        risk_manager = RiskManager()
        logger.info("Bot components initialized successfully")
    except Exception as e:
        logger.warning(f"Bot components initialization failed: {e}")
        BOT_COMPONENTS_AVAILABLE = False
else:
    logger.info("Running dashboard without bot components (visualization only)")


@app.route('/')
def index():
    """Render main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get bot status."""
    return jsonify({
        'bot_running': dashboard_state['bot_running'],
        'components_available': BOT_COMPONENTS_AVAILABLE,
        'last_update': dashboard_state['last_update'],
        'timestamp': datetime.now().isoformat(),
        'paper_trading': dashboard_state.get('paper_trading', {'enabled': False})
    })


@app.route('/api/paper-trading/stats')
def api_paper_trading_stats():
    """Get paper trading statistics."""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from paper_trader import PaperTrader
        
        trader = PaperTrader()
        stats = trader.get_performance_stats()
        
        return jsonify({
            'enabled': True,
            'stats': stats,
            'open_positions': [t.to_dict() for t in trader.get_open_positions()],
            'recent_trades': [t.to_dict() for t in trader.get_closed_positions(20)]
        })
    except Exception as e:
        logger.error(f"Error getting paper trading stats: {e}")
        return jsonify({
            'enabled': False,
            'error': str(e)
        })


@app.route('/api/positions')
def api_positions():
    """Get current positions."""
    return jsonify({
        'positions': dashboard_state['positions'],
        'count': len(dashboard_state['positions'])
    })


@app.route('/api/trades')
def api_trades():
    """Get recent trades."""
    limit = request.args.get('limit', 50, type=int)
    trades = dashboard_state['trades'][-limit:]
    return jsonify({
        'trades': trades,
        'count': len(trades)
    })


@app.route('/api/pnl')
def api_pnl():
    """Get P&L data."""
    return jsonify({
        'pnl_history': dashboard_state['pnl_history'],
        'total_pnl': sum(p.get('pnl', 0) for p in dashboard_state['pnl_history']),
        'performance_stats': dashboard_state.get('performance_stats', {})
    })


@app.route('/api/opportunities')
def api_opportunities():
    """Get arbitrage opportunities."""
    return jsonify({
        'opportunities': dashboard_state['opportunities'],
        'count': len(dashboard_state['opportunities'])
    })


@app.route('/api/whales')
def api_whales():
    """Get whale activity."""
    return jsonify({
        'whale_activity': dashboard_state['whale_activity'],
        'count': len(dashboard_state['whale_activity'])
    })


@app.route('/api/market/<market_slug>')
def api_market(market_slug):
    """Get market data."""
    if not BOT_COMPONENTS_AVAILABLE:
        return jsonify({'error': 'Bot components not available'})
    
    try:
        # Get sentiment analysis
        sentiment = sentiment_tracker.analyze_market(market_slug)
        
        # Get historical analysis
        history = historical_analyzer.analyze_market_history(market_slug, days=7)
        
        # Get patterns
        patterns = historical_analyzer.find_patterns(market_slug, days=14)
        
        return jsonify({
            'market_slug': market_slug,
            'sentiment': sentiment,
            'history': history,
            'patterns': patterns
        })
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return jsonify({'error': str(e)})


@app.route('/api/wallet/<address>')
def api_wallet(address):
    """Get wallet analysis."""
    if not BOT_COMPONENTS_AVAILABLE:
        return jsonify({'error': 'Bot components not available'})
    
    try:
        days = request.args.get('days', 30, type=int)
        performance = wallet_tracker.calculate_performance(address, days)
        strategies = wallet_tracker.detect_strategies(address, days)
        
        return jsonify({
            'address': address,
            'performance': performance,
            'strategies': strategies
        })
    except Exception as e:
        logger.error(f"Error getting wallet data: {e}")
        return jsonify({'error': str(e)})


@app.route('/api/charts/portfolio')
def api_chart_portfolio():
    """Get portfolio chart JSON."""
    try:
        fig = visualizer.plot_portfolio_overview(
            dashboard_state['positions'],
            dashboard_state['pnl_history']
        )
        return jsonify({'chart': fig.to_json()})
    except Exception as e:
        logger.error(f"Error generating portfolio chart: {e}")
        return jsonify({'error': str(e)})


@app.route('/api/charts/trading')
def api_chart_trading():
    """Get trading activity chart JSON."""
    try:
        fig = visualizer.plot_trading_activity(dashboard_state['trades'])
        return jsonify({'chart': fig.to_json()})
    except Exception as e:
        logger.error(f"Error generating trading chart: {e}")
        return jsonify({'error': str(e)})


@app.route('/api/charts/whales')
def api_chart_whales():
    """Get whale activity chart JSON."""
    try:
        fig = visualizer.plot_whale_activity(dashboard_state['whale_activity'])
        return jsonify({'chart': fig.to_json()})
    except Exception as e:
        logger.error(f"Error generating whale chart: {e}")
        return jsonify({'error': str(e)})


@app.route('/api/charts/arbitrage')
def api_chart_arbitrage():
    """Get arbitrage opportunities chart JSON."""
    try:
        fig = visualizer.plot_arbitrage_opportunities(dashboard_state['opportunities'])
        return jsonify({'chart': fig.to_json()})
    except Exception as e:
        logger.error(f"Error generating arbitrage chart: {e}")
        return jsonify({'error': str(e)})


@app.route('/api/dashboard')
def api_dashboard():
    """Get full dashboard data."""
    return jsonify({
        'status': {
            'bot_running': dashboard_state['bot_running'],
            'last_update': dashboard_state['last_update'],
            'components_available': BOT_COMPONENTS_AVAILABLE
        },
        'summary': {
            'open_positions': len(dashboard_state['positions']),
            'total_pnl': sum(p.get('pnl', 0) for p in dashboard_state['pnl_history']),
            'recent_trades': len(dashboard_state['trades']),
            'opportunities': len(dashboard_state['opportunities']),
            'whale_signals': len(dashboard_state['whale_activity'])
        },
        'performance': dashboard_state.get('performance_stats', {}),
        'risk': dashboard_state.get('risk_status', {})
    })


@app.route('/api/update', methods=['POST'])
def api_update():
    """Update dashboard state with new data from bot."""
    try:
        data = request.get_json()
        
        if 'positions' in data:
            dashboard_state['positions'] = data['positions']
        if 'trades' in data:
            dashboard_state['trades'] = data['trades']
        if 'pnl_history' in data:
            dashboard_state['pnl_history'] = data['pnl_history']
        if 'opportunities' in data:
            dashboard_state['opportunities'] = data['opportunities']
        if 'whale_activity' in data:
            dashboard_state['whale_activity'] = data['whale_activity']
        if 'performance_stats' in data:
            dashboard_state['performance_stats'] = data['performance_stats']
        if 'risk_status' in data:
            dashboard_state['risk_status'] = data['risk_status']
        if 'bot_running' in data:
            dashboard_state['bot_running'] = data['bot_running']
        
        dashboard_state['last_update'] = datetime.now().isoformat()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)})


def generate_mock_data():
    """Generate mock data for demonstration."""
    import random
    
    # Mock positions
    dashboard_state['positions'] = [
        {
            'position_id': f'pos_{i}',
            'symbol': f'MARKET_{i}',
            'direction': 'up' if i % 2 == 0 else 'down',
            'size_usd': random.uniform(50, 500),
            'entry_price': random.uniform(0.3, 0.7),
            'pnl': random.uniform(-20, 50)
        }
        for i in range(5)
    ]
    
    # Mock P&L history
    now = datetime.now()
    pnl = 0
    for i in range(24):
        pnl += random.uniform(-5, 10)
        dashboard_state['pnl_history'].append({
            'timestamp': (now - timedelta(hours=24-i)).timestamp(),
            'pnl': pnl
        })
    
    # Mock trades
    for i in range(20):
        dashboard_state['trades'].append({
            'timestamp': (now - timedelta(minutes=i*30)).timestamp(),
            'symbol': f'MARKET_{i%5}',
            'side': 'buy' if i % 2 == 0 else 'sell',
            'size_usd': random.uniform(50, 500),
            'pnl': random.uniform(-15, 25)
        })
    
    # Mock opportunities
    for i in range(8):
        dashboard_state['opportunities'].append({
            'symbol': f'MARKET_{i}',
            'expected_profit': random.uniform(0.02, 0.15),
            'divergence': random.uniform(-0.1, 0.1),
            'confidence': random.uniform(0.5, 0.9)
        })
    
    # Mock whale activity
    for i in range(10):
        dashboard_state['whale_activity'].append({
            'timestamp': (now - timedelta(minutes=i*15)).timestamp(),
            'trader_address': f'0x{random.randint(1000000000, 9999999999)}',
            'size_usd': random.uniform(5000, 50000),
            'side': 'buy_yes' if i % 2 == 0 else 'buy_no',
            'confidence': random.uniform(0.6, 0.95)
        })
    
    # Mock performance stats
    dashboard_state['performance_stats'] = {
        'total_pnl': sum(p.get('pnl', 0) for p in dashboard_state['positions']),
        'total_trades': len(dashboard_state['trades']),
        'wins': sum(1 for t in dashboard_state['trades'] if t.get('pnl', 0) > 0),
        'losses': sum(1 for t in dashboard_state['trades'] if t.get('pnl', 0) <= 0),
        'win_rate': 65.0,
        'open_positions': len(dashboard_state['positions']),
        'avg_pnl_per_trade': 12.5
    }
    
    # Mock risk status
    dashboard_state['risk_status'] = {
        'daily_pnl': 45.20,
        'max_daily_loss': 1000.0,
        'remaining_daily_budget': 954.80,
        'emergency_shutdown': False,
        'stop_loss_pct': 0.15,
        'take_profit_pct': 0.90
    }
    
    # Load paper trading data
    try:
        from paper_trader import PaperTrader
        trader = PaperTrader()
        stats = trader.get_performance_stats()
        
        dashboard_state['paper_trading'] = {
            'enabled': True,
            'virtual_balance': stats['current_balance'],
            'initial_balance': stats['initial_balance']
        }
    except Exception as e:
        logger.debug(f"Could not load paper trading data: {e}")
        dashboard_state['paper_trading'] = {
            'enabled': False,
            'virtual_balance': 0.0,
            'initial_balance': 0.0
        }
    
    dashboard_state['bot_running'] = True
    dashboard_state['last_update'] = now.isoformat()


def create_templates():
    """Create HTML templates if they don't exist."""
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Trading Bot Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
        }
        
        .paper-trading-banner {
            background: linear-gradient(90deg, #4a148c 0%, #7b1fa2 50%, #4a148c 100%);
            color: #fff;
            padding: 0.75rem 2rem;
            text-align: center;
            font-weight: bold;
            font-size: 1rem;
            display: none;
        }
        
        .paper-trading-banner.visible {
            display: block;
        }
        
        .header {
            background: #16213e;
            padding: 1rem 2rem;
            border-bottom: 2px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            color: #00ff88;
            font-size: 1.5rem;
        }
        
        .status {
            display: flex;
            gap: 1rem;
            align-items: center;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff6b6b;
        }
        
        .status-indicator.running {
            background: #00ff88;
            box-shadow: 0 0 10px #00ff88;
        }
        
        .container {
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: #16213e;
            border-radius: 8px;
            padding: 1.5rem;
            border: 1px solid #0f3460;
        }
        
        .card.paper-mode {
            background: linear-gradient(135deg, #16213e 0%, #2d1b4e 100%);
            border: 1px solid #7b1fa2;
        }
        
        .card h3 {
            color: #888;
            font-size: 0.875rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        
        .card .value {
            font-size: 2rem;
            font-weight: bold;
            color: #00ff88;
        }
        
        .card .value.negative {
            color: #ff6b6b;
        }
        
        .card .value.paper {
            color: #ce93d8;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
        }
        
        .chart-container {
            background: #16213e;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #0f3460;
        }
        
        .chart-container h3 {
            color: #fff;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #0f3460;
        }
        
        .loading {
            text-align: center;
            padding: 3rem;
            color: #888;
        }
        
        .error {
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid #ff6b6b;
            color: #ff6b6b;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
        }
    </style>
</head>
<body>
    <div id="paper-banner" class="paper-trading-banner">
        📝 PAPER TRADING MODE - All trades are SIMULATED - No real money at risk
    </div>
    
    <div class="header">
        <h1>🤖 Polymarket Trading Bot</h1>
        <div class="status">
            <span id="status-text">Loading...</span>
            <div id="status-indicator" class="status-indicator"></div>
        </div>
    </div>
    
    <div class="container">
        <div class="summary-cards" id="summary-cards">
            <div class="card">
                <h3>Open Positions</h3>
                <div class="value" id="open-positions">-</div>
            </div>
            <div class="card">
                <h3>Total P&L</h3>
                <div class="value" id="total-pnl">-</div>
            </div>
            <div class="card">
                <h3>Win Rate</h3>
                <div class="value" id="win-rate">-</div>
            </div>
            <div class="card">
                <h3>Opportunities</h3>
                <div class="value" id="opportunities">-</div>
            </div>
        </div>
        
        <div class="summary-cards" id="paper-trading-cards" style="display: none;">
            <div class="card paper-mode">
                <h3>💰 Virtual Balance</h3>
                <div class="value paper" id="virtual-balance">-</div>
            </div>
            <div class="card paper-mode">
                <h3>📊 Total Trades</h3>
                <div class="value paper" id="paper-total-trades">-</div>
            </div>
            <div class="card paper-mode">
                <h3>📈 Sharpe Ratio</h3>
                <div class="value paper" id="sharpe-ratio">-</div>
            </div>
            <div class="card paper-mode">
                <h3>📉 Max Drawdown</h3>
                <div class="value" id="max-drawdown">-</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h3>Portfolio Overview</h3>
                <div id="portfolio-chart" class="loading">Loading chart...</div>
            </div>
            <div class="chart-container">
                <h3>Trading Activity</h3>
                <div id="trading-chart" class="loading">Loading chart...</div>
            </div>
            <div class="chart-container">
                <h3>Whale Activity</h3>
                <div id="whale-chart" class="loading">Loading chart...</div>
            </div>
            <div class="chart-container">
                <h3>Arbitrage Opportunities</h3>
                <div id="arbitrage-chart" class="loading">Loading chart...</div>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = '';
        let paperTradingEnabled = false;
        
        async function fetchData() {
            try {
                const [dashboardRes, paperRes] = await Promise.all([
                    fetch(`${API_BASE}/api/dashboard`),
                    fetch(`${API_BASE}/api/paper-trading/stats`)
                ]);
                
                const data = await dashboardRes.json();
                const paperData = await paperRes.json();
                
                updateDashboard(data);
                updatePaperTrading(paperData);
            } catch (error) {
                console.error('Error fetching dashboard data:', error);
            }
        }
        
        function updateDashboard(data) {
            // Update status
            const statusIndicator = document.getElementById('status-indicator');
            const statusText = document.getElementById('status-text');
            
            if (data.status.bot_running) {
                statusIndicator.classList.add('running');
                statusText.textContent = 'Bot Running';
            } else {
                statusIndicator.classList.remove('running');
                statusText.textContent = 'Bot Stopped';
            }
            
            // Update summary cards
            document.getElementById('open-positions').textContent = data.summary.open_positions;
            
            const pnlElement = document.getElementById('total-pnl');
            pnlElement.textContent = `$${data.summary.total_pnl.toFixed(2)}`;
            pnlElement.classList.toggle('negative', data.summary.total_pnl < 0);
            
            document.getElementById('win-rate').textContent = 
                data.performance.win_rate ? `${data.performance.win_rate.toFixed(1)}%` : '-';
            document.getElementById('opportunities').textContent = data.summary.opportunities;
        }
        
        function updatePaperTrading(data) {
            if (!data.enabled) return;
            
            paperTradingEnabled = true;
            
            // Show paper trading banner
            document.getElementById('paper-banner').classList.add('visible');
            
            // Show paper trading cards
            document.getElementById('paper-trading-cards').style.display = 'grid';
            
            // Update paper trading stats
            const stats = data.stats;
            document.getElementById('virtual-balance').textContent = `$${stats.current_balance.toFixed(2)}`;
            document.getElementById('paper-total-trades').textContent = stats.total_trades;
            document.getElementById('sharpe-ratio').textContent = stats.sharpe_ratio.toFixed(2);
            
            const drawdownEl = document.getElementById('max-drawdown');
            drawdownEl.textContent = `${stats.max_drawdown_percent.toFixed(2)}%`;
            drawdownEl.classList.toggle('negative', stats.max_drawdown > 0);
        }
        
        async function loadCharts() {
            // Load portfolio chart
            try {
                const response = await fetch(`${API_BASE}/api/charts/portfolio`);
                const data = await response.json();
                if (data.chart) {
                    const chartData = JSON.parse(data.chart);
                    Plotly.newPlot('portfolio-chart', chartData.data, chartData.layout);
                }
            } catch (error) {
                document.getElementById('portfolio-chart').innerHTML = 
                    '<div class="error">Error loading chart</div>';
            }
            
            // Load trading chart
            try {
                const response = await fetch(`${API_BASE}/api/charts/trading`);
                const data = await response.json();
                if (data.chart) {
                    const chartData = JSON.parse(data.chart);
                    Plotly.newPlot('trading-chart', chartData.data, chartData.layout);
                }
            } catch (error) {
                document.getElementById('trading-chart').innerHTML = 
                    '<div class="error">Error loading chart</div>';
            }
            
            // Load whale chart
            try {
                const response = await fetch(`${API_BASE}/api/charts/whales`);
                const data = await response.json();
                if (data.chart) {
                    const chartData = JSON.parse(data.chart);
                    Plotly.newPlot('whale-chart', chartData.data, chartData.layout);
                }
            } catch (error) {
                document.getElementById('whale-chart').innerHTML = 
                    '<div class="error">Error loading chart</div>';
            }
            
            // Load arbitrage chart
            try {
                const response = await fetch(`${API_BASE}/api/charts/arbitrage`);
                const data = await response.json();
                if (data.chart) {
                    const chartData = JSON.parse(data.chart);
                    Plotly.newPlot('arbitrage-chart', chartData.data, chartData.layout);
                }
            } catch (error) {
                document.getElementById('arbitrage-chart').innerHTML = 
                    '<div class="error">Error loading chart</div>';
            }
        }
        
        // Initial load
        fetchData();
        loadCharts();
        
        // Refresh every 30 seconds
        setInterval(fetchData, 30000);
        setInterval(loadCharts, 60000);
    </script>
</body>
</html>
'''
    
    template_file = templates_dir / "dashboard.html"
    if not template_file.exists():
        template_file.write_text(dashboard_html)
        logger.info(f"Created template: {template_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Polymarket Trading Bot Dashboard')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--mock', action='store_true', help='Use mock data for demo')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Create templates
    create_templates()
    
    # Generate mock data if requested
    if args.mock:
        logger.info("Generating mock data for demonstration...")
        generate_mock_data()
    
    # Run Flask app
    logger.info(f"Starting dashboard server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
