@echo off
title MARSHALL AI System
color 0A
echo.
echo  ¦¦¦+   ¦¦¦+ ¦¦¦¦¦+ ¦¦¦¦¦¦+ ¦¦¦¦¦¦¦+¦¦+  ¦¦+ ¦¦¦¦¦+ ¦¦+     ¦¦+
echo  ¦¦¦¦+ ¦¦¦¦¦¦¦+--¦¦+¦¦+--¦¦+¦¦+----+¦¦¦  ¦¦¦¦¦+--¦¦+¦¦¦     ¦¦¦
echo  ¦¦+¦¦¦¦+¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦++¦¦¦¦¦¦¦+¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦     ¦¦¦
echo  ¦¦¦+¦¦++¦¦¦¦¦+--¦¦¦¦¦+--¦¦++----¦¦¦¦¦+--¦¦¦¦¦+--¦¦¦¦¦¦     ¦¦¦
echo  ¦¦¦ +-+ ¦¦¦¦¦¦  ¦¦¦¦¦¦  ¦¦¦¦¦¦¦¦¦¦¦¦¦¦  ¦¦¦¦¦¦  ¦¦¦¦¦¦¦¦¦¦+¦¦¦¦¦¦¦+
echo  +-+     +-++-+  +-++-+  +-++------++-+  +-++-+  +-++------++------+
echo.
echo  Initializing MARSHALL AI System...
echo.

cd /d "%~dp0"

:: Start Python backend
echo  [1/2] Starting MARSHALL Backend (Python)...
start "MARSHALL Backend" cmd /k "python main.py"

:: Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

:: Start Next.js frontend
echo  [2/2] Starting MARSHALL Orb UI (Next.js)...
start "MARSHALL UI" cmd /k "cd /d ..\ultron-marshall && npm run dev"

:: Wait and open browser
timeout /t 5 /nobreak >nul
echo.
echo  MARSHALL is online. Opening browser...
start http://localhost:3000

echo.
echo  Backend API: http://localhost:8000
echo  Orb UI:      http://localhost:3000
echo  API Docs:    http://localhost:8000/docs
echo.
pause
