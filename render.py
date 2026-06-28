#!/usr/bin/env python3
# render.py — re-render viewer.html from the EXISTING shortcuts.json + viewer.template.html.
# Pure template render: NO scanning/collecting, so it never touches your scanned data.
#   • Use this when you only changed the UI/template (layout, colors, JS).
#   • Use ./refresh.sh when you want to RE-SCAN your shortcuts (needs Accessibility).
import json, os
PROJ = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(PROJ, "shortcuts.json")))
tpl = open(os.path.join(PROJ, "viewer.template.html")).read()
open(os.path.join(PROJ, "viewer.html"), "w").write(tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)))
print(f"Rendered viewer.html from shortcuts.json — {data['meta']['total']} shortcuts (no re-scan).")
