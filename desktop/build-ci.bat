@echo off
setlocal enabledelayedexpansion
:: ============================================================
::  CI Build Script — GitHub Actions Windows runner
::  Clean build (no historical data) for Friend Edition
:: ============================================================

echo === Prepare static ===
if not exist "backend\static" mkdir "backend\static"
xcopy /e /y /q "frontend\dist\*" "backend\static\"

echo === Copy launcher ===
copy /y "desktop\desktop_launcher.py" "backend\app\desktop_launcher.py"

echo === Create empty seed ===
if not exist "backend\seed_clean" mkdir "backend\seed_clean"
echo clean > "backend\seed_clean\README.txt"

echo === Build with PyInstaller ===
cd backend

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
    app\desktop_launcher.py

if %errorlevel% neq 0 exit /b %errorlevel%

echo === Build done ===
dir dist\WeightHealth-Friend\WeightHealth-Friend.exe
