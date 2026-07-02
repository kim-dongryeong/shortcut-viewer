#!/usr/bin/env python3
# find_adobe_keymaps.py — RUN THIS ON THE MAC THAT HAS ADOBE (Photoshop/Illustrator/After Effects).
# It locates each app's DEFAULT keyboard-shortcut file (like Premiere's bundled *.kys) so we can build a
# programmatic extractor — NO guessing, NO web. It only READS + prints paths/format sniffs; writes nothing.
#
#   usage:  python3 find_adobe_keymaps.py
#
# Adobe stores shortcut sets in a few shapes:
#   • Premiere/Photoshop:  *.kys  (XML — already parsed for Premiere by dump_premiere.py)
#   • Illustrator:         "Adobe Illustrator ... Defaults"  (text) or exported .txt from the Kbd Shortcuts dialog
#   • After Effects:       "... Shortcuts.txt" / "...aftereffects... .txt"
# If nothing default is found in-bundle, the guaranteed-complete fallback is the app's own export:
#   Photoshop:     Edit ▸ Keyboard Shortcuts ▸ Summarize…      → HTML (all tools/menus/panels)
#   Illustrator:   Edit ▸ Keyboard Shortcuts ▸ Export Text (⬇)  → .txt
#   After Effects: (CC) the active set lives as a .txt in prefs (printed below)
import os, glob, sys

HOME = os.path.expanduser("~")
APPS = "/Applications"
PATTERNS = [
    # (label, glob) — bundle defaults first, then per-user preference sets
    ("Photoshop · bundle .kys",   APPS + "/Adobe Photoshop */**/*.kys"),
    ("Photoshop · prefs .kys",    HOME + "/Library/Preferences/Adobe Photoshop * Settings/**/*.kys"),
    ("Photoshop · prefs (any kb)",HOME + "/Library/Preferences/Adobe Photoshop * Settings/**/*eyboard*"),
    ("Illustrator · bundle",      APPS + "/Adobe Illustrator */**/*Defaults*"),
    ("Illustrator · prefs sets",  HOME + "/Library/Preferences/Adobe Illustrator * Settings/**/*"),
    ("After Effects · bundle",    APPS + "/Adobe After Effects */**/*Shortcuts*.txt"),
    ("After Effects · prefs",     HOME + "/Library/Preferences/Adobe/After Effects/**/*.txt"),
    ("Any Adobe .kys (broad)",    APPS + "/Adobe */**/*.kys"),
]

def sniff(path):
    try:
        with open(path, "rb") as f: head = f.read(240)
    except Exception as e:
        return f"(unreadable: {e})"
    txt = head.decode("utf-8", "replace").replace("\n", " ").replace("\r", " ")
    kind = "xml/.kys" if b"<" in head[:64] and b"kys" in head[:200].lower() or head[:5] == b"<?xml" \
        else ("text" if all(9 <= b <= 126 or b in (10, 13) for b in head[:64]) else "binary")
    return f"[{kind}] {txt[:120]}"

def main():
    print("Adobe 기본 키맵 파일 탐색 (읽기만, 변경 없음)\n" + "=" * 60)
    found = 0
    for label, pat in PATTERNS:
        hits = sorted(set(p for p in glob.glob(pat, recursive=True) if os.path.isfile(p)))
        if not hits:
            print(f"· {label}: 없음")
            continue
        print(f"● {label}: {len(hits)}개")
        for p in hits[:12]:
            size = os.path.getsize(p)
            print(f"    {p}  ({size:,}B)")
            print(f"      → {sniff(p)}")
            found += 1
        if len(hits) > 12: print(f"    … 외 {len(hits)-12}개")
    print("=" * 60)
    if found:
        print("위 경로 중 '기본(Default)' 키맵으로 보이는 파일 경로를 알려주시면 파서를 만들어 채웁니다.")
    else:
        print("번들 기본 키맵이 안 보입니다 → 각 앱의 내장 내보내기를 쓰세요:")
        print("  Photoshop:   Edit ▸ Keyboard Shortcuts ▸ Summarize…  → 저장된 .htm 경로 알려주기")
        print("  Illustrator: Edit ▸ Keyboard Shortcuts ▸ Export(⬇)   → 저장된 .txt 경로 알려주기")
        print("  After Effects: 활성 단축키 .txt (위 'prefs' 목록 참고)")

if __name__ == "__main__":
    main()
