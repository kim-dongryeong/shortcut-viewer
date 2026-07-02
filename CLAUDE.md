# Shortcut Viewer — project guide for agents

A unified **macOS** keyboard-shortcut viewer: aggregates shortcuts from every source (macOS system,
app menus, VS Code/Obsidian keymaps, Karabiner, BetterTouchTool, Raycast, manual globals) onto one
interactive **keyboard-grid** HTML viewer with conflict + free-combo finding. MIT, open source.

## Architecture / data flow

```
collectors (build.py + axmenudump) → shortcuts.json → viewer.html  (from viewer.template.html)
```
- `build.py` — collects + normalizes every source into the canonical entry schema (`mods,key,action,source,scope,detail,group`), then renders the viewer.
- `axmenudump.swift` → `axmenudump` (compiled binary) — reads running apps' menu shortcuts via the Accessibility API.
- `viewer.template.html` — the interactive grid UI; data is injected at the `/*__DATA__*/` marker.
- `render.py` — re-renders `viewer.html` from the existing `shortcuts.json` only (no scan).
- **Final normalize pass** (build.py, after `collect_community()`): NSEvent PUA chars (``대 = arrows/F-keys from AX `cmdChar`) + glyphs (`⎋↖↘⇞⇟`) → canonical key names; shifted symbols (`+<>?"{`…) → base key + `shift` mod; exact-dup removal. This is the ONLY point covering all sources (menu-reuse & community packs bypass `add()`). `normalize_packs.py` applies the same tables (keep in sync) to the tracked `defaults/` packs — order-preserving, idempotent.
- `refresh.sh` — (re)compile axmenudump + run build.py (full scan). `dump_vscode.sh` — export VS Code default keybindings. `dump_codex.sh` — extract Codex in-app shortcuts from its app.asar.

## ⚠️ The build-vs-render rule (most important)

- **UI / template change → `python3 render.py`.** Pure render from existing data; no scan, no Accessibility needed. An agent can run this anytime — it never touches scan data.
- **Collector / data change → the USER runs `./refresh.sh`** from a terminal that has **Accessibility** (System Settings ▸ Privacy & Security ▸ Accessibility). The app-menu scan needs it. An agent's shell lacks Accessibility → the menu scan returns 0; `collect_menus()` then *reuses* the previous scan's `app menu` entries from `shortcuts.json` so they aren't wiped — but you still won't get a *fresh* scan. **Prefer `render.py`; ask the user to run `refresh.sh` for a real re-scan.**

## 🔒 Never commit personal data

These are gitignored and hold the user's ACTUAL shortcuts — never `git add -f` them:
`shortcuts.json`, `viewer.html`, `vscode_default_keybindings.json`, `codex_keybindings.json`, `raycast_manual.json`, `manual_globals.json`, `axmenudump`.
Only source files + `*.example.json` + `screenshot.png` are tracked.

**Exception — `defaults/` IS committed.** `defaults/<app>/<version>.json` is the shared default-keybinding corpus (app **defaults** only — VS Code's `default` export, Codex's compiled `defaultKeybindings` — no PII).

**Cross-machine sharing.** Scan on a Mac that has more apps, share the *app's own* shortcuts (not your BTT/Raycast config) via the tracked `defaults/` corpus + git: `share_menus.py "<App>" …` promotes that app's **menu-bar** shortcuts into `defaults/<app>/menu-<ver>.json` — but **drops the system "Apple ▸" menu** (which holds `Log Out <your name>`) and scrubs name/username/home (aborts if any PII survives). `collect_community()` (runs last in build.py) seeds those `menu-*.json` packs for apps NOT scanned locally (marked `공유 · 타 기기`), so you see another machine's app shortcuts without installing the app. Raw `shortcuts.json` (the menu scan) is gitignored because it contains the Apple-menu name; only the scrubbed `defaults/` packs are shared. A scan with the app installed *saves* its defaults there; a machine without it *seeds* from the newest version (entries marked `· seed`). `meta.env` records OS/app versions + locale per scan (no host/user/serial). Never put user customizations there. See `defaults/README.md`.

## Verifying viewer changes (don't rely on the user to eyeball)

```sh
python3 render.py
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1480,900 \
  --force-device-scale-factor=2 --virtual-time-budget=2500 \
  --screenshot=/tmp/shot.png "file://$PWD/viewer.html"
```
Read the PNG to confirm. To screenshot a specific state, `sed`-replace the defaults in a copy (e.g. `selectedKey=null;`→`selectedKey='F9';`, `ctxSet=new Set(['Global'])`→`...(['Code'])`, `let sticky=new Set()`→`...(['cmd'])`).

## Data-source facts (already reverse-engineered — don't re-derive)

