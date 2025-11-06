#!/bin/bash

# OpenQuest Installation Script for Linux/macOS
# This script sets up a virtual environment and installs all dependencies

set -e  # Exit on error

echo "=================================================="
echo "  OpenQuest - Installation Script"
echo "  Platform: Linux/macOS"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}[1/7]${NC} Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.11+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required${NC}"
    echo "Current version: Python $PYTHON_VERSION"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment
echo -e "${YELLOW}[2/7]${NC} Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}Warning: venv directory already exists${NC}"
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✓${NC} Virtual environment recreated"
    else
        echo -e "${YELLOW}→${NC} Using existing virtual environment"
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi
echo ""

# Activate virtual environment
echo -e "${YELLOW}[3/7]${NC} Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo ""

# Upgrade pip
echo -e "${YELLOW}[4/7]${NC} Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓${NC} pip upgraded to latest version"
echo ""

# Install dependencies
echo -e "${YELLOW}[5/7]${NC} Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt
echo -e "${GREEN}✓${NC} All dependencies installed"
echo ""

# Create necessary directories
echo -e "${YELLOW}[6/7]${NC} Creating necessary directories..."
mkdir -p config
mkdir -p static/js
mkdir -p static/css
mkdir -p templates
mkdir -p symbols
mkdir -p logs
mkdir -p docs
echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Verify QuestDB
echo -e "${YELLOW}[7/7]${NC} Checking QuestDB connection..."
echo "Attempting to connect to QuestDB at http://127.0.0.1:9000"

if command -v curl &> /dev/null; then
    if curl -s --connect-timeout 5 http://127.0.0.1:9000 > /dev/null; then
        echo -e "${GREEN}✓${NC} QuestDB is running and accessible"
    else
        echo -e "${YELLOW}⚠${NC} QuestDB is not running"
        echo ""
        echo "To start QuestDB with Docker:"
        echo "  docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb"
        echo ""
        echo "Or download from: https://questdb.io/get-questdb/"
    fi
else
    echo -e "${YELLOW}⚠${NC} curl not found, skipping QuestDB check"
fi
echo ""

# Installation complete
echo "=================================================="
echo -e "${GREEN}  Installation Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment (if not already active):"
echo "   ${GREEN}source venv/bin/activate${NC}"
echo ""
echo "2. Ensure QuestDB is running:"
echo "   Docker: ${GREEN}docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb${NC}"
echo "   Or: Download from https://questdb.io/get-questdb/"
echo ""
echo "3. Ensure OpenAlgo is running:"
echo "   REST API: http://127.0.0.1:5000"
echo "   WebSocket: ws://127.0.0.1:8765"
echo ""
echo "4. Start OpenQuest:"
echo "   ${GREEN}python app.py${NC}"
echo ""
echo "5. Access the application:"
echo "   Dashboard:      ${GREEN}http://127.0.0.1:5001${NC}"
echo "   Charts:         ${GREEN}http://127.0.0.1:5001/chart${NC}"
echo "   Market Profile: ${GREEN}http://127.0.0.1:5001/market-profile${NC}"
echo ""
echo "6. Configure OpenAlgo API key in the web UI"
echo ""
echo "=================================================="
echo "Documentation:"
echo "  README.md              - General documentation"
echo "  docs/MARKET_PROFILE.md - Market Profile guide"
echo "=================================================="
echo ""
echo "To deactivate the virtual environment later:"
echo "  ${YELLOW}deactivate${NC}"
echo ""
