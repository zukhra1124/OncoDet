@echo off
REM Real-time integration startup script for Windows
REM Starts both backend and frontend servers in separate terminal windows

echo ==========================================
echo Starting Full Stack Application
echo ==========================================
echo.

REM Kill existing processes on ports
echo Stopping existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5001" ^| find "LISTENING"') do taskkill /pid %%a /f /t 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5175" ^| find "LISTENING"') do taskkill /pid %%a /f /t 2>nul
timeout /t 2 /nobreak

REM Start Backend in new terminal
echo Starting Backend Server (port 5001)...
cd backend
start "Backend - Pneumonia Detection" cmd /k python app.py
cd ..
timeout /t 3 /nobreak

REM Start Frontend in new terminal  
echo Starting Frontend Server (port 5175)...
cd frontend
start "Frontend - Pneumonia Detection" cmd /k npm run dev
cd ..

echo.
echo ==========================================
echo ^✓ Full Stack Running
echo ==========================================
echo.
echo Backend:  http://localhost:5001
echo Frontend: http://localhost:5175
echo API:      http://localhost:5175/api
echo.
echo ^> Open http://localhost:5175 in your browser
echo.
echo ==========================================
pause
