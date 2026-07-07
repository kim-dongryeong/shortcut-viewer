#!/usr/bin/env python3
# dump_photoshop.py — extract Adobe Photoshop DEFAULT keyboard shortcuts.
# Source 1 (bundle .kys, XML): <command name> + 1..n <shortcut>Opt+Cmd+V</shortcut>
#   (multiple = ALTERNATIVE bindings). <tool>/<taskspace-tool> carry NO key data (FourCC ids).
# Source 2 (optional, Edit ▸ Keyboard Shortcuts ▸ Summarize… export .htm): adds Tools (V/M/B…),
#   Panel Menus, Taskspace — rows are <tr> with indent tds; name+combo in class="shortcutcols"
#   cells; <br> separates alternative combos; submenu headers end with '>'.
# Merged, deduped on (mods, key, leaf action) — kys is authoritative, htm fills the rest.
#   usage:  python3 dump_photoshop.py [Default Keyboard Shortcuts.kys] [version] [Summarize.htm]
import os, re, sys, glob, json, html as htmllib
import xml.etree.ElementTree as ET
PROJ = os.path.dirname(os.path.abspath(__file__))
OUTBASE = os.path.join(PROJ, "win", "defaults") if os.name == "nt" else os.path.join(PROJ, "defaults")   # 플랫폼별 조합이 달라 corpus 분리
APPNAME = "Adobe Photoshop 2026"   # must match the AX-scan scope so packs merge into one context
MODS = {"Cmd": "cmd", "Opt": "opt", "Shift": "shift", "Control": "ctrl", "Ctrl": "ctrl", "Alt": "opt"}   # Ctrl/Alt = Windows .kys 토큰

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
    pats = ["/Applications/Adobe Photoshop */Locales/*/Support Files/Shortcuts/Mac/Default Keyboard Shortcuts.kys",
            os.path.expandvars(r"%ProgramFiles%\Adobe\Adobe Photoshop *\Locales\*\Support Files\Shortcuts\Win\Default Keyboard Shortcuts.kys")]
    for p in pats:
        g = glob.glob(p)
        if g: return g[0]
    return None

def _clean(t):
    return htmllib.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ").strip()

def parse_summarize(path):
    # Summarize .htm → [(section, path▸leaf, combo)] — indent depth = leading empty tds; headers end '>'
    txt = open(path, encoding="utf-8", errors="replace").read()
    out, section, stack = [], "?", []   # stack[d] = submenu name at depth d
    for chunk in re.split(r"(<h2>[^<]*</h2>)", txt):
        m = re.match(r"<h2>([^<]*)</h2>", chunk)
        if m:
            s = _clean(m.group(1))
            if s: section = s; stack = []
            continue
        for tr in re.findall(r"<tr>(.*?)</tr>", chunk, re.S):
            tds = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
            if not tds: continue
            texts = [_clean(t) for _, t in tds]
            if any("#cccccc" in a for a, _ in tds):            # 메뉴 그룹 헤더 (Photoshop/File/…)
                if texts and texts[-1]: stack = [texts[-1]]
                continue
            depth = 0
            while depth < len(texts) and not texts[depth]: depth += 1
            sc_idx = [i for i, (a, _) in enumerate(tds) if "shortcutcols" in a and texts[i]]
            if not sc_idx:                                      # 하위메뉴 헤더 행 ("Preferences>")
                hdr = next((t for t in texts if t.endswith(">")), None)
                if hdr: stack = stack[:max(depth, 1)] + [hdr.rstrip(">").strip()]
                continue
            name = texts[sc_idx[0]]
            combos = []
            if len(sc_idx) > 1:                                 # 마지막 shortcutcols 셀 = 단축키(<br>=대안)
                raw = re.sub(r"<br[^>]*>", "\n", tds[sc_idx[-1]][1])
                combos = [c.strip() for c in _clean(raw).split("\n") if c.strip()] if sc_idx[-1] != sc_idx[0] else []
            stack = stack[:max(depth, 1)]
            for c in combos: out.append((section, " ▸ ".join(stack + [name]) if stack else name, c))
    return out

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else find_kys()
    if not path or not os.path.exists(path): sys.exit("Photoshop 'Default Keyboard Shortcuts.kys' 못 찾음 — 경로를 인자로 주세요.")
    ver = sys.argv[2] if len(sys.argv) > 2 else (re.search(r"Photoshop (\d{4})", path) or [None, "kys"])[1]
    htm = sys.argv[3] if len(sys.argv) > 3 else None
    ents, seen = [], set()
    root = ET.parse(path).getroot()
    for el in root.iter():
        if el.tag not in ("command",): continue
        name = el.get("name")
        shorts = [s.text for s in el.iter("shortcut") if s.text]
        if not name or not shorts: continue
        for sc in shorts:
            mods, key = parse_combo(sc)
            if not key: continue
            seen.add((tuple(sorted(mods)), key, name))
            ents.append({"mods": mods, "key": key, "action": name, "source": "app config", "scope": APPNAME,
                         "detail": f"photoshop .kys default · {sc}" + (" · alt" if sc != shorts[0] else ""),
                         "group": APPNAME})
    if htm and os.path.exists(htm):
        n0 = len(ents)
        for section, pathname, combo in parse_summarize(htm):
            mods, key = parse_combo(combo)
            if not key: continue
            leaf = pathname.split(" ▸ ")[-1]
            fp = (tuple(sorted(mods)), key, leaf)
            if fp in seen: continue                              # kys가 이미 가진 조합·명령
            seen.add(fp)
            ents.append({"mods": mods, "key": key, "action": leaf, "source": "app config", "scope": APPNAME,
                         "detail": f"photoshop summarize · {section} · {pathname} · {combo}", "group": APPNAME})
        print(f"  summarize에서 +{len(ents) - n0}건 (Tools/Panel/Taskspace)")
    d = os.path.join(OUTBASE, APPNAME); os.makedirs(d, exist_ok=True)
    prov = {"kind": "app-bundle", "file": os.path.basename(path)}
    if htm and os.path.exists(htm): prov["summarize"] = os.path.basename(htm)   # 도구/패널 키는 Summarize 내보내기에서
    payload = {"app": APPNAME, "version": str(ver), "scope": APPNAME, "provenance": prov,
               "entries": sorted(ents, key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
    out = os.path.join(d, f"keymap-{ver}.json")
    open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"  → {os.path.relpath(out, PROJ)}  ({len(ents)}건 · 대안 바인딩 포함)")
    print("검토:  python3 normalize_packs.py && git diff -- defaults/")

if __name__ == "__main__":
    main()
