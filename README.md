# Shortcut Viewer

**A unified keyboard-shortcut viewer for macOS and Windows.** See every shortcut from *every* source
— system shortcuts, each app's menu bar, app keymaps (VS Code, Adobe, Obsidian), Karabiner-Elements /
PowerToys, BetterTouchTool (per preset), Raycast — laid out on one interactive **keyboard grid**. Pick a
modifier layer (or just hold the keys) and every key lights up with what it's bound to, color-coded
by source. Find conflicts, and find the **free** combos. Even for apps you don't have installed, it
ships with **thousands of pre-collected default shortcuts** (VS Code, Adobe, Office, and more).

![Shortcut Viewer](screenshot.png)

> **🔎 Just want the shortcuts? No install.** Browse searchable cheat sheets for 20+ apps in any browser →
> **[kim-dongryeong.github.io/shortcut-viewer](https://kim-dongryeong.github.io/shortcut-viewer/)**
>
> **🖥 Want the full tool?** It scans *your own* machine and merges every source onto one grid, on top
> of the thousands of shortcuts it already ships with — [download below ↓](#download--install).

## Why

Every other tool shows you a slice:

- **Cheat-sheet viewers** (CheatSheet, KeyCue, KeyClu, KeyMinder) show only the **current app's menu** shortcuts.
- **Conflict detectors** (HotkeyClash) scan system + Karabiner + running apps, but miss BTT / Raycast / IDE keymaps and aren't a keyboard grid.
- **Learning tools** (KeyCombiner) use manual collections, not your live config.

Shortcut Viewer is the only one that **aggregates your whole machine, across all sources, onto one
keyboard grid** — with conflict + free-combo finding, per-app context filtering, and BTT-preset depth.

## Sources it reads

| Source | How |
|---|---|
| macOS system | `com.apple.symbolichotkeys` + curated defaults (Spotlight, screenshots, Mission Control, ⌃⌘D lookup, fn/Globe…) |
| App menus | Accessibility API menu-bar scan of every running app |
| VS Code | `keybindings.json` + exported default keymap (incl. `when` clauses) |
| Obsidian | per-vault `.obsidian/hotkeys.json` |
| Karabiner-Elements | `~/.config/karabiner/karabiner.json` |
| BetterTouchTool | its Core Data SQLite store directly — no socket server (incl. preset + app scope + action name) |
| Raycast | `raycast_manual.json` (its DB is encrypted) |
| Manual globals | `manual_globals.json` (app-registered global hotkeys, e.g. Google Drive) |

## Download & install

### Option A — download & run (no terminal, no git)

- **Mac**: build `packaging/mac/build_dmg.sh` yourself (see below) → **Shortcut Viewer.dmg** → drag
  to Applications → double-click. First launch: unsigned (v1, no Apple Developer account yet), so
  Gatekeeper says "unidentified developer" — right-click ▸ Open once to allow it.
- **Windows**: build `packaging\win\build_exe.bat` on a Windows machine → **ShortcutViewer.exe** →
  double-click. Unsigned too — SmartScreen says "Windows protected your PC" → More info ▸ Run anyway.

Either way, on first launch it already shows **thousands of pre-collected default shortcuts** (VS
Code, Adobe, Office, and more — no scanning needed), then merges in whatever it can read from *your*
machine (installed apps, BetterTouchTool, Karabiner/PowerToys, …) on top. Re-launch anytime to rescan.

We don't publish pre-built binaries yet (this is a fresh, unsigned v1) — build your own from source
with the scripts above; see [`packaging/mac/`](packaging/mac/) and [`packaging/win/`](packaging/win/).

### Option B — install from source (power users, or to re-scan without a rebuild)

Prerequisites: **macOS 14+**, Xcode command-line tools (`swift`), **Python 3**, and **`jq`**.

```sh
xcode-select --install     # once, if you don't have swift
brew install jq            # once, if you don't have jq
git clone https://github.com/kim-dongryeong/shortcut-viewer.git
cd shortcut-viewer
./refresh.sh               # scan every source → shortcuts.json → viewer.html
open viewer.html           # opens the grid in your default browser
```

- The **viewer** is a local `viewer.html` file — it opens in **any browser** (Safari/Chrome/Firefox),
  works **offline**, no server, printable to PDF. It's a self-contained local web app, not a website.
- `refresh.sh` re-scans everything (grant your terminal **Accessibility** for the app-menu scan — see below).
- `render.py` only re-renders the viewer from existing `shortcuts.json` (no re-scan) — for UI tweaks.
- **Global hotkeys** (optional, native): `./install_hotkeys.sh` builds & installs **SV Hotkeys.app**
  (menu-bar app, auto-starts at login; no Accessibility needed for ⌘/⌥/⌃ combos).
- **Windows**: same idea, `win/build_win.py` — see [`win/README.md`](win/README.md).

### One-time setup for full coverage

1. **App menus** — grant your terminal **Accessibility** (System Settings ▸ Privacy & Security ▸ Accessibility), then run `./refresh.sh` from it.
2. **VS Code** — run `./dump_vscode.sh` once (drives VS Code to export its default keybindings), or in VS Code: ⇧⌘P → *Open Default Keyboard Shortcuts (JSON)* → save as `vscode_default_keybindings.json`.
3. **Raycast / global app hotkeys** — `cp raycast_manual.example.json raycast_manual.json` and `cp manual_globals.example.json manual_globals.json`, then edit.

## Using the viewer

- Toggle modifier chips (⌃⌥⇧⌘ / Hyper / Meh / 🌐fn) **or physically hold** the keys → the grid switches layer live.
- Each key shows a count + source-colored dots even on the base layer (which keys are "busy").
- Click a key (or press it) → see **all 16 modifier combos** for it, taken *and* free.
- Context chips filter by app (multi-select), plus `BTT (all)` and per-preset.
- 📋 list view, search by action/key/combo, and a "free combos only" filter.
- **⚠️ Conflicts · ✨ Free combos · 📊 Stats · 🎓 Quiz · 🖨 Print/PDF · ⤓ CSV/MD · ☾ theme · URL deep-links · ＋ My Shortcuts** — competitor-parity views (KeyCue/KeyClu/CheatSheet/KeyCombiner).

## Set global hotkeys (SV Hotkeys) 🌐

Shortcut Viewer doesn't just *show* shortcuts — it can **set real global hotkeys**. Because it already
knows every shortcut from every source, it uniquely lets you **find a conflict-free combo and bind it in one place**
(open an app, run a command, paste text — from anywhere).

The product is our **own** app — **SV Hotkeys** (a native menu-bar app with a visual editor:
record a combo, pick an app, conflict-aware) plus the viewer's **🌐 글로벌 핫키** builder. No third-party tool required:

```sh
./install_hotkeys.sh          # build + install SV Hotkeys.app, auto-start at login (no Accessibility for ⌘/⌥/⌃)
```

*(Optional)* if you already run **Karabiner / skhd / Hammerspoon**, `python3 gen_hotkeys.py` exports the same
`hotkeys.json` to those tools too — a convenience, not a dependency.

Full guide + 15+ ready-to-use scenarios: **[HOTKEYS.md](HOTKEYS.md)**. Hotkey mechanism adapted from `~/dev/maverything` (Carbon `RegisterEventHotKey` + `CGEventTap`).

## How it works

```
collectors (build.py + axmenudump.swift)  →  shortcuts.json  →  viewer.html
                                                              (viewer.template.html)
```

- **`build.py`** — collects + normalizes every source into one canonical schema, then renders the viewer.
- **`axmenudump.swift`** — reads running apps' menu shortcuts via the Accessibility API (`swiftc axmenudump.swift -o axmenudump`; `refresh.sh` builds it for you).
- **`viewer.template.html`** — the interactive keyboard-grid UI; data is injected at the `/*__DATA__*/` marker.

## Public cheat sheets (web)

Beyond the personal viewer, `python3 gen_seo.py` generates a **static, SEO-friendly site** into `docs/`
— one searchable page per app (*"`<App>` keyboard shortcuts for Mac"*) plus an index, `sitemap.xml`, and
`robots.txt`. It's built **only** from the shareable, PII-free corpus (`defaults/` + `web_shortcuts.json`,
never your personal scan), so it's safe to publish. Enable **GitHub Pages ▸ `main` ▸ `/docs`** to serve it.

## Limitations (honest)

- **No tool can enumerate every global hotkey** on macOS — third-party apps' `RegisterEventHotKey` registrations aren't exposed by any public API. We read every source we *can*; the rest go in the manual files.
- **Raycast** encrypts its local DB → manual entry only.
- **App menus** are read only for *running* apps (an Accessibility limitation).
- **BTT action labels** — the base action name is read from the DB; full parameter labels (window coordinates, etc.) live in binary-plist blobs and aren't fully reconstructed.
- The macOS NSEvent *Function* flag is set intrinsically on F-keys/arrows/nav keys; those are shown without `fn` (only real 🌐+letter combos keep `fn`).

## License

GPL-3.0-or-later © 2026 KDR

> 무료·오픈으로 배포하되 누가 닫아서(비공개) 상품으로 팔지 못하게 copyleft(GPL-3.0)를 택했습니다. 자유롭게 쓰고·고치고·배포할 수 있으나, 배포하는 파생물은 소스를 함께 공개해야 합니다.
