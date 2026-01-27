"""
Exchange price monitoring via WebSocket.

Connects to cryptocurrency exchanges and monitors real-time price feeds
for configured trading pairs.
"""

import asyncio
import ccxt.async_support as ccxt
from typing import Dict, Optional, Callable, Any
from datetime import datetime
import logging


class ExchangeMonitor:
    """
    Monitor cryptocurrency prices on exchanges via WebSocket.
    
    Maintains real-time price data and notifies subscribers of updates.
    """
    
    def __init__(self, exchange_name: str, symbols: list[str], 
                 api_key: str = "", api_secret: str = "",
                 testnet: bool = False):
        """
        Initialize exchange monitor.
        
        Args:
            exchange_name: Name of exchange (e.g., 'binance', 'coinbase')
            symbols: List of symbols to monitor (e.g., ['BTC/USDT'])
            api_key: Exchange API key
            api_secret: Exchange API secret
            testnet: Whether to use testnet
        """
        self.exchange_name = exchange_name
        self.symbols = symbols
        self.logger = logging.getLogger(f"ExchangeMonitor.{exchange_name}")
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        if testnet:
            self.exchange.set_sandbox_mode(True)
        
        # Price cache
        self.prices: Dict[str, float] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # Callbacks
        self.price_callbacks: list[Callable] = []
        
        # Running state
        self.running = False
        self._tasks: list[asyncio.Task] = []
    
    def add_price_callback(self, callback: Callable[[str, float, datetime], None]) -> None:
        """
        Add callback to be notified of price updates.
        
        Args:
            callback: Function(symbol, price, timestamp) to call on price update
        """
        self.price_callbacks.append(callback)
    
    async def start(self) -> None:
        """Start monitoring exchange prices."""
        if self.running:
            self.logger.warning("Monitor already running")
            return
        
        self.running = True
        self.logger.info(f"Starting monitor for {self.exchange_name} with symbols: {self.symbols}")
        
        # Check if exchange supports WebSocket
        if self.exchange.has['watchTicker']:
            self._tasks = [
                asyncio.create_task(self._watch_ticker(symbol))
                for symbol in self.symbols
            ]
        else:
            # Fallback to polling
            self.logger.warning(f"{self.exchange_name} doesn't support WebSocket, using polling")
            self._tasks = [asyncio.create_task(self._poll_prices())]
    
    async def stop(self) -> None:
        """Stop monitoring."""
        self.running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close exchange connection
        await self.exchange.close()
        
        self.logger.info(f"Stopped monitor for {self.exchange_name}")
    
    async def _watch_ticker(self, symbol: str) -> None:
        """
        Watch ticker via WebSocket for a specific symbol.
        
        Args:
            symbol: Trading symbol to watch
        """
        while self.running:
            try:
                ticker = await self.exchange.watch_ticker(symbol)
                price = ticker['last']
                timestamp = datetime.now()
                
                # Update cache
                self.prices[symbol] = price
                self.last_update[symbol] = timestamp
                
                # Notify callbacks
                for callback in self.price_callbacks:
                    try:
                        await callback(symbol, price, timestamp)
                    except Exception as e:
                        self.logger.error(f"Error in price callback: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error watching ticker for {symbol}: {e}")
                await asyncio.sleep(5)
    
    async def _poll_prices(self) -> None:
        """Poll prices at regular intervals (fallback for exchanges without WebSocket)."""
        while self.running:
            try:
                for symbol in self.symbols:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    price = ticker['last']
                    timestamp = datetime.now()
                    
                    # Update cache
                    self.prices[symbol] = price
                    self.last_update[symbol] = timestamp
                    
                    # Notify callbacks
                    for callback in self.price_callbacks:
                        try:
                            await callback(symbol, price, timestamp)
                        except Exception as e:
                            self.logger.error(f"Error in price callback: {e}")
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error polling prices: {e}")
                await asyncio.sleep(5)
    
    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get latest cached price for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price or None if not available
        """
        return self.prices.get(symbol)
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        Get all cached prices.
        
        Returns:
            Dictionary of symbol -> price
        """
        return self.prices.copy()


class MultiExchangeMonitor:
    """
    Monitor multiple exchanges simultaneously.
    
    Aggregates price data from multiple exchanges and provides
    a unified interface for price queries.
    """
    
    def __init__(self):
        """Initialize multi-exchange monitor."""
        self.monitors: Dict[str, ExchangeMonitor] = {}
        self.logger = logging.getLogger("MultiExchangeMonitor")
    
    def add_exchange(self, exchange_name: str, symbols: list[str],
                    api_key: str = "", api_secret: str = "",
                    testnet: bool = False) -> ExchangeMonitor:
        """
        Add an exchange to monitor.
        
        Args:
            exchange_name: Name of exchange
            symbols: Symbols to monitor
            api_key: API key
            api_secret: API secret
            testnet: Use testnet
            
        Returns:
            Created ExchangeMonitor instance
        """
        monitor = ExchangeMonitor(exchange_name, symbols, api_key, api_secret, testnet)
        self.monitors[exchange_name] = monitor
        return monitor
    
    async def start_all(self) -> None:
        """Start all exchange monitors."""
        self.logger.info(f"Starting {len(self.monitors)} exchange monitors")
        
        tasks = [monitor.start() for monitor in self.monitors.values()]
        await asyncio.gather(*tasks)
    
    async def stop_all(self) -> None:
        """Stop all exchange monitors."""
        self.logger.info("Stopping all exchange monitors")
        
        tasks = [monitor.stop() for monitor in self.monitors.values()]
        await asyncio.gather(*tasks)
    
    def get_price(self, exchange: str, symbol: str) -> Optional[float]:
        """
        Get price from specific exchange.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            
        Returns:
            Price or None if not available
        """
        monitor = self.monitors.get(exchange)
        if monitor:
            return monitor.get_price(symbol)
        return None
    
    def get_best_price(self, symbol: str, side: str = "buy") -> Optional[tuple[str, float]]:
        """
        Get best price across all exchanges.
        
        Args:
            symbol: Trading symbol
            side: 'buy' for lowest price, 'sell' for highest price
            
        Returns:
            Tuple of (exchange_name, price) or None
        """
        prices = []
        for exchange_name, monitor in self.monitors.items():
            price = monitor.get_price(symbol)
            if price is not None:
                prices.append((exchange_name, price))
        
        if not prices:
            return None
        
        if side == "buy":
            return min(prices, key=lambda x: x[1])
        else:
            return max(prices, key=lambda x: x[1])
