#!/usr/bin/env bash
# ============================================================
#  🖥️  Build macOS desktop app (.app + .dmg)
#  Run from project root: bash desktop/build-mac.sh
#
#  BUILD_DIST=1  Build clean distribution (no seed/ data)
#                Friend-version: empty database on first launch
#                DMG named Weight-Health-Friend-macOS-arm64.dmg
# ============================================================
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="/Users/wuzhe/.workbuddy/binaries/python/envs/default/bin/python"
NPM="/Users/wuzhe/.workbuddy/binaries/node/versions/22.22.2/bin/npm"

BUILD_DIST="${BUILD_DIST:-0}"

if [ "$BUILD_DIST" = "1" ]; then
    echo "==> Mode: BUILD_DIST=1 (clean distribution, no seed/ data)"
    DMG_NAME="Weight-Health-Friend-macOS-arm64.dmg"
else
    echo "==> Mode: developer build (includes seed/ data)"
    DMG_NAME="Weight-Health-macOS-arm64.dmg"
fi

echo "==> 1. Building frontend..."
( cd "$ROOT/frontend" && "$NPM" run build )

echo "==> 2. Installing build dependencies..."
"$PY" -m pip install pywebview pyinstaller aiofiles -q

echo "==> 3. Preparing static files..."
rm -rf "$ROOT/backend/static"
mkdir -p "$ROOT/backend/static"
cp -r "$ROOT/frontend/dist/"* "$ROOT/backend/static/"

echo "==> 4. Building macOS .app..."
cd "$ROOT/backend"

# Copy desktop_launcher into backend/app for PyInstaller
cp "$ROOT/desktop/desktop_launcher.py" "$ROOT/backend/app/"

# Build PyInstaller args conditionally based on BUILD_DIST
# Always include schema.sql (DB structure) and static/ (frontend)
# Only include seed/ in developer builds (BUILD_DIST unset)
PYI_ARGS=(
    --name "Weight Health"
    --noconfirm
    --onedir
    --windowed
    --add-data "static:static"
    --add-data "schema.sql:."
    --hidden-import=sqlmodel
    --hidden-import=fastapi
    --hidden-import=uvicorn
    --hidden-import=uvicorn.loops.auto
    --hidden-import=uvicorn.protocols.http.auto
    --hidden-import=aiofiles
    --hidden-import=pydantic
    --hidden-import=webview
    --hidden-import=webview.platforms.cocoa
    --collect-all=app
    --osx-bundle-identifier=com.wz.weighthealth
    app/desktop_launcher.py
)

if [ "$BUILD_DIST" != "1" ]; then
    # Developer build: include seed/ data (your historical records)
    PYI_ARGS=(--add-data "seed:seed" "${PYI_ARGS[@]}")
else
    echo "    [BUILD_DIST=1] Skipping seed/ — friend gets empty database"
fi

"$PY" -m PyInstaller "${PYI_ARGS[@]}"

# Cleanup
rm "$ROOT/backend/app/desktop_launcher.py"
rm -rf "$ROOT/backend/static"

echo "==> 5. Creating DMG..."
mkdir -p "$ROOT/backend/dist/dmg_temp"
cp -r "$ROOT/backend/dist/Weight Health.app" "$ROOT/backend/dist/dmg_temp/"
hdiutil create -volname "Weight Health" \
    -srcfolder "$ROOT/backend/dist/dmg_temp" \
    -ov -format UDZO \
    "$ROOT/releases/$DMG_NAME"
rm -rf "$ROOT/backend/dist/dmg_temp"

echo ""
echo "✅ Done! DMG at: releases/$DMG_NAME"
