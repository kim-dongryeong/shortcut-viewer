#!/bin/zsh
# install_hotkeys.sh — one-command setup of the SV Hotkeys native daemon for NON-TECHNICAL users.
#   1) builds "SV Hotkeys.app" (universal)          2) copies it to ~/Applications
#   3) seeds ~/.config/shortcut-viewer/hotkeys.json 4) installs a LaunchAgent (auto-start at login)
#   5) launches it. No Accessibility needed for ⌘/⌥/⌃ combos.
#   usage:  ./install_hotkeys.sh          (uninstall:  ./install_hotkeys.sh uninstall)
set -e
cd "${0:A:h}"
LABEL="com.shortcutviewer.hotkeys"
AGENT="$HOME/Library/LaunchAgents/$LABEL.plist"
APPDIR="$HOME/Applications"
APP="$APPDIR/SV Hotkeys.app"
CFG="$HOME/.config/shortcut-viewer/hotkeys.json"

if [[ "${1:-}" == "uninstall" ]]; then
  echo "▸ 제거 중…"
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$AGENT" 2>/dev/null || true
  rm -f "$AGENT"; rm -rf "$APP"
  echo "✓ 제거됨 (설정 $CFG 은 남겨둠 — 지우려면 직접 rm)"
  exit 0
fi

echo "▸ 1/5  앱 빌드 (universal)"
( cd hotkeys && ./build.sh >/dev/null && echo "  ✓ SV Hotkeys.app 빌드됨" )

echo "▸ 2/5  ~/Applications 에 설치"
mkdir -p "$APPDIR"; rm -rf "$APP"; cp -R "hotkeys/SV Hotkeys.app" "$APP"
echo "  ✓ $APP"

echo "▸ 3/5  설정 파일 준비"
mkdir -p "$(dirname "$CFG")"
if [[ ! -f "$CFG" ]]; then cp hotkeys.example.json "$CFG"; echo "  ✓ 예제 15개 핫키를 $CFG 에 넣음 (뷰어에서 편집·내보내기 가능)"
else echo "  · 기존 설정 유지: $CFG"; fi

echo "▸ 4/5  로그인 자동시작 (LaunchAgent)"
mkdir -p "$(dirname "$AGENT")"
cat > "$AGENT" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$APP/Contents/MacOS/svhotkeys</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
  <key>ProcessType</key><string>Interactive</string>
</dict></plist>
PLIST
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$AGENT" 2>/dev/null || launchctl load "$AGENT"
echo "  ✓ 로그인 때마다 자동 실행"

echo "▸ 5/5  실행"
launchctl kickstart -k "gui/$(id -u)/$LABEL" 2>/dev/null || open "$APP"
echo ""
echo "✅ 완료! 메뉴바에 ⌘ 아이콘이 뜹니다. 눌러서 핫키 목록·설정을 확인하세요."
echo "   • 예: ⌥Space = 단축키 뷰어 열기 · ⌥F = Finder · ⌃⌥T = 터미널"
echo "   • 편집: 메뉴바 아이콘 ▸ '설정 파일 열기' 또는 뷰어의 '글로벌 핫키' 에서 내보내기"
echo "   • ⇧Space 같이 다른 앱도 잡는 조합은 메뉴바 ▸ 'any-combo 켜기'(Accessibility)"
echo "   • 제거:  ./install_hotkeys.sh uninstall"
