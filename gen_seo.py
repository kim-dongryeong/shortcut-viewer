#!/usr/bin/env python3
# gen_seo.py — build a static, SEO-optimized public site from the PII-FREE shared corpus
#              (defaults/*  +  web_shortcuts.json).  One page per app
#              ("<App> keyboard shortcuts for Mac"), an index, sitemap.xml, robots.txt.
#
#   • Reads ONLY tracked, shareable data — NEVER shortcuts.json / viewer.html (those hold PII).
#   • Output → docs/   (committed; GitHub Pages serves it from  main ▸ /docs).
#   • Re-run anytime:  python3 gen_seo.py    (no scan, no Accessibility, no wall-clock in output).
#
# Why: the interactive viewer is personal (gitignored). These pages are the PUBLIC face —
# each targets a real search ("photoshop keyboard shortcuts mac") so the project earns reach.
import json, os, re, glob, shutil, html
from svkeys import KEYPAD_KEY

PROJ = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(PROJ, "docs")
BASE_URL = "https://kim-dongryeong.github.io/shortcut-viewer"   # GitHub Pages URL (enable Pages ▸ main /docs)
REPO_URL = "https://github.com/kim-dongryeong/shortcut-viewer"
SITE     = "Shortcut Viewer"
TAGLINE  = "Every Mac keyboard shortcut, on one keyboard grid."

# ── key / modifier display ────────────────────────────────────────────────────
MOD_ORDER = ["fn", "ctrl", "opt", "shift", "cmd"]
MOD_SYM   = {"fn": "🌐", "ctrl": "⌃", "opt": "⌥", "shift": "⇧", "cmd": "⌘"}
KEY_DISP  = {"Left": "←", "Right": "→", "Up": "↑", "Down": "↓",
             "Return": "⏎", "Enter": "⏎", "Tab": "⇥", "Escape": "esc",
             "Delete": "⌫", "ForwardDelete": "⌦", "Space": "Space",
             "Home": "↖", "End": "↘", "PageUp": "⇞", "PageDown": "⇟",
             "KeypadEnter": "Num⏎", "KeypadPlus": "Num+", "KeypadMinus": "Num−",
             "KeypadMultiply": "Num×", "KeypadDivide": "Num÷", "KeypadDecimal": "Num.",
             "KeypadComma": "Num,", "KeypadClear": "NumClear", "KeypadEquals": "Num=",
             "browserback": "Back", "browserforward": "Fwd", "MouseBack": "Mouse⤺",
             "Help": "Help"}
for _n in range(10): KEY_DISP.setdefault(f"Keypad{_n}", f"Num{_n}")

def key_disp(k):
    if not k: return ""
    k = KEYPAD_KEY.get(k, k)
    if k in KEY_DISP: return KEY_DISP[k]
    return k.upper() if len(k) == 1 and k.isalpha() else k

def mods_syms(mods):
    return [MOD_SYM[m] for m in MOD_ORDER if m in (mods or [])]

# ── VS Code raw command-id → friendly label ──────────────────────────────────
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
def prettify(action):
    if " " in action or "▸" in action: return action           # already human
    s = action
    for pre in ("workbench.action.", "editor.action.", "workbench.", "editor."):
        if s.startswith(pre): s = s[len(pre):]; break
    s = s.replace(".", " ").replace("_", " ")
    s = _CAMEL.sub(r"\1 \2", s).strip()
    return (s[:1].upper() + s[1:]) if s else action

# ── section grouping (a page's H2 buckets) ───────────────────────────────────
_CAT = {"tools": "Tools", "tool": "Tools", "menus": "Menus", "menu": "Menus", "panels": "Panels"}
def section_of(e):
    a = e.get("action", "")
    if "▸" in a:                                                # menu path → top menu
        return a.split("▸")[0].strip()
    segs = [s.strip() for s in (e.get("detail") or "").split("·")]
    if len(segs) >= 3 and segs[1].lower() in _CAT:             # Adobe PS/AI "… · Tools · …"
        return _CAT[segs[1].lower()]
    return "Commands"

# ── canonical version sort (type-safe: elements are uniform tuples so mixed
#    "1.127.0" vs "Build 4200" vs "" never raise) ──────────────────────────────
def vkey(v):
    out = []
    for x in re.split(r"[.\s]+", str(v or "")):
        if x.isdigit(): out.append((1, int(x), ""))
        elif x:         out.append((0, 0, x))
    return out

