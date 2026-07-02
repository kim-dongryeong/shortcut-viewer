#!/bin/zsh
# build.sh — compile svhotkeys.swift into a UNIVERSAL (Apple Silicon + Intel) menu-bar
# .app, ad-hoc signed. No SPM, no external deps — mirrors the repo's swiftc style.
#   ./build.sh           # build + assemble SV Hotkeys.app
#   ./build.sh run       # build + launch
#   ./build.sh --list    # build + headless config self-test (no GUI)
set -e
cd "${0:A:h}"
APP="SV Hotkeys.app"
BIN="svhotkeys"

echo "▸ swiftc (universal: arm64 + x86_64)"
if swiftc -O -target arm64-apple-macos11  svhotkeys.swift -o /tmp/svhotkeys.arm64 2>/dev/null \
   && swiftc -O -target x86_64-apple-macos11 svhotkeys.swift -o /tmp/svhotkeys.x86_64 2>/dev/null \
   && lipo -create /tmp/svhotkeys.arm64 /tmp/svhotkeys.x86_64 -output "$BIN" 2>/dev/null; then
  rm -f /tmp/svhotkeys.arm64 /tmp/svhotkeys.x86_64
  echo "  → universal ($(lipo -archs "$BIN"))"
else
  echo "  (universal 실패 — 네이티브 아치로)"
  swiftc -O svhotkeys.swift -o "$BIN"
fi

if [[ "${1:-}" == "--list" ]]; then ./"$BIN" --list; exit 0; fi

echo "▸ assembling \"$APP\""
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/svhotkeys"
cp Info.plist "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"

echo "▸ codesign (ad-hoc)"
codesign --force --sign - "$APP" 2>&1 | sed 's/^/   /' || true
echo "✓ built \"$APP\""

if [[ "${1:-}" == "run" ]]; then echo "▸ launching"; open "$APP"; fi
