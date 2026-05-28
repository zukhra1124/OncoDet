#!/bin/bash
# Real-time integration startup script
# Starts both backend and frontend servers

echo "=========================================="
echo "Starting Full Stack Application"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Windows or Linux
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    IS_WINDOWS=true
else
    IS_WINDOWS=false
fi

# Kill existing processes
if [ "$IS_WINDOWS" = true ]; then
    echo -e "${YELLOW}Stopping existing processes...${NC}"
    pkill -f "python backend/app.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
else
    echo -e "${YELLOW}Stopping existing processes...${NC}"
    pkill -f "python backend/app.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
fi

sleep 2

# Start Backend
echo -e "${GREEN}Starting Backend Server (port 5001)...${NC}"
cd backend
python app.py &
BACKEND_PID=$!
sleep 3

# Start Frontend
echo -e "${GREEN}Starting Frontend Server (port 5175)...${NC}"
cd ../frontend
npm run dev &
FRONTEND_PID=$!

sleep 2

# Print status
echo ""
echo "=========================================="
echo "✅ Full Stack Running"
echo "=========================================="
echo -e "${GREEN}Backend:  http://localhost:5001${NC}"
echo -e "${GREEN}Frontend: http://localhost:5175${NC}"
echo -e "${GREEN}API:      http://localhost:5175/api${NC}"
echo ""
echo "🏥 Open http://localhost:5175 in your browser"
echo ""
echo "Press CTRL+C to stop all services"
echo "=========================================="

# Wait for processes
wait
