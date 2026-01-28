"""
Market data visualization using Plotly.

This module provides interactive charts and dashboards for visualizing
prediction market data, trading activity, positions, and analysis results.
Integrates with the bot's trading systems for real-time monitoring.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class MarketVisualizer:
    """Create interactive visualizations for market and trading data."""
    
    def __init__(self, theme: str = "plotly_dark", config_path: str = "config.json"):
        """
        Initialize market visualizer.
        
        Args:
            theme: Plotly theme
            config_path: Path to configuration file
        """
        self.theme = theme
        self.chart_height = 500
        self.chart_width = 1000
        
        # Load config for colors
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                viz_config = config.get('visualization', {})
                self.theme = viz_config.get('theme', theme)
                self.chart_height = viz_config.get('chart_height', 500)
                self.chart_width = viz_config.get('chart_width', 1000)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        
        # Color scheme
        self.colors = {
            'primary': '#00ff88',
            'secondary': '#4287f5',
            'danger': '#ff6b6b',
            'warning': '#f5a742',
            'info': '#9b59b6',
            'neutral': '#95a5a6'
        }
    
    def plot_price_history(self, market_slug: str, 
                           price_data: List[Dict], 
                           title: Optional[str] = None) -> go.Figure:
        """
        Create line chart of price history.
        
        Args:
            market_slug: Market slug identifier
            price_data: List of price points with timestamp and price
            title: Chart title (optional)
            
        Returns:
            Plotly figure
        """
        if not price_data:
            return self._create_error_figure("No price data available")
        
        timestamps = []
        prices = []
        volumes = []
        
        for p in price_data:
            ts = p.get('timestamp')
            if isinstance(ts, (int, float)):
                timestamps.append(datetime.fromtimestamp(ts))
            else:
                timestamps.append(ts)
            prices.append(p.get('price', 0))
            volumes.append(p.get('volume', 0))
        
        # Create subplots with volume
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3],
            subplot_titles=('Price', 'Volume')
        )
        
        # Price line
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=prices,
            mode='lines',
            name='Price',
            line=dict(color=self.colors['primary'], width=2),
            hovertemplate='Price: %{y:.4f}<br>%{x}<extra></extra>'
        ), row=1, col=1)
        
        # Volume bars
        if any(volumes):
            fig.add_trace(go.Bar(
                x=timestamps,
                y=volumes,
                name='Volume',
                marker_color=self.colors['secondary'],
                opacity=0.6,
                hovertemplate='Volume: $%{y:.0f}<extra></extra>'
            ), row=2, col=1)
        
        fig.update_layout(
            title=title or f"Price History: {market_slug}",
            template=self.theme,
            height=self.chart_height,
            width=self.chart_width,
            hovermode='x unified',
            showlegend=False
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume ($)", row=2, col=1)
        
        return fig
    
    def plot_sentiment_dashboard(self, market_slug: str, 
                                  sentiment_data: Dict[str, Any],
                                  price_data: List[Dict]) -> go.Figure:
        """
        Create comprehensive sentiment dashboard.
        
        Args:
            market_slug: Market slug identifier
            sentiment_data: Sentiment analysis results
            price_data: Price history data
            
        Returns:
            Plotly figure with multiple subplots
        """
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Price History',
                'Sentiment Score',
                'Volume Trend',
                'Momentum'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "indicator"}],
                [{"type": "bar"}, {"type": "indicator"}]
            ]
        )
        
        # Price history
        if price_data:
            timestamps = []
            prices = []
            for p in price_data[-48:]:  # Last 48 points
                ts = p.get('timestamp')
                if isinstance(ts, (int, float)):
                    timestamps.append(datetime.fromtimestamp(ts))
                else:
                    timestamps.append(ts)
                prices.append(p.get('price', 0))
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=prices,
                    mode='lines',
                    name='Price',
                    line=dict(color=self.colors['primary'])
                ),
                row=1, col=1
            )
        
        # Sentiment indicator
        sentiment_score = sentiment_data.get('sentiment_score', 0)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=sentiment_score * 100,
                title={'text': "Sentiment"},
                delta={'reference': 0},
                gauge={
                    'axis': {'range': [-100, 100]},
                    'bar': {'color': self.colors['primary']},
                    'steps': [
                        {'range': [-100, -30], 'color': self.colors['danger']},
                        {'range': [-30, 30], 'color': self.colors['neutral']},
                        {'range': [30, 100], 'color': self.colors['primary']}
                    ],
                    'threshold': {
                        'line': {'color': 'white', 'width': 4},
                        'thickness': 0.75,
                        'value': sentiment_score * 100
                    }
                }
            ),
            row=1, col=2
        )
        
        # Volume bars from price data
        if price_data:
            volumes = [p.get('volume', 0) for p in price_data[-24:]]
            fig.add_trace(
                go.Bar(
                    x=list(range(len(volumes))),
                    y=volumes,
                    name='Volume',
                    marker_color=self.colors['secondary']
                ),
                row=2, col=1
            )
        
        # Momentum indicator
        momentum = sentiment_data.get('momentum', 0)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=momentum * 100,
                title={'text': "Momentum (%)"},
                gauge={
                    'axis': {'range': [-100, 100]},
                    'bar': {'color': self.colors['info']},
                    'steps': [
                        {'range': [-100, 0], 'color': self.colors['danger']},
                        {'range': [0, 100], 'color': self.colors['primary']}
                    ]
                }
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title=f"Market Dashboard: {market_slug}",
            template=self.theme,
            height=self.chart_height * 1.3,
            width=self.chart_width,
            showlegend=False
        )
        
        return fig
    
    def plot_portfolio_overview(self, positions: List[Dict], 
                                 pnl_history: List[Dict]) -> go.Figure:
        """
        Create portfolio overview dashboard.
        
        Args:
            positions: List of position dictionaries
            pnl_history: P&L history data
            
        Returns:
            Plotly figure
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'P&L Over Time',
                'Position Distribution',
                'Position Sizes',
                'Win/Loss Ratio'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "indicator"}]
            ]
        )
        
        # P&L line
        if pnl_history:
            timestamps = [datetime.fromtimestamp(p.get('timestamp', 0)) for p in pnl_history]
            pnl_values = [p.get('pnl', 0) for p in pnl_history]
            cumulative = []
            cumsum = 0
            for pnl in pnl_values:
                cumsum += pnl
                cumulative.append(cumsum)
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=cumulative,
                    mode='lines',
                    name='Cumulative P&L',
                    line=dict(color=self.colors['primary']),
                    fill='tozeroy'
                ),
                row=1, col=1
            )
        
        # Position distribution by direction
        if positions:
            long_count = sum(1 for p in positions if p.get('direction') == 'up')
            short_count = sum(1 for p in positions if p.get('direction') == 'down')
            
            fig.add_trace(
                go.Pie(
                    labels=['Long (Up)', 'Short (Down)'],
                    values=[long_count, short_count],
                    marker_colors=[self.colors['primary'], self.colors['danger']]
                ),
                row=1, col=2
            )
        
        # Position sizes
        if positions:
            position_names = [p.get('symbol', 'Unknown')[:15] for p in positions]
            sizes = [p.get('size_usd', 0) for p in positions]
            colors = [self.colors['primary'] if p.get('pnl', 0) >= 0 
                     else self.colors['danger'] for p in positions]
            
            fig.add_trace(
                go.Bar(
                    x=position_names,
                    y=sizes,
                    marker_color=colors,
                    name='Position Size'
                ),
                row=2, col=1
            )
        
        # Win rate indicator
        if positions:
            wins = sum(1 for p in positions if p.get('pnl', 0) > 0)
            total = len(positions)
            win_rate = (wins / total * 100) if total > 0 else 0
            
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=win_rate,
                    title={'text': "Win Rate"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': self.colors['primary']},
                        'steps': [
                            {'range': [0, 40], 'color': self.colors['danger']},
                            {'range': [40, 60], 'color': self.colors['warning']},
                            {'range': [60, 100], 'color': self.colors['primary']}
                        ]
                    }
                ),
                row=2, col=2
            )
        
        fig.update_layout(
            title="Portfolio Overview",
            template=self.theme,
            height=self.chart_height * 1.3,
            width=self.chart_width,
            showlegend=False
        )
        
        return fig
    
    def plot_trading_activity(self, trades: List[Dict]) -> go.Figure:
        """
        Visualize recent trading activity.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Plotly figure
        """
        if not trades:
            return self._create_error_figure("No trade data available")
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Trade P&L', 'Trade Volume Over Time'),
            vertical_spacing=0.15
        )
        
        # Trade P&L bars
        timestamps = []
        pnls = []
        colors = []
        
        for trade in trades:
            ts = trade.get('timestamp', 0)
            timestamps.append(datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else ts)
            pnl = trade.get('pnl', 0)
            pnls.append(pnl)
            colors.append(self.colors['primary'] if pnl >= 0 else self.colors['danger'])
        
        fig.add_trace(
            go.Bar(
                x=timestamps,
                y=pnls,
                marker_color=colors,
                name='P&L'
            ),
            row=1, col=1
        )
        
        # Cumulative volume
        volumes = []
        cumsum = 0
        for trade in trades:
            cumsum += trade.get('size_usd', 0)
            volumes.append(cumsum)
        
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=volumes,
                mode='lines',
                name='Cumulative Volume',
                line=dict(color=self.colors['secondary']),
                fill='tozeroy'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title="Trading Activity",
            template=self.theme,
            height=self.chart_height * 1.2,
            width=self.chart_width,
            showlegend=False
        )
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume ($)", row=2, col=1)
        
        return fig
    
    def plot_whale_activity(self, whale_data: List[Dict]) -> go.Figure:
        """
        Visualize whale tracking data.
        
        Args:
            whale_data: List of whale activity records
            
        Returns:
            Plotly figure
        """
        if not whale_data:
            return self._create_error_figure("No whale data available")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Whale Volume Over Time',
                'Top Whales',
                'Buy/Sell Distribution',
                'Whale Confidence'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "pie"}, {"type": "histogram"}]
            ]
        )
        
        # Volume over time
        timestamps = []
        volumes = []
        for w in whale_data:
            ts = w.get('timestamp', 0)
            timestamps.append(datetime.fromtimestamp(ts) if isinstance(ts, (int, float)) else ts)
            volumes.append(w.get('size_usd', 0))
        
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=volumes,
                mode='lines+markers',
                name='Whale Volume',
                line=dict(color=self.colors['info'])
            ),
            row=1, col=1
        )
        
        # Top whales by volume
        sorted_whales = sorted(whale_data, key=lambda x: x.get('size_usd', 0), reverse=True)[:10]
        addresses = [w.get('trader_address', 'Unknown')[:10] + '...' for w in sorted_whales]
        sizes = [w.get('size_usd', 0) for w in sorted_whales]
        
        fig.add_trace(
            go.Bar(
                x=addresses,
                y=sizes,
                marker_color=self.colors['info']
            ),
            row=1, col=2
        )
        
        # Buy/sell distribution
        buy_volume = sum(w.get('size_usd', 0) for w in whale_data 
                        if w.get('side', '').startswith('buy'))
        sell_volume = sum(w.get('size_usd', 0) for w in whale_data 
                         if w.get('side', '').startswith('sell'))
        
        fig.add_trace(
            go.Pie(
                labels=['Buying', 'Selling'],
                values=[buy_volume, sell_volume],
                marker_colors=[self.colors['primary'], self.colors['danger']]
            ),
            row=2, col=1
        )
        
        # Confidence distribution
        confidences = [w.get('confidence', 0.5) * 100 for w in whale_data]
        fig.add_trace(
            go.Histogram(
                x=confidences,
                nbinsx=10,
                marker_color=self.colors['secondary']
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title="Whale Activity Analysis",
            template=self.theme,
            height=self.chart_height * 1.3,
            width=self.chart_width,
            showlegend=False
        )
        
        return fig
    
    def plot_arbitrage_opportunities(self, opportunities: List[Dict]) -> go.Figure:
        """
        Visualize arbitrage opportunities.
        
        Args:
            opportunities: List of arbitrage opportunity dictionaries
            
        Returns:
            Plotly figure
        """
        if not opportunities:
            return self._create_error_figure("No arbitrage opportunities available")
        
        # Sort by expected profit
        sorted_opps = sorted(opportunities, 
                            key=lambda x: x.get('expected_profit', 0), 
                            reverse=True)[:20]
        
        fig = go.Figure()
        
        symbols = [o.get('symbol', 'Unknown') for o in sorted_opps]
        profits = [o.get('expected_profit', 0) * 100 for o in sorted_opps]
        divergences = [abs(o.get('divergence', 0)) * 100 for o in sorted_opps]
        
        # Expected profit bars
        fig.add_trace(go.Bar(
            x=symbols,
            y=profits,
            name='Expected Profit (%)',
            marker_color=self.colors['primary']
        ))
        
        # Divergence line
        fig.add_trace(go.Scatter(
            x=symbols,
            y=divergences,
            mode='lines+markers',
            name='Divergence (%)',
            line=dict(color=self.colors['warning'], width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="Arbitrage Opportunities",
            xaxis_title="Market",
            yaxis_title="Expected Profit (%)",
            yaxis2=dict(
                title="Divergence (%)",
                overlaying='y',
                side='right'
            ),
            template=self.theme,
            height=self.chart_height,
            width=self.chart_width,
            hovermode='x unified'
        )
        
        return fig
    
    def create_full_dashboard(self, data: Dict[str, Any]) -> go.Figure:
        """
        Create comprehensive trading dashboard.
        
        Args:
            data: Dictionary containing all dashboard data
            
        Returns:
            Plotly figure
        """
        # Create tabs or use subplots for different sections
        fig = make_subplots(
            rows=3, cols=3,
            subplot_titles=(
                'Portfolio P&L', 'Win Rate', 'Active Positions',
                'Recent Trades', 'Market Sentiment', 'Volume',
                'Arbitrage Ops', 'Whale Activity', 'Risk Status'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "indicator"}, {"type": "indicator"}],
                [{"type": "bar"}, {"type": "indicator"}, {"type": "bar"}],
                [{"type": "bar"}, {"type": "scatter"}, {"type": "indicator"}]
            ],
            vertical_spacing=0.1,
            horizontal_spacing=0.05
        )
        
        # Portfolio P&L
        pnl_history = data.get('pnl_history', [])
        if pnl_history:
            timestamps = [datetime.fromtimestamp(p.get('timestamp', 0)) for p in pnl_history]
            cumulative_pnl = []
            cumsum = 0
            for p in pnl_history:
                cumsum += p.get('pnl', 0)
                cumulative_pnl.append(cumsum)
            
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=cumulative_pnl,
                    mode='lines',
                    name='P&L',
                    line=dict(color=self.colors['primary']),
                    fill='tozeroy'
                ),
                row=1, col=1
            )
        
        # Win rate
        stats = data.get('performance_stats', {})
        win_rate = stats.get('win_rate', 0)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=win_rate,
                title={'text': "Win Rate %"},
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': self.colors['primary']}}
            ),
            row=1, col=2
        )
        
        # Active positions
        open_positions = stats.get('open_positions', 0)
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=open_positions,
                title={'text': "Open Positions"},
                delta={'reference': 5}  # Reference to max positions
            ),
            row=1, col=3
        )
        
        # Update layout
        fig.update_layout(
            title="Polymarket Trading Bot - Live Dashboard",
            template=self.theme,
            height=self.chart_height * 1.8,
            width=self.chart_width,
            showlegend=False
        )
        
        return fig
    
    def _create_error_figure(self, error_message: str) -> go.Figure:
        """
        Create a figure displaying an error message.
        
        Args:
            error_message: Error message to display
            
        Returns:
            Plotly figure with error
        """
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color=self.colors['danger'])
        )
        
        fig.update_layout(
            template=self.theme,
            height=self.chart_height,
            width=self.chart_width
        )
        
        return fig
    
    def save_figure(self, fig: go.Figure, filename: str, format: str = 'html') -> None:
        """
        Save figure to file.
        
        Args:
            fig: Plotly figure
            filename: Output filename
            format: Output format ('html', 'png', 'svg', 'pdf')
        """
        if format == 'html':
            fig.write_html(filename)
        else:
            fig.write_image(filename)
    
    def to_json(self, fig: go.Figure) -> str:
        """
        Convert figure to JSON for web rendering.
        
        Args:
            fig: Plotly figure
            
        Returns:
            JSON string
        """
        return fig.to_json()
