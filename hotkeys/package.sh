#!/bin/zsh
# package.sh — build SV Hotkeys and wrap it in a distributable .dmg (drag-to-Applications).
# For sharing with non-technical users who'd rather not run a script.
#   ./package.sh   →  SV-Hotkeys.dmg
set -e
cd "${0:A:h}"
./build.sh >/dev/null
APP="SV Hotkeys.app"
DMG="SV-Hotkeys.dmg"
STAGE="/tmp/svhk-dmg"
rm -rf "$STAGE" "$DMG"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"      # drag target
hdiutil create -volname "SV Hotkeys" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"
echo "✓ $DMG ($(du -h "$DMG" | cut -f1)) — 열어서 앱을 Applications 로 드래그하면 설치"
echo "  ⚠️ ad-hoc 서명이라 첫 실행 시: 우클릭 ▸ 열기 (Gatekeeper 우회) 또는 시스템 설정 ▸ 보안에서 허용"
