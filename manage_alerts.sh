#!/bin/bash

case "$1" in
  start)
    cd ~/gubu-workspace/tmp/repos/polymarket-arbitrage-bot/
    nohup python3 -u trade_alerts.py > trade_alerts.log 2>&1 &
    echo $! > trade_alerts.pid
    echo "✅ Trade alerts started (PID: $(cat trade_alerts.pid))"
    ;;
  stop)
    if [ -f trade_alerts.pid ]; then
      kill $(cat trade_alerts.pid)
      rm trade_alerts.pid
      echo "✅ Trade alerts stopped"
    fi
    ;;
  status)
    if [ -f trade_alerts.pid ] && ps -p $(cat trade_alerts.pid) > /dev/null; then
      echo "✅ Trade alerts running (PID: $(cat trade_alerts.pid))"
    else
      echo "❌ Trade alerts not running"
    fi
    ;;
  logs)
    tail -f trade_alerts.log
    ;;
  *)
    echo "Usage: $0 {start|stop|status|logs}"
    exit 1
    ;;
esac
