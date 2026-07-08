#!/bin/bash
# Build a self-contained "Shortcut Viewer.app" and a .dmg for macOS.
#
# This creates a lightweight macOS app bundle. The app runs a shell script that
# automatically starts the local python server (if not already running) and opens
# the app in Chrome.
#
# Usage:
#   ./scripts/make-macos-app.sh          -> build dist/Shortcut Viewer.app
#   ./scripts/make-macos-app.sh --dmg    -> also build dist/Shortcut-Viewer.dmg

set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd)"
APP="dist/Shortcut Viewer.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Copy all essential files into the app bundle so it is fully self-contained!
cp -R app.py build.py render.py viewer.template.html assets scripts shortcuts.json "$APP/Contents/Resources/"

# We already generated this icns using sips
cp assets/icon.icns "$APP/Contents/Resources/icon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Shortcut Viewer</string>
  <key>CFBundleDisplayName</key><string>Shortcut Viewer</string>
  <key>CFBundleIdentifier</key><string>com.kimdongryeong.shortcut-viewer</string>
  <key>CFBundleVersion</key><string>1.0.0</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST

cat > "$APP/Contents/MacOS/launch" <<'LAUNCH'
#!/bin/bash
PORT=8787
URL="http://127.0.0.1:$PORT"

# Move to the embedded Resources directory so python finds the files
cd "$(dirname "$0")/../Resources"

# If already running, just open and exit
if curl -s -o /dev/null "$URL" 2>/dev/null; then 
  open -b com.google.Chrome "$URL" || open "$URL"
  exit 0
fi

# Build viewer.html if missing
if [ ! -f viewer.html ]; then
  python3 build.py
fi

# Run the python server directly. Since LSUIElement=true, it runs in the background
# without a Dock icon, and stays alive as long as the user wants.
python3 app.py --port="$PORT" &
sleep 1
open -b com.google.Chrome "$URL" || open "$URL"
wait
LAUNCH

chmod +x "$APP/Contents/MacOS/launch"

# Refresh icon cache
touch "$APP"
echo "built: $APP"

if [ "${1:-}" = "--dmg" ]; then
  DMG="dist/Shortcut-Viewer.dmg"
  rm -f "$DMG"
  STAGE="$(mktemp -d)"
  cp -R "$APP" "$STAGE/"
  ln -s /Applications "$STAGE/Applications"
  hdiutil create -volname "Shortcut Viewer" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
  rm -rf "$STAGE"
  echo "built: $DMG  (drag the app onto Applications)"
fi
