#!/usr/bin/env python3
"""
Quick start script - Sets up and runs the bot with minimal configuration
"""

import json
import os
import sys


def create_quick_config():
    """Create a minimal working configuration"""
    config = {
        "paper_trading": {
            "enabled": True,
            "initial_balance_usdc": 5000.0,
            "slippage_min": 0.005,
            "slippage_max": 0.01,
            "gas_cost_gwei": 50,
            "gas_limit": 200000
        },
        "risk_management": {
            "daily_loss_limit_percent": 5.0,
            "max_position_size_percent": 5.0,
            "max_concurrent_positions": 5,
            "min_win_rate_percent": 50.0,
            "min_trades_for_win_rate": 20,
            "auto_unfollow_bad_performers": True,
            "stop_loss_percent": 10.0,
            "take_profit_percent": 20.0
        },
        "target_wallets": [],
        "wallet_discovery": {
            "enabled": True,
            "min_monthly_trades": 5,
            "min_win_rate_percent": 55,
            "focus_categories": ["politics", "sports"],
            "lookback_days": 90
        },
        "monitoring": {
            "poll_interval_seconds": 15,
            "rpc_endpoints": [
                "https://polygon-rpc.com",
                "https://rpc.ankr.com/polygon"
            ],
            "graphql_endpoint": "https://api.polymarket.com/graphql"
        },
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "notifications": {
                "on_trade_copy": True,
                "on_daily_summary": True,
                "on_wallet_unfollow": True,
                "on_risk_limit_hit": True,
                "on_performance_alert": True
            },
            "daily_summary_time": "20:00"
        },
        "data_export": {
            "enabled": True,
            "export_interval_hours": 24,
            "formats": ["json", "csv"],
            "output_directory": "./exports"
        },
        "logging": {
            "level": "INFO",
            "file": "bot.log",
            "max_size_mb": 100,
            "backup_count": 5
        },
        "live_trading": {
            "enabled": False,
            "private_key": "",
            "wallet_address": ""
        }
    }
    
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("✅ Created config.json with default settings")
    print("   - Starting balance: $5,000 USDC")
    print("   - Auto-discovery enabled for politics & sports")
    print("   - Telegram disabled (enable in config to use)")


def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required = [
        "web3", "requests", "aiohttp", "pandas", "python-telegram-bot"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("✅ All dependencies installed")
    return True


def main():
    print("=" * 60)
    print("🚀 Polymarket Copy Trading Bot - Quick Start")
    print("=" * 60)
    
    # Check if config exists
    if not os.path.exists("config.json"):
        print("\n⚙️  Creating configuration...")
        create_quick_config()
    else:
        print("\n✅ Configuration already exists (config.json)")
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎯 Ready to start!")
    print("=" * 60)
    
    print("\nOptions:")
    print("  1. Start the bot now")
    print("  2. Analyze a wallet first")
    print("  3. Discover top wallets")
    print("  4. Run tests")
    print("  5. Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        print("\n🚀 Starting bot...")
        os.system(f"{sys.executable} main.py")
    
    elif choice == "2":
        wallet = input("\nEnter wallet address: ").strip()
        if wallet:
            os.system(f"{sys.executable} wallet_analyzer.py {wallet}")
    
    elif choice == "3":
        print("\n🔍 Discovering wallets...")
        os.system(f"{sys.executable} wallet_analyzer.py --discover")
    
    elif choice == "4":
        print("\n🧪 Running tests...")
        os.system(f"{sys.executable} tests.py")
    
    else:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
