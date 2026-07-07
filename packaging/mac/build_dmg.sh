#!/bin/zsh
# packaging/mac/build_dmg.sh — "Shortcut Viewer.app" + "Shortcut Viewer.dmg"를 만든다.
# 일반 사용자용 배포판: repo를 클론할 필요 없이 .dmg → 드래그 설치 → 더블클릭이면 끝.
# ad-hoc 서명(비용 없음, v1) — 그래도 "확인되지 않은 개발자" 경고가 한 번 뜨면 우클릭 ▸ 열기.
#   usage:  ./packaging/mac/build_dmg.sh   (repo 루트에서 실행해도, 여기서 실행해도 됨)
set -e
HERE="${0:A:h}"; ROOT="${HERE:h:h}"          # packaging/mac → packaging → repo 루트
OUT="$HERE/dist"
APP="$OUT/Shortcut Viewer.app"
RES="$APP/Contents/Resources"

echo "▸ 1/5  axmenudump 컴파일 (universal: Apple Silicon + Intel)"
cd "$ROOT"
if swiftc -target arm64-apple-macos11 axmenudump.swift -o /tmp/svax.arm64 2>/dev/null \
   && swiftc -target x86_64-apple-macos11 axmenudump.swift -o /tmp/svax.x86_64 2>/dev/null \
   && lipo -create /tmp/svax.arm64 /tmp/svax.x86_64 -output /tmp/svax.universal 2>/dev/null; then
  rm -f /tmp/svax.arm64 /tmp/svax.x86_64
  AXBIN=/tmp/svax.universal
  echo "  ✓ universal ($(lipo -archs $AXBIN))"
else
  echo "  (universal 실패 — 이 머신 아키텍처로만 빌드)"
  swiftc axmenudump.swift -o /tmp/svax.universal
  AXBIN=/tmp/svax.universal
fi

echo "▸ 2/5  앱 번들 조립"
rm -rf "$OUT"; mkdir -p "$APP/Contents/MacOS" "$RES"
cp "$HERE/Info.plist" "$APP/Contents/Info.plist"
cp "$HERE/launcher.sh" "$APP/Contents/MacOS/ShortcutViewer"; chmod +x "$APP/Contents/MacOS/ShortcutViewer"
cp "$AXBIN" "$RES/axmenudump"; chmod +x "$RES/axmenudump"
for f in build.py render.py svkeys.py svann.py viewer.template.html; do
  cp "$ROOT/$f" "$RES/"
done
cp -R "$ROOT/defaults" "$RES/defaults"
cp "$ROOT/web_shortcuts.json" "$RES/web_shortcuts.json"
echo "  ✓ $(du -sh "$APP" | cut -f1) — $(find "$RES/defaults" -name '*.json' | wc -l | tr -d ' ') defaults 팩"

# Apple Silicon은 서명이 아예 없는 실행 파일의 실행 자체를 거부한다(Gatekeeper의 "확인되지 않은
# 개발자" 경고와는 별개 문제) — 비용 없는 ad-hoc 서명(-s -)으로 axmenudump·앱 번들 둘 다 서명.
# 유료 Developer ID가 아니므로 Gatekeeper 경고 자체는 남음(우클릭 ▸ 열기로 1회 넘기면 됨).
echo "▸ 3/5  ad-hoc 서명"
codesign --force -s - "$RES/axmenudump"
codesign --force --deep -s - "$APP"
echo "  ✓ $(codesign -dv "$APP" 2>&1 | grep -o 'adhoc' || echo signed)"

echo "▸ 4/5  DMG 생성"
DMG="$OUT/Shortcut Viewer.dmg"; rm -f "$DMG"
hdiutil create -volname "Shortcut Viewer" -srcfolder "$APP" -ov -format UDZO "$DMG" >/dev/null
echo "  ✓ $DMG ($(du -sh "$DMG" | cut -f1))"

echo "▸ 5/5  완료 — 테스트: open \"$APP\""
echo "배포 전 체크: 서명 없음 → 받은 사람은 우클릭 ▸ 열기(또는 시스템 설정 ▸ 개인정보 보호 및 보안에서 허용) 1회 필요."
