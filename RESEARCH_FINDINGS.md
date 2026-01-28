# Polymarket Arbitrage Bot - Research Findings

## ✅ Research Complete - Here's What Actually Works

### 🎯 The Real Arbitrage Strategy

**NOT** direct price arbitrage between Polymarket and Binance/Coinbase.

**ACTUAL STRATEGY**: Trade on Polymarket's **15-minute crypto price markets** using signals from spot exchanges.

#### How it Works:
1. Monitor BTC/ETH/SOL/XRP prices on Binance/Coinbase in **real-time**
2. Polymarket has **15-minute markets** predicting whether crypto will be "UP" or "DOWN" in next 15 mins
3. When spot price moves significantly, bet on the corresponding direction on Polymarket
4. Exit positions using take-profit/stop-loss automation

**Example**: BTC spikes 2% on Binance → Buy "BTC UP" on Polymarket's 15-min market

### 📚 Polymarket API - The Real Deal

#### Authentication: Wallet-Based (NOT API Keys)
```python
from py_clob_client.client import ClobClient

client = ClobClient(
    host="https://clob.polymarket.com",
    key=PRIVATE_KEY,                    # Polygon wallet private key
    chain_id=137,                       # Polygon mainnet
    signature_type=2,                   # 0=EOA, 1=Email/Magic, 2=Browser wallet proxy
    funder=PROXY_WALLET_ADDRESS         # Your Polymarket Safe address
)

# Generate API credentials from wallet
api_creds = client.create_or_derive_api_creds()
client.set_api_creds(api_creds)
```

#### Finding Markets: Gamma API
```python
# Get current 15-minute BTC market
url = "https://gamma-api.polymarket.com/events"
markets = requests.get(url, params={"tag": "crypto"}).json()

# Filter for 15-minute markets
btc_15min = [m for m in markets 
             if "BTC" in m['question'] 
             and "15" in m['question']]
```

#### Placing Orders
```python
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

# Market order (instant execution)
order = MarketOrderArgs(
    token_id="<token-id>",       # From market data
    amount=10.0,                 # $10 USDC
    side=BUY                     # or SELL
)
signed = client.create_market_order(order)
response = client.post_order(signed, OrderType.FOK)

# Limit order (specific price)
from py_clob_client.clob_types import OrderArgs

order = OrderArgs(
    token_id="<token-id>",
    price=0.65,                  # 65% probability (0.00-1.00)
    size=10.0,                   # 10 shares
    side=BUY
)
signed = client.create_order(order)
response = client.post_order(signed, OrderType.GTC)
```

### 🔥 Real-World Bot Implementations

#### 1. **Spike Detection Bot** (Trust412)
**Strategy**: Detect price spikes and trade on momentum
- Monitors price changes in real-time
- Triggers on 1-2% price movements
- Auto TP/SL: +$3 profit / -$3 loss
- Hold time limit: 60 seconds
- **Reported Results**: $300K+ profits

**Config**:
```env
trade_unit=3.0              # $3 per trade
spike_threshold=0.01        # 1% price change triggers
pct_profit=0.03             # 3% take profit
pct_loss=-0.025             # -2.5% stop loss
holding_time_limit=60       # Max 60 seconds hold
max_concurrent_trades=3     # Max 3 positions
```

#### 2. **Flash Crash Strategy** (discountry)
**Strategy**: Buy dips in 15-minute markets
- Detects sudden probability drops (30%+ in 10 seconds)
- Buys the crashed side
- Quick exits: +$0.10 TP / -$0.05 SL

#### 3. **Market Making Bot** (terrytrl100)
**Strategy**: Provide liquidity and earn maker rewards
- Places orders on both sides
- Optimizes for Polymarket's reward formula
- Automated position merging
- **Reported**: Consistent daily rewards

### 💰 The Money Flow

**How Bots Profit**:
1. **Temporal Arbitrage**: Exploit lag between spot exchanges and Polymarket prices
2. **Maker Rewards**: Polymarket pays rewards for providing liquidity
3. **Statistical Edge**: Better probability models than retail traders

**Documented Profits**:
- One bot: $313 → $414,000 in one month (Reddit)
- $40M in total arbitrage profits extracted (Apr 2024 - Apr 2025)
- Single-market arbitrage: $39.5M+ (buying when YES+NO < $1.00)

### 🏗️ Technical Architecture

#### Required Components:

1. **Polymarket Integration** (`py-clob-client`)
   ```bash
   pip install py-clob-client
   ```

