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
if swiftc -O -target arm64-apple-macos13  svhotkeys.swift -o /tmp/svhotkeys.arm64 2>/dev/null \
   && swiftc -O -target x86_64-apple-macos13 svhotkeys.swift -o /tmp/svhotkeys.x86_64 2>/dev/null \
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
[ -f AppIcon.icns ] && cp AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"

# 안정적인 self-signed 인증서로 서명 → 재빌드해도 신원(designated requirement)이 같아
# Accessibility(손쉬운 사용) 허가가 유지됨. `./make-cert.sh`가 전용 키체인에 인증서를 만들어
# codesign이 비대화식(암호창 없음)으로 쓰게 함. 없으면 ad-hoc 폴백(재빌드마다 권한 재부여 필요).
CN="SV Hotkeys Dev"
SIGNKC="$HOME/Library/Keychains/svhotkeys-signing.keychain-db"
if [ -f "$SIGNKC" ]; then
  security unlock-keychain -p svhk "$SIGNKC" 2>/dev/null || true
  # 이름 중복(로그인 키체인 잔재 등)에 흔들리지 않게 SHA-1 해시로 서명
  HASH=$(security find-certificate -c "$CN" -Z "$SIGNKC" 2>/dev/null | awk '/SHA-1 hash:/{print $NF}')
  if [ -n "$HASH" ]; then
    echo "▸ codesign ($CN · $HASH · 권한 유지)"
    codesign --force --sign "$HASH" --keychain "$SIGNKC" "$APP" 2>&1 | sed 's/^/   /' || true
  else
    echo "▸ codesign (ad-hoc — 전용 키체인에 '$CN' 인증서 없음)"; codesign --force --sign - "$APP" 2>&1 | sed 's/^/   /' || true
  fi
else
  echo "▸ codesign (ad-hoc — './make-cert.sh' 먼저 실행하면 재빌드해도 권한 유지)"
  codesign --force --sign - "$APP" 2>&1 | sed 's/^/   /' || true
fi
echo "✓ built \"$APP\""
codesign -dv "$APP" 2>&1 | grep -iE 'Authority|Identifier|Signature' | sed 's/^/   /' || true

if [[ "${1:-}" == "run" ]]; then echo "▸ launching"; open "$APP"; fi
