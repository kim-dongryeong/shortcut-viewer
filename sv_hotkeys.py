#!/usr/bin/env python3
"""sv_hotkeys.py — SV Hotkeys 데몬 설정(hotkeys.json) 관리 CLI/모듈. 에이전트용 (skill/MCP 공용).

  python3 sv_hotkeys.py list
  python3 sv_hotkeys.py add --title "메모 열기" --combo "cmd+opt+N" --type open_app --value Notes
  python3 sv_hotkeys.py add --title "빌드" --combo "hyper+B" --type run_shell --value "make -C ~/x" --force
  python3 sv_hotkeys.py remove <id>
  python3 sv_hotkeys.py enable <id> / disable <id>

설정: ~/.config/shortcut-viewer/hotkeys.json — 데몬(SV Hotkeys.app)이 파일 워처로 감시하므로
쓰기만 하면 즉시 리로드된다(데몬 재시작 불필요). 원자적 쓰기(temp→rename).

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


def load():
    if not os.path.exists(CONFIG):
        return {"version": 1, "hotkeys": []}
    with open(CONFIG) as f:
        return json.load(f)


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
    lines = [fmt(h) for h in doc.get("hotkeys", [])]
    head = f"{len(lines)} hotkey(s) in {CONFIG}" + ("" if daemon_running() else "  ⚠️ 데몬 미실행 — 등록해도 발동 안 함")
    return "\n".join([head] + lines)


def add(title, combo, atype, value="", app=None, any_combo=False, hid=None, force=False):
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
         "enabled": True, "anyCombo": bool(any_combo)}
    if app:
        h["app"] = app
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
    for c in ("remove", "enable", "disable"):
        sub.add_parser(c).add_argument("id")
    a = ap.parse_args()
    if a.cmd == "list":
        print(list_hotkeys())
    elif a.cmd == "add":
        print(add(a.title, a.combo, a.type, a.value, a.app, a.any_combo, a.id, a.force))
    elif a.cmd == "remove":
        print(remove(a.id))
    else:
        print(set_enabled(a.id, a.cmd == "enable"))


if __name__ == "__main__":
    main()
