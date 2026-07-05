# SV Hotkeys (Windows) — 초안

macOS의 **SV Hotkeys**(글로벌 핫키 + 마우스 북마크)에 대응하는 **Windows 네이티브 앱 skeleton**.
`AutoHotKey`가 아니라 **C#/.NET(WinForms)** 으로 — AHK-컴파일 exe는 백신 오탐이 잦은 반면 .NET exe는 훨씬 깔끔하기 때문.

## 무엇이 들어있나 (macOS 대칭)
| 층 | macOS | 이 폴더(Windows) |
|---|---|---|
| 핫키·마우스 실행 | SV Hotkeys (Swift) | **C#/.NET** — `SvHotkeysWin/Program.cs` |
| 수집기(뷰어 데이터) | `build.py`+`axmenudump` | `build_win.py` (스켈레톤) — AHK·PowerToys·시스템 시드 |
| 뷰어 화면 | `viewer.html` | **공유** (같은 HTML 그리드) |

## 기능(초안)
- **글로벌 핫키**: Win32 `RegisterHotKey` + 숨은 message-only 창 → `WM_HOTKEY`.
- **마우스 북마크 10칸(1..9,0)**:
  - `Ctrl+Alt+<n>` = 현재 커서 위치를 슬롯 n에 **저장**
  - `Alt+<n>` = 슬롯 n으로 **이동 → 좌클릭 → 원위치 복귀**
- **영속화**: `%APPDATA%\shortcut-viewer\mouse_bookmarks.json`
- **트레이 아이콘**(맥 메뉴바 대응) + **세련된 토스트 HUD**(어두운 라운드·하단중앙·페이드).

## 빌드/실행 (Windows + .NET 8 SDK)
```powershell
cd win/SvHotkeysWin
dotnet run                                   # 개발 실행
# 단일 실행파일(자체포함, 런타임 설치 불필요):
dotnet publish -c Release -r win-x64 -p:PublishSingleFile=true --self-contained true
```

## TODO / 업그레이드 포인트
- `mouse_event` → **`SendInput`** 로 교체(권장 API).
- ✅ 바인딩을 **`hotkeys.json`** 에서 읽음(맥과 스키마 공유). `%APPDATA%\shortcut-viewer\hotkeys.json`, 없으면 마우스 10칸 기본.
- 우클릭/더블클릭 액션, `goto`(이동만) 등 액션 확장.
- **배포**: 미서명 exe는 SmartScreen "알 수 없는 앱" 경고 → 원하면 Windows 코드서명 인증서(연 $$). v1은 미서명으로 시작 가능.
- **수집기**(`build_win.py`) 신설: 레지스트리 핫키·AutoHotKey 스크립트·PowerToys Keyboard Manager·앱 accelerator → 뷰어 스키마(`mods,key,action,source,scope`).

## 라이선스
repo 전체 라이선스를 따름(→ 루트 `LICENSE`).
