# Configuration Schema Documentation

## Overview

This document describes the configuration schema for the Polymarket Arbitrage Bot.

## Schema Version: 2.0

Updated: 2026-01-29

---

## Configuration Classes

### LoggingConfig

```python
@dataclass
class LoggingConfig:
    level: str = "INFO"              # Logging level (DEBUG, INFO, WARNING, ERROR)
    log_file: str = "logs/bot.log"   # Main log file path
    log_trades: bool = True           # Enable trade logging
    trade_log: str = "logs/trades.log"  # Trade log file path
    error_log: str = "logs/errors.log"  # Error log file path
```

**JSON Example:**
```json
{
  "logging": {
    "level": "INFO",
    "log_file": "logs/bot.log",
    "trade_log": "logs/trades.log",
    "error_log": "logs/errors.log"
  }
}
```

### StrategyConfig

```python
@dataclass
class StrategyConfig:
    enabled: bool = True
    min_divergence: float = 0.03
    max_execution_time_ms: int = 500
    cooldown_seconds: int = 10
    min_spread_percent: float = 0.01
    lookback_periods: int = 10
    momentum_threshold: float = 0.02
    confidence_threshold: float = 0.7
    min_order_size_usd: float = 5000.0
    tracking_window_seconds: int = 300
    follow_threshold: float = 0.6
```

### StrategiesConfig

```python
@dataclass
class StrategiesConfig:
    latency: StrategyConfig
    spread: StrategyConfig
    momentum: StrategyConfig
    whale: StrategyConfig
```

**JSON Example:**
```json
{
  "strategies": {
    "latency": {
      "enabled": true,
      "min_divergence": 0.03,
      "max_execution_time_ms": 500,
      "cooldown_seconds": 10
    },
    "spread": {
      "enabled": true,
      "min_spread_percent": 0.01
    },
    "momentum": {
      "enabled": true,
      "lookback_periods": 10,
      "momentum_threshold": 0.02,
      "confidence_threshold": 0.7
    },
    "whale": {
      "enabled": true,
      "min_order_size_usd": 5000,
      "tracking_window_seconds": 300,
      "follow_threshold": 0.6
    }
  }
}
```

### ProductionConfig

```python
@dataclass
class ProductionConfig:
    max_restart_attempts: int = 5
    health_check_interval: int = 60
```

**JSON Example:**
```json
{
  "production": {
    "max_restart_attempts": 5,
    "health_check_interval": 60
  }
}
```

### TelegramConfig

```python
@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""
    alerts_enabled: bool = False
```

**JSON Example:**
```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "6559976977",
    "alerts_enabled": true
  }
}
```

---

## Migration Guide

### From v1.x to v2.0

#### Changes to LoggingConfig

**Before (v1.x):**
```json
{
  "logging": {
    "level": "INFO",
    "log_file": "logs/bot.log"
  }
}
```

**After (v2.0):**
```json
{
  "logging": {
    "level": "INFO",
    "log_file": "logs/bot.log",
    "trade_log": "logs/trades.log",
    "error_log": "logs/errors.log"
  }
}
```

#### New Sections Required

Add these sections to your `config.json`:

```json
{
  "strategies": {
    "latency": {"enabled": true},
    "spread": {"enabled": true},
    "momentum": {"enabled": true},
    "whale": {"enabled": true}
  },
  "production": {
    "max_restart_attempts": 5,
    "health_check_interval": 60
  },
  "telegram": {
    "bot_token": "",
    "chat_id": "YOUR_TELEGRAM_ID",
    "alerts_enabled": false
  }
}
```

---

## Common Issues

### TypeError: got an unexpected keyword argument

This means your `config.json` has a field that doesn't match the dataclass definition.

**Fix:** Update your `config.json` to match the schema documented above.

### AttributeError: 'Config' object has no attribute

This means your code is trying to access a config section that doesn't exist.

**Fix:** Ensure all required config sections are present in your `config.json`.

---

## Validation

The config system automatically validates:
- ✅ Threshold values are between 0 and 1
- ✅ Position sizes are positive
- ✅ At least one symbol is enabled
- ✅ All required fields are present

---

## Complete Example

See `config.json` in the repository root for a complete, working example.

---

*Last Updated: 2026-01-29*
