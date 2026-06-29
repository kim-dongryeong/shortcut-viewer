#!/usr/bin/env python3
# share_menus.py — promote specific apps' MENU-BAR shortcuts from your local scan into the shareable
# defaults/ corpus, with personal data stripped:
#   • drops the system "Apple ▸ …" menu (which holds "Log Out <your name>", etc.)
#   • scrubs your real name / username / home path out of the remaining labels
#   • aborts if any known PII signature survives (defense in depth)
# Run on a Mac where the apps are installed AND were scanned (./refresh.sh with them open).
#   usage:  python3 share_menus.py "Microsoft Excel" "Notion" "Adobe Premiere Pro 2025"
import json, os, re, sys, subprocess, plistlib
PROJ = os.path.dirname(os.path.abspath(__file__)); HOME = os.path.expanduser("~")

def pii_set():
    s = {HOME}
    for cmd in (["id", "-un"], ["id", "-F"]):          # username, full name ("Kim Dongryeong")
        try:
            v = subprocess.check_output(cmd, text=True).strip()
            if v: s.add(v)
        except Exception: pass
    return {p for p in s if len(p) >= 3}               # never scrub 1-2 char strings

def scrub(t, pii):
    if not t: return t
    t = t.replace(HOME, "~"); t = re.sub(r"/Users/[^/\s'\"]+", "/Users/USER", t)
    for p in sorted(pii, key=len, reverse=True):
        if p != HOME: t = t.replace(p, "USER")
    return t

def version_of(bundle):
    if not bundle: return "menu"
    try:
        for path in subprocess.check_output(["mdfind", f"kMDItemCFBundleIdentifier == '{bundle}'"], text=True).splitlines():
            pl = os.path.join(path.strip(), "Contents/Info.plist")
            if os.path.exists(pl):
                d = plistlib.load(open(pl, "rb"))
                v = d.get("CFBundleShortVersionString") or d.get("CFBundleVersion")
                if v: return str(v)
    except Exception: pass
    return "menu"

def main(apps):
    sj = os.path.join(PROJ, "shortcuts.json")
    if not os.path.exists(sj): sys.exit("shortcuts.json 없음 — 먼저 ./refresh.sh 로 스캔하세요.")
    data = json.load(open(sj)); pii = pii_set(); want = set(apps)
    packs = {}
    for e in data.get("entries", []):
        if e.get("source") != "app menu" or e.get("scope") not in want: continue
        if e.get("action", "").lstrip().startswith("Apple "): continue        # drop system Apple menu (PII lives here)
        p = packs.setdefault(e["scope"], {"bundle": e.get("detail", "") or "", "items": []})
        p["items"].append({"mods": e["mods"], "key": e["key"], "action": scrub(e.get("action", ""), pii),
                           "source": "app menu", "scope": e["scope"], "detail": "app menu (shared)", "group": e["scope"]})
    if not packs:
        avail = sorted({e["scope"] for e in data.get("entries", []) if e.get("source") == "app menu"})
        sys.exit("해당 앱의 메뉴 항목 없음. 스캔된 앱(정확한 이름):\n  " + "\n  ".join(avail))
    for app, p in packs.items():
        ver = version_of(p["bundle"])
        d = os.path.join(PROJ, "defaults", app); os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"menu-{ver}.json")
        payload = {"app": app, "version": ver, "scope": app, "bundle": p["bundle"],
                   "provenance": {"kind": "scanned-app-menu", "note": "Apple menu dropped, PII-scrubbed"},
                   "entries": sorted(p["items"], key=lambda x: (len(x["mods"]), x["key"], x["action"]))}
        out = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True)
        leaks = [s for s in pii if s != HOME and s in out]
        if re.search(r"/Users/(?!USER\b)[A-Za-z]", out): leaks.append("/Users/<name>")
        if leaks: sys.exit(f"‼️ PII 잔존({app}): {leaks} — 중단(코드 점검 필요).")
        open(path, "w").write(out)
        emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", out)))
        warn = f"  ⚠️ 이메일 의심: {emails} — 리뷰하세요" if emails else ""
        print(f"  → {os.path.relpath(path, PROJ)}  ({len(p['items'])}건 · Apple메뉴 제외 · PII 스크럽 · v{ver}){warn}")
    print("⚠️ 푸시 전 반드시 검토:  git diff -- defaults/   그 다음:  git add defaults/ && git commit -m 'share <app> menus' && git push")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit('usage: python3 share_menus.py "Microsoft Excel" "Notion" ...')
    main(sys.argv[1:])
