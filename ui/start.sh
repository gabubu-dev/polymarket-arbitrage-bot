#!/bin/bash

# Polymarket Arbitrage Bot UI Startup Script
# Starts both backend (FastAPI) and frontend (React/Vite)

set -e

echo "🚀 Starting Polymarket Arbitrage Bot UI..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Check if backend dependencies are installed
if [ ! -d "backend/venv" ] && [ ! -f "backend/.deps-installed" ]; then
    echo "${YELLOW}📦 Installing backend dependencies...${NC}"
    cd backend
    pip install -q -r requirements.txt
    touch .deps-installed
    cd ..
    echo "${GREEN}✓ Backend dependencies installed${NC}"
fi

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "${YELLOW}📦 Installing frontend dependencies...${NC}"
    cd frontend
    npm install --silent
    cd ..
    echo "${GREEN}✓ Frontend dependencies installed${NC}"
fi

# Start backend
echo "${BLUE}Starting backend (FastAPI) on http://127.0.0.1:8000${NC}"
cd backend
python app/main.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        echo "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "${YELLOW}Warning: Backend may not have started properly${NC}"
        echo "Check backend.log for details"
    fi
    sleep 0.5
done

# Start frontend
echo "${BLUE}Starting frontend (React) on http://127.0.0.1:3000${NC}"
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 2

echo ""
echo "${GREEN}✅ UI is running!${NC}"
echo ""
echo "  Frontend: ${BLUE}http://127.0.0.1:3000${NC}"
echo "  Backend:  ${BLUE}http://127.0.0.1:8000${NC}"
echo "  API Docs: ${BLUE}http://127.0.0.1:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Try to open browser
if command -v xdg-open > /dev/null; then
    xdg-open http://127.0.0.1:3000 > /dev/null 2>&1 || true
elif command -v open > /dev/null; then
    open http://127.0.0.1:3000 > /dev/null 2>&1 || true
fi

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
