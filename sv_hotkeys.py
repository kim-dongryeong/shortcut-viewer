#!/usr/bin/env python3
"""sv_hotkeys.py — SV Hotkeys 데몬 설정(hotkeys.json) 관리 CLI/모듈. 에이전트용 (skill/MCP 공용).

  python3 sv_hotkeys.py list
  python3 sv_hotkeys.py add --title "메모 열기" --combo "cmd+opt+N" --type open_app --value Notes
  python3 sv_hotkeys.py add --title "빌드" --combo "hyper+B" --type run_shell --value "make -C ~/x" --force
  python3 sv_hotkeys.py remove <id>
  python3 sv_hotkeys.py enable <id> / disable <id>

  python3 sv_hotkeys.py presets                    # 프리셋(레이어) 목록: id·title·on/off·핫키수
  python3 sv_hotkeys.py preset-on datetime / preset-off datetime
  python3 sv_hotkeys.py preset-solo base           # 라디오 선택 — base만 켜고 master 제외 나머지 끔
  python3 sv_hotkeys.py assign dt_iso datetime     # 핫키를 다른 프리셋으로 이동(없으면 생성)
  python3 sv_hotkeys.py add --preset datetime --title … (기본 preset=base)

설정: ~/.config/shortcut-viewer/hotkeys.json — 데몬(SV Hotkeys.app)이 파일 워처로 감시하므로
쓰기만 하면 즉시 리로드된다(데몬 재시작 불필요). 원자적 쓰기(temp→rename).

프리셋(레이어): 마스터(항상 켜짐, 끌 수 없음) + 서브프리셋들(base/datetime/mousebm…). 핫키는
`preset` 필드로 하나에 속하고, `enabled(핫키) && presetOn(프리셋)`일 때만 데몬에 등록된다.
v1 파일(presets 없음)은 로드 시 전부 preset="base"로 자동 정규화되고 저장 시 v2로 승격된다.

⚠️ run_shell/applescript 액션은 키 입력으로 임의 코드가 실행되는 것 — 에이전트는 사용자에게
내용을 확인받은 뒤 --force 로만 추가할 것. add는 등록 전에 corpus(sv_query)로 충돌을 검사해
이미 쓰이는 조합이면 거부한다(--force 로 무시 가능; 대안 빈 키를 함께 제안).
"""
import os, sys, json, argparse, tempfile, subprocess
import sv_query

CONFIG = os.path.expanduser("~/.config/shortcut-viewer/hotkeys.json")
ACTION_TYPES = ("open_app", "open_url", "open_file", "open_folder", "run_shell",
                "applescript", "paste_text", "show_viewer",
                "mouse_save", "mouse_goto", "mouse_click")
DANGEROUS = ("run_shell", "applescript")
MASTER_TITLE = "마스터 — 항상 켜짐 (프리셋 전환 키)"


def _normalize(doc):
    """v1(presets 없음)→v2 승격 + 참조된 프리셋 자동 생성. load()/CLI 어디서 읽든 동일 적용."""
    doc.setdefault("hotkeys", [])
    presets = doc.get("presets")
    if presets is None:
        presets = {"master": {"title": MASTER_TITLE, "always_on": True},
                    "base": {"title": "기본", "enabled": True}}
    for h in doc["hotkeys"]:
        h.setdefault("preset", "base")
        presets.setdefault(h["preset"], {"enabled": True})
    presets.setdefault("master", {"title": MASTER_TITLE, "always_on": True})
    doc["presets"] = presets
    doc["version"] = 2
    return doc


def load():
    if not os.path.exists(CONFIG):
        return _normalize({"version": 1, "hotkeys": []})
    with open(CONFIG) as f:
        return _normalize(json.load(f))


def preset_on(doc, name):
    """§1 발화 조건: master는 항상 참, always_on 프리셋도 항상 참, 그 외 enabled(기본 true)."""
    if name == "master":
        return True
    p = doc.get("presets", {}).get(name, {})
    return True if p.get("always_on") else p.get("enabled", True)


def save(doc):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CONFIG), suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CONFIG)  # atomic — 데몬 파일 워처가 rename 이벤트로 리로드