- **BTT 6.x** = Core Data SQLite at `~/Library/Application Support/BetterTouchTool/btt_data_store.version_*` (+`-wal`/`-shm`). Keyboard shortcuts read **directly, no socket server**. `ZMODIFIERKEYS` = standard NSEvent mask (cmd `0x100000`, opt `0x80000`, ctrl `0x40000`, shift `0x20000`, fn `0x800000`). App-scoping is via the **`Z_2APPS_GESTURES` junction** (NOT `ZBELONGSTOAPP`; `BT.*` bundles = global). Preset name = `ZNAME3` of the entity at `ZBELONGSTOPRESET2` (`ZACTIVATED>0` = active). The real action lives in **child rows** (`ZPARENT`=trigger); the child `ZACTION` = `BTTPredefinedActionType` (map in `BTT_ACTIONS`); the trigger row's own `ZACTION` is generic (366). Full param labels (window coords) are in `ZACTIONDATA` bplist blobs — not reconstructed.
- **macOS Function flag**: NSEvent sets bit `0x800000` intrinsically on F-keys / arrows / nav keys — it does NOT mean the Globe key was pressed. Strip `fn` from those (`FN_INTRINSIC`); keep `fn` only for real 🌐+letter combos.
- **VS Code**: defaults aren't a file — export via `dump_vscode.sh` (osascript) or `keybindings.json`. `when` clauses are captured into `detail`. **Chords** (`cmd+k cmd+i`): 1st press lives on the grid; 2nd press stored per-entry as `cmods`/`ckey` and rendered as a "▸" leader menu + which-key mode. 3+ presses get a `(그다음 …)` action marker (only the 2nd is structured).
- **Codex** (OpenAI desktop, Electron `Codex.app`): in-app shortcuts (Settings ▸ Keyboard Shortcuts) are **not in the menu bar**, so the AX scan misses them. Defaults are compiled into `Contents/Resources/app.asar` as `{id, electron:{menuTitle}, defaultKeybindings:[{key:CmdOrCtrl+…}]}`; **multiple keys in the array = ALTERNATIVE bindings, not a chord**. `dump_codex.sh` greps the asar → `codex_keybindings.json` (gitignored); `collect_codex()` maps Electron accelerators (`CmdOrCtrl`=⌘, `Alt`=⌥) → schema, source `app config`, scope `Codex`. Menu-bar Codex items still come from the AX scan separately (a few overlap). Its leveldb localStorage is Snappy-compressed (no plain-text keymap).
- **Non-static triggers (gestures)**: tap-count / hold / L-R modifier triggers have NO regular key, so they can't live on the grid — they're a separate `gestures[]` list (schema `mod,side,count,hold,action,source,scope`) shown in the `#gestures` panel (`⌘⌘`, `⌘ hold (L)`, `⇪×3 hold`…). **Codex Appshots** is reverse-engineered from `app.asar`: `var y3=`DoubleCommand`` is the default for stored key `appshotHotkey` (options ⌘⌘/⌥⌥/⇧⇧/off, macOS-only, cmd id `capture-appshot`) → double-tap ⌘. Codex also has `globalDictationHold`/`globalDictationToggle`/`hotkeyWindow` (user-configured, no default). User's own cross-app gestures (KeyClu cmd-hold, AutoHotKey CapsLock multi-tap, …) go in `manual_gestures.json` (gitignored; `*.example.json` tracked).
- **Adobe full keymaps** (extractors: `dump_premiere.py` `dump_photoshop.py` `dump_illustrator.py` `dump_ae.py`; run on the Adobe Mac, or pass a copied file + version as args). Formats (already reverse-engineered):
  - **Photoshop** `Locales/en_US/…/Shortcuts/Mac/Default Keyboard Shortcuts.kys` = XML `<command name>` + 1..n `<shortcut>Opt+Cmd+V</shortcut>` (multiple = ALTERNATIVES). `<tool>`/`<taskspace-tool>` carry NO key data (FourCC ids) — PS tool defaults (V/M/B…) need Edit ▸ Keyboard Shortcuts ▸ Summarize export.
  - **Illustrator** `Presets.localized/en_US/Keyboard Shortcuts/Illustrator Defaults.kys` = PostScript-style text `/cmd { /Context /Modifiers /Represent /Key }` in `/Menus{}` + `/Tools{}`. Modifier mask: shift 32 · cmd 64 · opt 128. Key: 0=unassigned, 9=Tab, 14–25=F1–F12 (`F(n-13)`), ≥32=ASCII physical key; `/Represent` = display char (e.g. shows '+' for the '=' key). Trailing digit on ids (`paste2`) = alternative binding.
  - **After Effects**: no bundle file; AE writes the Default set to prefs `…/After Effects/<ver>/aeks/After Effects Default.txt`. Self-documented text: `["Context"] "Cmd" = "(combo)(combo2)"` — each `()` = alternative, `()` empty = unbound, `macControl`=ctrl, `"\`+newline+`"` splices strings, `Pad*`=keypad, `UxFFFF`=codepoint. Skip `TextIgnoreKey`/`NOP`. Same command repeats per context → merge, contexts into detail.
- **Web apps (Google Sheets/Docs/Drive…)**: no local source (shortcuts live in the page's JS). Pulled from the vendor's **OFFICIAL** shortcut docs (authoritative, not guessed) into `web_shortcuts.json` (**tracked** public reference, no PII — like `defaults/`). `collect_web()` parses the `⌘⌥⌃⇧`/`Fn` symbol notation → source `web` (cyan), scope = app name. Multi-step sequences and `A or B` / `↑/↓` alternatives keep the full string in `detail` and use the first key for grid placement. To update, re-fetch the vendor doc.
- **Raycast**: local DB is encrypted → unreadable; user lists hotkeys in `raycast_manual.json`. App-registered OS-global hotkeys (e.g. Google Drive `hyper+g`) go in `manual_globals.json`.
- **symbolichotkeys**: only stores *customized* combos; common macOS defaults are seeded in `build.py`'s `DEFAULTS`.

## Toolchain & style

macOS (Apple Silicon, 14+), `swift` (Xcode CLT), system `/usr/bin/python3`, `jq`. No external Python deps.
Match the existing compact style in `build.py` / `viewer.template.html`. License: MIT.