2. **Market Data Sources**:
   - Gamma API (https://gamma-api.polymarket.com) - Market discovery
   - WebSocket (wss://ws-subscriptions-clob.polymarket.com) - Real-time prices
   - Binance/Coinbase APIs - Spot price data

3. **Wallet Setup**:
   - Polygon wallet with private key
   - Polymarket Safe address (proxy wallet)
   - USDC balance on Polygon network
   - Token allowances set for trading

4. **Token Allowances** (Critical for EOA/MetaMask users):
   ```python
   # USDC approval
   approve(
       token="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC
       spender="0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",  # Exchange
       amount=unlimited
   )
   
   # Conditional tokens approval
   approve(
       token="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045",  # CTF
       spender="0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
       amount=unlimited
   )
   ```

### 📊 Key Metrics to Track

**Bot Performance**:
- Win rate (aim for 85%+)
- Average profit per trade
- Sharpe ratio
- Maximum drawdown

**Market Selection**:
- Liquidity (min $10+ on both sides)
- Volume (higher = better fills)
- Spread (tighter = lower slippage)
- Volatility (crypto markets best)

**Risk Management**:
- Max concurrent positions (3-5)
- Position size (1-5% of bankroll)
- Stop loss (-2% to -5%)
- Take profit (+2% to +5%)

### ⚠️ Common Pitfalls

1. **Latency**: 15-min windows are SHORT. Every millisecond matters.
2. **Slippage**: Check order book depth before trading
3. **Gas fees**: Use gasless trading (Builder Program) if possible
4. **Resolution risk**: Markets can resolve unexpectedly
5. **Liquidity**: Avoid markets with <$10 on either side

### 🎮 Builder Program (Gasless Trading)

Apply at: https://polymarket.com/settings?tab=builder

**Benefits**:
- Zero gas fees on all trades
- API credentials for programmatic access
- $100-$75,000 grants available
- Volume-based rewards

**Requirements**:
- Active trading history
- Developer credentials
- Business plan/strategy

### 🔧 Environment Setup

**Required Variables**:
```env
# Wallet
POLYGON_WALLET_PRIVATE_KEY=0x...
POLYMARKET_PROXY_ADDRESS=0x...
BOT_TRADER_ADDRESS=0x...

# Contract Addresses (Polygon)
USDC_CONTRACT=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
POLYMARKET_SETTLEMENT=0x56C79347e95530c01A2FC76E732f9566dA16E113

# Trading Parameters
TRADE_SIZE_USDC=10.0
SPIKE_THRESHOLD=0.02
TAKE_PROFIT_PCT=0.03
STOP_LOSS_PCT=-0.025
MAX_HOLDING_TIME=300
MAX_CONCURRENT_TRADES=3

# API Keys (for Builder Program)
BUILDER_API_KEY=...         # Optional
BUILDER_API_SECRET=...      # Optional
BUILDER_API_PASSPHRASE=...  # Optional
```

### 📈 Recommended Strategy (For Beginners)

**15-Minute Crypto Markets + Spike Detection**:

1. **Setup**:
   - Start with $100-500 USDC
   - Monitor BTC/ETH 15-minute markets
   - $3-5 per trade

2. **Entry Rules**:
   - Spot price spikes 1.5%+ in <10 seconds
   - Order book has $10+ liquidity
   - No existing position in same market

3. **Exit Rules**:
   - Take profit: +$1 or +3%
   - Stop loss: -$0.50 or -2%
   - Time limit: 5 minutes max

4. **Risk Management**:
   - Max 3 concurrent trades
   - Max $15 total exposure
   - Daily loss limit: -$20

### 🚀 Next Steps: Build Functional Bot

Now that I understand the real mechanics, I'll build:

1. **Core Bot**:
   - `py-clob-client` integration
   - Gamma API market discovery
   - WebSocket price monitoring
   - Binance/Coinbase spot data
   - Trade execution with TP/SL

2. **Web UI**:
   - Real-time dashboard (actual data)
   - Live P&L tracking
   - Market scanner (15-min markets)
   - Order book visualization
   - Position management
   - Configuration management

3. **Key Differences from Mock UI**:
   - **Real API integration** (not just mock endpoints)
   - **Actual market data** (live from Gamma API)
   - **Working trade execution** (real orders on Polymarket)
   - **Live position tracking** (actual balances)
   - **Functional WebSocket** (real-time prices)

### 📚 References

**Official Docs**:
- Polymarket Docs: https://docs.polymarket.com
- py-clob-client: https://github.com/Polymarket/py-clob-client
- Gamma API: https://docs.polymarket.com/developers/gamma-markets-api

**Working Bots (GitHub)**:
- Official Agent Framework: https://github.com/Polymarket/agents
- Spike Bot: https://github.com/Trust412/Polymarket-spike-bot-v1
- Flash Crash: https://github.com/discountry/polymarket-trading-bot
- Market Maker: https://github.com/terrytrl100/polymarket-automated-mm

**Research**:
- DeFi Prime Guide: https://defiprime.com/definitive-guide-to-the-polymarket-ecosystem
- Reddit Discussions: r/PredictionsMarkets, r/PolymarketTrading

---

**Status**: ✅ Research Complete
**Next**: Build functional bot with real API integration
