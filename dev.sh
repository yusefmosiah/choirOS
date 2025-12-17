#!/bin/bash
# ChoirOS Development Startup Script
# Runs both frontend and backend in parallel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🎹 Starting ChoirOS Development Environment${NC}"
echo ""

# Check if we're in the choirOS directory
if [ ! -d "choiros" ] || [ ! -d "api" ]; then
    echo -e "${RED}Error: Run this script from the choirOS root directory${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $FRONTEND_PID $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Setup Python virtual environment if needed
if [ ! -d "api/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd api
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    source api/venv/bin/activate
fi

echo -e "${GREEN}Starting Backend (FastAPI)...${NC}"
cd api
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

echo -e "${GREEN}Starting Frontend (Vite)...${NC}"
cd choiros
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}✅ ChoirOS is running!${NC}"
echo -e "   Frontend: ${YELLOW}http://localhost:5173${NC}"
echo -e "   Backend:  ${YELLOW}http://localhost:8000${NC}"
echo -e "   API Docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop"
echo ""

# Wait for either process to exit
wait $FRONTEND_PID $BACKEND_PID
