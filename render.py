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
    try:
        _a = json.load(open(_ap)); data["ann"] = {"fav": _a.get("fav", {}), "note": _a.get("note", {})}
    except Exception: pass
tpl = open(os.path.join(PROJ, "viewer.template.html")).read()
open(os.path.join(PROJ, "viewer.html"), "w").write(tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)))
print(f"Rendered viewer.html from shortcuts.json — {data['meta']['total']} shortcuts (no re-scan).")
