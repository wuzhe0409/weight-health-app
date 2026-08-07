@echo off
:: ============================================================
::  CI Build Script for Windows (used by GitHub Actions)
::  Clean version — no historical data
:: ============================================================
setlocal

echo [1/3] Preparing static...
if exist "backend\static" rmdir /s /q "backend\static"
mkdir "backend\static"
xcopy /e /y "frontend\dist\*" "backend\static\"

echo [2/3] Copying launcher...
copy /y "desktop\desktop_launcher.py" "backend\app\desktop_launcher.py"

echo [3/3] Building with PyInstaller...
cd backend
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

echo Build complete.
