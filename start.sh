#!/bin/bash

# OpenQuest Startup Script for Linux/macOS
# Activates virtual environment and starts the application

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=================================================="
echo "  OpenQuest - Startup Script"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    echo "Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}→${NC} Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo ""

# Check QuestDB
echo -e "${YELLOW}→${NC} Checking QuestDB..."
if command -v curl &> /dev/null; then
    if curl -s --connect-timeout 5 http://127.0.0.1:9000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} QuestDB is running"
    else
        echo -e "${YELLOW}⚠${NC} QuestDB is not running!"
        echo "Start QuestDB first:"
        echo "  docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
echo ""

# Start application
echo "=================================================="
echo -e "${GREEN}  Starting OpenQuest...${NC}"
echo "=================================================="
echo ""
echo "Access URLs:"
echo "  Dashboard:      http://127.0.0.1:5001"
echo "  Charts:         http://127.0.0.1:5001/chart"
echo "  Market Profile: http://127.0.0.1:5001/market-profile"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py
