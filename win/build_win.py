#!/usr/bin/env python3
# build_win.py — Windows 단축키 수집기 (설계 스켈레톤).
# macOS의 build.py에 대응하는 Windows판. Windows 소스에서 단축키를 긁어 **공유 스키마**
# (mods, key, action, source, scope)로 shortcuts.json을 만들고, 그걸 공유 뷰어(render.py +
# viewer.template.html)로 렌더한다. → 맥과 "같은 키보드 그리드"에 Windows 단축키를 통합.
#
# ⚠️ Windows에서 실행. 이 파일은 설계 스켈레톤(수집기 본체는 TODO). 파이썬 표준 라이브러리만.
#
# 실행 흐름:  python build_win.py   →  shortcuts.json  →  python ../render.py  →  ../viewer.html
#
# 수식키 매핑(윈→공유 스키마): Ctrl→ctrl · Alt→opt · Shift→shift · Win→cmd
#   (기존 뷰어 그리드/빈조합 로직을 그대로 쓰려고 맥 토큰에 매핑. 라벨은 뷰어에서 Win 모드로 표기 — TODO.)

import json, os, re, glob

PROJ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PROJ)   # repo 루트(공유 뷰어 템플릿 위치)
entries = []

def add(mods, key, action, source, scope="global", detail="", group=None, **extra):
    if not key:
        return
    e = {"mods": sorted(set(mods)), "key": key, "action": action, "source": source,
         "scope": scope, "detail": detail, "group": group or scope}
    e.update(extra)
    entries.append(e)

# ── 1) AutoHotKey 스크립트 파싱 ─────────────────────────────────────────────
# AHK 핫키 문법: 접두 기호(^Ctrl !Alt +Shift #Win) + 키 + "::" + 액션.  예:  ^!c::Run calc.exe
AHK_MOD = {"^": "ctrl", "!": "opt", "+": "shift", "#": "cmd"}   # Alt→opt, Win→cmd
AHK_KEYNAME = {  # AHK 키 이름 → 공유 스키마 키 (TODO: 확장)
    "space": "Space", "enter": "Return", "return": "Return", "tab": "Tab", "esc": "Escape", "escape": "Escape",
    "delete": "ForwardDelete", "backspace": "Delete", "left": "Left", "right": "Right", "up": "Up", "down": "Down",
    "home": "Home", "end": "End", "pgup": "PageUp", "pgdn": "PageDown",
}
_AHK_LINE = re.compile(r'^\s*([\^!+#<>*~$]*)([A-Za-z0-9]|[a-z]+|F\d{1,2})::(.+?)\s*(?:;.*)?$')

def collect_ahk(paths):
    for p in paths:
        for f in glob.glob(os.path.expanduser(p)):
            try:
                for line in open(f, encoding="utf-8-sig", errors="ignore"):
                    m = _AHK_LINE.match(line)
                    if not m:
                        continue
                    pre, rawkey, action = m.groups()
                    mods = [AHK_MOD[c] for c in pre if c in AHK_MOD]
                    key = AHK_KEYNAME.get(rawkey.lower())
                    if key is None:
                        key = rawkey.upper() if len(rawkey) == 1 else (rawkey if re.match(r"F\d", rawkey, re.I) else None)
                    add(mods, key, action.strip(), source="AutoHotKey",
                        detail=f"AHK: {os.path.basename(f)}", group="AutoHotKey")
            except Exception as e:
                print("  ahk parse fail", f, e)

# ── 2) PowerToys Keyboard Manager ──────────────────────────────────────────
# %LOCALAPPDATA%\Microsoft\PowerToys\Keyboard Manager\default.json (shortcut remaps)  (TODO: 실제 필드 매핑)
def collect_powertoys():
    p = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\PowerToys\Keyboard Manager\default.json")
    if not os.path.exists(p):
        return
    try:
        d = json.load(open(p, encoding="utf-8"))
        for r in d.get("remapShortcuts", {}).get("global", []):
            # TODO: r["originalKeys"](VK 코드 세미콜론 구분) → mods/key 로 디코드
            add([], "", f"PowerToys remap {r}", source="PowerToys", group="PowerToys")
    except Exception as e:
        print("  powertoys parse fail", e)

# ── 3) 시스템 기본 단축키 시드 (맥 build.py의 DEFAULTS 대응) ──────────────────
def collect_system_defaults():
    W = [  # (mods, key, action)
        (["cmd"], "E", "파일 탐색기"), (["cmd"], "R", "실행(Run)"), (["cmd"], "D", "바탕화면 표시"),
        (["cmd"], "L", "화면 잠금"), (["cmd"], "Tab", "작업 보기"), (["cmd", "shift"], "S", "영역 캡처"),
        (["ctrl", "shift"], "Escape", "작업 관리자"), (["cmd"], "V", "클립보드 기록"),
    ]
    for mods, key, action in W:
        add(mods, key, action, source="system", detail="Windows 기본 단축키", group="Windows 시스템")

# ── 4) 수동 글로벌 (맥 manual_globals.json 대응) ───────────────────────────
def collect_manual():
    p = os.path.join(PROJ, "manual_globals_win.json")
    if not os.path.exists(p):
        return
    for e in json.load(open(p, encoding="utf-8")):
        add(e.get("mods", []), e.get("key", ""), e.get("action", ""),
            source=e.get("source", "manual"), scope=e.get("scope", "global"), group=e.get("group"))

def main():
    collect_system_defaults()
    collect_ahk([r"%USERPROFILE%\Documents\AutoHotkey\*.ahk", r"%USERPROFILE%\*.ahk"])
    collect_powertoys()
    collect_manual()

    # TODO: 최종 정규화 pass (맥 build.py와 공유 — keys.py로 분리해 양쪽에서 import; 코덱스 리뷰 참고)
    from collections import Counter
    meta = {"total": len(entries), "platform": "windows",
            "counts": dict(Counter(e["source"] for e in entries))}
    data = {"meta": meta, "entries": entries, "gestures": [], "ann": {"fav": {}, "note": {}, "enote": {}, "custom": [], "ghk": []}}
    json.dump(data, open(os.path.join(ROOT, "shortcuts.json"), "w"), ensure_ascii=False, indent=1)
    print(f"shortcuts.json — {len(entries)}개 (Windows). 이제: python render.py 로 viewer.html 생성")

if __name__ == "__main__":
    main()