def daemon_running():
    return subprocess.run(["pgrep", "-xq", "svhotkeys"], capture_output=True).returncode == 0 \
        or subprocess.run(["pgrep", "-fq", "SV Hotkeys.app"], capture_output=True).returncode == 0


def fmt(h):
    combo = sv_query.combo_str(h.get("mods", []), h.get("key", ""))
    a = h.get("action", {})
    on = "✓" if h.get("enabled", True) else "✗"
    extra = "".join([f" app={h['app']}" if h.get("app") else "",
                     " anyCombo" if h.get("anyCombo") else ""])
    return f"{on} {h.get('id','?'):10s} {combo:22s} {a.get('type','?')}({a.get('value','')})  {h.get('title','')}{extra}"


def list_hotkeys():
    doc = load()
    lines, total = [], 0
    for pid, p in doc["presets"].items():
        hks = [h for h in doc["hotkeys"] if h.get("preset", "base") == pid]
        on = "always_on" if p.get("always_on") else ("on " if p.get("enabled", True) else "off")
        lines.append(f"── [{pid}] {p.get('title', pid)} ({on}, 핫키 {len(hks)}개) ──")
        lines.extend(fmt(h) for h in hks)
        total += len(hks)
    head = f"{total} hotkey(s) in {CONFIG}" + ("" if daemon_running() else "  ⚠️ 데몬 미실행 — 등록해도 발동 안 함")
    return "\n".join([head] + lines)


def presets_list():
    doc = load()
    lines = []
    for pid, p in doc["presets"].items():
        cnt = sum(1 for h in doc["hotkeys"] if h.get("preset", "base") == pid)
        on = "always_on" if p.get("always_on") else ("✓" if p.get("enabled", True) else "✗")
        lines.append(f"{on:9s} {pid:10s} {p.get('title', pid):32s} 핫키 {cnt}개")
    return "\n".join([f"{len(doc['presets'])} preset(s) in {CONFIG}"] + lines)


def preset_set(name, on):
    doc = load()
    p = doc["presets"].setdefault(name, {"enabled": True})
    if name == "master" or p.get("always_on"):
        if not on:
            raise SystemExit("🎛 마스터 프리셋은 항상 켜져 있어요 — 끌 수 없음")
        return f"프리셋 '{name}'은 이미 always_on"
    p["enabled"] = on
    save(doc)
    return f"🎛 프리셋 '{p.get('title', name)}' {'켜짐' if on else '꺼짐'}"


def preset_solo(name):
    """라디오 선택(preset_activate 의미): name만 켜고, master/always_on 제외 나머지 전부 끔."""
    doc = load()
    doc["presets"].setdefault(name, {"enabled": True})
    for pid, p in doc["presets"].items():
        if pid == "master" or p.get("always_on"):
            continue
        p["enabled"] = (pid == name)
    save(doc)
    return f"🎛 프리셋 '{doc['presets'][name].get('title', name)}' 선택"


def assign(hid, preset):
    doc = load()
    h = _find(doc, hid)
    doc["presets"].setdefault(preset, {"enabled": True})
    h["preset"] = preset
    save(doc)
    return f"'{hid}' → 프리셋 '{preset}'으로 이동"