# ── load structured packs (defaults/<app>/<file>.json) ───────────────────────
def load_packs():
    """→ {app_name: {'entries':[...], 'ver':str, 'dirs':set, 'sources':set}} (newest ver per kind)."""
    best = {}     # (app, kind) → (vkey, path, data)
    for path in sorted(glob.glob(os.path.join(PROJ, "defaults", "*", "*.json"))):
        try: data = json.load(open(path))
        except Exception: continue
        ents = data.get("entries")
        if not isinstance(ents, list) or not ents: continue
        app  = data.get("app") or os.path.basename(os.path.dirname(path))
        kind = "menu" if os.path.basename(path).startswith("menu") else "keymap"
        key  = (app, kind)
        vk   = vkey(data.get("version"))
        if key not in best or vk > best[key][0]:
            best[key] = (vk, path, data)
    apps = {}
    for (app, kind), (vk, path, data) in best.items():
        rec = apps.setdefault(app, {"entries": [], "ver": "", "dirs": set(), "sources": set()})
        rec["dirs"].add(os.path.basename(os.path.dirname(path)))
        v = str(data.get("version") or "")
        if v and vkey(v) >= vkey(rec["ver"]): rec["ver"] = v
        for e in data["entries"]:
            for kf in ("key", "ckey"):
                if e.get(kf) in KEYPAD_KEY: e[kf] = KEYPAD_KEY[e[kf]]
            rec["sources"].add(e.get("source", ""))
            rec["entries"].append(e)
    return apps

# ── load web_shortcuts.json → entries ────────────────────────────────────────
_WEB_MOD = {"⌘": "cmd", "⌥": "opt", "⌃": "ctrl", "⇧": "shift", "🌐": "fn", "Fn": "fn"}
def web_entry(keys, action):
    """Parse the vendor symbol notation into a render-ready entry (first step lands on the grid;
       full multi-step sequence kept in detail)."""
    steps = re.split(r"\s+then\s+|\s*,\s*", keys.strip(), flags=re.I)
    first = steps[0]
    mods, i = [], 0
    while i < len(first) and first[i] in _WEB_MOD:
        mods.append(_WEB_MOD[first[i]]); i += 1
    rest = first[i:].strip()
    seq = len(steps) > 1
    return {"mods": mods, "key": rest, "action": action, "source": "web",
            "web_seq": keys if seq else "", "detail": "web " + keys}

def load_web():
    apps = {}
    try: data = json.load(open(os.path.join(PROJ, "web_shortcuts.json")))
    except Exception: return apps
    for name, lst in data.items():
        if name == "_comment" or not isinstance(lst, list): continue
        rec = apps.setdefault(name, {"entries": [], "ver": "web", "dirs": {name}, "sources": {"web"}})
        for it in lst:
            k, a = it.get("keys", ""), it.get("action", "")
            if a: rec["entries"].append(web_entry(k, a))
    return apps

# ── merge structured + web by app display name ───────────────────────────────
def merge(a, b):
    for name, rec in b.items():
        if name in a:
            a[name]["entries"] += rec["entries"]
            a[name]["dirs"]    |= rec["dirs"]
            a[name]["sources"] |= rec["sources"]
            if a[name]["ver"] in ("", "web"): a[name]["ver"] = rec["ver"]
        else:
            a[name] = rec
    return a

# ── categories on the index ──────────────────────────────────────────────────
CATEGORY = {
    "VS Code": "Code editors", "Sublime Text": "Code editors", "Codex": "Code editors",
    "Adobe Photoshop 2026": "Design & video", "Adobe Illustrator 2026": "Design & video",
    "Adobe After Effects": "Design & video", "Adobe Premiere Pro": "Design & video",
    "Microsoft Word": "Office", "Microsoft Excel": "Office", "Microsoft PowerPoint": "Office",
    "Google Docs": "Google Workspace", "Google Sheets": "Google Workspace", "Google Drive (웹)": "Google Workspace",
    "Notion": "Notes & productivity", "Notion Calendar": "Notes & productivity",
}
CAT_ORDER = ["Code editors", "Design & video", "Office", "Google Workspace", "Notes & productivity", "Apps"]

