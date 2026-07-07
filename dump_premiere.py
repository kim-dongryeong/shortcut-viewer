#!/usr/bin/env python3
# dump_premiere.py — extract Adobe Premiere Pro DEFAULT keyboard shortcuts from its bundled
# .kys file (Contents/Keyboard Shortcuts/en/Adobe Premiere Pro Defaults.kys) → defaults/ corpus.
# App-bundle defaults = no PII. Reverse-engineered key encoding:
#   <virtualkey> >= 0x80000000  →  0x80000000 | ASCII  (a character key, e.g. 0x80000043 = 'C')
#   smaller values              →  Adobe's special-key enum (arrows/Space/Delete/…) via SPECIAL;
#                                  unknown codes are written as "vk<n>" AND printed so SPECIAL can be completed.
#   usage:  python3 dump_premiere.py ["/path/to/Adobe Premiere Pro Defaults.kys"]
import os, re, sys, glob, json
import xml.etree.ElementTree as ET
PROJ = os.path.dirname(os.path.abspath(__file__))
OUTBASE = os.path.join(PROJ, "win", "defaults") if os.name == "nt" else os.path.join(PROJ, "defaults")   # 플랫폼별 조합이 달라 corpus 분리
FLAG = 0x80000000
SPECIAL = {   # Adobe special-key code -> our key name (decoded from Premiere default command bindings)
    1: "Space", 2: "Delete", 3: "Tab", 4: "Return", 7: "F1", 11: "F5", 12: "F6",
    35: "ForwardDelete", 36: "Home", 37: "End", 38: "PageUp", 39: "PageDown",
    42: "Left", 43: "Right", 44: "Up", 45: "Down",
}
WINVK = {}   # Windows .kys가 Win32 VK 코드를 쓸 경우의 폴백 (win/build_win.py의 VK 테이블 재사용)
if os.name == "nt":
    try:
        sys.path.insert(0, os.path.join(PROJ, "win")); from build_win import VK as WINVK
    except Exception:
        pass

def humanize(cmd):
    out = []
    for p in (cmd or "").replace("cmd.", "", 1).split("."):
        p = re.sub(r"^\d+", "", p)            # "06razor" -> "razor"
        if p: out.append(p[:1].upper() + p[1:])
    return " ▸ ".join(out) or (cmd or "")

def decode(vk):
    n = int(vk)
    if n >= FLAG:
        c = n - FLAG
        return (chr(c).upper() if 32 <= c < 127 else None), None   # character key via ASCII
    key = SPECIAL.get(n) or (WINVK.get(n) if WINVK else None)       # special key → (win) VK 폴백 → unknown
    return key, n

def find_kys():
    pats = ["/Applications/Adobe Premiere Pro */*.app/Contents/Keyboard Shortcuts/en/Adobe Premiere Pro Defaults.kys",
            os.path.expandvars(r"%ProgramFiles%\Adobe\Adobe Premiere Pro *\Keyboard Shortcuts\en\Adobe Premiere Pro Defaults.kys")]
    for p in pats:
        g = glob.glob(p)
        if g: return g[0]
    return None

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else find_kys()
    if not path or not os.path.exists(path): sys.exit("Premiere 'Defaults.kys' 못 찾음 — 경로를 인자로 주세요.")
    ver = (re.search(r"Adobe Premiere Pro (\d[\d.]*)", path) or [None, "menu"])[1]
    MODS = (("ctrl", "ctrl"), ("shift", "shift"), ("opt", "opt"), ("command", "cmd"),
            ("alt", "opt"), ("win", "cmd"), ("meta", "cmd"))   # alt/win/meta = Windows .kys 태그 후보
    ents, unknown = [], {}
    for it in ET.parse(path).getroot().iter():
        if not it.tag.startswith("item."): continue
        cmd, vk = it.findtext("commandname"), it.findtext("virtualkey")
        if not cmd or vk is None: continue
        mods = [o for m, o in MODS if it.findtext("modifier." + m) == "true"]
        key, small = decode(vk)
        if key is None:
            key = f"vk{small}" if small is not None else "?"
            if small is not None: unknown.setdefault(small, []).append(cmd)
        ents.append({"mods": mods, "key": key, "action": humanize(cmd), "source": "app config",
                     "scope": "Adobe Premiere Pro", "detail": "premiere .kys default · " + cmd,
                     "group": "Adobe Premiere Pro"})
    d = os.path.join(OUTBASE, "Adobe Premiere Pro"); os.makedirs(d, exist_ok=True)
    payload = {"app": "Adobe Premiere Pro", "version": ver, "scope": "Adobe Premiere Pro",
               "provenance": {"kind": "app-bundle", "file": os.path.basename(path)},
               "entries": sorted(ents, key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
    open(os.path.join(d, f"keymap-{ver}.json"), "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"  → {os.path.relpath(d, PROJ)}/keymap-{ver}.json  ({len(ents)}건 · 문자키 ASCII 디코드)")
    if unknown:
        print(f"  ⚠️ 특수키 미매핑 {len(unknown)}종 — 아래(코드→예시 명령)를 붙여주시면 키 이름을 채웁니다:")
        for code in sorted(unknown):
            print(f"     vk{code}  ←  {', '.join(c.replace('cmd.','') for c in unknown[code][:3])}")
    print("검토:  git diff -- defaults/   →  git add defaults/ && git commit && git push")

if __name__ == "__main__":
    main()
