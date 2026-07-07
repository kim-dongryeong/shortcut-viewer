#!/usr/bin/env python3
# dump_ae.py — extract After Effects DEFAULT shortcuts from the aeks text file that AE writes to
# prefs (…/Preferences/Adobe/After Effects/<ver>/aeks/After Effects Default.txt). Self-documenting
# format:  ["Context"]  "Command" = "(Cmd+Option+HOME)(alt combo)…"  — each (…) group is an
# ALTERNATIVE binding; "()" = unbound. `"\` + newline + `"` splices a continued string.
# UxFFFF = unicode codepoint; Pad* = numeric keypad. macControl = ctrl.
#   usage:  python3 dump_ae.py [path/to/After Effects Default.txt] [version]
import os, re, sys, glob, json
from collections import OrderedDict
PROJ = os.path.dirname(os.path.abspath(__file__))
OUTBASE = os.path.join(PROJ, "win", "defaults") if os.name == "nt" else os.path.join(PROJ, "defaults")   # 플랫폼별 조합이 달라 corpus 분리
APPNAME = "Adobe After Effects"   # must match the AX-scan scope
MODS = {"Cmd": "cmd", "Option": "opt", "Shift": "shift", "macControl": "ctrl",
        "Ctrl": "ctrl", "Alt": "opt", "Win": "cmd"}   # Ctrl/Alt/Win = Windows aeks 토큰
KEY = {"LeftArrow": "Left", "RightArrow": "Right", "UpArrow": "Up", "DownArrow": "Down",
       "PageUP": "PageUp", "PageDOWN": "PageDown", "HOME": "Home", "END": "End",
       "FwdDel": "ForwardDelete", "Delete": "Delete", "Backspace": "Delete",
       "Return": "Return", "Enter": "keypad_enter", "Esc": "Escape", "Tab": "Tab", "Space": "Space",
       "Comma": ",", "SingleQuote": "'", "DoubleQuote": '"', "Backslash": "\\", "Plus": "+",
       "LParen": "(", "RParen": ")", "HELP": "Help", "Insert": "Insert", "NumLock": "NumLock",
       "Pause": "Pause", "CapsLock": "CapsLock"}
SKIP_CMDS = {"TextIgnoreKey", "NOP"}   # 억제 목록/무동작 — 사용자 단축키가 아님

def key_token(t):
    if t in KEY: return KEY[t]
    if re.fullmatch(r"F\d{1,2}", t): return t
    m = re.fullmatch(r"PadUx([0-9A-Fa-f]{4})", t)
    if m: return "keypad_" + chr(int(m.group(1), 16))
    m = re.fullmatch(r"Ux([0-9A-Fa-f]{4})", t)
    if m:
        c = chr(int(m.group(1), 16))
        return c.upper() if c.isalpha() else c
    m = re.fullmatch(r"Pad(.+)", t)
    if m: return "keypad_" + m.group(1).lower()
    if len(t) == 1: return t.upper() if t.isalpha() else t
    return t

def parse_combo(c):
    mods, key = [], None
    for t in c.split("+"):
        if t in MODS: mods.append(MODS[t])
        elif t: key = key_token(t)
    return mods, key

def humanize(cmd):
    s = cmd.replace("_", " ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return s.strip() or cmd

def find_txt():
    g = glob.glob(os.path.expanduser("~/Library/Preferences/Adobe/After Effects/*/aeks/After Effects Default.txt")) \
        or glob.glob(os.path.expandvars(r"%APPDATA%\Adobe\After Effects\*\aeks\After Effects Default.txt"))
    return sorted(g)[-1] if g else None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else find_txt()
    if not path or not os.path.exists(path): sys.exit("aeks 'After Effects Default.txt' 못 찾음 — 경로를 인자로 주세요.")
    ver = sys.argv[2] if len(sys.argv) > 2 else (re.search(r"After Effects[\\/]([\d.]+)[\\/]", path) or [None, "aeks"])[1]
    txt = open(path, encoding="utf-8", errors="replace").read()
    txt = re.sub(r'"\\\s*"', "", txt)                     # 줄 이음(splice): "…"\ ⏎ "…"
    ents = OrderedDict()                                   # (mods,key,action) → ctx set (같은 명령이 컨텍스트별 반복 → 병합)
    ctx = "?"
    for m in re.finditer(r'\[\s*"([^"]+)"\s*\]|"([^"]+)"\s*=\s*"([^"]*)"', txt):
        if m.group(1): ctx = m.group(1); continue
        cmd, val = m.group(2), m.group(3)
        if ctx == "** header **" or cmd in SKIP_CMDS: continue
        for combo in re.findall(r"\(([^)]*)\)", val):
            if not combo.strip(): continue
            mods, key = parse_combo(combo)
            if not key: continue
            fp = (tuple(sorted(mods)), key, cmd)
            e = ents.get(fp)
            if e: e["_ctx"].add(ctx); continue
            ents[fp] = {"mods": mods, "key": key, "action": humanize(cmd), "source": "app config",
                        "scope": APPNAME, "detail": f"ae aeks default · {combo} · {cmd}", "group": APPNAME,
                        "_ctx": {ctx}}
    out_ents = []
    for e in ents.values():
        cs = sorted(e.pop("_ctx"))
        e["detail"] += " · ctx: " + ", ".join(cs[:4]) + (f" 외 {len(cs)-4}" if len(cs) > 4 else "")
        out_ents.append(e)
    d = os.path.join(OUTBASE, APPNAME); os.makedirs(d, exist_ok=True)
    payload = {"app": APPNAME, "version": str(ver), "scope": APPNAME,
               "provenance": {"kind": "prefs-default-set", "file": os.path.basename(path),
                              "note": "AE writes the built-in Default set here on first run"},
               "entries": sorted(out_ents, key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
    outp = os.path.join(d, f"keymap-{ver}.json")
    open(outp, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"  → {os.path.relpath(outp, PROJ)}  ({len(out_ents)}건 · 컨텍스트 병합·대안 바인딩 포함)")
    print("검토:  python3 normalize_packs.py && git diff -- defaults/")

if __name__ == "__main__":
    main()
