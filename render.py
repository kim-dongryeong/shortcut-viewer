#!/usr/bin/env python3
# render.py — re-render viewer.html from the EXISTING shortcuts.json + viewer.template.html.
# Pure template render: NO scanning/collecting, so it never touches your scanned data.
#   • Use this when you only changed the UI/template (layout, colors, JS).
#   • Use ./refresh.sh when you want to RE-SCAN your shortcuts (needs Accessibility).
import json, os
PROJ = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(PROJ, "shortcuts.json")))
_ap = os.path.join(PROJ, "annotations.json")   # pick up favorites/notes edits without a re-scan
if os.path.exists(_ap):
    try:   # 5개 필드 전부 보존 (fav/note/enote=dict · custom/ghk=list) — 이전엔 fav/note만 구워 enote/custom/ghk 유실됐음
        _a = json.load(open(_ap))
        data["ann"] = {
            "fav":    _a.get("fav", {})    if isinstance(_a.get("fav"),    dict) else {},
            "note":   _a.get("note", {})   if isinstance(_a.get("note"),   dict) else {},
            "enote":  _a.get("enote", {})  if isinstance(_a.get("enote"),  dict) else {},
            "custom": _a.get("custom", []) if isinstance(_a.get("custom"), list) else [],
            "ghk":    _a.get("ghk", [])    if isinstance(_a.get("ghk"),    list) else [],
        }
    except Exception: pass
tpl = open(os.path.join(PROJ, "viewer.template.html")).read()
open(os.path.join(PROJ, "viewer.html"), "w").write(tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)))
print(f"Rendered viewer.html from shortcuts.json — {data['meta']['total']} shortcuts (no re-scan).")
