:: build-windows.bat
:: Run this on a Windows machine with Python 3.11+ installed.
:: Usage: build-windows.bat

@echo off
echo === Building frontend ===
cd /d "%~dp0frontend"
call npm install
call npm run build
if %errorlevel% neq 0 exit /b %errorlevel%

echo === Preparing static files ===
cd /d "%~dp0backend"
if exist "static" rmdir /s /q "static"
mkdir "static"
xcopy /e /y "..\frontend\dist\*" "static\"

echo === Installing PyInstaller ===
pip install pyinstaller aiofiles -q

echo === Building Windows exe ===
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
    --collect-all=app ^
    app/desktop_launcher.py

echo === Build complete ===
echo Output: backend\dist\WeightHealth\WeightHealth.exe
pause
