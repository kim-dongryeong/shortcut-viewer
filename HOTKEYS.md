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
- **편집은 앱 안에서** (JSON 몰라도 됨): 메뉴바 아이콘 ▸ **"핫키 편집기 열기"** → 목록에서 추가/삭제/켜기·끄기, 새 핫키는 **조합 필드를 클릭하고 실제로 눌러서 녹화**, 동작은 드롭다운(앱 열기면 **앱 목록에서 선택**). 조합을 녹화하면 **"✅ 완전히 빈 조합 / ⚠️ 이미 사용 중"** 을 바로 알려주고 **✨빈 키 추천**도 됩니다.
- 제거: `./install_hotkeys.sh uninstall`

> **권한**: `⌘`/`⌥`/`⌃` 가 들어간 조합은 **아무 권한도 필요 없습니다**(Carbon RegisterEventHotKey).
> `⇧Space`처럼 다른 앱도 잡는 조합만 메뉴바 ▸ "any-combo 켜기"(손쉬운 사용 권한)가 필요합니다.

## 우리 앱이 곧 제품 (＋ 선택: 이미 쓰는 도구로도)

**진짜 "글로벌 단축키를 설정하는 프로그램"은 우리 자체 앱 하나입니다** — `SV Hotkeys.app`(네이티브) + 웹 뷰어의 🌐 빌더.
아무것도 안 깔아도 되고, 편집기·충돌검사·빈키추천이 앱 안에 다 있습니다.

그 외 셋(**Karabiner·skhd·Hammerspoon**)은 우리 앱을 **대신하는 게 아니라**, *이미 그 도구를 쓰고 있는 사람*이 원하면
같은 `hotkeys.json`을 그쪽 설정으로도 낼 수 있게 한 **선택 내보내기**입니다. 안 써도 전혀 상관없습니다.

| | 무엇 | 설치 | 대상 |
|---|---|---|---|
| ⭐ **SV Hotkeys (우리 앱)** | 자체 데몬 + GUI 편집기 | `./install_hotkeys.sh` (또는 배포용 `.dmg`) | **모두** |
| (선택) Karabiner로 내보내기 | `hotkeys.json` → 복합수정 규칙 | 이미 Karabiner 사용 시 | Karabiner 유저 |
| (선택) skhd로 내보내기 | → `skhdrc` | 이미 skhd 사용 시 | 타일링 유저 |
| (선택) Hammerspoon으로 내보내기 | → `init.lua` | 이미 HS 사용 시 | Lua 유저 |

선택 내보내기 생성:
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

## 프리셋(레이어) — 상황별로 묶어 켜고 끄기

상황에 따라 다른 단축키 세트를 원할 때가 있습니다. 예를 들어:
- 일반 작업(앱·폴더 열기)은 항상 켜져 있고
- 날짜/시간을 자주 입력하는 시간대는 입력 관련 단축키만 켜고
- 마우스 북마크는 필요할 때만 켜서 쓰기

**프리셋**은 이런 상황별로 핫키를 그룹으로 나누고, **각 그룹을 한 번에 켜고 끌** 수 있게 합니다 — BetterTouchTool의 "마스터 프리셋 + 서브프리셋" 모델을 따릅니다.

### 프리셋의 3가지 종류

| 이름 | 설명 | 기본 상태 | 켤 수 있나 |
|---|---|---|---|
| **마스터** | 항상 켜져 있는 기본 레이어 (프리셋 전환 키가 여기 있음) | ✓ 켜짐 | ❌ 안 됨 |
| **기본 (base)** | 일상 작업용 (앱·폴더·URL 열기) | ✓ 켜짐 | ✅ 가능 |
| **날짜·시간** | 날짜/시간 입력(⌃⌥D) | ✓ 켜짐 | ✅ 가능 |
| **마우스 북마크** | 커서 위치 저장/복원 | ❌ 꺼짐 | ✅ 가능 |

### 프리셋 켜고 끄기 — 두 가지 방식

**1) 토글** — 원하는 프리셋만 켜고 나머지는 유지
```sh
sv_hotkeys preset-toggle datetime    # "날짜·시간" 켜짐 ↔️ 꺼짐
```
메뉴바 HUD: `🎛 프리셋 '날짜·시간 입력' 켜짐`

**2) 라디오 선택** (Activate) — 마스터는 항상 켜두고, 다른 프리셋 하나만 활성화
```sh
sv_hotkeys preset-solo base         # 마스터는 켜두고, 기본(base)만 켜짐 (다른 건 꺼짐)
sv_hotkeys preset-solo datetime     # 마스터는 켜두고, 날짜·시간만 켜짐
```
메뉴바 HUD: `🎛 프리셋 '기본' 선택`

### 프리셋 전환 키 (권장: 마스터 프리셋에만)

당신이 손쉽게 프리셋을 바꾸려면 **전환 단축키 자체도 핫키로 등록**해야 합니다. 이 키들을 "마스터" 프리셋에 두면, 다른 프리셋이 켜져 있어도 언제든 프리셋을 전환할 수 있습니다:

