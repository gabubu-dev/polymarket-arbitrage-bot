"""
FastAPI backend for Polymarket Arbitrage Bot UI.
Provides API endpoints for configuration, monitoring, and control.
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psutil

# Add bot source to path
BOT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BOT_ROOT / "src"))

app = FastAPI(title="Polymarket Arbitrage Bot API", version="1.0.0")

# CORS - localhost only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bot state
bot_process: Optional[subprocess.Popen] = None
bot_pid: Optional[int] = None

# File paths
CONFIG_PATH = BOT_ROOT / "config.json"
LOG_PATH = BOT_ROOT / "logs" / "bot.log"
TRADES_LOG_PATH = BOT_ROOT / "logs" / "trades.json"


# ============================================================================
# Pydantic Models
# ============================================================================

class PolymarketConfig(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    private_key: str = ""
    chain_id: int = 137


class ExchangeConfig(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = False


class TradingConfig(BaseModel):
    divergence_threshold: float = 0.05
    min_profit_threshold: float = 0.02
    position_size_usd: float = 100.0
    max_positions: int = 5
    max_position_size_usd: float = 500.0


class MarketsConfig(BaseModel):
    enabled_symbols: List[str] = ["BTC/USDT", "ETH/USDT"]
    polymarket_market_types: List[str] = ["15MIN_UP", "15MIN_DOWN"]
    refresh_interval_seconds: int = 5


class RiskManagementConfig(BaseModel):
    stop_loss_percentage: float = 0.15
    take_profit_percentage: float = 0.90
    max_daily_loss_usd: float = 1000.0
    emergency_shutdown_loss_usd: float = 5000.0


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_file: str = "logs/bot.log"
    log_trades: bool = True


class NotificationsConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class BotConfig(BaseModel):
    polymarket: PolymarketConfig
    exchanges: Dict[str, ExchangeConfig]
    trading: TradingConfig
    markets: MarketsConfig
    risk_management: RiskManagementConfig
    logging: LoggingConfig
    notifications: NotificationsConfig


class BotStatus(BaseModel):
    running: bool
    pid: Optional[int]
    uptime_seconds: Optional[int]
    cpu_percent: Optional[float]
    memory_mb: Optional[float]


class Trade(BaseModel):
    timestamp: str
    symbol: str
    side: str
    size_usd: float
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    status: str


class PerformanceStats(BaseModel):
    daily_pnl: float
    weekly_pnl: float
    all_time_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    open_positions: int


# ============================================================================
# Helper Functions
# ============================================================================

def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
    """Mask sensitive string values, showing only last few characters."""
    if not value or len(value) <= show_chars:
        return "*" * 8
    return "*" * (len(value) - show_chars) + value[-show_chars:]


def unmask_if_unchanged(new_value: str, masked_value: str) -> Optional[str]:
    """Return None if value is masked (unchanged), otherwise return new value."""
    if new_value.startswith("*"):
        return None
    return new_value


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if not CONFIG_PATH.exists():
        # Return default config
        return {
            "polymarket": {"api_key": "", "api_secret": "", "private_key": "", "chain_id": 137},
            "exchanges": {
                "binance": {"api_key": "", "api_secret": "", "testnet": False},
                "coinbase": {"api_key": "", "api_secret": ""}
            },
            "trading": {
                "divergence_threshold": 0.05,
                "min_profit_threshold": 0.02,
                "position_size_usd": 100.0,
                "max_positions": 5,
                "max_position_size_usd": 500.0
            },
            "markets": {
                "enabled_symbols": ["BTC/USDT", "ETH/USDT"],
                "polymarket_market_types": ["15MIN_UP", "15MIN_DOWN"],
                "refresh_interval_seconds": 5
            },
            "risk_management": {
                "stop_loss_percentage": 0.15,
                "take_profit_percentage": 0.90,
                "max_daily_loss_usd": 1000.0,
                "emergency_shutdown_loss_usd": 5000.0
            },
            "logging": {
                "level": "INFO",
                "log_file": "logs/bot.log",
                "log_trades": True
            },
            "notifications": {
                "enabled": False,
                "webhook_url": ""
            }
        }
    
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to JSON file."""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