def add(title, combo, atype, value="", app=None, any_combo=False, hid=None, force=False, preset="base"):
    if atype not in ACTION_TYPES:
        raise SystemExit(f"unknown action type '{atype}' — one of {', '.join(ACTION_TYPES)}")
    if atype in DANGEROUS and not force:
        raise SystemExit(f"'{atype}'는 키 입력으로 임의 코드를 실행한다 — 사용자에게 명령 내용을 "
                         "확인받은 뒤 --force로 다시 실행할 것")
    mods, key = sv_query.parse_combo(combo)
    if not key:
        raise SystemExit(f"combo '{combo}'에서 키를 못 읽음")
    doc = load()
    dup = [h for h in doc["hotkeys"] if sorted(h.get("mods", [])) == mods and h.get("key") == key]
    if dup and not force:
        raise SystemExit(f"이미 같은 조합의 핫키가 있음: {fmt(dup[0])}  (--force로 추가 강행 가능)")
    users = []
    try:
        hits = sv_query._index(sv_query.load()).get((tuple(mods), key), [])
        # 글로벌 핫키는 모든 사용처와 충돌; 앱 스코프(app=) 핫키는 글로벌 + 그 앱 사용처만 충돌
        users = [u for u in hits if not app or u.get("scope") in sv_query.GLOBALISH or u.get("scope") == app]
    except SystemExit:
        pass  # corpus 없음 — 충돌검사 생략
    if users and not force:
        alt = sv_query.free("+".join(mods)).splitlines()[-1].strip().split()[:5]
        lines = [f"  [{u.get('scope','?')}] {u.get('action','?')} ({u.get('source','?')})" for u in users[:6]]
        raise SystemExit(f"조합 {sv_query.combo_str(mods, key)} 은 이미 사용 중:\n" + "\n".join(lines)
                         + f"\n빈 대안 키: {' '.join(alt)}   (그래도 등록하려면 --force)")
    h = {"id": hid or ("a%06x" % (int.from_bytes(os.urandom(3), "big"))), "title": title,
         "mods": mods, "key": key, "action": {"type": atype, "value": value},
         "enabled": True, "anyCombo": bool(any_combo), "preset": preset}
    if app:
        h["app"] = app
    doc["presets"].setdefault(preset, {"enabled": True})
    doc["hotkeys"].append(h)
    save(doc)
    note = "" if daemon_running() else "\n⚠️ SV Hotkeys 데몬이 실행 중이 아님 — `open '<repo>/hotkeys/SV Hotkeys.app'`으로 시작"
    return f"등록됨 (데몬이 파일 워처로 자동 리로드):\n{fmt(h)}{note}"


def _find(doc, hid):
    for h in doc["hotkeys"]:
        if h.get("id") == hid:
            return h
    raise SystemExit(f"id '{hid}' 없음 — `list`로 확인")


def remove(hid):
    doc = load()
    h = _find(doc, hid)
    doc["hotkeys"] = [x for x in doc["hotkeys"] if x.get("id") != hid]
    save(doc)
    return f"삭제됨: {fmt(h)}"


def set_enabled(hid, on):
    doc = load()
    h = _find(doc, hid)
    h["enabled"] = on
    save(doc)
    return fmt(h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("add")
    p.add_argument("--title", required=True); p.add_argument("--combo", required=True)
    p.add_argument("--type", required=True, choices=ACTION_TYPES); p.add_argument("--value", default="")
    p.add_argument("--app", help="이 앱이 앞일 때만 (bundle id 또는 앱 이름)")
    p.add_argument("--any-combo", action="store_true"); p.add_argument("--id")
    p.add_argument("--force", action="store_true")
    p.add_argument("--preset", default="base", help="핫키가 속할 프리셋(레이어), 기본 base")
    for c in ("remove", "enable", "disable"):
        sub.add_parser(c).add_argument("id")
    sub.add_parser("presets")
    for c in ("preset-on", "preset-off", "preset-solo"):
        sub.add_parser(c).add_argument("name")
    pa = sub.add_parser("assign")
    pa.add_argument("hotkey_id"); pa.add_argument("preset")
    a = ap.parse_args()
    if a.cmd == "list":
        print(list_hotkeys())
    elif a.cmd == "add":
        print(add(a.title, a.combo, a.type, a.value, a.app, a.any_combo, a.id, a.force, a.preset))
    elif a.cmd == "remove":
        print(remove(a.id))
    elif a.cmd in ("enable", "disable"):
        print(set_enabled(a.id, a.cmd == "enable"))
    elif a.cmd == "presets":
        print(presets_list())
    elif a.cmd in ("preset-on", "preset-off"):
        print(preset_set(a.name, a.cmd == "preset-on"))
    elif a.cmd == "preset-solo":
        print(preset_solo(a.name))
    elif a.cmd == "assign":
        print(assign(a.hotkey_id, a.preset))


if __name__ == "__main__":
    main()
