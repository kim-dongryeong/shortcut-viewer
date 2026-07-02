# SV Hotkeys — 글로벌 단축키 직접 설정하기

Shortcut Viewer는 이제 **단축키를 보여주기만** 하지 않고, **직접 글로벌 단축키를 설정**할 수 있습니다.
당신이 원하는 키 조합(예: `⌥F`)을 누르면 **어느 앱에 있든** 앱을 열거나, 명령을 실행하거나, 텍스트를 붙여넣습니다.

## 왜 Shortcut Viewer가 이걸 해야 잘 맞나 (시너지)

새 단축키를 만들 때 제일 어려운 건 **"이 조합이 이미 어디서 쓰이나?"** 입니다.
Shortcut Viewer는 이미 당신 맥의 **모든 소스**(시스템·앱 메뉴·VS Code·Adobe·BTT·Raycast…)의 단축키를 압니다.
그래서 다른 도구는 못 하는 걸 합니다:

> **✨ 충돌 없는 빈 조합을 찾아서 → 바로 그 자리에 글로벌 핫키를 설정** — 한 곳에서.

KeyCue·CheatSheet는 보여주기만, Karabiner·skhd는 설정만 합니다. 우리는 **둘을 잇습니다.**

## 가장 쉬운 시작 (컴퓨터 잘 몰라도 OK)

터미널에서 프로젝트 폴더로 간 뒤 **한 줄**:

```sh
./install_hotkeys.sh
```

끝입니다. 메뉴바에 **⌘ 아이콘**이 뜨고, 예제 핫키 15개가 바로 동작합니다(로그인 시 자동 실행).
- `⌥Space` → 단축키 뷰어 열기 · `⌥F` → Finder · `⌥C` → 계산기 · `⌃⌥T` → 터미널 …
- 편집: 메뉴바 아이콘 ▸ **"설정 파일 열기"**, 또는 뷰어의 **🌐 글로벌 핫키** 탭에서 만들어 **내보내기**.
- 제거: `./install_hotkeys.sh uninstall`

> **권한**: `⌘`/`⌥`/`⌃` 가 들어간 조합은 **아무 권한도 필요 없습니다**(Carbon RegisterEventHotKey).
> `⇧Space`처럼 다른 앱도 잡는 조합만 메뉴바 ▸ "any-combo 켜기"(손쉬운 사용 권한)가 필요합니다.

## 4가지 실행 방식 (버전) — 원하는 걸로 테스트하세요

같은 `hotkeys.json` 하나를 **네 가지 백엔드** 중 아무거나로 실행할 수 있습니다. 뷰어의 🌐 글로벌 핫키 탭에서 네 설정을 모두 미리 보고 고르세요.

| 방식 | 설치 | 권한 | 추천 대상 |
|---|---|---|---|
| **① 네이티브 데몬 (SV Hotkeys.app)** | `./install_hotkeys.sh` | 불필요(⌘⌥⌃) | **대부분의 사용자** — 아무것도 안 깔아도 됨 |
| ② Karabiner-Elements | 이미 쓰면 `gen_hotkeys.py` → 규칙 추가 | 자체 권한 | Karabiner 사용자 |
| ③ skhd | `brew install skhd` → `skhdrc.sv` 추가 | 없음 | 타일링/터미널 유저 |
| ④ Hammerspoon | 이미 쓰면 `init.lua`에 추가 | 자체 | Lua 스크립터 |

②③④ 설정 생성:
```sh
python3 gen_hotkeys.py            # hotkeys.json → karabiner-sv.json · skhdrc.sv · hammerspoon-sv.lua
```

## 동작 종류 (action types)

| type | 하는 일 | 값(value) 예시 |
|---|---|---|
| `open_app` | 앱 실행/전환 | `Finder` · `Calculator` · `com.google.Chrome`(번들 id) · `/Applications/…app` |
| `open_url` | 웹사이트 열기 | `https://chatgpt.com` |
| `open_folder` | 폴더 열기 | `~/Downloads` |
| `open_file` | 파일 열기 | `~/Documents/todo.md` |
| `run_shell` | zsh 명령 실행 | `screencapture -i -c` |
| `applescript` | AppleScript | `tell application "Spotify" to playpause` |
| `paste_text` | 텍스트 붙여넣기(클립보드+⌘V) | `me@example.com` |
| `show_viewer` | 이 단축키 뷰어 열기 | (비움) |

## 사용 시나리오 15+ (그대로 쓰거나 참고)

각 항목은 `hotkeys.json`의 한 줄입니다. 뷰어 🌐 글로벌 핫키 탭에서 클릭 몇 번으로 만들거나, `hotkeys.example.json`을 복사해 시작하세요.

