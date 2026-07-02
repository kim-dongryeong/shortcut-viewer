#!/usr/bin/env python3
# dump_sublime.py — extract Sublime Text DEFAULT keybindings into the shared defaults/ corpus.
# Default keymap = Packages/Default/"Default (OSX).sublime-keymap" — a loose file OR inside the
# Default.sublime-package zip. Format: JSON (with // and /* */ comments) array of
#   { "keys": ["super+s", ...], "command": "...", "args": {...}, "context": [...] }
# Multiple keys in the array = a CHORD (1st press on the grid, 2nd press = cmods/ckey). App-bundle
# defaults = no PII.  usage:  python3 dump_sublime.py ["/path/Default (OSX).sublime-keymap"]
import os, re, sys, json, glob, zipfile, plistlib
PROJ = os.path.dirname(os.path.abspath(__file__))
APP = "/Applications/Sublime Text.app"
KEYMAP = "Default (OSX).sublime-keymap"

def strip_jsonc(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"(^|\s)//[^\n]*", r"\1", s)
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    return s

def read_keymap(arg):
    if arg: return open(arg, encoding="utf-8").read(), arg
    loose = os.path.join(APP, "Contents/MacOS/Packages/Default", KEYMAP)
    if os.path.exists(loose): return open(loose, encoding="utf-8").read(), loose
    for pkg in glob.glob(os.path.join(APP, "Contents/MacOS/Packages/Default.sublime-package")) + \
               glob.glob(os.path.join(os.path.expanduser("~"), "Library/Application Support/Sublime Text*/Packages/Default.sublime-package")):
        try:
            with zipfile.ZipFile(pkg) as z:
                for n in z.namelist():
                    if n.endswith(KEYMAP): return z.read(n).decode("utf-8"), f"{pkg}!{n}"
        except Exception: pass
    hits = glob.glob(os.path.join(APP, "**", KEYMAP), recursive=True)
    if hits: return open(hits[0], encoding="utf-8").read(), hits[0]
    return None, None

SUB_MODS = {"super":"cmd","cmd":"cmd","command":"cmd","ctrl":"ctrl","control":"ctrl","alt":"opt","option":"opt","shift":"shift"}
SUB_KEY = {"up":"Up","down":"Down","left":"Left","right":"Right","enter":"Return","tab":"Tab","space":"Space",
           "backspace":"Delete","delete":"ForwardDelete","home":"Home","end":"End","pageup":"PageUp","pagedown":"PageDown",
           "escape":"Escape","forward_slash":"/","backslash":"\\","backquote":"`","plus":"=","minus":"-","equals":"="}
def combo(token):
    mods, key = [], None
    for p in token.split("+"):
        lp = p.lower()
        if lp in SUB_MODS: mods.append(SUB_MODS[lp])
        elif p: key = p
    if not key: return mods, None
    lk = key.lower()
    if lk in SUB_KEY: return mods, SUB_KEY[lk]
    if re.fullmatch(r"f\d+", lk): return mods, "F" + lk[1:]
    if len(key) == 1: return mods, (key.upper() if key.isalpha() else key)
    return mods, key
def humanize(cmd, args):
    base = (cmd or "").replace("_", " ").strip().title()
    if isinstance(args, dict):
        f = args.get("file")
        if isinstance(f, str):    # run_macro_file 등 — 파일명이 실제 동작명 ("Delete Left Right" ≠ "Add Line in Braces")
            return base + " (" + os.path.splitext(os.path.basename(f))[0] + ")"
        for k in ("to", "by", "panel", "name", "extend", "characters", "level"):
            v = args.get(k)
            if isinstance(v, (str, int)) and not isinstance(v, bool): base += f" ({v})"; break
    return base or (cmd or "")
def app_ver():
    try:
        d = plistlib.load(open(os.path.join(APP, "Contents/Info.plist"), "rb"))
        return str(d.get("CFBundleShortVersionString") or d.get("CFBundleVersion") or "menu")
    except Exception: return "menu"

def main():
    txt, src = read_keymap(sys.argv[1] if len(sys.argv) > 1 else None)
    if not txt: sys.exit(f"'{KEYMAP}' 못 찾음 — 경로를 인자로 주세요. (Sublime 설치/실행 확인)")
    try: data = json.loads(strip_jsonc(txt))
    except Exception as e: sys.exit(f"keymap 파싱 실패: {e}")
    ents, skipped = [], 0
    for it in data:
        keys, cmd = it.get("keys") or [], it.get("command")
        if not keys or not cmd: skipped += 1; continue
        mods, key = combo(keys[0])
        if not key: skipped += 1; continue
        e = {"mods": mods, "key": key, "action": humanize(cmd, it.get("args")), "source": "app config",
             "scope": "Sublime Text", "detail": "sublime default · " + " ".join(keys) + " · " + cmd, "group": "Sublime Text"}
        if len(keys) > 1:
            cm, ck = combo(keys[1])
            if ck: e["cmods"] = cm or []; e["ckey"] = ck
        ents.append(e)
    before = len(ents)   # 같은 조합·동작이 context별로 여러 행 → 사용자에겐 동일하므로 붕괴
    seen, uniq = set(), []
    for e in ents:
        fp = (tuple(e["mods"]), e["key"], e["action"], e.get("ckey"), tuple(e.get("cmods") or []))
        if fp not in seen: seen.add(fp); uniq.append(e)
    ents = uniq
    if before > len(ents): print(f"  context-변형 중복 {before - len(ents)}건 붕괴")
    ver = app_ver()
    d = os.path.join(PROJ, "defaults", "Sublime Text"); os.makedirs(d, exist_ok=True)
    payload = {"app": "Sublime Text", "version": ver, "scope": "Sublime Text",
               "provenance": {"kind": "app-bundle", "source": os.path.basename(src)},
               "entries": sorted(ents, key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
    open(os.path.join(d, f"keymap-{ver}.json"), "w").write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"  → defaults/Sublime Text/keymap-{ver}.json  ({len(ents)}건, chord 포함; skip {skipped})  src={src}")
    print("검토:  git diff -- defaults/   →  git add defaults/ && git commit -m 'share Sublime keymap' && git push")

if __name__ == "__main__":
    main()
