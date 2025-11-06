# OpenQuest - Installation Guide

Complete step-by-step installation guide for OpenQuest with virtual environment setup.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Install (Automated)](#quick-install-automated)
3. [Manual Installation](#manual-installation)
4. [Verifying Installation](#verifying-installation)
5. [Starting OpenQuest](#starting-openquest)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before installing OpenQuest, ensure you have the following:

### Required Software

1. **Python 3.11+**
   - Download: https://www.python.org/downloads/
   - During Windows installation, check "Add Python to PATH"
   - Verify: `python --version` or `python3 --version`

2. **QuestDB**
   - Option A (Docker): `docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb`
   - Option B (Direct): Download from https://questdb.io/get-questdb/
   - Verify: Access http://127.0.0.1:9000

3. **OpenAlgo**
   - Must be running at:
     - REST API: http://127.0.0.1:5000
     - WebSocket: ws://127.0.0.1:8765
   - Get from: https://github.com/marketcalls/openalgo

### Optional but Recommended

- **Git**: For cloning the repository
- **curl**: For testing API endpoints
- **Docker**: For easy QuestDB setup

---

## Quick Install (Automated)

### Linux / macOS

```bash
# 1. Clone the repository
git clone https://github.com/marketcalls/openquest.git
cd openquest

# 2. Run installation script
chmod +x install.sh
./install.sh

# 3. Ensure QuestDB is running
docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb

# 4. Start OpenQuest
./start.sh
```

### Windows

```batch
REM 1. Clone the repository
git clone https://github.com/marketcalls/openquest.git
cd openquest

REM 2. Run installation script
install.bat

REM 3. Ensure QuestDB is running
docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb

REM 4. Start OpenQuest
start.bat
```

---

## Manual Installation

If you prefer to install manually or the automated script fails:

### Step 1: Clone Repository

```bash
git clone https://github.com/marketcalls/openquest.git
cd openquest
```

### Step 2: Create Virtual Environment

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```batch
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Upgrade pip

```bash
# All platforms (inside activated venv)
pip install --upgrade pip
```

### Step 4: Install Dependencies

```bash
# All platforms (inside activated venv)
pip install -r requirements.txt
```

This will install:
- Flask & Flask-SocketIO (web framework)
- psycopg2-binary (QuestDB connection)
- openalgo (OpenAlgo Python SDK)
- pytz (timezone support)
- pandas, numpy (data processing)
- All other required packages

Installation may take 2-5 minutes depending on your internet speed.

### Step 5: Create Directories

```bash
# Linux / macOS
mkdir -p config static/js static/css templates symbols logs docs

# Windows
mkdir config static\js static\css templates symbols logs docs
```

### Step 6: Verify Installation

```bash
# Check installed packages
pip list

# Check Python modules
python -c "import flask, psycopg2, openalgo, pytz; print('All imports successful')"
```

---

## Verifying Installation

### 1. Check Virtual Environment

```bash
# Should show (venv) in prompt
# Verify pip is using venv
which pip   # Linux/macOS
where pip   # Windows

# Should point to venv/bin/pip or venv\Scripts\pip
```

### 2. Check QuestDB

```bash
# Test connection
curl http://127.0.0.1:9000

# Or open in browser: http://127.0.0.1:9000
# You should see QuestDB console
```

### 3. Check OpenAlgo

```bash
# Test REST API
curl http://127.0.0.1:5000/api/v1

# Or verify in OpenAlgo dashboard
```

### 4. Test OpenQuest

```bash
# Activate venv if not active
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Start application
python app.py

# Should see:
# OpenQuest Started - Real-Time Data Aggregation
# Dashboard: http://127.0.0.1:5001
```

---

## Starting OpenQuest

### Using Start Scripts (Recommended)

**Linux / macOS:**
```bash
./start.sh
```

**Windows:**
```batch
start.bat
```

### Manual Start

```bash
# 1. Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 2. Start application
python app.py
```

### Access Application

Once started, access:
- **Dashboard**: http://127.0.0.1:5001
- **Charts**: http://127.0.0.1:5001/chart
- **Market Profile**: http://127.0.0.1:5001/market-profile

### Stopping OpenQuest

Press `Ctrl+C` in the terminal where OpenQuest is running.

---

## Troubleshooting

### Python Not Found

**Problem**: `python: command not found`

**Solution**:
```bash
# Try python3 instead
python3 --version

# Or add Python to PATH (Windows)
# Reinstall Python and check "Add Python to PATH"
```

### Virtual Environment Activation Fails

**Problem**: `venv/bin/activate: No such file or directory`

**Solution**:
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv

# Windows
rmdir /s venv
python -m venv venv
```

### pip Install Fails

**Problem**: `ERROR: Could not find a version that satisfies the requirement...`

**Solution**:
```bash
# Upgrade pip
pip install --upgrade pip

# Use specific index
pip install -r requirements.txt --index-url https://pypi.org/simple

# Check Python version (must be 3.11+)
python --version
```

### QuestDB Connection Failed

**Problem**: `Failed to connect to QuestDB`

**Solution**:
```bash
# Check if QuestDB is running
docker ps | grep questdb

# Start QuestDB if not running
docker start questdb

# Or create new instance
docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb

# Test connection
curl http://127.0.0.1:9000
```

### OpenAlgo API Key Not Working

**Problem**: `Market profile not initialized` or `API key not configured`

**Solution**:
1. Open OpenQuest dashboard: http://127.0.0.1:5001
2. Click on Configuration
3. Enter your OpenAlgo API key
4. Set REST URL: `http://127.0.0.1:5000`
5. Set WebSocket URL: `ws://127.0.0.1:8765`
6. Click "Save Configuration"

### Port Already in Use

**Problem**: `Address already in use: ('127.0.0.1', 5001)`

**Solution**:
```bash
# Find process using port 5001
# Linux/macOS
lsof -i :5001
kill -9 <PID>

# Windows
netstat -ano | findstr :5001
taskkill /PID <PID> /F

# Or change port in app.py (line 463)
# Change: port=5001
# To:     port=5002
```

### Market Profile Not Loading

**Problem**: Expiries not showing or OI data not fetching

**Solution**:
1. Verify OpenAlgo is running and API key is valid
2. Check OpenAlgo expiry API:
   ```bash
   curl http://127.0.0.1:5000/api/v1/expiry
   ```
3. Check browser console for JavaScript errors (F12)
4. Ensure market is open (9:15 AM - 3:30 PM IST)
5. Try fetching for NIFTY first (most liquid)

### Slow Data Fetching

**Problem**: OI fetch takes too long

**Solution**:
- Normal: 10-30 seconds for ±20 strikes (40 options)
- This is expected due to API rate limiting
- Reduce strike range in config if needed
- Subsequent fetches are faster (cached)

---

## Updating OpenQuest

To update to the latest version:

```bash
# 1. Backup your config.json (if configured)
cp config.json config.json.backup

# 2. Pull latest changes
git pull origin main

# 3. Activate venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 4. Update dependencies
pip install -r requirements.txt --upgrade

# 5. Restart application
./start.sh  # or start.bat on Windows
```

---

## Uninstalling

To completely remove OpenQuest:

```bash
# 1. Stop the application (Ctrl+C)

# 2. Deactivate virtual environment
deactivate

# 3. Remove directory
cd ..
rm -rf openquest  # Linux/macOS
rmdir /s openquest  # Windows

# 4. Stop and remove QuestDB container (optional)
docker stop questdb
docker rm questdb
```

---

## Production Deployment

For production deployment, consider:

1. **Use a process manager**:
   - Linux: systemd, supervisor
   - Windows: NSSM (Non-Sucking Service Manager)

2. **Use a proper web server**:
   - nginx + gunicorn (Linux)
   - IIS + waitress (Windows)

3. **Secure the installation**:
   - Use environment variables for API keys
   - Enable HTTPS
   - Set up firewall rules
   - Use strong passwords for QuestDB

4. **Configure logging**:
   - Enable file-based logging
   - Set up log rotation
   - Monitor error logs

See docs/ for production deployment guides.

---

## Getting Help

- **Documentation**: [README.md](README.md), [docs/MARKET_PROFILE.md](docs/MARKET_PROFILE.md)
- **Issues**: https://github.com/marketcalls/openquest/issues
- **OpenAlgo Docs**: https://docs.openalgo.in
- **QuestDB Docs**: https://questdb.io/docs/

---

**Installation complete! Happy trading! 📊🚀**
