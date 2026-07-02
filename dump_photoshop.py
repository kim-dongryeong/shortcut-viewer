#!/usr/bin/env python3
# dump_photoshop.py — extract Adobe Photoshop DEFAULT keyboard shortcuts from its bundled .kys
# (XML: <photoshop-keyboard-shortcuts version="4"> / <command name><shortcut>Opt+Cmd+V</shortcut>).
# Multiple <shortcut> children = ALTERNATIVE bindings (like Codex), not a chord.
# NOTE: <tool>/<taskspace-tool> elements carry NO key data (FourCC tool ids only) — Photoshop's
# tool defaults (V/M/B…) are hardcoded elsewhere; export via Edit ▸ Keyboard Shortcuts ▸ Summarize.
#   usage:  python3 dump_photoshop.py [path/to/Default Keyboard Shortcuts.kys] [version]
import os, re, sys, glob, json
import xml.etree.ElementTree as ET
PROJ = os.path.dirname(os.path.abspath(__file__))
APPNAME = "Adobe Photoshop 2026"   # must match the AX-scan scope so packs merge into one context
MODS = {"Cmd": "cmd", "Opt": "opt", "Shift": "shift", "Control": "ctrl"}

def parse_combo(text):
    mods, key = [], None
    toks = (text or "").split("+")
    for i, t in enumerate(toks):
        if t in MODS: mods.append(MODS[t])
        elif t == "" and i == len(toks) - 1: key = "+"      # "Cmd++" → key '+'
        elif t: key = t
    if key and re.fullmatch(r"F\d+", key): return mods, key
    if key and len(key) == 1: return mods, (key.upper() if key.isalpha() else key)
    return mods, key

def find_kys():
    g = glob.glob("/Applications/Adobe Photoshop */Locales/*/Support Files/Shortcuts/Mac/Default Keyboard Shortcuts.kys")
    return g[0] if g else None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else find_kys()
    if not path or not os.path.exists(path): sys.exit("Photoshop 'Default Keyboard Shortcuts.kys' 못 찾음 — 경로를 인자로 주세요.")
    ver = sys.argv[2] if len(sys.argv) > 2 else (re.search(r"Photoshop (\d{4})", path) or [None, "kys"])[1]
    ents = []
    root = ET.parse(path).getroot()
    for el in root.iter():
        if el.tag not in ("command",): continue
        name = el.get("name")
        shorts = [s.text for s in el.iter("shortcut") if s.text]
        if not name or not shorts: continue
        for sc in shorts:
            mods, key = parse_combo(sc)
            if not key: continue
            ents.append({"mods": mods, "key": key, "action": name, "source": "app config", "scope": APPNAME,
                         "detail": f"photoshop .kys default · {sc}" + (" · alt" if sc != shorts[0] else ""),
                         "group": APPNAME})
    d = os.path.join(PROJ, "defaults", APPNAME); os.makedirs(d, exist_ok=True)
    payload = {"app": APPNAME, "version": str(ver), "scope": APPNAME,
               "provenance": {"kind": "app-bundle", "file": os.path.basename(path)},
               "entries": sorted(ents, key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
    out = os.path.join(d, f"keymap-{ver}.json")
    open(out, "w").write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"  → {os.path.relpath(out, PROJ)}  ({len(ents)}건 · 대안 바인딩 포함)")
    print("검토:  python3 normalize_packs.py && git diff -- defaults/")

if __name__ == "__main__":
    main()
