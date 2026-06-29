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
- `refresh.sh` — (re)compile axmenudump + run build.py (full scan). `dump_vscode.sh` — export VS Code default keybindings.

## ⚠️ The build-vs-render rule (most important)

- **UI / template change → `python3 render.py`.** Pure render from existing data; no scan, no Accessibility needed. An agent can run this anytime — it never touches scan data.
- **Collector / data change → the USER runs `./refresh.sh`** from a terminal that has **Accessibility** (System Settings ▸ Privacy & Security ▸ Accessibility). The app-menu scan needs it. An agent's shell lacks Accessibility → the menu scan returns 0; `collect_menus()` then *reuses* the previous scan's `app menu` entries from `shortcuts.json` so they aren't wiped — but you still won't get a *fresh* scan. **Prefer `render.py`; ask the user to run `refresh.sh` for a real re-scan.**

## 🔒 Never commit personal data

These are gitignored and hold the user's ACTUAL shortcuts — never `git add -f` them:
`shortcuts.json`, `viewer.html`, `vscode_default_keybindings.json`, `raycast_manual.json`, `manual_globals.json`, `axmenudump`.
Only source files + `*.example.json` + `screenshot.png` are tracked.

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
- **VS Code**: defaults aren't a file — export via `dump_vscode.sh` (osascript) or `keybindings.json`. `when` clauses are captured into `detail`.
- **Raycast**: local DB is encrypted → unreadable; user lists hotkeys in `raycast_manual.json`. App-registered OS-global hotkeys (e.g. Google Drive `hyper+g`) go in `manual_globals.json`.
- **symbolichotkeys**: only stores *customized* combos; common macOS defaults are seeded in `build.py`'s `DEFAULTS`.

## Toolchain & style

macOS (Apple Silicon, 14+), `swift` (Xcode CLT), system `/usr/bin/python3`, `jq`. No external Python deps.
Match the existing compact style in `build.py` / `viewer.template.html`. License: MIT.
