@echo off
REM OpenQuest Startup Script for Windows
REM Activates virtual environment and starts the application

echo ==================================================
echo   OpenQuest - Startup Script
echo ==================================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo [ERROR] Virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Check QuestDB
echo [INFO] Checking QuestDB...
curl -s --connect-timeout 5 http://127.0.0.1:9000 >nul 2>&1
if errorlevel 1 (
    echo [WARNING] QuestDB is not running!
    echo Start QuestDB first:
    echo   docker run -d -p 9000:9000 -p 9009:9009 -p 8812:8812 --name questdb questdb/questdb
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
) else (
    echo [OK] QuestDB is running
)
echo.

REM Start application
echo ==================================================
echo   Starting OpenQuest...
echo ==================================================
echo.
echo Access URLs:
echo   Dashboard:      http://127.0.0.1:5001
echo   Charts:         http://127.0.0.1:5001/chart
echo   Market Profile: http://127.0.0.1:5001/market-profile
echo.
echo Press Ctrl+C to stop
echo.

python app.py
