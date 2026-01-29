# Polymarket API Examples

Ready-to-run examples for accessing Polymarket data.

## Prerequisites

```bash
pip install requests
# Optional but recommended:
pip install polymarket-apis
```

## Examples

### 1. test_apis.py - Test All APIs

Quick test to verify all APIs are working.

```bash
python examples/test_apis.py
```

**What it does:**
- ✅ Tests Gamma API (market metadata)
- ✅ Tests Data API (holders, positions)
- ✅ Tests CLOB API (order book, prices)
- ✅ Tests Search functionality

**Run this first!** It will verify your connection to all Polymarket APIs.

---

### 2. simple_monitor.py - Live Market Monitor

Real-time dashboard showing top markets by volume.

```bash
python examples/simple_monitor.py
```

**What it does:**
- Shows top 15 markets by 24h volume
- Auto-refreshes every 30 seconds
- Displays prices, volume, and liquidity
- Clean terminal UI

Press `Ctrl+C` to stop.

---

### 3. get_market_data.py - Detailed Market Info

Get comprehensive data for any market.

```bash
# By slug
python examples/get_market_data.py presidential-election-winner-2024

# By search term
python examples/get_market_data.py "Trump win"
```

**What it shows:**
- Market details (question, ID, slug)
- Volume and liquidity stats
- Current prices for all outcomes
- Top 10 holders
- Recent 15 trades

---

### 4. websocket_prices.py - Real-Time Price Feed

Live WebSocket connection for real-time price updates.

```bash
python examples/websocket_prices.py
```

**What it does:**
- Connects to Polymarket WebSocket
- Subscribes to top 5 trending markets
- Prints real-time price changes
- Shows percentage changes

---

## Finding Market Slugs

**Method 1:** Browse polymarket.com
```
https://polymarket.com/event/some-event/this-is-the-market-slug
                                        ^^^^^^^^^^^^^^^^^^^^^^
```

**Method 2:** Search via API
```python
import requests
results = requests.get(
    "https://gamma-api.polymarket.com/search",
    params={"query": "your search term"}
).json()

for r in results:
    if r['type'] == 'market':
        print(r['slug'])
```

**Method 3:** Use get_market_data.py with search
```bash
python examples/get_market_data.py "bitcoin"
# Shows matching markets, lets you select one
```

---

## Next Steps

1. **Run the test script** to verify everything works
2. **Try the monitor** to see live data
3. **Explore specific markets** with get_market_data.py
4. **Build your dashboard** using these as templates

See `POLYMARKET_DATA_ACCESS.md` for comprehensive documentation.
