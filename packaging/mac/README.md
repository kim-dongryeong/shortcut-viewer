# macOS 패키징 — Shortcut Viewer.dmg

`build_dmg.sh` 하나로 끝: axmenudump(universal) 컴파일 → `Shortcut Viewer.app` 조립(스크립트 +
`defaults/`·`web_shortcuts.json` corpus 통째로 번들) → ad-hoc 서명 → `.dmg`.

```sh
./packaging/mac/build_dmg.sh
open "packaging/mac/dist/Shortcut Viewer.app"   # 테스트
```

## 앱이 하는 일

더블클릭 → `Contents/Resources`에서 그 자리에 번들된 `build.py`를 실행(자기 자신의 Resources에
`shortcuts.json`/`viewer.html` 기록 — 앱이 `~/Applications`처럼 사용자 소유 위치에 있으면 문제없음)
→ 기본 브라우저로 `viewer.html`을 연다. Accessibility 권한은 앱 자신에게 요청됨(터미널이 아니라).

## 서명

- **ad-hoc 서명**(`codesign -s -`, 무료) — Apple Silicon은 서명이 아예 없는 실행 파일을 거부하므로 필수.
- Gatekeeper의 "확인되지 않은 개발자" 경고 자체는 유료 Developer ID(연 $99) 없이는 안 없어짐 — v1은
  이 경고를 감수(우클릭 ▸ 열기 1회). 필요해지면 Developer ID 서명 + notarization으로 업그레이드 가능.

## 알려진 제약 (v1)

- 앱 자체 Resources에 직접 쓰기 때문에, `.dmg`를 새로 받아 덮어씌우면 로컬 스캔 결과·즐겨찾기가 리셋됨
  (다음 실행이 자동으로 다시 채워주긴 함). `~/Library/Application Support/`로 옮기는 건 다음 개선 후보.
- 앱 아이콘 없음(기본 아이콘) — `.icns` 추가는 다음 개선 후보.
