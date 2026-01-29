#!/bin/bash
# Start Polymarket Live Dashboard

cd "$(dirname "$0")"

echo "=========================================="
echo "🚀 Starting Polymarket Live Dashboard"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check for required dependencies
echo "Checking dependencies..."
python3 -c "import flask, flask_cors, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required dependencies..."
    pip3 install flask flask-cors requests -q
fi

echo "✅ Dependencies OK"
echo ""

# Kill any existing dashboard processes
pkill -f "dashboard_live.py" 2>/dev/null
pkill -f "dashboard.py" 2>/dev/null
sleep 1

# Start the dashboard
echo "Starting dashboard server..."
echo "📊 Dashboard will be available at: http://localhost:8080"
echo "📈 API Health check: http://localhost:8080/api/health"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="

python3 dashboard_live.py
