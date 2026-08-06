@echo off
:: ============================================================
::  Weight Health — Clean Build for Windows (Friend Edition)
::  NO historical data, fresh start with new icon
::  Run this on a Windows machine with Python 3.11+ installed.
:: ============================================================
@echo off
setlocal

echo.
echo ============================================================
echo   Weight Health · Friend Edition · Windows Clean Build
echo ============================================================
echo.

echo [1/4] Building frontend...
cd /d "%~dp0frontend"
call npm install
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: Frontend build failed!
    exit /b %errorlevel%
)

echo [2/4] Preparing static files...
cd /d "%~dp0backend"
if exist "static" rmdir /s /q "static"
mkdir "static"
xcopy /e /y "..\frontend\dist\*" "static\"

echo [3/4] Installing build dependencies...
pip install pywebview pyinstaller aiofiles Pillow -q

echo [4/4] Building Windows executable...
:: Copy clean icon to dist
if exist "app-icon.ico" (
    copy /y "app-icon.ico" "app-icon-temp.ico"
)

python -m PyInstaller ^
    --name "WeightHealth-Friend" ^
    --onedir ^
    --windowed ^
    --add-data "static;static" ^
    --add-data "seed_clean;seed" ^
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

if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed!
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo   BUILD COMPLETE!
echo.
echo   Output: backend\dist\WeightHealth-Friend\WeightHealth-Friend.exe
echo.
echo   To send to your friend:
echo   1. Copy the entire "backend\dist\WeightHealth-Friend" folder
echo   2. They just double-click WeightHealth-Friend.exe
echo.
echo   Icon file: backend\app-icon.ico
echo   (Right-click the exe - Properties - Change Icon)
echo ============================================================
echo.
pause
