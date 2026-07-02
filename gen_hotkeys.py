#!/usr/bin/env python3
# gen_hotkeys.py — turn one hotkeys.json (the same file SV Hotkeys daemon reads, and that
# viewer.html exports) into config for the global-hotkey tools you may ALREADY run:
#   • Karabiner-Elements  → karabiner-sv.json   (a complex-modification rule set)
#   • skhd                → skhdrc.sv
#   • Hammerspoon         → hammerspoon-sv.lua
# So "set a global shortcut" works whether or not you install our native daemon.
#   usage:  python3 gen_hotkeys.py [hotkeys.json]     (default: ~/.config/shortcut-viewer/hotkeys.json)
import os, sys, json

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.config/shortcut-viewer/hotkeys.json")
OUT = os.path.dirname(os.path.abspath(__file__))

# viewer key name → (karabiner key_code, skhd key, hammerspoon key)
KEYS = {
    **{c: (c.lower(), c.lower(), c.lower()) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    **{d: (d, d, d) for d in "0123456789"},
    "Space":("spacebar","space","space"), "Return":("return_or_enter","return","return"),
    "Tab":("tab","tab","tab"), "Escape":("escape","escape","escape"),
    "Delete":("delete_or_backspace","backspace","delete"), "ForwardDelete":("delete_forward","delete","forwarddelete"),
    "Left":("left_arrow","left","left"), "Right":("right_arrow","right","right"),
    "Up":("up_arrow","up","up"), "Down":("down_arrow","down","down"),
    "Home":("home","home","home"), "End":("end","end","end"),
    "PageUp":("page_up","pageup","pageup"), "PageDown":("page_down","pagedown","pagedown"),
    "-":("hyphen","0x1B","-"), "=":("equal_sign","0x18","="),
    "[":("open_bracket","0x21","["), "]":("close_bracket","0x1E","]"),
    "\\":("backslash","0x2A","\\"), ";":("semicolon","0x29",";"), "'":("quote","0x27","'"),
    ",":("comma","0x2B",","), ".":("period","0x2F","."), "/":("slash","0x2C","/"),
    "`":("grave_accent_and_tilde","0x32","`"),
    **{f"F{n}":(f"f{n}",f"f{n}",f"f{n}") for n in range(1,21)},
}
KMOD = {"cmd":"command","opt":"option","ctrl":"control","shift":"shift"}
SKMOD = {"cmd":"cmd","opt":"alt","ctrl":"ctrl","shift":"shift"}
HSMOD = {"cmd":"cmd","opt":"alt","ctrl":"ctrl","shift":"shift"}

def shq(s):  # single-quote for shell
    return "'" + str(s).replace("'", "'\\''") + "'"

def to_shell(a):
    """action → a shell command string (the lowest common denominator every backend runs)."""
    t, v = a.get("type"), a.get("value", "")
    if t == "open_app":
        if v.startswith("/"): return f"open {shq(v)}"
        if "." in v and " " not in v: return f"open -b {shq(v)}"      # bundle id
        return f"open -a {shq(v)}"
    if t == "open_url":  return f"open {shq(v)}"
    if t in ("open_folder","open_file"): return f"open {shq(os.path.expanduser(v)) if v.startswith('~') else shq(v)}"
    if t == "run_shell": return v
    if t == "applescript": return f"osascript -e {shq(v)}"
    if t == "paste_text":
        return f"printf %s {shq(v)} | pbcopy && osascript -e 'tell application \"System Events\" to keystroke \"v\" using command down'"
    if t == "show_viewer":
        p = v or "~/dev/shortcut-viewer/viewer.html"
        return f"open {shq(os.path.expanduser(p))}"
    return f"echo 'unknown action {t}'"

def load():
    if not os.path.exists(SRC): sys.exit(f"설정 없음: {SRC}\n(뷰어에서 내보내거나 hotkeys.example.json 복사)")
    d = json.load(open(SRC))
    return [h for h in d.get("hotkeys", []) if h.get("enabled", True)]

def gen_karabiner(hks):
    manips = []
    for h in hks:
        kc = KEYS.get(h["key"])
        if not kc: continue
        manips.append({"type":"basic",
            "from":{"key_code":kc[0], "modifiers":{"mandatory":[KMOD[m] for m in h["mods"] if m in KMOD]}},
            "to":[{"shell_command": to_shell(h["action"])}],
            "description": h.get("title","")})
    rule = {"description":"Shortcut Viewer 글로벌 핫키", "manipulators":manips}
    doc = {"title":"Shortcut Viewer", "rules":[rule]}
    p = os.path.join(OUT, "karabiner-sv.json")
    open(p,"w").write(json.dumps(doc, ensure_ascii=False, indent=2))
    return p, len(manips)

def gen_skhd(hks):
    lines = ["# Shortcut Viewer 글로벌 핫키 — skhd", "# 설치: cp skhdrc.sv ~/.config/skhd/skhdrc  (또는 내용 추가) 후  skhd --reload", ""]
    n = 0
    for h in hks:
        kc = KEYS.get(h["key"])
        if not kc: continue
        mods = " + ".join(SKMOD[m] for m in h["mods"] if m in SKMOD)
        lhs = f"{mods} - {kc[1]}" if mods else kc[1]
        lines.append(f"# {h.get('title','')}"); lines.append(f"{lhs} : {to_shell(h['action'])}"); n += 1
    p = os.path.join(OUT, "skhdrc.sv"); open(p,"w").write("\n".join(lines)+"\n"); return p, n

def gen_hammerspoon(hks):
    lines = ["-- Shortcut Viewer 글로벌 핫키 — Hammerspoon",
             "-- 설치: 이 내용을 ~/.hammerspoon/init.lua 에 추가 후 Hammerspoon ▸ Reload Config", ""]
    n = 0
    for h in hks:
        kc = KEYS.get(h["key"])
        if not kc: continue
        mods = "{" + ", ".join(f'"{HSMOD[m]}"' for m in h["mods"] if m in HSMOD) + "}"
        cmd = to_shell(h["action"]).replace("\\","\\\\").replace('"','\\"')
        title = (h.get("title","") or "").replace('"','\\"')
        lines.append(f'hs.hotkey.bind({mods}, "{kc[2]}", function() hs.execute("{cmd}", true) end)  -- {title}'); n += 1
    p = os.path.join(OUT, "hammerspoon-sv.lua"); open(p,"w").write("\n".join(lines)+"\n"); return p, n

def main():
    hks = load()
    print(f"소스: {SRC}  ({len(hks)}개 활성 핫키)\n")
    for gen, name in ((gen_karabiner,"Karabiner-Elements"), (gen_skhd,"skhd"), (gen_hammerspoon,"Hammerspoon")):
        p, n = gen(hks); print(f"  {name:20} → {os.path.relpath(p, OUT)}  ({n}개)")
    print("""
설치 방법 (셋 중 이미 쓰는 것 하나만):
  • Karabiner:  karabiner-sv.json 을 ~/.config/karabiner/assets/complex_modifications/ 에 복사
                → Karabiner-Elements ▸ Complex Modifications ▸ Add rule ▸ 'Shortcut Viewer' 활성화
  • skhd:       skhdrc.sv 내용을 ~/.config/skhd/skhdrc 에 추가 →  skhd --reload   (brew install skhd)
  • Hammerspoon: hammerspoon-sv.lua 내용을 ~/.hammerspoon/init.lua 에 추가 → Reload Config
  • 아무 도구도 없으면 → 우리 네이티브 데몬:  cd hotkeys && ./build.sh run  (설치 불필요)""")

if __name__ == "__main__":
    main()
