#!/usr/bin/env python3
"""
Unified Polymarket Trading Bot Launcher
Launch either bot instance with proper configuration
"""

import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Launch Polymarket trading bot')
    parser.add_argument('instance', choices=['primary', 'secondary', 'both'],
                      help='Which bot instance to run')
    parser.add_argument('--mode', choices=['live', 'paper'], default='paper',
                      help='Trading mode (live or paper trading)')
    parser.add_argument('--config', help='Custom config file path')
    
    args = parser.parse_args()
    
    # Set up paths
    repo_root = Path(__file__).parent
    
    if args.instance in ['primary', 'both']:
        print(f"Starting PRIMARY bot in {args.mode} mode...")
        primary_config = args.config or repo_root / 'bots/primary/config.json'
        primary_db = repo_root / 'bots/primary/paper_trading.db'
        # Launch primary bot
        os.system(f'cd {repo_root} && python scripts/main.py --config {primary_config}')
    
    if args.instance in ['secondary', 'both']:
        print(f"Starting SECONDARY bot in {args.mode} mode...")
        secondary_config = args.config or repo_root / 'bots/secondary/config.json'
        bot_script = 'bot_paper.py' if args.mode == 'paper' else 'bot.py'
        # Launch secondary bot
        os.system(f'cd {repo_root}/bots/secondary && python {bot_script}')

if __name__ == '__main__':
    main()