| 단축키 | 동작 | 설정 | 프리셋 |
|---|---|---|---|
| `⌃⌥8` | '기본'을 라디오 선택 | `preset_activate base` | **마스터** |
| `⌃⌥9` | '날짜·시간' 토글 | `preset_toggle datetime` | **마스터** |
| `⌃⌥0` | '마우스 북마크' 토글 | `preset_toggle mousebm` | **마스터** |

> **⚠️ 중요**: 프리셋 전환 키를 "기본" 프리셋에 두면, 그 프리셋이 꺼졌을 때 전환할 수 없습니다. 항상 켜진 **마스터** 프리셋에만 두세요.

### 설정 파일 v2 예시

프리셋 정보는 이제 `hotkeys.json`에 포함됩니다:

```json
{
  "version": 2,
  "presets": {
    "master":   {"title": "마스터 — 항상 켜짐 (프리셋 전환 키)", "always_on": true},
    "base":     {"title": "기본 (앱·폴더·URL)", "enabled": true},
    "datetime": {"title": "날짜·시간 입력", "enabled": true},
    "mousebm":  {"title": "마우스 북마크", "enabled": false}
  },
  "hotkeys": [
    {"title":"Finder 열기", "mods":["opt"], "key":"F", "preset":"base",
     "action":{"type":"open_app","value":"Finder"}, "enabled":true},
    {"title":"기본으로 전환", "mods":["ctrl","opt"], "key":"8", "preset":"master",
     "action":{"type":"preset_activate","value":"base"}, "enabled":true}
  ]
}
```

각 핫키는 이제 `"preset": "프리셋id"`를 가집니다(기본값: `"base"`). 프리셋이 꺼져 있으면 그 안의 핫키는 등록되지 않습니다.

> **구 버전 호환성**: 예전 `hotkeys.json`(프리셋 없음)을 열면 자동으로 모든 핫키가 `"preset":"base"`로 변환되고 v2로 저장됩니다. 걱정 없이 업그레이드하세요.

## 날짜·시간 입력 (⌃⌥D 리더)

매일 입력하는 **날짜**나 **시간**을 단축키 한 번에 붙여넣을 수 있습니다. 일정 앱·이메일·일기 등에서 유용합니다.

### 기본 포맷 (⌃⌥D → 다음 키)

`⌃⌥D`를 누른 후, **화면 중앙 HUD에서 원하는 포맷을 선택**하거나 다음 키를 누르면 자동 입력됩니다:

| 다음 키 | 포맷 | 예시 |
|---|---|---|
| `D` | `yyMMdd` | `260721` |
| `I` | `yyyy-MM-dd` | `2026-07-21` (ISO 표준) |
| `.` | `yyyy.MM.dd` | `2026.07.21` |
| `K` | `yyyy년 M월 d일` | `2026년 7월 21일` (한국식) |
| `T` | `HH:mm` | `14:35` (시:분) |
| `S` | `HH:mm:ss` | `14:35:42` (시:분:초) |
| `F` | `yyyy-MM-dd HH:mm` | `2026-07-21 14:35` (전체) |

화면에는 각 선택지가 HUD로 표시됩니다 — which-key 방식으로 `⌃⌥D`를 누르고 원하는 포맷 글자를 누르면 해당 형식으로 현재 시각이 입력됩니다.

> 이 기능은 **frogcontrol**(AutoHotkey 자동화 도구)의 날짜 입력 모드에서 영감을 얻었습니다. SV Hotkeys는 이를 **기존 시퀀스 엔진**(which-key HUD)으로 재구현해 모달 상태 없이 직관적으로 사용할 수 있습니다.

### 커스텀 포맷

기본 7가지 외에 원하는 포맷을 직접 만들 수도 있습니다. `hotkeys.json`에서:

```json
{
  "title": "시간만 (HH:mm)",
  "mods": ["ctrl", "opt"],
  "key": "Semicolon",
  "preset": "datetime",
  "action": {"type": "insert_datetime", "value": "HH:mm"},
  "enabled": true
}
```

**포맷 패턴** (macOS DateFormatter 기준):
- `yyyy` = 4자리 연도 · `yy` = 2자리 연도
- `MM` = 두 자리 월(01~12) · `M` = 한 자리 월(1~12)
- `dd` = 두 자리 일(01~31) · `d` = 한 자리 일(1~31)
- `HH` = 24시간 형식(00~23) · `hh` = 12시간 형식(01~12)
- `mm` = 분(00~59) · `ss` = 초(00~59)
- `EEEE` = 요일 전체(`Monday`, `월요일` 등) · `EEE` = 축약(`Mon`, `월` 등)
- 그 외 분리 문자는 그대로 입력 가능: `- / . , : 공백` 등

예시:
- `yyyy년 MM월 dd일 EEEE` → `2026년 07월 21일 월요일`
- `MM/dd/yyyy` → `07/21/2026`
- `HH:mm 기준` → `14:35 기준`

