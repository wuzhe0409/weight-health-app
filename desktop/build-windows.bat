@echo off
REM ============================================================
REM Weight Health — Windows build script
REM
REM 用法:
REM   desktop\build-windows.bat                默认 (含示例 seed)
REM   set BUILD_DIST=1 ^&^& desktop\build-windows.bat   干净版 (不含 seed，给朋友用)
REM
REM 输出:
REM   backend\dist\WeightHealth\               单文件夹版本
REM   desktop\installer_output\WeightHealth-Setup-1.0.0.exe  安装器 (如已装 Inno Setup)
REM
REM 数据安全: 本脚本只读 frontend\dist + backend\seed + backend\schema.sql
REM         绝不会触碰 backend\data\, 任何 %USERPROFILE%\.weight-health\, 或 backend\data\app.db
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo.
echo === [1/5] 检查 Python ===
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 python，请先安装 Python 3.11+ 并加入 PATH
    pause
    exit /b 1
)
python --version
for /f "tokens=2" %%v in ('python --version') do set PY_VER=%%v
echo Python !PY_VER!

echo.
echo === [2/5] 创建 venv 安装依赖 ===
if not exist backend\.venv-win\Scripts (
    python -m venv backend\.venv-win
)
call backend\.venv-win\Scripts\activate.bat

REM Windows 特定的额外依赖: pywebview 在 Windows 上需要 pythonnet + pywin32
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if exist desktop\requirements-win.txt (
    pip install --quiet -r desktop\requirements-win.txt
)

echo.
echo === [3/5] 构建前端 (Vite) ===
cd frontend
call npm install --silent
call npm run build
if %errorlevel% neq 0 (
    echo 错误: 前端构建失败
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo === [4/5] 拷贝静态资源 + launcher 到 backend\ ===
if exist backend\static rmdir /s /q backend\static
xcopy /e /i /y frontend\dist backend\static >nul
if not exist backend\app\desktop_launcher.py (
    copy /y desktop\desktop_launcher.py backend\app\desktop_launcher.py >nul
)

REM "BUILD_DIST=1" 表示这是发布版本，不打包示例 seed，避免泄漏任何数据
set SEED_ARG=
if defined BUILD_DIST (
    echo [BUILD_DIST=1] 干净模式 — 不打包 seed/ 目录
    set SEED_ARG=--exclude-module=seed
) else (
    set SEED_ARG=--add-data "seed;seed"
)

echo.
echo === [5/5] PyInstaller 打包 ===
cd backend
rmdir /s /q "dist\WeightHealth" 2>nul
rmdir /s /q build 2>nul
del /q "WeightHealth.spec" 2>nul

pyinstaller ^
    --name "WeightHealth" ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --add-data "static;static" ^
    --add-data "schema.sql;." ^
    %SEED_ARG% ^
    --hidden-import=sqlmodel ^
    --hidden-import=fastapi ^
    --hidden-import=uvicorn ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=aiofiles ^
    --hidden-import=pydantic ^
    --hidden-import=webview ^
    --hidden-import=webview.platforms.edgechromium ^
    --hidden-import=webview.platforms.winforms ^
    --collect-all=app ^
    app\desktop_launcher.py

if %errorlevel% neq 0 (
    echo 错误: PyInstaller 打包失败
    cd ..
    pause
    exit /b 1
)

REM 清理临时文件
rmdir /s /q static 2>nul
del /q app\desktop_launcher.py 2>nul

cd ..

echo.
echo ============================================================
echo ✅ 构建完成
echo    单文件夹版:   backend\dist\WeightHealth\
echo    (可选) 安装器: 跑 desktop\build-installer.bat (需先装 Inno Setup)
echo ============================================================

REM 用户要求时打安装器
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    call desktop\build-installer.bat
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    call desktop\build-installer.bat
)

pause
