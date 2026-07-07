#!/bin/bash
# Shortcut Viewer.app/Contents/MacOS/ShortcutViewer — 더블클릭하면 실행되는 런처.
# Resources 안에 통째로 들어있는 build.py를 그 자리에서 돌려 shortcuts.json/viewer.html을
# 만들고 기본 브라우저로 연다. 앱이 ~/Applications(사용자 소유)에 있으므로 자기 Resources에
# 직접 써도 안전 — 별도 쓰기 가능 디렉터리로 복사하지 않는다(v1, 단순함 우선).
set -e
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
cd "$RES"

PY=$(command -v python3 || echo /usr/bin/python3)
if ! "$PY" --version >/dev/null 2>&1; then
  osascript -e 'display alert "Python 3가 필요합니다" message "터미널에서 xcode-select --install 을 실행해 Command Line Tools를 설치한 뒤 다시 열어 주세요." as critical'
  exit 1
fi

if ! "$PY" build.py > "$RES/last_scan.log" 2>&1; then
  osascript -e 'display alert "스캔 중 오류가 있었습니다" message "일부 단축키가 빠졌을 수 있어요. 뷰어는 그대로 열립니다. 자세한 내용: '"$RES"'/last_scan.log" as warning'
fi
open "$RES/viewer.html"
