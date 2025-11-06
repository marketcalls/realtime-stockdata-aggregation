@echo off
REM OpenQuest Installation Script for Windows
REM This script sets up a virtual environment and installs all dependencies

echo ==================================================
echo   OpenQuest - Installation Script
echo   Platform: Windows
echo ==================================================
echo.

REM Check Python installation
echo [1/7] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo [OK] Python detected
echo.

REM Create virtual environment
echo [2/7] Creating virtual environment...
if exist venv (
    echo [WARNING] venv directory already exists
    set /p RECREATE="Do you want to recreate it? (y/n): "
    if /i "%RECREATE%"=="y" (
        rmdir /s /q venv
        python -m venv venv
        echo [OK] Virtual environment recreated
    ) else (
        echo [INFO] Using existing virtual environment
    )
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)
echo.

REM Activate virtual environment
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [4/7] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded to latest version
echo.

REM Install dependencies
echo [5/7] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] All dependencies installed
echo.

REM Create necessary directories
echo [6/7] Creating necessary directories...
if not exist config mkdir config
if not exist static\js mkdir static\js
if not exist static\css mkdir static\css
if not exist templates mkdir templates
if not exist symbols mkdir symbols
if not exist logs mkdir logs
if not exist docs mkdir docs
echo [OK] Directories created
echo.

REM Check QuestDB
echo [7/7] Checking QuestDB connection...
echo Attempting to connect to QuestDB at http://127.0.0.1:9000
curl -s --connect-timeout 5 http://127.0.0.1:9000 >nul 2>&1
if errorlevel 1 (
    echo [WARNING] QuestDB is not running
    echo.
    echo To start QuestDB with Docker:
    echo   docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb
    echo.
    echo Or download from: https://questdb.io/get-questdb/
) else (
    echo [OK] QuestDB is running and accessible
)
echo.

REM Installation complete
echo ==================================================
echo   Installation Complete!
echo ==================================================
echo.
echo Next steps:
echo.
echo 1. Activate the virtual environment (if not already active):
echo    venv\Scripts\activate
echo.
echo 2. Ensure QuestDB is running:
echo    Docker: docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb
echo    Or: Download from https://questdb.io/get-questdb/
echo.
echo 3. Ensure OpenAlgo is running:
echo    REST API: http://127.0.0.1:5000
echo    WebSocket: ws://127.0.0.1:8765
echo.
echo 4. Start OpenQuest:
echo    python app.py
echo.
echo 5. Access the application:
echo    Dashboard:      http://127.0.0.1:5001
echo    Charts:         http://127.0.0.1:5001/chart
echo    Market Profile: http://127.0.0.1:5001/market-profile
echo.
echo 6. Configure OpenAlgo API key in the web UI
echo.
echo ==================================================
echo Documentation:
echo   README.md              - General documentation
echo   docs\MARKET_PROFILE.md - Market Profile guide
echo ==================================================
echo.
echo To deactivate the virtual environment later:
echo   deactivate
echo.

pause
