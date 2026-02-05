#!/bin/bash
# Read alert queue and send via OpenClaw sessions_spawn with message tool

QUEUE_FILE="/tmp/polymarket_alerts_queue.jsonl"
PROCESSED_FILE="/tmp/polymarket_alerts_processed.txt"
USER_ID="5766153421"

# Create processed file if it doesn't exist
touch "$PROCESSED_FILE"

echo "🚀 Alert sender started"
echo "📝 Monitoring: $QUEUE_FILE"
echo ""

while true; do
    if [ -f "$QUEUE_FILE" ]; then
        # Read unprocessed alerts
        while IFS= read -r line; do
            # Check if already processed
            line_hash=$(echo "$line" | md5sum | cut -d' ' -f1)
            if grep -q "$line_hash" "$PROCESSED_FILE"; then
                continue
            fi
            
            # Parse JSON alert
            title=$(echo "$line" | jq -r '.title')
            message=$(echo "$line" | jq -r '.message')
            
            # Send via OpenClaw CLI
            full_message="**$title**

$message"
            
            # Use sessions_spawn to send message
            sessions_spawn --label send-alert --task "message action=send channel=telegram target=$USER_ID message='$full_message'"
            
            # Mark as processed
            echo "$line_hash" >> "$PROCESSED_FILE"
            echo "✅ Sent: $title"
            
            sleep 1
        done < "$QUEUE_FILE"
        
        # Clear queue after processing
        > "$QUEUE_FILE"
    fi
    
    sleep 3
done
