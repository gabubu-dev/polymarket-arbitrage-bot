#!/usr/bin/env python3
"""
Mobile-optimized CLI status for Polymarket bots
Usage: ./status-mobile.py
       ./status-mobile.py --json
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
PURPLE = '\033[95m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Paths
PRIMARY_DB = Path.home() / "Stable" / "polymarket-bot" / "paper_trading.db"
SECONDARY_DB = Path.home() / "gubu-workspace" / "tmp" / "repos" / "polymarket-arbitrage-bot" / "paper_trading.db"

def get_bot_stats(db_path: Path) -> Dict[str, Any]:
    """Get stats from a bot database"""
    if not db_path.exists():
        return {
            'balance': 1000.0,
            'pnl': 0.0,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'open_positions': 0
        }
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check which tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    balance = 1000.0
    pnl = 0.0
    trades = 0
    wins = 0
    losses = 0
    open_positions = 0
    
    # Try to get balance from balance_history if it exists
    if 'balance_history' in tables:
        try:
            cursor.execute("SELECT balance FROM balance_history ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                balance = row[0]
        except:
            pass
    
    # Get trade stats from trades table if it exists
    if 'trades' in tables:
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(COALESCE(realized_pnl, 0)) as total_pnl
                FROM trades
                WHERE realized_pnl IS NOT NULL
            """)
            row = cursor.fetchone()
            if row:
                trades, wins, losses, pnl = row
                trades = trades or 0
                wins = wins or 0
                losses = losses or 0
                pnl = pnl or 0.0
        except:
            pass
    
    # Try statistics table if trades table doesn't exist (secondary bot)
    elif 'statistics' in tables:
        try:
            cursor.execute("SELECT value FROM state WHERE key = 'balance'")
            row = cursor.fetchone()
            if row:
                balance = float(row[0])
        except:
            pass
    
    # Get open positions count
    if 'positions' in tables:
        try:
            cursor.execute("SELECT COUNT(*) FROM positions")
            row = cursor.fetchone()
            if row:
                open_positions = row[0] or 0
        except:
            pass
    
    conn.close()
    
    return {
        'balance': balance,
        'pnl': pnl,
        'trades': trades,
        'wins': wins,
        'losses': losses,
        'open_positions': open_positions
    }

def format_money(amount: float) -> str:
    """Format money with color"""
    if amount > 0:
        return f"{GREEN}${amount:,.2f}{RESET}"
    elif amount < 0:
        return f"{RED}-${abs(amount):,.2f}{RESET}"
    else:
        return f"${amount:,.2f}"

def format_percentage(pnl: float, balance: float) -> str:
    """Format P&L percentage with color"""
    if balance == 0:
        return "(0.0%)"
    pct = (pnl / balance) * 100
    if pct > 0:
        return f"{GREEN}(+{pct:.1f}%){RESET}"
    elif pct < 0:
        return f"{RED}({pct:.1f}%){RESET}"
    else:
        return "(0.0%)"

