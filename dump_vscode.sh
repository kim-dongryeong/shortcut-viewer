#!/bin/zsh
# dump_vscode.sh — export VS Code's full default keybindings (~550) without you navigating menus.
# Run this from YOUR Terminal (so macOS can ask to grant it Accessibility once):
#     ~/shortcut-viewer/dump_vscode.sh
# First run macOS will prompt "Terminal wants to control System Events / Visual Studio Code" → Allow,
# then run it again. It drives VS Code for ~4s; don't touch the keyboard while it runs.
cd "${0:A:h}" || exit 1
out="vscode_default_keybindings.json"

osascript \
 -e 'tell application "Visual Studio Code" to activate' \
 -e 'delay 0.9' \
 -e 'tell application "System Events"' \
 -e 'keystroke "p" using {command down, shift down}' \
 -e 'delay 0.6' \
 -e 'keystroke "Default Keyboard Shortcuts (JSON)"' \
 -e 'delay 0.9' \
 -e 'key code 36' \
 -e 'delay 1.5' \
 -e 'keystroke "a" using {command down}' \
 -e 'delay 0.3' \
 -e 'keystroke "c" using {command down}' \
 -e 'end tell' || { echo "osascript failed — grant this terminal Accessibility (System Settings ▸ Privacy & Security ▸ Accessibility) and retry."; exit 1; }

pbpaste > "$out"
if grep -q '"command"' "$out"; then
  echo "OK: wrote $out ($(grep -c '"command"' "$out") bindings). Now run: ./refresh.sh"
else
  echo "Clipboard didn't contain keybindings. Make sure VS Code is running and retry; or export manually."
  exit 1
fi
