#!/bin/bash
# 더블클릭하면 Shortcut Viewer 서버가 실행되고 브라우저가 열립니다. (macOS)
cd "$(dirname "$0")"
PORT="${1:-8787}"
URL="http://127.0.0.1:$PORT"

if curl -s -o /dev/null "$URL" 2>/dev/null; then
  echo "이미 실행 중입니다 → $URL"
  open "$URL"; exit 0
fi

# 실행 전 viewer.html이 없으면 빌드합니다.
if [ ! -f viewer.html ]; then
  echo "viewer.html을 빌드합니다..."
  python3 build.py
fi

exec python3 app.py --port="$PORT" --open
