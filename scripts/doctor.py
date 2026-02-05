#!/usr/bin/env python3
"""
Polymarket Bot Doctor - Diagnostic and auto-fix tool
Usage: ./doctor.py [--fix]
"""

import sys
import os
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Paths
PRIMARY_BOT_DIR = Path.home() / "Stable" / "polymarket-bot"
SECONDARY_BOT_DIR = Path.home() / "gubu-workspace" / "tmp" / "repos" / "polymarket-arbitrage-bot"
PRIMARY_DB = PRIMARY_BOT_DIR / "paper_trading.db"
SECONDARY_DB = SECONDARY_BOT_DIR / "paper_trading.db"

def print_header(text):
    """Print section header"""
    print(f"\n{BOLD}{BLUE}{'=' * 50}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 50}{RESET}\n")

def print_check(name, status, details=""):
    """Print check result"""
    status_icon = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    print(f"{status_icon} {name}")
    if details:
        print(f"  └─ {details}")

def check_bot_processes():
    """Check if bot processes are running"""
    print_header("🔍 CHECKING BOT PROCESSES")
    
    # Check primary bot
    primary_running = False
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python main.py"],
            capture_output=True,
            text=True,
            cwd=str(PRIMARY_BOT_DIR)
        )
        primary_running = bool(result.stdout.strip())
        primary_pid = result.stdout.strip() if primary_running else "N/A"
    except:
        primary_pid = "N/A"
    
    print_check(
        "Primary Bot", 
        primary_running, 
        f"PID: {primary_pid}" if primary_running else "Not running"
    )
    
    # Check secondary bot
    secondary_running = False
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python bot_paper.py"],
            capture_output=True,
            text=True
        )
        secondary_running = bool(result.stdout.strip())
        secondary_pid = result.stdout.strip() if secondary_running else "N/A"
    except:
        secondary_pid = "N/A"
    
    print_check(
        "Secondary Bot", 
        secondary_running,
        f"PID: {secondary_pid}" if secondary_running else "Not running"
    )
    
    return primary_running, secondary_running

def check_databases():
    """Check database integrity"""
    print_header("💾 CHECKING DATABASES")
    
    # Check primary database
    primary_ok = PRIMARY_DB.exists()
    if primary_ok:
        try:
            conn = sqlite3.connect(str(PRIMARY_DB))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            print_check("Primary Database", True, f"{table_count} tables")
        except Exception as e:
            print_check("Primary Database", False, f"Error: {e}")
            primary_ok = False
    else:
        print_check("Primary Database", False, "File not found")
    
    # Check secondary database
    secondary_ok = SECONDARY_DB.exists()
    if secondary_ok:
        try:
            conn = sqlite3.connect(str(SECONDARY_DB))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            print_check("Secondary Database", True, f"{table_count} tables")
        except Exception as e:
            print_check("Secondary Database", False, f"Error: {e}")
            secondary_ok = False
    else:
        print_check("Secondary Database", False, "File not found")
    
    return primary_ok, secondary_ok

def check_logs():
    """Check recent log entries for errors"""
    print_header("📝 CHECKING LOGS")
    
    # Primary bot log
    primary_log = PRIMARY_BOT_DIR / "bot.log"
    if primary_log.exists():
        try:
            with open(primary_log, 'r') as f:
                lines = f.readlines()
                recent = lines[-50:] if len(lines) > 50 else lines
                errors = [l for l in recent if 'ERROR' in l or 'CRITICAL' in l]
                
                if errors:
                    print_check("Primary Bot Logs", False, f"{len(errors)} errors in last 50 lines")
                    print(f"\n{YELLOW}Recent errors:{RESET}")
                    for err in errors[-3:]:
                        print(f"  {err.strip()}")
                else:
                    print_check("Primary Bot Logs", True, "No recent errors")
        except Exception as e:
            print_check("Primary Bot Logs", False, f"Can't read: {e}")
    else:
        print_check("Primary Bot Logs", False, "Log file not found")
    
    # Secondary bot log
    secondary_log = SECONDARY_BOT_DIR / "paper_bot_live.log"
    if secondary_log.exists():
        try:
            with open(secondary_log, 'r') as f:
                lines = f.readlines()
                recent = lines[-50:] if len(lines) > 50 else lines
                errors = [l for l in recent if 'ERROR' in l or 'CRITICAL' in l or 'Traceback' in l]
                
                if errors:
                    print_check("Secondary Bot Logs", False, f"{len(errors)} errors in last 50 lines")
                    print(f"\n{YELLOW}Recent errors:{RESET}")
                    for err in errors[-3:]:
                        print(f"  {err.strip()}")
                else:
                    print_check("Secondary Bot Logs", True, "No recent errors")
        except Exception as e:
            print_check("Secondary Bot Logs", False, f"Can't read: {e}")
    else:
        print_check("Secondary Bot Logs", False, "Log file not found")

