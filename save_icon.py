#!/usr/bin/env python3
# save_icon.py — extract an installed app's icon into the shared defaults/ corpus so it shows in
# the viewer's context chips EVEN ON MACHINES WHERE THE APP ISN'T INSTALLED. App icons are public
# (no PII), so defaults/<App>/icon.png IS committed — run this on the Mac that HAS the app.
#   usage:  python3 save_icon.py "Adobe Photoshop 2026" "Microsoft Excel" "Notion" …
# Match a scope name (as it appears in the viewer) — fuzzy against installed apps by name/bundle.
import os, sys, subprocess, plistlib, glob
PROJ = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = os.path.join(PROJ, "defaults")

def app_for(term):
    # try bundle-id match, then app display name via mdfind
    for q in (f"kMDItemCFBundleIdentifier == '{term}'",
              f"kMDItemKind == 'Application' && kMDItemDisplayName == '*{term}*'cd",
              f"kMDItemContentType == 'com.apple.application-bundle' && kMDItemFSName == '*{term}*'cd"):
        try:
            for p in subprocess.check_output(["mdfind", q], text=True, stderr=subprocess.DEVNULL).splitlines():
                if p.strip().endswith(".app"): return p.strip()
        except Exception: pass
    # last resort: /Applications glob
    for g in glob.glob(f"/Applications/*{term}*.app") + glob.glob(f"/Applications/**/*{term}*.app", recursive=True):
        return g
    return None

def icns_of(app):
    try: pl = plistlib.load(open(os.path.join(app, "Contents/Info.plist"), "rb"))
    except Exception: pl = {}
    res = os.path.join(app, "Contents/Resources")
    icon = pl.get("CFBundleIconFile")
    if icon:
        cand = os.path.join(res, icon if icon.lower().endswith(".icns") else icon + ".icns")
        if os.path.exists(cand): return cand
    g = glob.glob(os.path.join(res, "*.icns"))
    return next((x for x in g if "AppIcon" in x or "icon" in os.path.basename(x).lower()), (g[0] if g else None))

def main(terms):
    for term in terms:
        app = app_for(term)
        if not app: print(f"  ✗ '{term}' — 설치된 앱 못 찾음"); continue
        icns = icns_of(app)
        if not icns: print(f"  ✗ '{term}' — .icns 없음 ({app})"); continue
        # scope name = the term as the user typed it (must match the viewer's scope/app name)
        d = os.path.join(DEFAULTS, term); os.makedirs(d, exist_ok=True)
        out = os.path.join(d, "icon.png")
        r = subprocess.run(["sips", "-s", "format", "png", "-Z", "40", icns, "--out", out], capture_output=True)
        if r.returncode == 0: print(f"  ✓ {term} → {os.path.relpath(out, PROJ)}  (from {os.path.basename(app)})")
        else: print(f"  ✗ '{term}' — sips 실패")
    print("\n검토:  git add defaults/*/icon.png && git commit -m 'share app icons' && git push")
    print("주의: defaults/<앱> 이름은 뷰어의 스코프 이름과 정확히 같아야 매칭됩니다 (예: 'Adobe Photoshop 2026').")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit('usage: python3 save_icon.py "Adobe Photoshop 2026" "Microsoft Excel" …')
    main(sys.argv[1:])
