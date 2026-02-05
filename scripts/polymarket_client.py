"""
Polymarket Client - GraphQL API Wrapper
Handles all interactions with Polymarket's GraphQL API and on-chain data
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from web3 import Web3
from eth_abi import decode
from rate_limiter import AdaptiveRateLimiter

logger = logging.getLogger(__name__)

# Polymarket Contract Addresses
POLYMARKET_ADDRESSES = {
    "ctf_exchange": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
    "neg_risk_adapter": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
    "neg_risk_exchange": "0xC5d563A36AE3d66CD6C8946f5e703426975230BE",
    "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "conditional_tokens": "0x4D97DCd97eC93972b64e1a1438D19479e9fBD86B"
}

# ABI Fragments for decoding
CTF_EXCHANGE_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "taker", "type": "address"},
            {"indexed": False, "name": "maker", "type": "address"},
            {"indexed": True, "name": "marketId", "type": "bytes32"},
            {"indexed": False, "name": "outcomeIndex", "type": "uint256"},
            {"indexed": False, "name": "side", "type": "uint8"},
            {"indexed": False, "name": "price", "type": "uint256"},
            {"indexed": False, "name": "amount", "type": "uint256"}
        ],
        "name": "OrderFilled",
        "type": "event"
    }
]

USDC_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Approval",
        "type": "event"
    }
]


class PolymarketClient:
    """Client for interacting with Polymarket GraphQL API and Polygon chain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.graphql_endpoint = config.get("monitoring", {}).get(
            "graphql_endpoint", 
            "https://api.polymarket.com/graphql"
        )
        self.rpc_endpoints = config.get("monitoring", {}).get(
            "rpc_endpoints",
            ["https://polygon-rpc.com"]
        )
        
        # Initialize Web3 with multiple RPC fallbacks
        self.w3 = None
        for rpc in self.rpc_endpoints:
            try:
                self.w3 = Web3(Web3.HTTPProvider(rpc))
                if self.w3.is_connected():
                    logger.info(f"Connected to Polygon RPC: {rpc}")
                    break
            except Exception as e:
                logger.warning(f"Failed to connect to {rpc}: {e}")
        
        if not self.w3 or not self.w3.is_connected():
            raise ConnectionError("Failed to connect to any Polygon RPC endpoint")
        
        # Initialize rate limiter for RPC calls
        self.rate_limiter = AdaptiveRateLimiter(
            db_path='rate_limits.db',
            provider='polygon-rpc'
        )
        logger.info("AdaptiveRateLimiter integrated into PolymarketClient")
        
        # GraphQL client
        self._graphql_client = None
        self._session = None
        
    async def _get_graphql_client(self) -> Client:
        """Get or create GraphQL client"""
        if self._graphql_client is None:
            transport = AIOHTTPTransport(url=self.graphql_endpoint)
            self._graphql_client = Client(
                transport=transport,
                fetch_schema_from_transport=True
            )
        return self._graphql_client
    
    async def close(self):
        """Close connections"""
        if self._graphql_client:
            await self._graphql_client.close_async()
            self._graphql_client = None
    
    # ==================== GraphQL Queries ====================
    
    async def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market details by ID"""
        query = gql("""
            query GetMarket($id: String!) {
                market(id: $id) {
                    id
                    question
                    slug
                    description
                    outcomes
                    outcomePrices
                    volume
                    liquidity
                    endDate
                    status
                    category
                    resolutionSource
                    icon
                    locked
                }
            }
        """)
        
        try:
            client = await self._get_graphql_client()
            result = await client.execute(query, {"id": market_id})
            return result.get("market")
        except Exception as e:
            logger.error(f"Error fetching market {market_id}: {e}")
            return None
    
    async def get_active_markets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch active markets"""
        query = gql("""
            query GetActiveMarkets($limit: Int!) {
                markets(
                    where: {active: true}
                    first: $limit
                    orderBy: volume
                    orderDirection: desc
                ) {
                    id
                    question
                    slug
                    outcomes
                    outcomePrices
                    volume
                    liquidity
                    endDate
                    status
                    category
                }
            }
        """)
        
        try:
            client = await self._get_graphql_client()
            result = await client.execute(query, {"limit": limit})
            return result.get("markets", [])
        except Exception as e:
            logger.error(f"Error fetching active markets: {e}")
            return []
    
    async def get_market_by_condition_id(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """Fetch market by condition ID"""
        query = gql("""
            query GetMarketByCondition($conditionId: String!) {
                markets(where: {conditionId: $conditionId}) {
                    id
                    question
                    slug
                    outcomes
                    outcomePrices
                    volume
                    liquidity
                    endDate
                    status
                    category
                    conditionId
                }
            }
        """)
        
        try:
            client = await self._get_graphql_client()
            result = await client.execute(query, {"conditionId": condition_id})
            markets = result.get("markets", [])
            return markets[0] if markets else None
        except Exception as e:
            logger.error(f"Error fetching market by condition {condition_id}: {e}")
            return None
    
    async def get_user_positions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Fetch user's current positions"""
        query = gql("""
            query GetUserPositions($user: String!) {
                user(id: $user) {
                    positions {
                        market {
                            id
                            question
                            slug
                            outcomes
                            outcomePrices
                            status
                        }
                        outcomeIndex
                        quantity
                        avgPrice
                        value
                        pnl
                    }
                }
            }
        """)
        
        try:
            client = await self._get_graphql_client()
            result = await client.execute(query, {"user": wallet_address.lower()})
            user = result.get("user")
            return user.get("positions", []) if user else []
        except Exception as e:
            logger.error(f"Error fetching positions for {wallet_address}: {e}")
            return []
    
    async def get_user_trades(
        self, 
        wallet_address: str, 
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch user's trade history"""
        since_timestamp = int(since.timestamp()) if since else 0
        
        query = gql("""
            query GetUserTrades($user: String!, $since: Int!) {
                trades(
                    where: {
                        user: $user,
                        timestamp_gte: $since
                    }
                    orderBy: timestamp
                    orderDirection: desc
                    first: 1000
                ) {
                    id
                    market {
                        id
                        question
                        slug
                        outcomes
                        category
                    }
                    outcomeIndex
                    side
                    price
                    amount
                    timestamp
                    transactionHash
                }
            }
        """)
        
        try:
            client = await self._get_graphql_client()
            result = await client.execute(query, {
                "user": wallet_address.lower(),
                "since": since_timestamp
            })
            return result.get("trades", [])
        except Exception as e:
            logger.error(f"Error fetching trades for {wallet_address}: {e}")
            return []
    
    async def get_leaderboard(
        self, 
        limit: int = 100,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch top traders from leaderboard"""
        query = gql("""
            query GetLeaderboard($limit: Int!) {
                users(
                    first: $limit
                    orderBy: totalVolume
                    orderDirection: desc
                ) {
                    id
                    totalVolume
                    profit
                    winRate
                    totalTrades
                    positions {
                        market {
                            category
                        }
                    }
                }
            }
        """)
        
        try:
            client = await self._get_graphql_client()
            result = await client.execute(query, {"limit": limit * 2})  # Get extra for filtering
            users = result.get("users", [])
            
            # Filter by category if specified
            if category:
                filtered = []
                for user in users:
                    categories = set()
                    for pos in user.get("positions", []):
                        cat = pos.get("market", {}).get("category")
                        if cat:
                            categories.add(cat.lower())
                    if category.lower() in categories:
                        filtered.append(user)
                users = filtered[:limit]
            
            return users[:limit]
        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            return []
    
    # ==================== On-Chain Methods ====================
    
    async def get_latest_block(self) -> int:
        """Get the latest block number"""
        await self.rate_limiter.acquire()
        return self.w3.eth.block_number
    
    async def get_block_timestamp(self, block_number: int) -> datetime:
        """Get timestamp for a block"""
        await self.rate_limiter.acquire()
        block = self.w3.eth.get_block(block_number)
        return datetime.fromtimestamp(block.timestamp)
    
    async def parse_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Parse a transaction receipt for Polymarket trades"""
        try:
            await self.rate_limiter.acquire()
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if not receipt:
                return None
            
            trades = []
            for log in receipt.logs:
                # Check if this is a Polymarket CTF Exchange event
                if log.address.lower() == POLYMARKET_ADDRESSES["ctf_exchange"].lower():
                    trade = self._decode_ctf_exchange_log(log)
                    if trade:
                        trades.append(trade)
            
            return {
                "transaction_hash": tx_hash,
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "effective_gas_price": receipt.effectiveGasPrice,
                "status": receipt.status,
                "trades": trades
            }
        except Exception as e:
            logger.error(f"Error parsing transaction {tx_hash}: {e}")
            return None
    
    def _decode_ctf_exchange_log(self, log) -> Optional[Dict[str, Any]]:
        """Decode a CTF Exchange event log"""
        try:
            # Event signature for OrderFilled
            # keccak256("OrderFilled(address,address,bytes32,uint256,uint8,uint256,uint256)")
            event_signature = "0x4a504a94899432f4f0e6af3e20b4c5a3e1c9c3e8e8e8e8e8e8e8e8e8e8e8e8e8e"
            
            if len(log.topics) < 2:
                return None
            
            topic0 = log.topics[0].hex()
            
            # Decode based on event type
            if topic0 == event_signature[:66]:
                # Decode OrderFilled event
                taker = "0x" + log.topics[1].hex()[-40:]
                market_id = log.topics[2].hex()
                
                # Decode data
                data = log.data
                decoded = decode(
                    ['address', 'uint256', 'uint8', 'uint256', 'uint256'],
                    data
                )
                
                return {
                    "event": "OrderFilled",
                    "taker": self.w3.to_checksum_address(taker),
                    "maker": decoded[0],
                    "market_id": market_id,
                    "outcome_index": decoded[1],
                    "side": "BUY" if decoded[2] == 0 else "SELL",
                    "price": decoded[3] / 1e6,  # USDC has 6 decimals
                    "amount": decoded[4] / 1e6,
                    "log_index": log.logIndex,
                    "block_number": log.blockNumber
                }
            
            return None
        except Exception as e:
            logger.error(f"Error decoding log: {e}")
            return None
    
    async def get_usdc_balance(self, wallet_address: str) -> float:
        """Get USDC balance for a wallet"""
        try:
            await self.rate_limiter.acquire()
            usdc_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(POLYMARKET_ADDRESSES["usdc"]),
                abi=USDC_ABI
            )
            balance = usdc_contract.functions.balanceOf(wallet_address).call()
            return balance / 1e6  # USDC has 6 decimals
        except Exception as e:
            logger.error(f"Error fetching USDC balance for {wallet_address}: {e}")
            return 0.0
    
    async def estimate_gas_cost(self, gas_limit: int = 200000) -> float:
        """Estimate gas cost in USDC"""
        try:
            await self.rate_limiter.acquire()
            gas_price = self.w3.eth.gas_price  # in wei
            gas_cost_wei = gas_price * gas_limit
            gas_cost_matic = self.w3.from_wei(gas_cost_wei, 'ether')
            
            # Convert MATIC to USDC (approximate)
            # This would need a price oracle in production
            matic_price_usd = 0.50  # Approximate, should fetch from oracle
            gas_cost_usdc = float(gas_cost_matic) * matic_price_usd
            
            return gas_cost_usdc
        except Exception as e:
            logger.error(f"Error estimating gas cost: {e}")
            return 0.01  # Default fallback
    
    # ==================== Wallet Discovery ====================
    
    async def discover_profitable_wallets(
        self,
        min_monthly_trades: int = 5,
        min_win_rate: float = 0.55,
        lookback_days: int = 90,
        categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Discover profitable wallets based on criteria"""
        logger.info("Discovering profitable wallets...")
        
        # Get leaderboard
        leaderboard = await self.get_leaderboard(limit=200)
        
        candidates = []
        since = datetime.utcnow() - timedelta(days=lookback_days)
        
        for user in leaderboard:
            wallet_address = user.get("id")
            if not wallet_address:
                continue
            
            # Basic filtering
            total_trades = user.get("totalTrades", 0)
            win_rate = user.get("winRate", 0) / 100  # Convert from percentage
            
            # Calculate monthly trades
            monthly_trades = total_trades / (lookback_days / 30)
            
            if monthly_trades < min_monthly_trades:
                continue
            
            if win_rate < min_win_rate:
                continue
            
            # Get detailed trade history
            trades = await self.get_user_trades(wallet_address, since)
            
            if len(trades) < min_monthly_trades * (lookback_days / 30):
                continue
            
            # Category analysis
            trade_categories = set()
            for trade in trades:
                cat = trade.get("market", {}).get("category")
                if cat:
                    trade_categories.add(cat.lower())
            
            # Check if matches desired categories
            if categories:
                has_matching_category = any(
                    cat.lower() in trade_categories for cat in categories
                )
                if not has_matching_category:
                    continue
            
            candidates.append({
                "address": wallet_address,
                "total_volume": float(user.get("totalVolume", 0)),
                "profit": float(user.get("profit", 0)),
                "win_rate": win_rate,
                "total_trades": total_trades,
                "monthly_trades": monthly_trades,
                "categories": list(trade_categories),
                "recent_trades": len(trades)
            })
        
        # Sort by profit
        candidates.sort(key=lambda x: x["profit"], reverse=True)
        
        logger.info(f"Found {len(candidates)} candidate wallets")
        return candidates
