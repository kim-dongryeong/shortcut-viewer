# Windows 패키징 — ShortcutViewer.exe

⚠️ **Windows에서 실행해야 함** — PyInstaller는 크로스 컴파일이 안 되고 빌드하는 그 OS용 실행 파일만 만든다.

```powershell
git clone https://github.com/kim-dongryeong/shortcut-viewer.git
cd shortcut-viewer
packaging\win\build_exe.bat
packaging\win\dist\ShortcutViewer.exe   # 테스트
```

`build_exe.bat`이 필요하면 PyInstaller를 설치하고, `build_exe.spec`으로 `launcher.py` +
`win/build_win.py`·`win/winkeys.py`·`render.py`·`svkeys.py`·`svann.py`·`viewer.template.html`·
`dump_*.py`·`win/defaults/`·`win/packs/`(공유 corpus)를 통째로 `ShortcutViewer.exe` 하나로 얼린다.

## 실행 파일이 하는 일 (`launcher.py`)

PyInstaller onefile은 실행마다 임시 폴더에 압축을 풀고 종료 시 지우므로, 결과물을 거기 바로 쓰면
브라우저가 열기도 전에 파일이 사라질 수 있다. 그래서 번들된 스크립트/코퍼스를
`%LOCALAPPDATA%\ShortcutViewer\`(영구 위치)로 복사한 뒤 그 자리에서 `win/build_win.py` → `render.py`를
그대로 실행하고 `viewer.html`을 기본 브라우저로 연다. 재실행해도 스캔 결과(`shortcuts.json` 등)는
보존하고 스크립트·corpus만 새로 갱신한다.

## 알려진 제약 (v1)

- **Adobe 전체 키맵 추출**(`collect_adobe_dumps()`가 `dump_ae.py` 등을 서브프로세스로 돌리는 부분)은
  얼린 exe 안에서 동작 안 함 — `sys.executable`이 파이썬 인터프리터가 아니라 exe 자기 자신을 가리켜서.
  실패해도 전체가 죽지는 않고 그 부분만 조용히 스킵됨(다른 수집기는 전부 정상). 필요하면 소스 설치
  (`python win\build_win.py`)로 돌리면 됨.
- 서명 없음 — SmartScreen "Windows의 PC 보호" 경고 → 더 보기 ▸ 실행으로 넘기면 됨. 코드서명 인증서는
  유료라 v1은 생략(win/README.md에도 같은 방침 기록됨).
- 콘솔 창이 잠깐 뜸(진단 로그 확인용, v1). 안정화되면 `build_exe.spec`의 `console=False`로 숨길 수 있음.
