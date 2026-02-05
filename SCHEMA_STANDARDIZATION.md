# Database Schema Standardization - Long-term Fix

**Applied:** 2026-02-05 10:51 EST

## Problem

The codebase had **inconsistent field naming** across different layers:

**Database:**
- `size_usd`
- `entry_time`
- `direction`
- `position_id`

**Backend API (old mapping):**
- Mapped `size_usd` → `shares` 
- Mapped `entry_time` → `opened_at`
- Mapped `direction` → `outcome`
- Mapped `position_id` → `trade_id`

**Frontend:**
- Sometimes used `pos.size`
- Sometimes used `pos.shares`
- Sometimes used `pos.size_usd`
- Result: **undefined values, missing data**

## Solution Applied

**Eliminated all mapping layers. Use database field names directly.**

### Standard Schema (Official)

```sql
CREATE TABLE positions (
    position_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    market_id TEXT NOT NULL,
    side TEXT NOT NULL,
    direction TEXT NOT NULL,        -- 'up' or 'down'
    size_usd REAL NOT NULL,         -- Dollar amount of position
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,
    exit_price REAL,
    exit_time TEXT,
    pnl REAL DEFAULT 0.0,
    exit_reason TEXT,
    status TEXT NOT NULL,           -- 'open' or 'closed'
    order_id TEXT
);
```

### Changes Made

**1. Backend (`ui/backend/app/main.py`):**
- **Removed** all schema mapping code
- **Returns** raw database fields directly
- **No translation** between old/new names

```python
# BEFORE (mapping hell):
pos['opened_at'] = pos.get('entry_time')
pos['outcome'] = pos.get('direction')
pos['shares'] = pos.get('size_usd')
pos['size'] = pos.get('size_usd')
pos['trade_id'] = pos.get('position_id')

# AFTER (raw fields):
# Just return dict(row) - no mapping
```

**2. Frontend (`ui/frontend/src/components/OpenPositions.jsx`):**
- **Changed:** `pos.size` → `pos.size_usd`
- **Changed:** `pos.opened_at` → `pos.entry_time`
- **Uses** exact database field names

**3. Frontend (`ui/frontend/src/components/LiveTradeFeed.jsx`):**
- **Changed:** `trade.outcome` → `trade.direction`
- **Fallback:** `trade.direction || trade.outcome` (for old data)

## Field Name Reference

**Use these names everywhere:**

| Concept | Database Field | Frontend | Backend API |
|---------|---------------|----------|-------------|
| Position ID | `position_id` | `pos.position_id` | Same |
| Market | `symbol` | `pos.symbol` | Same |
| Market ID | `market_id` | `pos.market_id` | Same |
| Direction | `direction` | `pos.direction` | Same |
| Position Size | `size_usd` | `pos.size_usd` | Same |
| Entry Price | `entry_price` | `pos.entry_price` | Same |
| Entry Time | `entry_time` | `pos.entry_time` | Same |
| Exit Price | `exit_price` | `pos.exit_price` | Same |
| Exit Time | `exit_time` | `pos.exit_time` | Same |
| P&L | `pnl` | `pos.pnl` | Same |
| Status | `status` | `pos.status` | Same |

## Migration Notes

**Old field names (deprecated):**
- ❌ `opened_at` → Use `entry_time`
- ❌ `outcome` → Use `direction`
- ❌ `shares` → Use `size_usd`
- ❌ `size` → Use `size_usd`
- ❌ `trade_id` → Use `position_id`

**Backward compatibility:**
- LiveTradeFeed still checks `trade.outcome` as fallback for old data
- Once all trades are closed, remove fallbacks

## Benefits

✅ **No more undefined values**
✅ **No mapping code to maintain**
✅ **Single source of truth** (database schema)
✅ **Easier debugging** (fields match DB exactly)
✅ **Faster development** (no translation layer)

## Testing

```bash
# Check database fields
sqlite3 paper_trading.db "SELECT * FROM positions LIMIT 1;"

# Check API response
curl http://localhost:8000/api/all-positions | jq '.positions[0]'

# Verify field names match schema
# Should see: position_id, symbol, direction, size_usd, entry_time
```

## Future Guidelines

**When adding new fields:**

1. **Add to database schema first**
2. **Use the EXACT same name** in backend
3. **Use the EXACT same name** in frontend
4. **No mapping, no aliases**

**Example:**
```python
# Database: exit_reason TEXT
# Backend: return row['exit_reason']
# Frontend: pos.exit_reason
```

## Lesson Learned

**Consistency > Flexibility**

Don't try to "improve" field names at different layers. Pick good names once, use them everywhere. The pain of mapping is worse than slightly verbose field names.

---

**Files Changed:**
- `ui/backend/app/main.py` (removed mapping)
- `ui/frontend/src/components/OpenPositions.jsx` (standardized fields)
- `ui/frontend/src/components/LiveTradeFeed.jsx` (standardized fields)

**Status:** ✅ Applied and tested
