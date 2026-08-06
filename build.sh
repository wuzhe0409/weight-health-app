#!/usr/bin/env bash
# Build desktop app for macOS (Apple Silicon) and Windows.
# Usage: bash build.sh [mac|win|all]

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="/Users/wuzhe/.workbuddy/binaries/python/envs/default/bin/python"

echo "==> 1. Building frontend..."
( cd "$ROOT/frontend" && /Users/wuzhe/.workbuddy/binaries/node/versions/22.22.2/bin/npm run build )

echo "==> 2. Installing build dependencies..."
"$PY" -m pip install pywebview pyinstaller aiofiles -q

echo "==> 3. Preparing static files for packaging..."
# Copy frontend dist into backend directory for PyInstaller to bundle
rm -rf "$ROOT/backend/static"
mkdir -p "$ROOT/backend/static"
cp -r "$ROOT/frontend/dist/"* "$ROOT/backend/static/"

build_mac() {
    echo "==> Building macOS app (Apple Silicon)..."
    cd "$ROOT/backend"
    # Fix the module for PyInstaller
    "$PY" -m PyInstaller \
        --name "Weight Health" \
        --onedir \
        --windowed \
        --add-data "static:static" \
        --add-data "seed:seed" \
        --add-data "schema.sql:." \
        --hidden-import=sqlmodel \
        --hidden-import=fastapi \
        --hidden-import=uvicorn \
        --hidden-import=uvicorn.loops.auto \
        --hidden-import=uvicorn.protocols.http.auto \
        --hidden-import=aiofiles \
        --hidden-import=pydantic \
        --hidden-import=webview \
        --hidden-import=webview.platforms.cocoa \
        --collect-all=app \
        --osx-bundle-identifier=com.wz.weighthealth \
        app/desktop_launcher.py

    echo "macOS app built: $ROOT/backend/dist/Weight Health"
    # Cleanup temp files
    rm -rf "$ROOT/backend/build"
}

build_win() {
    echo "==> Building Windows exe (cross-compile note)..."
    echo "⚠️  Windows build must be done on a Windows machine or via Wine."
    echo "    The spec file has been generated for Windows use."
    cd "$ROOT/backend"
    # Generate spec only for Windows (can be used on a Windows machine)
    "$PY" -m PyInstaller \
        --name "WeightHealth" \
        --onefile \
        --windowed \
        --add-data "static;static" \
        --add-data "seed;seed" \
        --add-data "schema.sql;." \
        --hidden-import=sqlmodel \
        --hidden-import=fastapi \
        --hidden-import=uvicorn \
        --hidden-import=uvicorn.loops.auto \
        --hidden-import=uvicorn.protocols.http.auto \
        --hidden-import=aiofiles \
        --hidden-import=pydantic \
        --collect-all=app \
        app/desktop_launcher.py \
    2>&1 || echo "Cross-compile may fail on macOS — spec is ready for Windows build"

    echo "Windows spec: $ROOT/backend/WeightHealth.spec"
}

case "${1:-mac}" in
    mac)  build_mac ;;
    win)  build_win ;;
    all)
        build_mac
        build_win
        ;;
    *) echo "Usage: bash build.sh [mac|win|all]" ;;
esac

# Clean up the static copy after build
rm -rf "$ROOT/backend/static"

echo "==> Done!"
