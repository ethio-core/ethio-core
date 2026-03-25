@echo off
setlocal

set "ROOT=%~dp0"
set "API_DIR=%ROOT%ethio-core\mvp-api"
set "FE_DIR=%ROOT%ethio-core\modules\m7-frontend"
set "FE_ENV=%FE_DIR%\.env.local"

echo Starting Ethio Core MVP locally...
echo.

if not exist "%API_DIR%\main.py" (
  echo ERROR: API directory not found at %API_DIR%
  pause
  exit /b 1
)

if not exist "%FE_DIR%\package.json" (
  echo ERROR: Frontend directory not found at %FE_DIR%
  pause
  exit /b 1
)

if not exist "%FE_ENV%" (
  echo API_BASE_URL=http://127.0.0.1:8000>"%FE_ENV%"
  echo Created %FE_ENV%
)

echo Launching API on http://127.0.0.1:8000 ...
start "MVP API" cmd /k "cd /d ""%API_DIR%"" && pip install -r requirements.txt && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo Launching Frontend on http://localhost:3000 ...
start "MVP Frontend" cmd /k "cd /d ""%FE_DIR%"" && npm install && npm run dev"

echo Waiting for services to warm up...
timeout /t 8 >nul

echo Opening browser...
start "" "http://localhost:3000"

echo.
echo Done. Use these credentials:
echo admin@ethio-core.com / admin123
echo.
echo Keep both terminal windows open while testing.
endlocal