> ⚠️ `strftime` 패턴(Python/Unix)과 다릅니다. macOS DateFormatter 패턴을 따르세요.

## 로드맵 — 다음 단계

우리가 다음에 구현할 기능들입니다. 사용해보고 피드백을 보내주세요.

### 1️⃣ **CapsLock으로 창 이동·리사이즈** (최우선)
**AltDrag·frogcontrol 스타일** — 모달 호출 없이, CapsLock 누른 채로 마우스로 창을 드래그:
- `CapsLock + 왼쪽클릭 드래그` → 창 이동
- `CapsLock + 오른쪽클릭 드래그` → 창 리사이즈 (모서리/모서리로부터 방향 자동)

이건 **창 관리 중 핵심 기능**이고, 거의 모든 다른 창 매니저(Rectangle·Magnet)는 단축키로만 지원하므로 손쉬운 사용 권한이 필요 없습니다.

### 2️⃣ 키보드만으로 창 이동·리사이즈·스냅
- 좌/우/위/아래 모니터 절반 맞춤 · 모서리·중앙 위치 고정 · 창 크기 조절
- 예: `⌃⌥←` → 왼쪽 절반 / `⌃⌥↑` → 위쪽 절반 등

### 3️⃣ 뷰어 그리드에 레이어별 충돌 하이라이트
지금은 글로벌 핫키 빌더에만 충돌을 표시하는데, 메인 그리드에서도 각 프리셋별로 **어떤 키가 겹치는지** 시각적으로 보여줄 예정입니다.

### 4️⃣ 빠른 스크롤 (검토 중)
스크롤 속도 튜닝 또는 다단계 스크롤 지원.

## 고급 트리거 (Karabiner·BTT급) — 손쉬운 사용 권한 필요

일반 조합(⌘/⌥/⌃)은 권한 0이지만, 아래는 **CGEventTap**을 쓰므로 손쉬운 사용 권한이 필요합니다(메뉴바 ▸ "고급 트리거 켜기"). 편집기에서 **트리거 종류: 조합 · 제스처 · 시퀀스**로 고르거나 JSON을 직접 씁니다.

| 기능 | 무엇 | JSON |
|---|---|---|
| **앱별 핫키** | 그 앱이 최전면일 때만 발동 (아니면 통과) | `"app":"Figma"` (이름 또는 bundle id) |
| **L/R 수식키** | 왼쪽/오른쪽 구분 (skhd·Karabiner식) | `"mods":["ropt"]` = 오른쪽 ⌥ (`l`/`r` + cmd/opt/ctrl/shift) |
| **제스처** | 수식키 더블탭·멀티탭·길게 누름 | `"trigger":{"kind":"double","mod":"cmd","side":"left"}` · `{"kind":"hold","mod":"shift","ms":450}` · `{"kind":"multitap","mod":"opt","count":3}` |
| **시퀀스/리더** | 첫 조합 → 다음 조합 (⌘K ⌘I, ⌥Space→C) | `"sequence":[{"mods":["cmd"],"key":"K"},{"mods":["cmd"],"key":"I"}]` (첫 조합 뒤 2초 안에 다음 키; 화면 중앙 HUD 표시) |
| **런타임 진단** | 아무 조합이나 눌러 **누가 쓰나** 확인 (모든 소스 대조) | 메뉴바 ▸ 🔎 진단 모드 (Shortcut Detective식, 단 크로스소스) |

```json
{"title":"Figma에서만 이름변경", "mods":["opt"], "key":"R", "app":"Figma",
 "action":{"type":"run_shell","value":"..."}, "enabled":true}
{"title":"왼쪽 ⌘ 더블탭 → 뷰어", "trigger":{"kind":"double","mod":"cmd","side":"left"},
 "action":{"type":"show_viewer","value":""}}
{"title":"⌘K ⌘I → 계산기", "sequence":[{"mods":["cmd"],"key":"K"},{"mods":["cmd"],"key":"I"}],
 "action":{"type":"open_app","value":"Calculator"}}
```

> 예시는 `hotkeys.example.json` 하단 5개(기본 꺼짐)에 있습니다. 켜려면 편집기에서 토글하거나 `"enabled":true`.

## 안전 / 프라이버시

- `hotkeys.json`·생성된 `karabiner-sv.json`/`skhdrc.sv`/`hammerspoon-sv.lua`는 **당신의 실제 핫키·홈 경로**를 담아 **git에 안 올라갑니다**(`.gitignore`). 공유되는 건 `hotkeys.example.json`뿐.
- 네이티브 데몬은 네트워크·수집 없음, 순수 로컬. `⌘⌥⌃` 조합은 권한 0.
- 코드: `hotkeys/svhotkeys.swift` (단일 파일, universal 빌드). 핫키 메커니즘은 `~/dev/maverything`에서 검증된 Carbon/EventTap 방식.
