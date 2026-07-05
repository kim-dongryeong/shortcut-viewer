#!/usr/bin/env python3
# normalize_packs.py — hygiene pass over the SHARED defaults/ corpus (tracked, PII-free packs).
# Older scans wrote raw NSEvent PUA chars (-range = arrows/F-keys → invisible "tofu" on the
# grid) and shifted symbols ('+','<','?' … which have no physical key cell); newer build.py
# normalizes these at load, but the packs are the corpus other machines consume — keep them clean.
#   • PUA/glyph key names → canonical names (Up/F5/PageUp/Escape…)
#   • shifted symbol keys → base key + 'shift' mod  (⌘+  →  ⌘⇧=)
#   • exact-duplicate entries removed (same combo+action from context variants)
# Idempotent; rewrites only files that change.  usage:  python3 normalize_packs.py
import os, glob, json
PROJ = os.path.dirname(os.path.abspath(__file__))

# keep in sync with build.py's PUA_KEY / SHIFTED
PUA_KEY = {chr(0xF700): "Up", chr(0xF701): "Down", chr(0xF702): "Left", chr(0xF703): "Right",
           chr(0xF728): "ForwardDelete", chr(0xF729): "Home", chr(0xF72B): "End", chr(0xF72C): "PageUp", chr(0xF72D): "PageDown",
           "⎋": "Escape", "⌫": "Delete", "⌦": "ForwardDelete", "⇥": "Tab", "↩": "Return", "⏎": "Return", "Esc": "Escape",
           "↖": "Home", "↘": "End", "⇞": "PageUp", "⇟": "PageDown"}
PUA_KEY.update({chr(0xF704 + i): "F" + str(i + 1) for i in range(20)})
SHIFTED = {'+': '=', '_': '-', '~': '`', '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8',
           '(': '9', ')': '0', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'}
ORDER = ["ctrl", "opt", "shift", "cmd", "fn"]
from svkeys import KEYPAD_KEY   # keypad_*/numpad* → Keypad* (build.py와 공유)

def norm(e):
    for kf, mf in (("key", "mods"), ("ckey", "cmods")):
        k = e.get(kf)
        if not k: continue
        k = PUA_KEY.get(k, k)
        k = KEYPAD_KEY.get(k, k)
        if k in SHIFTED:
            k = SHIFTED[k]
            if "shift" not in (e.get(mf) or []): e[mf] = (e.get(mf) or []) + ["shift"]
        e[kf] = k
        e[mf] = [m for m in ORDER if m in set(e.get(mf) or [])]
    return e

def main():
    changed = 0
    for path in sorted(glob.glob(os.path.join(PROJ, "defaults", "*", "*.json"))):
        data = json.load(open(path))
        ents = data.get("entries")
        if not isinstance(ents, list): continue
        seen, uniq = set(), []
        for e in ents:   # 원본 순서 보존 — 재정렬하면 다음 스캔(save_app_defaults는 원본 순서로 씀)과 diff 핑퐁이 생김
            fp = json.dumps(norm(e), sort_keys=True, ensure_ascii=False)
            if fp not in seen: seen.add(fp); uniq.append(e)
        data["entries"] = uniq
        out = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
        if out != open(path).read():
            open(path, "w").write(out)
            print(f"  ✎ {os.path.relpath(path, PROJ)}  ({len(ents)} → {len(uniq)}건)")
            changed += 1
    print(f"{changed}개 파일 정규화" if changed else "모든 팩이 이미 정규 상태")

if __name__ == "__main__":
    main()
