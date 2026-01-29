#!/usr/bin/env python3
"""
Quick verification script for competitive upgrade.
Tests that all new modules import correctly without making external API calls.
"""

import sys
import json
from pathlib import Path

def test_imports():
    """Test that all new modules can be imported."""
    print("🔍 Verifying Competitive Upgrade Installation...\n")
    
    tests_passed = []
    tests_failed = []
    
    # Test 1: Market Discovery
    try:
        from src.market_discovery import PolymarketDiscovery, MarketOpportunity
        print("✅ Market Discovery module imported")
        tests_passed.append("Market Discovery")
    except Exception as e:
        print(f"❌ Market Discovery import failed: {e}")
        tests_failed.append("Market Discovery")
    
    # Test 2: Twitter Intelligence
    try:
        from src.twitter_intelligence import TwitterIntelligence, BotDiscovery, StrategyInsight
        print("✅ Twitter Intelligence module imported")
        tests_passed.append("Twitter Intelligence")
    except Exception as e:
        print(f"❌ Twitter Intelligence import failed: {e}")
        tests_failed.append("Twitter Intelligence")
    
    # Test 3: Enhanced Strategy Orchestrator
    try:
        from src.strategy_orchestrator import StrategyOrchestrator, StrategyOpportunity
        print("✅ Strategy Orchestrator (enhanced) imported")
        tests_passed.append("Strategy Orchestrator")
    except Exception as e:
        print(f"❌ Strategy Orchestrator import failed: {e}")
        tests_failed.append("Strategy Orchestrator")
    
    # Test 4: Enhanced Telegram Alerts
    try:
        from src.telegram_alerts import TelegramAlerter
        print("✅ Telegram Alerts (enhanced) imported")
        tests_passed.append("Telegram Alerts")
    except Exception as e:
        print(f"❌ Telegram Alerts import failed: {e}")
        tests_failed.append("Telegram Alerts")
    
    return tests_passed, tests_failed


def verify_config():
    """Verify config.json has new sections."""
    print("\n🔍 Verifying Configuration...\n")
    
    config_path = Path("config.json")
    if not config_path.exists():
        print("❌ config.json not found!")
        return False
    
    with open(config_path) as f:
        config = json.load(f)
    
    checks = []
    
    # Check market_discovery section
    if "market_discovery" in config:
        print("✅ market_discovery configuration found")
        checks.append(True)
    else:
        print("❌ market_discovery configuration missing")
        checks.append(False)
    
    # Check twitter_intelligence section
    if "twitter_intelligence" in config:
        print("✅ twitter_intelligence configuration found")
        checks.append(True)
    else:
        print("❌ twitter_intelligence configuration missing")
        checks.append(False)
    
    # Check competitive_intelligence section
    if "competitive_intelligence" in config:
        print("✅ competitive_intelligence configuration found")
        checks.append(True)
    else:
        print("❌ competitive_intelligence configuration missing")
        checks.append(False)
    
    # Check telegram config
    telegram = config.get("telegram", {})
    if telegram.get("chat_id") == "6559976977":
        print("✅ Telegram chat_id correct (qippu)")
        checks.append(True)
    else:
        print("⚠️  Telegram chat_id not set to qippu's ID")
        checks.append(False)
    
    return all(checks)


def verify_documentation():
    """Verify documentation exists."""
    print("\n🔍 Verifying Documentation...\n")
    
    docs = []
    
    if Path("COMPETITIVE_UPGRADE.md").exists():
        print("✅ COMPETITIVE_UPGRADE.md found")
        docs.append(True)
    else:
        print("❌ COMPETITIVE_UPGRADE.md missing")
        docs.append(False)
    
    if Path("README.md").exists():
        print("✅ README.md found")
        docs.append(True)
    else:
        print("⚠️  README.md missing")
        docs.append(False)
    
    return all(docs)


def check_bird_cli():
    """Check if bird CLI is available."""
    print("\n🔍 Checking Bird CLI (Twitter Intelligence)...\n")
    
    import shutil
    if shutil.which("bird"):
        print("✅ bird CLI found in PATH")
        print("   Twitter intelligence will work")
        return True
    else:
        print("⚠️  bird CLI not found")
        print("   Install with: npm install -g @steipete/bird")
        print("   Twitter intelligence will be disabled")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Polymarket Bot - Competitive Upgrade Verification")
    print("=" * 60)
    print()
    
    # Test imports
    tests_passed, tests_failed = test_imports()
    
    # Verify config
    config_ok = verify_config()
    
    # Verify documentation
    docs_ok = verify_documentation()
    
    # Check bird CLI (optional)
    bird_ok = check_bird_cli()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print()
    
    print(f"✅ Module Imports: {len(tests_passed)}/{len(tests_passed) + len(tests_failed)}")
    if tests_failed:
        print(f"   Failed: {', '.join(tests_failed)}")
    
    print(f"{'✅' if config_ok else '❌'} Configuration: {'OK' if config_ok else 'INCOMPLETE'}")
    print(f"{'✅' if docs_ok else '❌'} Documentation: {'OK' if docs_ok else 'MISSING'}")
    print(f"{'✅' if bird_ok else '⚠️ '} Bird CLI: {'Available' if bird_ok else 'Not installed (optional)'}")
    
    print()
    
    # Overall status
    critical_ok = not tests_failed and config_ok
    
    if critical_ok:
        print("🎉 COMPETITIVE UPGRADE VERIFIED!")
        print()
        print("Next steps:")
        print("  1. Run: python bot_enhanced.py --mode paper")
        print("  2. Monitor Telegram for alerts")
        print("  3. Check data/competitive_intelligence.json")
        print()
        if not bird_ok:
            print("Optional: Install bird CLI for Twitter intelligence")
            print("  npm install -g @steipete/bird")
        print()
        return 0
    else:
        print("❌ VERIFICATION FAILED")
        print()
        print("Please fix the issues above and try again.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