def display_status():
    """Display mobile-optimized status"""
    # Get stats from both bots
    primary = get_bot_stats(PRIMARY_DB)
    secondary = get_bot_stats(SECONDARY_DB)
    
    # Calculate combined stats
    total_balance = primary['balance'] + secondary['balance']
    total_pnl = primary['pnl'] + secondary['pnl']
    total_trades = primary['trades'] + secondary['trades']
    total_wins = primary['wins'] + secondary['wins']
    total_losses = primary['losses'] + secondary['losses']
    total_open = primary['open_positions'] + secondary['open_positions']
    
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    
    # Current time
    now = datetime.now().strftime("%I:%M %p EST")
    
    # Check if bots are running
    try:
        import psutil
        primary_running = any('main.py' in ' '.join(p.cmdline()) 
                             for p in psutil.process_iter(['cmdline']))
        secondary_running = any('bot_paper.py' in ' '.join(p.cmdline()) 
                               for p in psutil.process_iter(['cmdline']))
    except:
        primary_running = False
        secondary_running = False
    
    # Load activity log
    activity_file = Path.home() / "Stable" / "polymarket-bot" / "bot_activity.json"
    activity = {'primary': {}, 'secondary': {}}
    if activity_file.exists():
        try:
            with open(activity_file) as f:
                activity = json.load(f)
        except:
            pass
    
    # JSON output
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_balance': total_balance,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'wins': total_wins,
            'losses': total_losses,
            'open_positions': total_open,
            'win_rate': win_rate,
            'bots': {
                'primary': {
                    'running': primary_running,
                    **primary
                },
                'secondary': {
                    'running': secondary_running,
                    **secondary
                }
            }
        }
        print(json.dumps(data, indent=2))
        sys.exit(0)
    
    # Build display
    width = 40
    print()
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ 🤖 {BOLD}Polymarket Trading Bot{RESET}".ljust(width + 10) + "│")
    print(f"│ ⏰ {now}".ljust(width + 10) + "│")
    print("├" + "─" * (width - 2) + "┤")
    print("│".ljust(width) + "│")
    
    # Total Balance
    print(f"│   {BLUE}💰 TOTAL BALANCE{RESET}".ljust(width + 10) + "│")
    print(f"│      {BOLD}{format_money(total_balance)}{RESET}".ljust(width + 30) + "│")
    print("│".ljust(width) + "│")
    
    # Today's P&L
    print(f"│   {PURPLE}📈 TODAY'S P&L{RESET}".ljust(width + 10) + "│")
    pnl_str = f"      {format_money(total_pnl)} {format_percentage(total_pnl, total_balance)}"
    print(f"│{pnl_str}".ljust(width + 30) + "│")
    print("│".ljust(width) + "│")
    
    print("├" + "─" * (width - 2) + "┤")
    print(f"│  {YELLOW}🎯 QUICK STATS{RESET}".ljust(width + 10) + "│")
    print("│".ljust(width) + "│")
    
    # Stats row
    stats_line = f"│  ✅ {total_wins}    ❌ {total_losses}    ⏳ {total_open}"
    print(stats_line.ljust(width) + "│")
    print(f"│  Win Rate: {win_rate:.0f}%".ljust(width) + "│")
    print("│".ljust(width) + "│")
    
    print("├" + "─" * (width - 2) + "┤")
    print(f"│  {BOLD}🤖 BOTS{RESET}".ljust(width + 10) + "│")
    print("│".ljust(width) + "│")
    
    # Primary bot
    status_dot = f"{GREEN}🟢{RESET}" if primary_running else f"{RED}🔴{RESET}"
    print(f"│  {status_dot} Primary: ${primary['balance']:,.2f}".ljust(width + 10) + "│")
    print(f"│     {primary['trades']} trades".ljust(width) + "│")
    
    # Show last activity if available
    if activity.get('primary', {}).get('last_check'):
        last = activity['primary']['last_check']
        try:
            last_dt = datetime.fromisoformat(last)
            mins_ago = int((datetime.now() - last_dt).total_seconds() / 60)
            print(f"│     Last check: {mins_ago}m ago".ljust(width) + "│")
        except:
            pass
    
    print("│".ljust(width) + "│")
    
    # Secondary bot
    status_dot = f"{GREEN}🟢{RESET}" if secondary_running else f"{RED}🔴{RESET}"
    print(f"│  {status_dot} Secondary: ${secondary['balance']:,.2f}".ljust(width + 10) + "│")
    print(f"│     {secondary['trades']} trades".ljust(width) + "│")
    
    # Show last activity if available
    if activity.get('secondary', {}).get('last_check'):
        last = activity['secondary']['last_check']
        try:
            last_dt = datetime.fromisoformat(last)
            mins_ago = int((datetime.now() - last_dt).total_seconds() / 60)
            print(f"│     Last check: {mins_ago}m ago".ljust(width) + "│")
        except:
            pass
    
    print("│".ljust(width) + "│")
    
    print("└" + "─" * (width - 2) + "┘")
    print()

if __name__ == "__main__":
    try:
        display_status()
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)