### 🗂 일상 — 앱·폴더 빠르게 열기
1. **`⌥Space` → 내 단축키 전체 보기** (`show_viewer`) — 뭘 눌러야 할지 까먹었을 때. 우리 앱 자체를 핫키로.
2. **`⌥F` → Finder 열기** (`open_app: Finder`) — 파일 탐색 즉시.
3. **`⌥C` → 계산기** (`open_app: Calculator`).
4. **`⌃⌥T` → 터미널** (`open_app: Terminal`).
5. **`⌥H` → 홈 폴더** · **`⌥D` → 다운로드 폴더** (`open_folder: ~` / `~/Downloads`) — Finder 안 뒤져도 됨.

### 🌐 웹 — 자주 가는 사이트 한 방에
6. **`⌥G` → Google** (`open_url: https://www.google.com`).
7. **`⌥Return` → ChatGPT** (`open_url: https://chatgpt.com`) — AI 즉시.
8. **`⌃⌥C` → 캘린더 열기** (`open_url: https://calendar.google.com`).

### ⚡ 생산성 — 명령·시스템 제어
9. **`⌃⌥L` → 화면 잠그고 절전** (`run_shell: pmset displaysleepnow`) — 자리 비울 때.
10. **`⌃⌥S` → 영역 스크린샷(클립보드로)** (`run_shell: screencapture -i -c`) — 바로 붙여넣기 가능.
11. **`⌃⌥Delete` → 휴지통 비우기** (`applescript: … empty trash`).
12. **`⌃⌥D` → 다크모드 켜기/끄기** (`applescript: … set dark mode to not dark mode`).
13. **`⌃⌥P` → 음악 재생/일시정지** (`applescript: tell application "Spotify" to playpause`).

### ✍️ 글쓰기 — 반복 텍스트·메모
14. **`⌥E` → 내 이메일 주소 붙여넣기** (`paste_text: me@example.com`) — 폼 채울 때.
15. **`⌥N` → 새 메모** (`applescript: tell application "Notes" to make new note`).
16. **`⌥S` → 자주 쓰는 서명/주소 붙여넣기** (`paste_text: …`) — 원하는 만큼 여러 개.

### 🧑‍💻 개발자 — 프로젝트·도구
17. **`⌃⌥V` → VS Code로 프로젝트 열기** (`run_shell: code ~/dev/shortcut-viewer`).
18. **`⌃⌥G` → GitHub 열기** (`open_url: https://github.com`).
19. **`⌃⌥R` → 특정 스크립트 실행** (`run_shell: ~/bin/deploy.sh`).

> **조합 고르는 팁**: 새 글로벌 핫키는 **`⌥`(옵션)** 또는 **`⌃⌥`** 레이어를 쓰세요 — 시스템·앱과 거의 안 겹칩니다.
> 뷰어의 **✨ 빈 조합** 탭이 그 레이어의 빈 키를 초록으로 보여주고, 🌐 글로벌 핫키 폼은 조합을 고를 때마다 **"완전히 빔 ✅ / 앱에서 사용 ⚠️ / 시스템 충돌 ⚠️"** 를 즉시 알려줍니다.

## 설정 파일 형식 (`~/.config/shortcut-viewer/hotkeys.json`)

```json
{
  "version": 1,
  "hotkeys": [
    {"title":"Finder 열기", "mods":["opt"], "key":"F",
     "action":{"type":"open_app","value":"Finder"}, "enabled":true, "anyCombo":false}
  ]
}
```
- `mods`: `cmd` `opt` `ctrl` `shift` 중 0개 이상
- `key`: 뷰어와 같은 이름 — `A`~`Z` · `0`~`9` · `Space` `Return` `Tab` `Escape` `Delete` · `Left`/`Right`/`Up`/`Down` · `Home`/`End`/`PageUp`/`PageDown` · `F1`~`F20` · 기호 `- = [ ] \ ; ' , . / ``
- `anyCombo`: `true`면 다른 앱도 잡는 조합까지 가로챔(손쉬운 사용 권한 필요)
- `enabled`: `false`면 잠시 끔

데몬은 이 파일이 **바뀌면 자동으로 다시 읽습니다** — 뷰어에서 내보내고 저장하면 즉시 반영.

## 안전 / 프라이버시

- `hotkeys.json`·생성된 `karabiner-sv.json`/`skhdrc.sv`/`hammerspoon-sv.lua`는 **당신의 실제 핫키·홈 경로**를 담아 **git에 안 올라갑니다**(`.gitignore`). 공유되는 건 `hotkeys.example.json`뿐.
- 네이티브 데몬은 네트워크·수집 없음, 순수 로컬. `⌘⌥⌃` 조합은 권한 0.
- 코드: `hotkeys/svhotkeys.swift` (단일 파일, universal 빌드). 핫키 메커니즘은 `~/dev/maverything`에서 검증된 Carbon/EventTap 방식.
