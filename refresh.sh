#!/bin/zsh
# refresh.sh — recompile the menu dumper if needed, recollect all sources, regenerate viewer.html.
# IMPORTANT: run this from a terminal that HAS Accessibility permission, or app-menu shortcuts
# will be skipped. (System Settings ▸ Privacy & Security ▸ Accessibility ▸ add your terminal.)
cd "${0:A:h}" || exit 1
if [[ ! -x ./axmenudump || axmenudump.swift -nt ./axmenudump ]]; then
  echo "compiling axmenudump…"
  swiftc axmenudump.swift -o axmenudump || exit 1
fi
/usr/bin/python3 build.py
echo "→ open ./viewer.html"
