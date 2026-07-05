# Changelog

All notable changes to **Shortcut Viewer** are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning is [SemVer](https://semver.org/).

## [1.0.0] — first public release

The first open-source release. A unified **macOS** keyboard-shortcut viewer: it aggregates shortcuts from
*every* source on your machine onto one interactive **keyboard grid**, finds conflicts and free combos, and
can set real global hotkeys — plus a public, searchable cheat-sheet site for each app's default shortcuts.

### Viewer
- **One keyboard grid** for every shortcut, color-coded by source; toggle a modifier layer (⌃⌥⇧⌘ / Hyper /
  Meh / 🌐fn) or physically hold the keys and the grid switches live.
- Click/press any key → all **16 modifier combos** for it, taken *and* free.
- **Conflict finder** with three classes — real (same scope), global-intercept, context-branch (`when`/app).
- **Free-combo finder**, per-app context filtering (multi-select), BTT-preset depth.
- Views: ⚠️ Conflicts · ✨ Free combos · 📊 Stats · 🎓 Quiz · 🩺 **Health/diagnostic** · 🖨 Print/PDF ·
  ⤓ CSV/MD export · ☾ theme · URL deep-links · ＋ My Shortcuts.
- The viewer is a self-contained local `viewer.html` — opens in any browser, offline, no server.

### Sources it reads
- macOS system (`com.apple.symbolichotkeys` + curated defaults), running-app menu bars (Accessibility API),
  VS Code & Obsidian keymaps, Adobe keymaps (Photoshop/Illustrator/After Effects/Premiere),
  Karabiner-Elements, BetterTouchTool (its Core Data store directly — per preset + app scope), Raycast,
  manual globals & gestures.

### Global hotkeys — **SV Hotkeys**
- Native menu-bar app: record a conflict-aware combo and bind it (open app/URL/folder/file, run shell,
  AppleScript, paste text, show viewer). Carbon `RegisterEventHotKey` for ⌘/⌥/⌃ (no permission); optional
  `CGEventTap` for anyCombo / CapsLock / left-right-specific / gesture triggers.
- `./install_hotkeys.sh` builds & installs it (universal binary, auto-start at login).

### Public cheat sheets (SEO site)
- `gen_seo.py` builds a static, searchable site into `docs/` — one page per app
  (*"`<App>` keyboard shortcuts for Mac"*), an index, `sitemap.xml`, `robots.txt`. **15 apps · 4,318 default
  shortcuts.** Built only from the shareable, PII-free corpus (`defaults/` + `web_shortcuts.json`).
- Serve it with **GitHub Pages ▸ `main` ▸ `/docs`**.

### Privacy
- Personal scan output (`shortcuts.json`, `viewer.html`, your BTT/Raycast/Karabiner config) is **gitignored
  and never leaves your machine**. Only the app-defaults corpus (`defaults/`) and web docs (`web_shortcuts.json`)
  are shared — scrubbed of names/usernames/home paths.

### License
- **GPL-3.0-or-later.** Free to use, modify, and redistribute; derivatives must stay open.

[1.0.0]: https://github.com/kim-dongryeong/shortcut-viewer/releases/tag/v1.0.0
