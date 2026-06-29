#!/usr/bin/env bash
# dump_codex.sh — extract Codex (OpenAI desktop, an Electron app) in-app keyboard shortcuts.
# The big "Settings ▸ Keyboard Shortcuts" list is NOT in the menu bar (so the AX menu scan
# misses it) — the defaults are compiled into app.asar as `{id, electron:{menuTitle}, defaultKeybindings:[{key}]}`.
# This pulls them into codex_keybindings.json, which build.py's collect_codex() reads.
# Re-run after Codex updates. Reads the installed bundle read-only; needs no Accessibility.
set -euo pipefail
PROJ="$(cd "$(dirname "$0")" && pwd)"
ASAR="${1:-/Applications/Codex.app/Contents/Resources/app.asar}"
if [ ! -f "$ASAR" ]; then echo "Codex app.asar not found at: $ASAR"; exit 1; fi

TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
strings -n 4 "$ASAR" > "$TMP"
python3 - "$TMP" "$PROJ/codex_keybindings.json" <<'PY'
import re, sys, json
txt = open(sys.argv[1], encoding='utf-8', errors='ignore').read()
out, seen = [], set()
# each command:  {id:`x`, ... electron:{menuTitle:`Title`, ...}, defaultKeybindings:[{key:`CmdOrCtrl+P`}, ...]}
# multiple keys in the array = ALTERNATIVE bindings for the same command (not a chord).
for m in re.finditer(r'defaultKeybindings:\[(.*?)\]', txt):
    keys = re.findall(r'key:`([^`]+)`', m.group(1))
    if not keys: continue
    back = txt[max(0, m.start()-600):m.start()]
    idm = re.findall(r'id:`([^`]+)`', back)
    tit = re.findall(r'(?:menuTitle|title):`([^`]+)`', back)
    cid = idm[-1] if idm else ''
    title = tit[-1] if tit else ''
    for k in keys:
        sig = (cid, k)
        if sig in seen: continue
        seen.add(sig)
        out.append({'id': cid, 'title': title, 'key': k})
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
print(f"Wrote {sys.argv[2]} — {len(out)} Codex keybindings")
PY
