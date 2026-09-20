@echo off
title MARSHALL AI

:: Re-launch as Administrator if not already elevated
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [MARSHALL] Requesting Administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
    exit /b
)

color 0A
echo.
echo  ===================================
echo   M.A.R.S.H.A.L.L  STARTING UP
echo   Running as Administrator
echo  ===================================
echo.

:: Kill anything already on port 8000
echo [MARSHALL] Clearing port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do taskkill /PID %%a /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start backend (serves UI + API + unlock)
echo [MARSHALL] Starting AI backend on port 8000...
start "MARSHALL Backend" cmd /k "cd /d %~dp0 && python main.py"
timeout /t 5 /nobreak >nul

:: Open the orb UI
start "" "http://localhost:8000"

echo.
echo  MARSHALL ONLINE - http://localhost:8000
echo  Running as Administrator - unlock feature active
echo  Check Phone panel in orb for remote QR code
echo.
pause