def get_bot_status() -> BotStatus:
    """Get current bot status."""
    global bot_pid
    
    # Check if we have a stored PID
    if bot_pid:
        try:
            process = psutil.Process(bot_pid)
            if process.is_running() and 'python' in process.name().lower():
                # Calculate uptime
                create_time = process.create_time()
                uptime = int(datetime.now().timestamp() - create_time)
                
                return BotStatus(
                    running=True,
                    pid=bot_pid,
                    uptime_seconds=uptime,
                    cpu_percent=process.cpu_percent(interval=0.1),
                    memory_mb=process.memory_info().rss / 1024 / 1024
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            bot_pid = None
    
    # Try to find bot process by searching for bot.py
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'bot.py' in ' '.join(cmdline):
                bot_pid = proc.info['pid']
                process = psutil.Process(bot_pid)
                create_time = process.create_time()
                uptime = int(datetime.now().timestamp() - create_time)
                
                return BotStatus(
                    running=True,
                    pid=bot_pid,
                    uptime_seconds=uptime,
                    cpu_percent=process.cpu_percent(interval=0.1),
                    memory_mb=process.memory_info().rss / 1024 / 1024
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue
    
    return BotStatus(running=False, pid=None, uptime_seconds=None, cpu_percent=None, memory_mb=None)


def load_trades() -> List[Trade]:
    """Load trade history from logs."""
    if not TRADES_LOG_PATH.exists():
        return []
    
    trades = []
    try:
        with open(TRADES_LOG_PATH, 'r') as f:
            for line in f:
                try:
                    trade_data = json.loads(line.strip())
                    trades.append(Trade(**trade_data))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    
    return sorted(trades, key=lambda t: t.timestamp, reverse=True)


def calculate_performance() -> PerformanceStats:
    """Calculate performance statistics from trade history."""
    trades = load_trades()
    
    if not trades:
        return PerformanceStats(
            daily_pnl=0.0,
            weekly_pnl=0.0,
            all_time_pnl=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            open_positions=0
        )
    
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)
    
    daily_pnl = 0.0
    weekly_pnl = 0.0
    all_time_pnl = 0.0
    winning_trades = 0
    losing_trades = 0
    open_positions = 0
    
    for trade in trades:
        trade_time = datetime.fromisoformat(trade.timestamp.replace('Z', '+00:00'))
        
        if trade.status == 'open':
            open_positions += 1
            continue
        
        pnl = trade.pnl or 0.0
        all_time_pnl += pnl
        
        if trade_time >= one_day_ago:
            daily_pnl += pnl
        
        if trade_time >= one_week_ago:
            weekly_pnl += pnl
        
        if pnl > 0:
            winning_trades += 1
        elif pnl < 0:
            losing_trades += 1
    
    total_closed = winning_trades + losing_trades
    win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0.0
    
    return PerformanceStats(
        daily_pnl=daily_pnl,
        weekly_pnl=weekly_pnl,
        all_time_pnl=all_time_pnl,
        total_trades=len(trades),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        open_positions=open_positions
    )


def get_recent_logs(num_lines: int = 100) -> List[str]:
    """Get recent log lines."""
    if not LOG_PATH.exists():
        return []
    
    try:
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-num_lines:]]
    except Exception:
        return []


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Polymarket Arbitrage Bot API", "version": "1.0.0"}


@app.get("/api/config")
async def get_config():
    """Get current configuration with masked sensitive values."""
    config = load_config()
    
    # Mask sensitive values
    if config.get('polymarket'):
        config['polymarket']['api_key'] = mask_sensitive_value(config['polymarket'].get('api_key', ''))
        config['polymarket']['api_secret'] = mask_sensitive_value(config['polymarket'].get('api_secret', ''))
        config['polymarket']['private_key'] = mask_sensitive_value(config['polymarket'].get('private_key', ''))
    
    for exchange_name in config.get('exchanges', {}):
        config['exchanges'][exchange_name]['api_key'] = mask_sensitive_value(
            config['exchanges'][exchange_name].get('api_key', '')
        )
        config['exchanges'][exchange_name]['api_secret'] = mask_sensitive_value(
            config['exchanges'][exchange_name].get('api_secret', '')
        )
    
    if config.get('notifications', {}).get('webhook_url'):
        config['notifications']['webhook_url'] = mask_sensitive_value(
            config['notifications']['webhook_url']
        )
    
    return config


