# Changelog

All notable changes to **Shortcut Viewer** are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning is [SemVer](https://semver.org/).

## [Unreleased]

### Viewer
- **Keyboard layout presets** — pick the keyboard you actually have; blocks it doesn't have disappear from
  the grid *and* the free-combo finder: MacBook built-in · Mac full-size (numpad) · Logitech tenkeyless
  (Insert + right ⌃) · generic tenkeyless (adds PrtSc·ScrLk·Pause) · **custom** (toggle each block:
  F13–F20 · ⌦/Home/End/PgUp/PgDn · numpad · Insert · PrtSc·ScrLk·Pause · right ⌃).
  Replaces the single 🔢 numpad toggle; the old setting migrates automatically.
- **Numpad matches the real Apple layout** — `KeypadEnter` (⌤) is now the tall two-row key at the
  bottom-right (was a stray single key beside `3`), so Karabiner shortcuts bound to it have a home.
- When **numpad + F13–F20 are both shown**, F13–F20 spread into one row (F13–F15 above the nav cluster,
  F16–F19 above the numpad) instead of a 4×2 block — matching Apple's full-size Magic Keyboard with Numeric
  Keypad, which has **F1–F19**. F20 has no Apple key (macOS/Karabiner-only) so it sits just past the numpad's edge.
- **Nav/PrtSc keys align to a clean grid** — Insert · ⌦ · Home/End · PgUp/PgDn · PrtSc/ScrLk/Pause now take the
  same standard width as the arrow keys, *except* under the 4-wide F13–F20 two-row block (numpad off), where
  they stay slightly wider to fill it.
- **Right cluster aligns to the real keyboard rows** — the nav/arrow/numpad clusters now sit at the exact
  vertical rows of a physical board: PrtSc·F13–F20 on the function row, Home/PgUp on the Backspace row,
  End/PgDn on the `\` row, the numpad directly under the F-keys, and the arrows pinned to the bottom two rows
  (as on a MacBook). Applies to every preset — full-size, both tenkeyless, and custom.

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