def slug(name):
    s = re.sub(r"\(.*?\)", "", name).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "app"

# ── html helpers ─────────────────────────────────────────────────────────────
def esc(s): return html.escape(str(s), quote=False)
def attr(s): return html.escape(str(s), quote=True)

def keys_html(e):
    caps = mods_syms(e.get("mods")) + ([key_disp(e["key"])] if e.get("key") else [])
    out = "".join(f'<kbd>{esc(c)}</kbd>' for c in caps) or '<kbd class="none">—</kbd>'
    if e.get("ckey"):
        chord = mods_syms(e.get("cmods")) + [key_disp(e["ckey"])]
        out += '<span class="then">then</span>' + "".join(f'<kbd>{esc(c)}</kbd>' for c in chord)
    if e.get("web_seq"):
        out = f'<span title="{attr(e["web_seq"])}">{out}<span class="then">seq</span></span>'
    return out

SRC_LABEL = {"app menu": "Menu", "app config": "Keymap", "web": "Web"}
def src_badge(s):
    lbl = SRC_LABEL.get(s, s or "")
    return f'<span class="src src-{attr((s or "x").replace(" ","-"))}">{esc(lbl)}</span>' if lbl else ""

HEAD = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="{site}">{ogimg}
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#0b1020">
<link rel="stylesheet" href="{css}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%E2%8C%98%3C/text%3E%3C/svg%3E">
{jsonld}"""

def head(title, desc, url, css, ogtype="website", ogimg="", jsonld=""):
    return HEAD.format(title=attr(title), desc=attr(desc[:158]), url=attr(url), site=attr(SITE),
                       css=attr(css), ogtype=ogtype,
                       ogimg=(f'\n<meta property="og:image" content="{attr(ogimg)}">' if ogimg else ""),
                       jsonld=jsonld)

def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"

NAV = f'''<header class="nav"><a class="brand" href="{{home}}"><span class="glyph">⌘</span> {SITE}</a>
<nav><a href="{{home}}">All apps</a><a href="{REPO_URL}" rel="noopener">★ GitHub</a></nav></header>'''

FOOT = f'''<footer><p><strong>{SITE}</strong> — {TAGLINE} A free, open-source (GPL-3.0) macOS tool that
aggregates shortcuts from every source (system, app menus, VS Code/Adobe keymaps, Karabiner, BetterTouchTool,
Raycast) onto one interactive keyboard grid, then finds conflicts and free key combos.</p>
<p><a href="{REPO_URL}" rel="noopener">Get it on GitHub →</a> · Shortcut data shown here is each app's public
default keymap. No tracking, no personal data.</p></footer>'''

def page(title, desc, url, css, home, body, **kw):
    return ("<!doctype html><html lang=\"en\"><head>" + head(title, desc, url, css, **kw) +
            "</head><body>" + NAV.format(home=home) + "<main>" + body + "</main>" + FOOT + "</body></html>")

# ── dedup + section-order within an app ──────────────────────────────────────
def dedup(entries):
    seen, out = set(), []
    for e in entries:
        fp = (tuple(sorted(e.get("mods") or [])), e.get("key", ""),
              e.get("ckey", ""), prettify(e.get("action", "")).lower())
        if fp in seen: continue
        seen.add(fp); out.append(e)
    return out

MENU_ORDER = ["Application", "File", "Edit", "View", "Insert", "Format", "Layer", "Image",
              "Type", "Select", "Selection", "Filter", "Object", "Effect", "Layout", "Table",
              "Go", "Sequence", "Clip", "Marker", "Playback", "Timeline", "Composition",
              "Animation", "Tools", "Menus", "Panels", "Commands", "Window", "Help"]
def sec_key(name, count):
    return (MENU_ORDER.index(name) if name in MENU_ORDER else len(MENU_ORDER), -count, name)

def render_app(name, rec):
    ents = dedup(rec["entries"])
    n = len(ents)
    ico = None
    for d in sorted(rec["dirs"]):
        p = os.path.join(PROJ, "defaults", d, "icon.png")
        if os.path.exists(p): ico = d; break
    ver = rec["ver"] if rec["ver"] not in ("", "web") else ""
    # group
    groups = {}
    for e in ents: groups.setdefault(section_of(e), []).append(e)
    order = sorted(groups, key=lambda g: sec_key(g, len(groups[g])))
    top = [prettify(e["action"]) for e in ents[:6]]
    desc = (f"Complete list of {n} default {name} keyboard shortcuts for Mac (macOS)"
            + (f", version {ver}" if ver else "") + f". Free, searchable {name} cheat sheet: "
            + ", ".join(top[:4]) + "…")
    url = f"{BASE_URL}/apps/{slug(name)}.html"
    srcs = " ".join(src_badge(s) for s in ("app menu", "app config", "web") if s in rec["sources"])
    icon_url = f"../icons/{slug(name)}.png" if ico else ""
    icon_abs = f"{BASE_URL}/icons/{slug(name)}.png" if ico else ""
    icon_html = f'<img class="appicon" src="{attr(icon_url)}" alt="{attr(name)} icon" width="56" height="56">' if ico else ""

    ld = jsonld([
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "All apps", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": url}]},
        {"@context": "https://schema.org", "@type": "ItemList", "name": f"{name} keyboard shortcuts for Mac",
         "numberOfItems": n, "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "name": prettify(e["action"]) + " — " + "".join(mods_syms(e.get("mods")) + [key_disp(e.get("key",""))])}
            for i, e in enumerate(ents[:25])]}])

    rows = []
    for g in order:
        gid = re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-") or "g"
        rows.append(f'<section class="grp" data-grp><h2 id="{attr(gid)}">{esc(g)} '
                    f'<span class="gc">{len(groups[g])}</span></h2><table><tbody>')
        for e in sorted(groups[g], key=lambda x: prettify(x["action"]).lower()):
            act = prettify(e["action"])
            q = (act + " " + "".join(mods_syms(e.get("mods"))) + (e.get("key") or "")).lower()
            rows.append(f'<tr data-q="{attr(q)}"><td class="k">{keys_html(e)}</td>'
                        f'<td class="a">{esc(act)}{(" " + src_badge(e.get("source"))) if len(rec["sources"])>1 else ""}</td></tr>')
        rows.append("</tbody></table></section>")

    body = f'''<nav class="crumb"><a href="../">All apps</a> › <span>{esc(name)}</span></nav>
<div class="apphdr">{icon_html}<div><h1>{esc(name)} keyboard shortcuts for Mac</h1>
<p class="sub"><strong>{n}</strong> default shortcuts{f" · v{esc(ver)}" if ver else ""} · {srcs}</p></div></div>
<p class="intro">Every default {esc(name)} keyboard shortcut on macOS, in one searchable cheat sheet.
Type below to filter by action or key.</p>
<input id="q" class="filter" type="search" placeholder="Filter {esc(name)} shortcuts… (e.g. zoom, ⌘S)" autocomplete="off" aria-label="Filter shortcuts">
<p id="noresult" class="noresult" hidden>No shortcut matches your filter.</p>
{''.join(rows)}
{RELATED}
<script>{FILTER_JS}</script>'''
    return url, page(f"{name} Keyboard Shortcuts for Mac — {n} shortcuts | {SITE}",
                     desc, url, "../style.css", "../", body,
                     ogtype="article", ogimg=icon_abs, jsonld=ld), ico, n

FILTER_JS = ("var q=document.getElementById('q'),rows=[].slice.call(document.querySelectorAll('tr[data-q]')),"
             "grps=[].slice.call(document.querySelectorAll('[data-grp]')),nr=document.getElementById('noresult');"
             "q.addEventListener('input',function(){var t=q.value.trim().toLowerCase(),hit=0;"
             "rows.forEach(function(r){var m=!t||r.dataset.q.indexOf(t)>=0;r.hidden=!m;if(m)hit++;});"
             "grps.forEach(function(g){g.hidden=!g.querySelector('tr:not([hidden])');});"
             "nr.hidden=hit>0;});")

RELATED = "{related}"   # filled per-app in main()

def render_index(apps):
    total = sum(a["_n"] for a in apps.values())
    by = {}
    for name, rec in apps.items():
        by.setdefault(CATEGORY.get(name, "Apps"), []).append((name, rec))
    cards = []
    for cat in CAT_ORDER:
        if cat not in by: continue
        cards.append(f'<h2>{esc(cat)}</h2><div class="grid">')
        for name, rec in sorted(by[cat], key=lambda x: -x[1]["_n"]):
            icon = (f'<img src="icons/{slug(name)}.png" alt="" width="40" height="40" loading="lazy">'
                    if rec.get("_ico") else '<span class="noico">⌘</span>')
            cards.append(f'<a class="card" href="apps/{slug(name)}.html">{icon}'
                         f'<span class="cn">{esc(name)}</span><span class="ct">{rec["_n"]} shortcuts</span></a>')
        cards.append("</div>")
    napps = len(apps)
    desc = (f"Free, searchable keyboard-shortcut cheat sheets for Mac: {napps} apps, {total:,} shortcuts — "
            "VS Code, Photoshop, Illustrator, After Effects, Word, Excel, Notion, Google Docs and more.")
    ld = jsonld({"@context": "https://schema.org", "@type": "WebSite", "name": SITE,
                 "url": BASE_URL + "/", "description": desc})
    body = f'''<section class="hero"><h1>Mac keyboard shortcut cheat sheets</h1>
<p class="lede">{esc(TAGLINE)} Searchable, always-current default shortcuts for
<strong>{napps} apps</strong> · <strong>{total:,} shortcuts</strong> — pulled straight from each app's own keymap.</p>
<p><a class="cta" href="{REPO_URL}" rel="noopener">★ Star / install the full viewer on GitHub</a></p></section>
{''.join(cards)}
<section class="about"><h2>What is {esc(SITE)}?</h2>
<p>The pages above are static cheat sheets for each app's <em>default</em> shortcuts. The real tool is an
interactive macOS app that merges shortcuts from <strong>every</strong> source on your machine — the system,
running app menus, VS Code &amp; Adobe keymaps, Karabiner, BetterTouchTool, Raycast and your own globals —
onto <strong>one keyboard grid</strong>, then flags conflicts and finds free key combos. Open source, GPL-3.0.</p></section>'''
    return page(f"Mac Keyboard Shortcut Cheat Sheets — {napps} apps, {total:,} shortcuts | {SITE}",
                desc, BASE_URL + "/", "style.css", "./", body, jsonld=ld)

def main():
    apps = merge(load_packs(), load_web())
    os.makedirs(os.path.join(OUT, "apps"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "icons"), exist_ok=True)
    # first pass: counts + icons (needed for index cards + related links)
    meta = {}
    for name, rec in apps.items():
        ents = dedup(rec["entries"]); rec["_n"] = len(ents)
        ico = next((d for d in sorted(rec["dirs"])
                    if os.path.exists(os.path.join(PROJ, "defaults", d, "icon.png"))), None)
        rec["_ico"] = ico
        meta[name] = (slug(name), rec["_n"], ico, CATEGORY.get(name, "Apps"))
    urls = [BASE_URL + "/"]
    for name, rec in apps.items():
        # related = other apps in same category
        cat = CATEGORY.get(name, "Apps")
        sibs = [n for n in apps if n != name and CATEGORY.get(n, "Apps") == cat][:6]
        rel = ("" if not sibs else '<section class="related"><h2>More Mac shortcut cheat sheets</h2><div class="grid">'
               + "".join(f'<a class="card" href="{slug(n)}.html"><span class="cn">{esc(n)}</span>'
                         f'<span class="ct">{apps[n]["_n"]} shortcuts</span></a>' for n in sibs)
               + '</div></section>')
        global RELATED; RELATED = rel
        url, htmlpage, ico, n = render_app(name, rec)
        if ico: shutil.copyfile(os.path.join(PROJ, "defaults", ico, "icon.png"),
                                os.path.join(OUT, "icons", slug(name) + ".png"))
        open(os.path.join(OUT, "apps", slug(name) + ".html"), "w").write(htmlpage)
        urls.append(url)
    open(os.path.join(OUT, "index.html"), "w").write(render_index(apps))
    # sitemap.xml + robots.txt + .nojekyll
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    open(os.path.join(OUT, "sitemap.xml"), "w").write(sm)
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    open(os.path.join(OUT, "style.css"), "w").write(CSS)
    total = sum(a["_n"] for a in apps.values())
    print(f"Generated docs/ — {len(apps)} apps, {total:,} shortcuts, {len(urls)} URLs → {BASE_URL}/")

CSS = r"""
:root{--bg:#0b1020;--panel:#141b31;--line:#26304d;--ink:#e9edf7;--dim:#9aa6c2;--acc:#6ea8ff;--kbd:#1b2340;}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.nav{position:sticky;top:0;z-index:9;display:flex;justify-content:space-between;align-items:center;gap:1rem;
  padding:.7rem 1.1rem;background:rgba(11,16,32,.86);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.brand{font-weight:700;color:var(--ink);font-size:1.05rem}.brand .glyph{color:var(--acc)}
.nav nav{display:flex;gap:1.1rem}.nav nav a{color:var(--dim);font-size:.92rem}
main{max-width:900px;margin:0 auto;padding:1.4rem 1.1rem 3rem}
h1{font-size:1.7rem;line-height:1.2;margin:.2rem 0}
h2{font-size:1.12rem;margin:1.8rem 0 .6rem;padding-bottom:.3rem;border-bottom:1px solid var(--line)}
.crumb{color:var(--dim);font-size:.85rem;margin:.2rem 0 1rem}.crumb span{color:var(--ink)}
.apphdr{display:flex;gap:1rem;align-items:center}.appicon{border-radius:12px;flex:none}
.sub{color:var(--dim);margin:.3rem 0 0}.sub strong{color:var(--ink)}
.intro{color:var(--dim);margin:.9rem 0}
.filter{width:100%;padding:.7rem .9rem;font-size:1rem;color:var(--ink);background:var(--panel);
  border:1px solid var(--line);border-radius:10px;margin:.3rem 0 .4rem}
.filter:focus{outline:none;border-color:var(--acc)}
.noresult{color:var(--dim);padding:.6rem 0}
.grp{margin-top:.4rem}.gc{color:var(--dim);font-weight:400;font-size:.8rem}
table{width:100%;border-collapse:collapse}
td{padding:.42rem .5rem;border-bottom:1px solid var(--line);vertical-align:top}
td.k{white-space:nowrap;width:1%;text-align:right;padding-right:1rem}
td.a{width:99%}
kbd{display:inline-block;min-width:1.5em;text-align:center;padding:.12em .45em;margin:0 .1em;
  font:600 .84rem/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink);
  background:var(--kbd);border:1px solid var(--line);border-bottom-width:2px;border-radius:6px}
