"""
Wallet Monitor - Monitor target wallets for Polymarket trades
Watches Polygon addresses for Polymarket contract interactions
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

from web3 import Web3
from web3.types import FilterParams, LogReceipt
from rate_limiter import AdaptiveRateLimiter

logger = logging.getLogger(__name__)

# Polymarket Contract Addresses
POLYMARKET_CONTRACTS = {
    "ctf_exchange": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
    "neg_risk_adapter": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296", 
    "neg_risk_exchange": "0xC5d563A36AE3d66CD6C8946f5e703426975230BE",
    "conditional_tokens": "0x4D97DCd97eC93972b64e1a1438D19479e9fBD86B"
}

# Event signatures
ORDER_FILLED_EVENT = "0x4a504a94899432f4f0e6af3e20b4c5a3e1c9c3e8e8e8e8e8e8e8e8e8e8e8e8e8e"


@dataclass
class TradeEvent:
    """Represents a detected trade event"""
    wallet_address: str
    market_id: str
    outcome: str  # YES or NO
    outcome_index: int
    side: str  # BUY or SELL
    amount: float  # In USDC
    price: float  # Price per share (0-1)
    shares: float  # Number of shares
    transaction_hash: str
    block_number: int
    timestamp: datetime
    gas_used: int
    gas_price: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet_address": self.wallet_address,
            "market_id": self.market_id,
            "outcome": self.outcome,
            "outcome_index": self.outcome_index,
            "side": self.side,
            "amount": self.amount,
            "price": self.price,
            "shares": self.shares,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "timestamp": self.timestamp.isoformat(),
            "gas_used": self.gas_used,
            "gas_price": self.gas_price
        }


@dataclass
class WalletConfig:
    """Configuration for a target wallet"""
    address: str
    name: str
    copy_percentage: float = 100.0
    categories: List[str] = field(default_factory=list)
    min_trade_size_usdc: float = 10.0
    max_trade_size_usdc: float = 10000.0
    
    @property
    def checksum_address(self) -> str:
        return Web3.to_checksum_address(self.address)


class WalletMonitor:
    """Monitors wallets for Polymarket trading activity"""
    
    def __init__(
        self, 
        w3: Web3,
        config: Dict[str, Any],
        callback: Optional[Callable[[TradeEvent], None]] = None,
        rate_limiter: Optional[AdaptiveRateLimiter] = None
    ):
        self.w3 = w3
        self.config = config
        self.callback = callback
        self.rate_limiter = rate_limiter or AdaptiveRateLimiter(
            db_path='rate_limits.db',
            provider='polygon-rpc'
        )
        logger.info("WalletMonitor: Rate limiter integrated")
        
        # Load wallet configs
        self.wallets: Dict[str, WalletConfig] = {}
        self._load_wallet_configs()
        
        # Tracking state
        self.last_checked_block: int = 0
        self.processed_txs: Set[str] = set()
        self.wallet_trade_history: Dict[str, List[TradeEvent]] = defaultdict(list)
        
        # Polling settings
        self.poll_interval = config.get("monitoring", {}).get("poll_interval_seconds", 15)
        self.block_lookback = config.get("monitoring", {}).get("block_lookback", 100)
        
        # Market cache (market_id -> market info)
        self.market_cache: Dict[str, Dict[str, Any]] = {}
        
        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info(f"WalletMonitor initialized with {len(self.wallets)} wallets")
    
    def _load_wallet_configs(self):
        """Load wallet configurations from config"""
        target_wallets = self.config.get("target_wallets", [])
        for wallet_data in target_wallets:
            wallet_config = WalletConfig(
                address=wallet_data["address"],
                name=wallet_data.get("name", "Unknown"),
                copy_percentage=wallet_data.get("copy_percentage", 100.0),
                categories=wallet_data.get("categories", []),
                min_trade_size_usdc=wallet_data.get("min_trade_size_usdc", 10.0),
                max_trade_size_usdc=wallet_data.get("max_trade_size_usdc", 10000.0)
            )
            self.wallets[wallet_config.checksum_address.lower()] = wallet_config
    
    def add_wallet(self, wallet_config: WalletConfig) -> bool:
        """Add a new wallet to monitor"""
        addr_lower = wallet_config.checksum_address.lower()
        if addr_lower in self.wallets:
            logger.warning(f"Wallet {wallet_config.address} already being monitored")
            return False
        
        self.wallets[addr_lower] = wallet_config
        logger.info(f"Added wallet to monitor: {wallet_config.name} ({wallet_config.address})")
        return True
    
    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet from monitoring"""
        addr_lower = Web3.to_checksum_address(address).lower()
        if addr_lower not in self.wallets:
            return False
        
        wallet = self.wallets.pop(addr_lower)
        logger.info(f"Removed wallet from monitoring: {wallet.name} ({wallet.address})")
        return True
    
    def get_monitored_wallets(self) -> List[WalletConfig]:
        """Get list of all monitored wallets"""
        return list(self.wallets.values())
    
    def get_wallet_stats(self, address: str) -> Optional[Dict[str, Any]]:
        """Get trading statistics for a wallet"""
        addr_lower = Web3.to_checksum_address(address).lower()
        trades = self.wallet_trade_history.get(addr_lower, [])
        
        if not trades:
            return None
        
        # Calculate stats
        total_trades = len(trades)
        total_volume = sum(t.amount for t in trades)
        buy_count = sum(1 for t in trades if t.side == "BUY")
        sell_count = sum(1 for t in trades if t.side == "SELL")
        
        # Recent trades (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(hours=24)
        recent_trades = [t for t in trades if t.timestamp > day_ago]
        
        return {
            "address": address,
            "total_trades": total_trades,
            "total_volume_usdc": total_volume,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "recent_trades_24h": len(recent_trades),
            "last_trade_time": trades[-1].timestamp.isoformat() if trades else None
        }
    
    async def start(self):
        """Start monitoring wallets"""
        if self._running:
            logger.warning("WalletMonitor already running")
            return
        
        self._running = True
        self.last_checked_block = self.w3.eth.block_number - self.block_lookback
        
        logger.info(f"Starting WalletMonitor from block {self.last_checked_block}")
        self._task = asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Stop monitoring wallets"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("WalletMonitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_new_blocks()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _check_new_blocks(self):
        """Check for new blocks and process transactions"""
        await self.rate_limiter.acquire()
        current_block = self.w3.eth.block_number
        
        if current_block <= self.last_checked_block:
            return
        
        # Process blocks in batches
        from_block = self.last_checked_block + 1
        to_block = min(current_block, from_block + 50)  # Max 50 blocks at a time
        
        logger.debug(f"Checking blocks {from_block} to {to_block}")
        
        try:
            # Get logs for all Polymarket contracts
            trades = await self._fetch_trades_in_range(from_block, to_block)
            
            for trade in trades:
                if trade.transaction_hash not in self.processed_txs:
                    self.processed_txs.add(trade.transaction_hash)
                    self.wallet_trade_history[trade.wallet_address.lower()].append(trade)
                    
                    # Trigger callback if set
                    if self.callback:
                        try:
                            await self.callback(trade) if asyncio.iscoroutinefunction(self.callback) else self.callback(trade)
                        except Exception as e:
                            logger.error(f"Error in trade callback: {e}")
            
            self.last_checked_block = to_block
            
            # Cleanup old processed transactions
            if len(self.processed_txs) > 10000:
                self.processed_txs = set(list(self.processed_txs)[-5000:])
                
        except Exception as e:
            logger.error(f"Error checking blocks {from_block}-{to_block}: {e}")
    
    async def _fetch_trades_in_range(
        self, 
        from_block: int, 
        to_block: int
    ) -> List[TradeEvent]:
        """Fetch trades from Polymarket contracts in block range"""
        trades = []
        
        # Set up event filter for CTF Exchange
        for contract_name, contract_address in POLYMARKET_CONTRACTS.items():
            if "exchange" not in contract_name:
                continue
            
            try:
                filter_params = FilterParams(
                    fromBlock=from_block,
                    toBlock=to_block,
                    address=Web3.to_checksum_address(contract_address)
                )
                
                await self.rate_limiter.acquire()
                logs = self.w3.eth.get_logs(filter_params)
                
                for log in logs:
                    trade = await self._parse_trade_log(log)
                    if trade:
                        trades.append(trade)
                        
            except Exception as e:
                logger.error(f"Error fetching logs from {contract_name}: {e}")
        
        return sorted(trades, key=lambda x: x.block_number)
    
    async def _parse_trade_log(self, log: LogReceipt) -> Optional[TradeEvent]:
        """Parse a trade event log"""
        try:
            # Get transaction hash
            tx_hash = log.transactionHash.hex()
            
            # Check if we've seen this transaction
            if tx_hash in self.processed_txs:
                return None
            
            # Decode the log data FIRST (no RPC calls)
            # Polymarket trade events have specific structure
            topics = log.get("topics", [])
            if len(topics) < 3:
                return None
            
            # Parse event data
            # Topic[0] = event signature
            # Topic[1] = taker address (indexed)
            # Topic[2] = marketId (indexed) or similar
            
            event_signature = topics[0].hex()
            
            # Handle OrderFilled event
            if event_signature.startswith("0x4a504a"):  # OrderFilled signature prefix
                taker = "0x" + topics[1].hex()[-40:]
                taker_lower = taker.lower()
                
                # EARLY EXIT: Check if this is one of our monitored wallets
                # This avoids making RPC calls for trades we don't care about
                if taker_lower not in self.wallets:
                    return None
                
                market_id = topics[2].hex()
                
                # Decode data field
                data = log.get("data", "0x")
                if data == "0x":
                    return None
                
                # Decode: maker (address), outcomeIndex (uint256), side (uint8), price (uint256), amount (uint256)
                # Remove 0x prefix and decode
                data_bytes = bytes.fromhex(data[2:])
                
                # Manual decoding for reliability
                if len(data_bytes) >= 160:  # 5 * 32 bytes
                    outcome_index = int.from_bytes(data_bytes[32:64], 'big')
                    side_code = int.from_bytes(data_bytes[64:96], 'big')
                    price_raw = int.from_bytes(data_bytes[96:128], 'big')
                    amount_raw = int.from_bytes(data_bytes[128:160], 'big')
                    
                    side = "BUY" if side_code == 0 else "SELL"
                    price = price_raw / 1e6  # USDC decimals
                    amount = amount_raw / 1e6
                    shares = amount / price if price > 0 else 0
                    
                    # Determine outcome (YES/NO based on index)
                    outcome = "YES" if outcome_index == 0 else "NO"
                    
                    # NOW get receipt and transaction details (only for monitored wallets)
                    await self.rate_limiter.acquire()
                    receipt = self.w3.eth.get_transaction_receipt(log.transactionHash)
                    if not receipt:
                        return None
                    
                    await self.rate_limiter.acquire()
                    tx = self.w3.eth.get_transaction(log.transactionHash)
                    
                    # Get block timestamp (with rate limiting)
                    await self.rate_limiter.acquire()
                    block = self.w3.eth.get_block(log.blockNumber)
                    timestamp = datetime.fromtimestamp(block.timestamp)
                    
                    return TradeEvent(
                        wallet_address=Web3.to_checksum_address(taker),
                        market_id=market_id,
                        outcome=outcome,
                        outcome_index=outcome_index,
                        side=side,
                        amount=amount,
                        price=price,
                        shares=shares,
                        transaction_hash=tx_hash,
                        block_number=log.blockNumber,
                        timestamp=timestamp,
                        gas_used=receipt.gasUsed,
                        gas_price=tx.get("gasPrice", 0)
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing trade log: {e}")
            return None
    
    def get_recent_trades(
        self, 
        wallet_address: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[TradeEvent]:
        """Get recent trades for a wallet or all wallets"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        if wallet_address:
            addr_lower = Web3.to_checksum_address(wallet_address).lower()
            trades = self.wallet_trade_history.get(addr_lower, [])
        else:
            trades = []
            for wallet_trades in self.wallet_trade_history.values():
                trades.extend(wallet_trades)
        
        # Filter by time and sort
        recent = [t for t in trades if t.timestamp > since]
        recent.sort(key=lambda x: x.timestamp, reverse=True)
        
        return recent[:limit]
    
    def clear_history(self, wallet_address: Optional[str] = None):
        """Clear trade history"""
        if wallet_address:
            addr_lower = Web3.to_checksum_address(wallet_address).lower()
            if addr_lower in self.wallet_trade_history:
                del self.wallet_trade_history[addr_lower]
                logger.info(f"Cleared trade history for {wallet_address}")
        else:
            self.wallet_trade_history.clear()
            logger.info("Cleared all trade history")
