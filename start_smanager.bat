@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "CONDA_ENV=smanager"

if "%~1"=="--check" goto check

echo [SManager] Project root: %ROOT%
echo [SManager] Starting backend on http://localhost:%BACKEND_PORT%
start "SManager Backend" /D "%ROOT%" cmd /k "call conda activate %CONDA_ENV% && python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port %BACKEND_PORT%"

echo [SManager] Starting frontend on http://localhost:%FRONTEND_PORT%
start "SManager Frontend" /D "%ROOT%frontend" cmd /k "npm run dev -- --host 0.0.0.0 --port %FRONTEND_PORT%"

echo.
echo [SManager] Services are starting in separate windows.
echo [SManager] Frontend: http://localhost:%FRONTEND_PORT%
echo [SManager] Backend health: http://localhost:%BACKEND_PORT%/health
echo.
echo Close the two service windows to stop SManager.
exit /b 0

:check
echo [SManager] Checking local launch prerequisites...
where conda >nul 2>nul
if errorlevel 1 (
  echo [ERROR] conda was not found on PATH.
  exit /b 1
)

call conda run -n %CONDA_ENV% python --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] conda environment "%CONDA_ENV%" is not available.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found on PATH.
  exit /b 1
)

if not exist "%ROOT%frontend\package.json" (
  echo [ERROR] frontend\package.json was not found.
  exit /b 1
)

echo [OK] conda, %CONDA_ENV%, npm, and frontend package metadata are available.
exit /b 0