kbd.none{color:var(--dim);border-style:dashed;font-weight:400}
.then{color:var(--dim);font-size:.72rem;margin:0 .35em;text-transform:uppercase;letter-spacing:.03em}
.src{display:inline-block;font-size:.66rem;font-weight:600;padding:.05em .4em;border-radius:20px;margin-left:.4em;
  vertical-align:middle;border:1px solid var(--line);color:var(--dim)}
.src-app-menu{color:#c8cfe0}.src-app-config{color:#7fe3d0;border-color:#1c4f47}.src-web{color:#7fd0ff;border-color:#1c435f}
.hero{padding:1.6rem 0 .6rem}.lede{color:var(--dim);font-size:1.08rem;max-width:44rem}.lede strong{color:var(--ink)}
.cta{display:inline-block;margin-top:.6rem;padding:.6rem 1rem;background:var(--acc);color:#08122b;font-weight:700;border-radius:10px}
.cta:hover{text-decoration:none;filter:brightness(1.08)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:.6rem;margin:.4rem 0 1rem}
.card{display:flex;flex-direction:column;gap:.15rem;padding:.8rem .9rem;background:var(--panel);
  border:1px solid var(--line);border-radius:12px;color:var(--ink)}
.card:hover{border-color:var(--acc);text-decoration:none;transform:translateY(-1px)}
.card img,.card .noico{width:40px;height:40px;border-radius:9px;margin-bottom:.3rem}
.card .noico{display:flex;align-items:center;justify-content:center;background:var(--bg);color:var(--acc);font-size:1.3rem}
.cn{font-weight:600}.ct{color:var(--dim);font-size:.82rem}
.about,.related{margin-top:2rem}.about p{color:var(--dim);max-width:46rem}
footer{max-width:900px;margin:0 auto;padding:1.6rem 1.1rem 3rem;border-top:1px solid var(--line);color:var(--dim);font-size:.9rem}
footer strong{color:var(--ink)}
@media(max-width:560px){td.k{white-space:normal}h1{font-size:1.4rem}}
"""

if __name__ == "__main__":
    main()
