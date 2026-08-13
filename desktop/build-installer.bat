@echo off
REM Run Inno Setup to wrap backend\dist\WeightHealth\ into an installer.
REM Requires Inno Setup 6 installed at the standard path.

setlocal
cd /d "%~dp0\.."

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo Inno Setup 6 未安装。跳过安装器构建，仅保留单文件夹版本。
    exit /b 0
)

mkdir desktop\installer_output 2>nul

%ISCC% desktop\installer.iss

if %errorlevel% equ 0 (
    echo.
    echo ✅ 安装器已生成: desktop\installer_output\WeightHealth-Setup-1.0.0.exe
) else (
    echo 错误: Inno Setup 失败
)