def check_config():
    """Check configuration files"""
    print_header("⚙️  CHECKING CONFIGURATION")
    
    # Primary config
    primary_config = PRIMARY_BOT_DIR / "config.json"
    primary_ok = primary_config.exists()
    print_check("Primary Config", primary_ok, 
                str(primary_config) if primary_ok else "Not found")
    
    # Secondary config
    secondary_config = SECONDARY_BOT_DIR / "config.json"
    secondary_ok = secondary_config.exists()
    print_check("Secondary Config", secondary_ok,
                str(secondary_config) if secondary_ok else "Not found")
    
    return primary_ok, secondary_ok

def get_database_stats():
    """Get stats from databases"""
    print_header("📊 DATABASE STATISTICS")
    
    # Primary stats
    if PRIMARY_DB.exists():
        try:
            conn = sqlite3.connect(str(PRIMARY_DB))
            cursor = conn.cursor()
            
            # Get balance
            cursor.execute("SELECT balance FROM state ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            balance = row[0] if row else 1000.0
            
            # Get trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
            row = cursor.fetchone()
            trades = row[0] if row else 0
            
            # Get open positions
            cursor.execute("SELECT COUNT(*) FROM positions WHERE status='open'")
            row = cursor.fetchone()
            positions = row[0] if row else 0
            
            conn.close()
            
            print(f"{BOLD}Primary Bot:{RESET}")
            print(f"  Balance: ${balance:,.2f}")
            print(f"  Closed Trades: {trades}")
            print(f"  Open Positions: {positions}")
        except Exception as e:
            print(f"{RED}Primary DB Error: {e}{RESET}")
    
    # Secondary stats
    if SECONDARY_DB.exists():
        try:
            conn = sqlite3.connect(str(SECONDARY_DB))
            cursor = conn.cursor()
            
            # Get balance
            cursor.execute("SELECT balance FROM state ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            balance = row[0] if row else 1000.0
            
            # Get trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
            row = cursor.fetchone()
            trades = row[0] if row else 0
            
            # Get open positions
            cursor.execute("SELECT COUNT(*) FROM positions WHERE status='open'")
            row = cursor.fetchone()
            positions = row[0] if row else 0
            
            conn.close()
            
            print(f"\n{BOLD}Secondary Bot:{RESET}")
            print(f"  Balance: ${balance:,.2f}")
            print(f"  Closed Trades: {trades}")
            print(f"  Open Positions: {positions}")
        except Exception as e:
            print(f"{RED}Secondary DB Error: {e}{RESET}")

def restart_bots():
    """Restart both bots"""
    print_header("🔄 RESTARTING BOTS")
    
    # Kill existing processes
    print("Stopping existing processes...")
    subprocess.run(["pkill", "-f", "python main.py"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "python bot_paper.py"], stderr=subprocess.DEVNULL)
    
    import time
    time.sleep(2)
    
    # Start primary bot
    print("Starting primary bot...")
    try:
        subprocess.Popen(
            ["bash", "-c", "cd ~/Stable/polymarket-bot && source venv/bin/activate && nohup python main.py > bot.log 2>&1 &"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"{GREEN}✓{RESET} Primary bot started")
    except Exception as e:
        print(f"{RED}✗{RESET} Failed to start primary bot: {e}")
    
    # Start secondary bot
    print("Starting secondary bot...")
    try:
        subprocess.Popen(
            ["bash", "-c", "cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot && nohup python bot_paper.py > paper_bot_live.log 2>&1 &"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"{GREEN}✓{RESET} Secondary bot started")
    except Exception as e:
        print(f"{RED}✗{RESET} Failed to start secondary bot: {e}")
    
    time.sleep(3)
    
    # Verify
    print("\nVerifying...")
    primary_running, secondary_running = check_bot_processes()
    
    if primary_running and secondary_running:
        print(f"\n{GREEN}{BOLD}✅ Both bots are now running!{RESET}")
    else:
        print(f"\n{YELLOW}⚠️  Check logs for startup errors{RESET}")

def main():
    """Main diagnostic routine"""
    auto_fix = "--fix" in sys.argv
    
    print(f"\n{BOLD}{BLUE}🏥 Polymarket Bot Doctor{RESET}")
    print(f"{BLUE}Diagnostic Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")
    
    # Run checks
    primary_running, secondary_running = check_bot_processes()
    primary_db_ok, secondary_db_ok = check_databases()
    check_logs()
    primary_config_ok, secondary_config_ok = check_config()
    get_database_stats()
    
    # Summary
    print_header("📋 SUMMARY")
    
    issues = []
    if not primary_running:
        issues.append("Primary bot is not running")
    if not secondary_running:
        issues.append("Secondary bot is not running")
    if not primary_db_ok:
        issues.append("Primary database has issues")
    if not secondary_db_ok:
        issues.append("Secondary database has issues")
    if not primary_config_ok:
        issues.append("Primary config missing")
    if not secondary_config_ok:
        issues.append("Secondary config missing")
    
    if issues:
        print(f"{YELLOW}Issues found:{RESET}")
        for issue in issues:
            print(f"  • {issue}")
        
        if auto_fix:
            if not primary_running or not secondary_running:
                restart_bots()
        else:
            print(f"\n{BLUE}💡 Tip: Run with --fix to auto-restart bots{RESET}")
    else:
        print(f"{GREEN}✅ All systems healthy!{RESET}")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)
