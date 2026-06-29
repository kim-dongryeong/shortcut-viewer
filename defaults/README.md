# `defaults/` — versioned default-keybinding corpus

App **default** keyboard shortcuts (NOT user customizations, no personal data), keyed by
`defaults/<app>/<version>.json`. This directory **is committed** — it's the shareable open dataset.

How it's used (see `collect_vscode` / `collect_codex` in `build.py`):

- A scan **with** the app installed **saves** its programmatically-extracted defaults here →
  the DB grows by app + version as people scan.
- A machine **without** the app **seeds** from the newest version found here, so the viewer still
  shows that app's shortcuts (those entries get a `· seed` marker in `detail`).

## Format

```json
{ "app": "VS Code", "version": "1.126.0", "scope": "Code",
  "entries": [ { "mods": ["cmd"], "key": "P", "action": "...", "source": "app config",
                 "scope": "Code", "detail": "vscode default · cmd+p", "group": "app config" } ] }
```
`entries` are the canonical viewer schema, so seeding is a direct pass-through.

## Privacy — what belongs here

ONLY programmatically-extracted **app defaults**: VS Code's built-in defaults (the `default` export,
never the user's `keybindings.json`), Codex's compiled `defaultKeybindings`, etc. These are the same
for everyone on a given version and contain no PII.

**Never** add user customizations (BetterTouchTool, Karabiner, Obsidian custom hotkeys,
`manual_globals.json`, customized `symbolichotkeys`) or machine identity — those stay local and
gitignored. The point of the split is that this folder is safe to share; the rest is not.
