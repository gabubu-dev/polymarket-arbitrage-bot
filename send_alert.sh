#!/bin/bash
# Helper script to send Telegram alerts via OpenClaw CLI

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "Usage: $0 <message>"
    exit 1
fi

# Write message to queue file
echo "$MESSAGE" >> /tmp/polymarket_alerts_queue.txt