@app.post("/api/config")
async def update_config(new_config: BotConfig):
    """Update configuration. Masked values (starting with *) are not updated."""
    current_config = load_config()
    new_config_dict = new_config.model_dump()
    
    # Handle polymarket config
    if new_config_dict.get('polymarket'):
        for key in ['api_key', 'api_secret', 'private_key']:
            new_val = new_config_dict['polymarket'].get(key, '')
            if not new_val.startswith('*'):
                current_config.setdefault('polymarket', {})[key] = new_val
        
        current_config['polymarket']['chain_id'] = new_config_dict['polymarket'].get('chain_id', 137)
    
    # Handle exchanges
    for exchange_name, exchange_data in new_config_dict.get('exchanges', {}).items():
        if exchange_name not in current_config.setdefault('exchanges', {}):
            current_config['exchanges'][exchange_name] = {}
        
        for key in ['api_key', 'api_secret']:
            new_val = exchange_data.get(key, '')
            if not new_val.startswith('*'):
                current_config['exchanges'][exchange_name][key] = new_val
        
        current_config['exchanges'][exchange_name]['testnet'] = exchange_data.get('testnet', False)
    
    # Update non-sensitive configs directly
    current_config['trading'] = new_config_dict.get('trading', current_config.get('trading', {}))
    current_config['markets'] = new_config_dict.get('markets', current_config.get('markets', {}))
    current_config['risk_management'] = new_config_dict.get('risk_management', current_config.get('risk_management', {}))
    current_config['logging'] = new_config_dict.get('logging', current_config.get('logging', {}))
    
    # Handle notifications webhook URL
    if new_config_dict.get('notifications'):
        webhook_url = new_config_dict['notifications'].get('webhook_url', '')
        if not webhook_url.startswith('*'):
            current_config.setdefault('notifications', {})['webhook_url'] = webhook_url
        current_config['notifications']['enabled'] = new_config_dict['notifications'].get('enabled', False)
    
    # Save updated config
    save_config(current_config)
    
    return {"message": "Configuration updated successfully"}


@app.get("/api/status")
async def get_status():
    """Get bot status and performance metrics."""
    bot_status = get_bot_status()
    performance = calculate_performance()
    
    return {
        "bot": bot_status.model_dump(),
        "performance": performance.model_dump()
    }


@app.get("/api/trades")
async def get_trades(limit: int = 50):
    """Get recent trades."""
    trades = load_trades()
    return [trade.model_dump() for trade in trades[:limit]]


@app.post("/api/control/start")
async def start_bot(background_tasks: BackgroundTasks):
    """Start the bot."""
    global bot_process, bot_pid
    
    status = get_bot_status()
    if status.running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    # Verify config exists
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=400, detail="Configuration file not found. Please configure the bot first.")
    
    # Start bot process
    try:
        bot_script = BOT_ROOT / "bot.py"
        bot_process = subprocess.Popen(
            [sys.executable, str(bot_script)],
            cwd=str(BOT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        bot_pid = bot_process.pid
        
        # Give it a moment to start
        await asyncio.sleep(1)
        
        return {"message": "Bot started successfully", "pid": bot_pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@app.post("/api/control/stop")
async def stop_bot():
    """Stop the bot."""
    global bot_pid
    
    status = get_bot_status()
    if not status.running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    try:
        process = psutil.Process(status.pid)
        process.terminate()
        
        # Wait for graceful shutdown
        try:
            process.wait(timeout=10)
        except psutil.TimeoutExpired:
            process.kill()
        
        bot_pid = None
        return {"message": "Bot stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")


@app.post("/api/control/restart")
async def restart_bot(background_tasks: BackgroundTasks):
    """Restart the bot."""
    # Stop if running
    status = get_bot_status()
    if status.running:
        await stop_bot()
        await asyncio.sleep(2)
    
    # Start
    return await start_bot(background_tasks)


@app.get("/api/logs")
async def get_logs(lines: int = 100):
    """Get recent log lines."""
    logs = get_recent_logs(lines)
    return {"logs": logs}


@app.delete("/api/logs")
async def clear_logs():
    """Clear log files."""
    try:
        if LOG_PATH.exists():
            LOG_PATH.unlink()
        if TRADES_LOG_PATH.exists():
            TRADES_LOG_PATH.unlink()
        
        # Recreate logs directory
        LOG_PATH.parent.mkdir(exist_ok=True)
        
        return {"message": "Logs cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    
    # Ensure logs directory exists
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Run on localhost only for security
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
