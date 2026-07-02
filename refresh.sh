#!/bin/zsh
# refresh.sh — recompile the menu dumper if needed, recollect all sources, regenerate viewer.html.
# IMPORTANT: run this from a terminal that HAS Accessibility permission, or app-menu shortcuts
# will be skipped. (System Settings ▸ Privacy & Security ▸ Accessibility ▸ add your terminal.)
cd "${0:A:h}" || exit 1
if [[ ! -x ./axmenudump || axmenudump.swift -nt ./axmenudump ]]; then
  echo "compiling axmenudump (universal: Apple Silicon + Intel)…"
  # Build a UNIVERSAL binary so the same axmenudump runs on both arm64 (Apple Silicon) and
  # x86_64 (Intel) Macs — the macOS SDK is universal, so we can cross-compile both here.
  if swiftc -target arm64-apple-macos11 axmenudump.swift -o /tmp/axmenudump.arm64 2>/dev/null \
     && swiftc -target x86_64-apple-macos11 axmenudump.swift -o /tmp/axmenudump.x86_64 2>/dev/null \
     && lipo -create /tmp/axmenudump.arm64 /tmp/axmenudump.x86_64 -output axmenudump 2>/dev/null; then
    rm -f /tmp/axmenudump.arm64 /tmp/axmenudump.x86_64
    echo "  → universal ($(lipo -archs axmenudump))"
  else                                    # cross-SDK unavailable → native-arch build still works locally
    echo "  (universal build failed — falling back to native arch)"
    swiftc axmenudump.swift -o axmenudump || exit 1
  fi
fi
/usr/bin/python3 build.py
echo "→ open ./viewer.html"
