# 🚀 Quick Start - Polymarket Data Access

**Get your Polymarket dashboard working in 5 minutes!**

---

## Step 1: Test the APIs (2 minutes)

```bash
cd /home/Gabe/gabubu-repos/polymarket-arbitrage-bot
python examples/test_apis.py
```

This will verify that all Polymarket APIs are accessible and working.

**Expected output:**
```
GAMMA API       ✓ PASS
DATA API        ✓ PASS
CLOB API        ✓ PASS
SEARCH          ✓ PASS

🎉 ALL TESTS PASSED! APIs are working correctly.
```

---

## Step 2: See Live Data (1 minute)

```bash
python examples/simple_monitor.py
```

This shows you top markets refreshed every 30 seconds. Press `Ctrl+C` to stop.

**You'll see:**
- Top 15 markets by 24h volume
- Current prices for each outcome
- Volume and liquidity stats

---

## Step 3: Explore a Market (1 minute)

```bash
# Search for a market
python examples/get_market_data.py "Trump"

# Or use a specific slug
python examples/get_market_data.py presidential-election-winner-2024
```

**You'll see:**
- Full market details
- Top 10 holders
- Recent 15 trades

---

## Step 4: Real-Time Updates (Optional)

```bash
pip install websockets  # If not already installed
python examples/websocket_prices.py
```

This connects to Polymarket's WebSocket feed and shows live price updates.

---

## Step 5: Install Python Package (Recommended)

For production use, install the official Python package:

```bash
pip install polymarket-apis
```

Then you can use it in your code:

```python
from polymarket_apis import PolymarketGammaClient

gamma = PolymarketGammaClient()
markets = gamma.get_markets(limit=20, active=True, order='volume24hr')

for market in markets:
    print(f"{market.question}: ${market.volume:,.0f}")
```

---

## Next Steps

### For Your Dashboard:

1. **Choose your approach:**
   - **Simple**: Use the raw REST APIs (examples show how)
   - **Recommended**: Use `polymarket-apis` package (more features, easier)

2. **Architecture suggestion:**
   ```
   Backend:  FastAPI + polymarket-apis + Redis (for caching)
   Frontend: React + WebSocket for live updates
   ```

3. **Key endpoints to use:**
   - `GET /api/markets/trending` → Show top markets
   - `GET /api/markets/{id}` → Market details
   - `WebSocket /ws/prices` → Real-time price updates

### Example Backend (FastAPI)

Create `backend/main.py`:

```python
from fastapi import FastAPI
from polymarket_apis import PolymarketGammaClient, PolymarketDataClient

app = FastAPI()
gamma = PolymarketGammaClient()
data = PolymarketDataClient()

@app.get("/api/markets/trending")
async def trending_markets(limit: int = 20):
    return gamma.get_markets(limit=limit, active=True, order='volume24hr')

@app.get("/api/markets/{condition_id}")
async def market_details(condition_id: str):
    return gamma.get_market(condition_id)

@app.get("/api/holders/{condition_id}")
async def top_holders(condition_id: str, limit: int = 10):
    return data.get_holders(market=condition_id, limit=limit)
```

Run it:
```bash
pip install fastapi uvicorn polymarket-apis
uvicorn backend.main:app --reload
```

Visit: http://localhost:8000/api/markets/trending

---

## 📚 Full Documentation

- **Complete API Guide**: `POLYMARKET_DATA_ACCESS.md`
- **Example Code**: `examples/` directory
- **Official Docs**: https://docs.polymarket.com

---

## 🆘 Troubleshooting

### "Connection refused" or timeout errors
- Check your internet connection
- Polymarket APIs might be rate limiting (add delays between requests)
- Try again in a few seconds

### "No module named 'requests'"
```bash
pip install requests
```

### "No module named 'websockets'" (for websocket_prices.py)
```bash
pip install websockets
```

### "Market not found"
- Check the slug is correct (copy from polymarket.com URL)
- Use the search feature: `python examples/get_market_data.py "search term"`

---

## 💡 Pro Tips

1. **Cache aggressively** - Market metadata doesn't change often (30-60s cache)
2. **Use WebSockets for prices** - Don't poll, subscribe!
3. **Start simple** - Get basic data working first, add features later
4. **Check the examples** - They show working implementations

---

## ✅ You're Ready!

All the tools are here:
- ✅ Working API examples
- ✅ Python package with full features
- ✅ Complete documentation
- ✅ Ready-to-run scripts

**Build your dashboard and ship it!** 🚀
