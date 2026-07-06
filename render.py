#!/usr/bin/env python3
# render.py — re-render viewer.html from the EXISTING shortcuts.json + viewer.template.html.
# Pure template render: NO scanning/collecting, so it never touches your scanned data.
#   • Use this when you only changed the UI/template (layout, colors, JS).
#   • Use ./refresh.sh when you want to RE-SCAN your shortcuts (needs Accessibility).
import json, os
from svkeys import KEYPAD_KEY   # keypad_*/numpad* → Keypad* : 재스캔 없이 기존 데이터도 canonical화(뷰어 JS 임시맵 제거)
PROJ = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(PROJ, "shortcuts.json")))
for _e in data.get("entries", []):
    for _kf in ("key", "ckey"):
        if _e.get(_kf) in KEYPAD_KEY: _e[_kf] = KEYPAD_KEY[_e[_kf]]
from svann import load_annotations   # 5필드 보존 로더(build/render 공유 — 코덱스 P0)
_ap = os.path.join(PROJ, "annotations.json")   # pick up favorites/notes edits without a re-scan
if os.path.exists(_ap):
    data["ann"] = load_annotations(_ap)   # fav/note/enote=dict · custom/ghk=list
tpl = open(os.path.join(PROJ, "viewer.template.html")).read()
open(os.path.join(PROJ, "viewer.html"), "w").write(tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)))
print(f"Rendered viewer.html from shortcuts.json — {data['meta']['total']} shortcuts (no re-scan).")
