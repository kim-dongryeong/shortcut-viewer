#!/usr/bin/env python3
# dump_illustrator.py — extract Adobe Illustrator DEFAULT shortcuts from its bundled
# "Illustrator Defaults.kys" (PostScript-style text, NOT XML):
#   /commandName { /Context 0 /Modifiers M /Represent R /Key K }   in /Menus{…} and /Tools{…}
# Reverse-engineered encoding (verified against AI's real defaults — palette F-keys, ⌘` doc cycling):
#   Modifiers bitmask: shift 32 · cmd 64 · opt 128 · (ctrl 16 — unseen in defaults, unverified)
#   Key: 0 = unassigned(skip) · 9 = Tab · 14–25 = F1–F12 (F(n-13)) · ≥32 = ASCII char (physical key)
#   Represent = display char when it differs from the physical key (e.g. '+' shown for '=' key).
#   usage:  python3 dump_illustrator.py [path/to/Illustrator Defaults.kys] [version]
import os, re, sys, glob, json
PROJ = os.path.dirname(os.path.abspath(__file__))
OUTBASE = os.path.join(PROJ, "win", "defaults") if os.name == "nt" else os.path.join(PROJ, "defaults")   # 플랫폼별 조합이 달라 corpus 분리
APPNAME = "Adobe Illustrator 2026"   # must match the AX-scan scope

def decode_key(k):
    if k == 0: return None
    if k == 9: return "Tab"
    if 14 <= k <= 25: return "F" + str(k - 13)
    if 32 <= k < 127:
        c = chr(k)
        return c.upper() if c.isalpha() else c
    return f"vk{k}"   # 미지 코드 — 경고 출력용

def decode_mods(m):
    out = []
    if os.name == "nt":   # Windows .kys: 64 = 주 수식키 슬롯(Ctrl — mac에선 Cmd), 128 = Alt
        if m & 64: out.append("ctrl")
        if m & 128: out.append("opt")
        if m & 32: out.append("shift")
        unknown = m & ~(32 | 64 | 128)
    else:
        if m & 16: out.append("ctrl")
        if m & 128: out.append("opt")
        if m & 32: out.append("shift")
        if m & 64: out.append("cmd")
        unknown = m & ~(16 | 32 | 64 | 128)
    return out, unknown

def humanize(raw):
    s = raw.replace("\\", "")
    s = re.sub(r"^(Adobe|AI|ai)[ _]", "", s)
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)      # camelCase 분리
    s = re.sub(r"\d+$", "", s).strip()                  # 꼬리 숫자(대안 바인딩 별칭: paste2)
    return (s[:1].upper() + s[1:]) if s else raw

def find_kys():
    pats = ["/Applications/Adobe Illustrator */Presets.localized/*/Keyboard Shortcuts/Illustrator Defaults.kys",
            os.path.expandvars(r"%ProgramFiles%\Adobe\Adobe Illustrator *\Presets*\*\Keyboard Shortcuts\Illustrator Defaults.kys")]
    for p in pats:
        g = glob.glob(p)
        if g: return g[0]
    return None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else find_kys()
    if not path or not os.path.exists(path): sys.exit("'Illustrator Defaults.kys' 못 찾음 — 경로를 인자로 주세요.")
    ver = sys.argv[2] if len(sys.argv) > 2 else (re.search(r"Illustrator (\d{4})", path) or [None, "kys"])[1]
    txt = open(path, encoding="utf-8", errors="replace").read()
    ti = txt.find("/Tools")
    ents, warn = [], {}
    pat = re.compile(r"/((?:[^{}\s\\]|\\.)+)\s*\{\s*/Context\s+(\d+)\s*/Modifiers\s+(\d+)\s*/Represent\s+(\d+)\s*/Key\s+(\d+)\s*\}")
    for m in pat.finditer(txt):
        raw, ctx, mod, rep, key = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        sec = "tools" if (ti >= 0 and m.start() > ti) else "menus"
        k = decode_key(key)
        if not k: continue
        if k.startswith("vk"): warn.setdefault(key, []).append(raw)
        mods, unk = decode_mods(mod)
        det = f"illustrator .kys default · {sec} · {raw.replace(chr(92), '')}"
        if rep and rep != key and 32 <= rep < 127: det += f" · 표기 {chr(rep)}"
        if unk: det += f" · ⚠️mod+{unk}"
        ents.append({"mods": mods, "key": k, "action": humanize(raw), "source": "app config", "scope": APPNAME,
                     "detail": det, "group": APPNAME})
    d = os.path.join(OUTBASE, APPNAME); os.makedirs(d, exist_ok=True)
    payload = {"app": APPNAME, "version": str(ver), "scope": APPNAME,
               "provenance": {"kind": "app-bundle", "file": os.path.basename(path)},
               "entries": sorted(ents, key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
    out = os.path.join(d, f"keymap-{ver}.json")
    open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"  → {os.path.relpath(out, PROJ)}  ({len(ents)}건 · menus+tools)")
    if warn:
        print(f"  ⚠️ 미지 Key 코드 {len(warn)}종:")
        for code in sorted(warn): print(f"     vk{code}  ←  {', '.join(warn[code][:3])}")
    print("검토:  python3 normalize_packs.py && git diff -- defaults/")

if __name__ == "__main__":
    main()
