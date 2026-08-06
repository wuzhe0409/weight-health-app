@echo off
:: ============================================================
::  🖥️  Build Windows desktop app (.exe)
::  Run from project root: desktop\build-windows.bat
:: ============================================================
setlocal

echo.
echo ============================================================
echo   Weight Health · Windows Desktop Build (Your Version)
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

echo [4/4] Building Windows executable...
python -m PyInstaller ^
    --name "WeightHealth" ^
    --onedir ^
    --windowed ^
    --add-data "static;static" ^
    --add-data "seed;seed" ^
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
echo   BUILD COMPLETE!
echo   Output: backend\dist\WeightHealth\WeightHealth.exe
echo ============================================================
pause
