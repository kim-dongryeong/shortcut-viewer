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
  <key>CFBundleIdentifier</key><string>kr.kdr.shortcut-viewer</string>
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
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"

# Work in a writable data dir, NEVER inside the .app: generated files
# (shortcuts.json, viewer.html, seed jsons) written into a signed bundle break the
# code-signature seal, and macOS App Management blocks the write outright on a
# notarized app (PermissionError) — the server then 404s forever.
DATA="$HOME/Library/Application Support/Shortcut Viewer"
mkdir -p "$DATA"
# Refresh the code payload every launch (cheap, keeps app updates effective);
# personal data files in $DATA persist untouched.
cp -Rf "$RES/app.py" "$RES/build.py" "$RES/render.py" "$RES/svkeys.py" "$RES/svann.py" \
       "$RES/viewer.template.html" "$RES/web_shortcuts.json" "$RES/defaults" "$RES/assets" "$DATA/"
[ -x "$RES/axmenudump" ] && cp -f "$RES/axmenudump" "$DATA/"
# --with-my-data builds ship a starter scan; seed it only if the user has none yet.
[ -f "$RES/shortcuts.json" ] && [ ! -f "$DATA/shortcuts.json" ] && cp "$RES/shortcuts.json" "$DATA/"
cd "$DATA"

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

# Sign the bundle. Prefer the Developer ID Application identity (notarizable — no
# Gatekeeper warning after notarize+staple); fall back to ad-hoc when absent.
# Inner Mach-O (axmenudump) is signed FIRST with hardened runtime + secure timestamp —
# both are notarization requirements for every Mach-O in the bundle.
SIGN_ID="${SV_SIGN_ID:-$(security find-identity -v -p codesigning 2>/dev/null \
  | sed -n 's/.*"\(Developer ID Application: [^"]*\)".*/\1/p' | head -1)}"
if [ -n "$SIGN_ID" ]; then
  echo "signing with: $SIGN_ID"
  [ -x "$APP/Contents/Resources/axmenudump" ] && \
    codesign --force --options runtime --timestamp --sign "$SIGN_ID" "$APP/Contents/Resources/axmenudump"
  codesign --force --options runtime --timestamp --sign "$SIGN_ID" "$APP"
else
  echo "no Developer ID identity — ad-hoc signing (downloaded copies hit Gatekeeper: Settings ▸ Privacy & Security ▸ Open Anyway)"
  codesign --force --deep -s - "$APP"
fi

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
  # Notarize + staple (SV_NOTARIZE=1; needs the Developer ID signing above and a
  # notarytool keychain profile — default "AC_PASSWORD"). Submit the DMG: its
  # contents are scanned too, and the ticket is stapled to the DMG for offline
  # first-launch verification. Apple review usually takes a few minutes.
  if [ "${SV_NOTARIZE:-0}" = "1" ]; then
    xcrun notarytool submit "$DMG" --keychain-profile "${SV_NOTARY_PROFILE:-AC_PASSWORD}" --wait
    xcrun stapler staple "$DMG"
  fi
  echo "built: $DMG  (drag the app onto Applications)"
fi
