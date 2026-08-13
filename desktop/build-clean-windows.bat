@echo off
:: ============================================================
::  🖥️  Build Windows desktop app — FRIEND EDITION (no history)
::  Run from project root: desktop\build-clean-windows.bat
:: ============================================================
setlocal

echo.
echo ============================================================
echo   Weight Health · Friend Edition · Clean Windows Build
echo ============================================================
echo.

echo [1/4] Building frontend...
cd /d "%~dp0..\frontend"
call npm install
call npm run build
if %errorlevel% neq 0 exit /b %errorlevel%

echo [2/4] Preparing static files...
cd /d "%~dp0..\backend"
if exist "static" rmdir /s /q "static"
mkdir "static"
xcopy /e /y "..\frontend\dist\*" "static\"

echo [3/4] Installing build dependencies...
pip install pywebview pyinstaller aiofiles -q

:: Copy launcher into backend/app
copy /y "%~dp0desktop_launcher.py" "app\desktop_launcher.py"

echo [4/4] Building Windows executable (CLEAN — no history data)...
python -m PyInstaller ^
    --name "WeightHealth-Friend" ^
    --onedir ^
    --windowed ^
    --add-data "static;static" ^
    --add-data "..\desktop\seed_clean;seed" ^
    --add-data "schema.sql;." ^
    --hidden-import=sqlmodel ^
    --hidden-import=fastapi ^
    --hidden-import=uvicorn ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=aiofiles ^
    --hidden-import=pydantic ^
    --hidden-import=webview ^
    --collect-all=app ^
    app/desktop_launcher.py

:: Cleanup
del "app\desktop_launcher.py"
rmdir /s /q "static"

echo.
echo ============================================================
echo   FRIEND EDITION BUILD COMPLETE!
echo   Output: backend\dist\WeightHealth-Friend\WeightHealth-Friend.exe
echo.
echo   This version has NO historical data — fresh start for your friend!
echo ============================================================
pause
