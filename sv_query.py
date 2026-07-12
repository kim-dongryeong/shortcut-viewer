#!/usr/bin/env python3
"""sv_query.py — 단축키 corpus(shortcuts.json) 조회 CLI/모듈. 에이전트용 (skill/MCP 공용).

  python3 sv_query.py lookup "cmd+shift+K"          # 이 조합에 뭐가 걸려 있나 (전 스코프)
  python3 sv_query.py free "cmd+shift" [--scope App] # 이 수식키 레이어에서 빈 키
  python3 sv_query.py conflicts [--scope App]        # 글로벌↔앱 겹침 조합
  python3 sv_query.py app "Finder" [--limit 40]      # 앱 하나의 단축키 목록
데이터: $SV_SHORTCUTS → ~/Library/Application Support/Shortcut Viewer/shortcuts.json → 스크립트 옆.
표준 라이브러리만 사용. 출력은 사람도 에이전트도 읽는 평문(줄 단위).
"""
import os, sys, json, argparse

PROJ = os.path.dirname(os.path.abspath(__file__))
MODS = ("cmd", "opt", "ctrl", "shift", "fn")
MOD_ALIAS = {"command": "cmd", "⌘": "cmd", "option": "opt", "alt": "opt", "⌥": "opt",
             "control": "ctrl", "⌃": "ctrl", "⇧": "shift", "globe": "fn", "🌐": "fn", "hyper": "hyper"}
KEY_ALIAS = {"esc": "Escape", "return": "Enter", "ret": "Enter", "space": "Space", "spacebar": "Space",
             "backspace": "Delete", "del": "Delete", "fwddelete": "ForwardDelete", "tab": "Tab",
             "up": "Up", "down": "Down", "left": "Left", "right": "Right", "pgup": "PageUp",
             "pgdn": "PageDown", "capslock": "CapsLock", "caps": "CapsLock"}
# 글로벌하게 작동해서 앱 스코프와 충돌을 일으키는 스코프들 (corpus의 scope 값 기준)
GLOBALISH = {"Global", "global", "macOS 시스템", "macOS 창 관리"}
PREF_KEYS = ["J", "K", "L", "U", "I", "O", "H", "N", "Y", "P", "B", "G", "R", "E", ";", "M",
             "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]


def data_path():
    for p in (os.environ.get("SV_SHORTCUTS"),
              os.path.expanduser("~/Library/Application Support/Shortcut Viewer/shortcuts.json"),
              os.path.join(PROJ, "shortcuts.json")):
        if p and os.path.exists(p):
            return p
    sys.exit("shortcuts.json not found — run Shortcut Viewer once (or set $SV_SHORTCUTS)")


def load():
    with open(data_path()) as f:
        return json.load(f).get("entries", [])


def parse_combo(s):
    """'cmd+shift+K' / '⌘⇧K' 류 → (sorted mods list, canonical key). 마지막 토큰이 키."""
    s = s.strip()
    for sym, name in (("⌘", "cmd+"), ("⌥", "opt+"), ("⌃", "ctrl+"), ("⇧", "shift+"), ("🌐", "fn+")):
        s = s.replace(sym, name)
    toks = [t.strip() for t in s.replace("-", "+").split("+") if t.strip() != ""]
    if not toks:
        return [], ""
    mods, key = [], toks[-1]
    for t in toks[:-1]:
        m = MOD_ALIAS.get(t.lower(), t.lower() if t.lower() in MODS else None)
        if m == "hyper":
            mods += ["cmd", "opt", "ctrl", "shift"]
        elif m:
            mods.append(m)
    kl = key.lower()
    key = KEY_ALIAS.get(kl, key.upper() if len(key) == 1 else key[:1].upper() + key[1:])
    return sorted(set(mods)), key


def combo_str(mods, key):
    order = {m: i for i, m in enumerate(("ctrl", "opt", "shift", "cmd", "fn"))}
    return "+".join(sorted(mods, key=lambda m: order.get(m, 9)) + [key])


def _index(entries):
    by = {}
    for e in entries:
        by.setdefault((tuple(sorted(e.get("mods", []))), e.get("key", "")), []).append(e)
    return by


def lookup(combo):
    mods, key = parse_combo(combo)
    hits = _index(load()).get((tuple(mods), key), [])
    out = [f"{combo_str(mods, key)} — {len(hits)} binding(s)"]
    for e in hits:
        out.append(f"  [{e.get('scope','?')}] {e.get('action','?')}  ({e.get('source','?')})")
    return "\n".join(out)


def free(mods_s, scope=None):
    mods, _ = parse_combo(mods_s + "+x")
    by = _index(load())
    taken = set()
    for (m, k), es in by.items():
        if list(m) != mods:
            continue
        for e in es:
            sc = e.get("scope", "")
            if scope is None or sc in GLOBALISH or sc == scope:
                taken.add(k)
                break
    pool = PREF_KEYS + [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in PREF_KEYS] \
        + [f"F{i}" for i in range(1, 13)] + ["Up", "Down", "Left", "Right", "Space", "Enter"]
    frees = [k for k in pool if k not in taken]
    where = f"scope={scope}+글로벌" if scope else "전 스코프"
    return f"free keys for [{'+'.join(mods) or '(no mods)'}] ({where}, 선호순):\n  " + " ".join(frees[:30])


def conflicts(scope=None):
    by = _index(load())
    out = []
    for (m, k), es in sorted(by.items()):
        scopes = {e.get("scope", "") for e in es}
        g = scopes & GLOBALISH
        apps = scopes - GLOBALISH
        if not (g and apps):
            continue
        if scope and scope not in apps:
            continue
        gact = next(e for e in es if e.get("scope") in g)
        out.append(f"{combo_str(list(m), k)} — 글로벌 '{gact.get('action','?')}' [{gact.get('scope')}]"
                   f" ↔ 앱 {len(apps)}곳: {', '.join(sorted(apps)[:6])}")
    return "\n".join(out) if out else "no global↔app conflicts" + (f" for {scope}" if scope else "")


def app_shortcuts(name, limit=40):
    es = [e for e in load() if e.get("scope", "").lower() == name.lower()]
    if not es:
        import difflib
        allsc = sorted({e.get("scope", "") for e in load()})
        near = [s for s in allsc if name.lower() in s.lower()] \
            or difflib.get_close_matches(name, allsc, n=8, cutoff=0.5)
        return f"scope '{name}' not found." + (f" 비슷한 스코프: {', '.join(near[:8])}" if near else "")
    out = [f"{name}: {len(es)} shortcuts" + (f" (first {limit})" if len(es) > limit else "")]
    for e in es[:limit]:
        out.append(f"  {combo_str(e.get('mods', []), e.get('key',''))}  {e.get('action','?')}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lookup"); p.add_argument("combo")
    p = sub.add_parser("free"); p.add_argument("mods"); p.add_argument("--scope")
    p = sub.add_parser("conflicts"); p.add_argument("--scope")
    p = sub.add_parser("app"); p.add_argument("name"); p.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    if a.cmd == "lookup":
        print(lookup(a.combo))
    elif a.cmd == "free":
        print(free(a.mods, a.scope))
    elif a.cmd == "conflicts":
        print(conflicts(a.scope))
    elif a.cmd == "app":
        print(app_shortcuts(a.name, a.limit))


if __name__ == "__main__":
    main()
