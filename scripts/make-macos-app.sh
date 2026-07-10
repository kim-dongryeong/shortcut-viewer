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

# Copy all essential files into the app bundle so it is fully self-contained.
# NOTE: personal scan data (shortcuts.json — BTT/Raycast/Karabiner, window titles…) is NOT
# bundled by default: this dmg may be published. The end user's first launch runs build.py,
# which fills in their own data on top of the PII-free corpus (defaults/ + web_shortcuts.json).
# For your own /Applications install, pass --with-my-data to bundle your current scan.
cp -R app.py build.py render.py svkeys.py svann.py viewer.template.html web_shortcuts.json defaults assets scripts "$APP/Contents/Resources/"
if [ "${1:-}" = "--with-my-data" ] || [ "${2:-}" = "--with-my-data" ]; then
  cp shortcuts.json "$APP/Contents/Resources/"
  echo "⚠ personal shortcuts.json bundled — do NOT publish this build"
fi
# App-menu scanner: bundle it if compiled so the app can rescan (needs Accessibility);
# without it build.py falls back to reusing the bundled shortcuts.json's menu entries.
[ -x axmenudump ] && cp axmenudump "$APP/Contents/Resources/"

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
  if [ -d "$HOME/Applications/Chrome Apps.localized/Shortcut Viewer.app" ]; then
    open -a "$HOME/Applications/Chrome Apps.localized/Shortcut Viewer.app"
  else
    open -b com.google.Chrome "$URL" || open "$URL"
  fi
  exit 0
fi

# Build viewer.html if missing; if the scan fails, fall back to rendering the
# bundled shortcuts.json so the viewer still opens instead of a server 404.
if [ ! -f viewer.html ]; then
  python3 build.py || python3 render.py
fi

# Detach the server and exit: if this script stayed alive (wait), a second
# double-click would send a reopen Apple Event to a process that can't answer it
# → "application is not responding". Detached, every double-click re-runs this
# script and hits the already-running branch above.
nohup python3 app.py --port="$PORT" >/dev/null 2>&1 &
disown
sleep 1
if [ -d "$HOME/Applications/Chrome Apps.localized/Shortcut Viewer.app" ]; then
  open -a "$HOME/Applications/Chrome Apps.localized/Shortcut Viewer.app"
else
  open -b com.google.Chrome "$URL" || open "$URL"
fi
LAUNCH

chmod +x "$APP/Contents/MacOS/launch"

# Ad-hoc sign the bundle (nested axmenudump too). Apple Silicon refuses wholly unsigned
# Mach-O binaries, and an unsigned bundle fails Gatekeeper with "no usable signature".
# NOT notarized (no paid Developer ID): a downloaded copy still shows "Apple could not
# verify…" once — the user approves via System Settings ▸ Privacy & Security ▸ Open Anyway.
codesign --force --deep -s - "$APP"

# Refresh icon cache
touch "$APP"
echo "built: $APP"

if [ "${1:-}" = "--dmg" ] || [ "${2:-}" = "--dmg" ]; then
  DMG="dist/Shortcut-Viewer.dmg"
  rm -f "$DMG"
  STAGE="$(mktemp -d)"
  cp -R "$APP" "$STAGE/"
  ln -s /Applications "$STAGE/Applications"
  hdiutil create -volname "Shortcut Viewer" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
  rm -rf "$STAGE"
  echo "built: $DMG  (drag the app onto Applications)"
fi
