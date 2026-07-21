#!/usr/bin/env python3
"""sv_mcp.py — Shortcut Viewer + SV Hotkeys MCP 서버 (stdio, 순수 표준 라이브러리).

에이전트(Claude Code, Codex 등 MCP 클라이언트)가 ① 단축키 corpus를 조회하고(충돌·빈 조합)
② SV Hotkeys 데몬에 글로벌 핫키를 등록/관리할 수 있게 한다. 조회(sv_query)와 등록(sv_hotkeys)을
한 서버에 두는 이유: 올바른 등록 흐름이 "빈 조합 조회 → 등록"으로 두 도구를 함께 쓰기 때문.

등록:  claude mcp add --scope user shortcut-viewer -- python3 <repo>/sv_mcp.py
프로토콜: MCP stdio(줄 단위 JSON-RPC 2.0) — 외부 SDK 없이 initialize/tools/list/tools/call만 구현.
"""
import sys, json, traceback
import sv_query, sv_hotkeys

PROTOCOL = "2025-06-18"

def combo_schema(desc):
    return {"type": "string", "description": desc + " 예: 'cmd+shift+K', 'hyper+J', 'ctrl+opt+Space'"}

TOOLS = [
    {"name": "shortcut_lookup",
     "description": "키 조합 하나가 이 Mac의 어디에(시스템/앱/BTT/웹앱…) 어떤 동작으로 걸려 있는지 조회.",
     "inputSchema": {"type": "object", "properties": {"combo": combo_schema("조회할 조합.")},
                     "required": ["combo"]}},
    {"name": "shortcut_free",
     "description": "주어진 수식키 레이어에서 아직 아무 데도 안 쓰인 빈 키를 선호순으로 제안. "
                    "새 핫키를 만들기 전 반드시 이걸로 충돌 없는 조합을 고를 것.",
     "inputSchema": {"type": "object", "properties": {
         "mods": {"type": "string", "description": "수식키 조합. 예: 'cmd+shift', 'hyper'"},
         "scope": {"type": "string", "description": "특정 앱 기준으로 보려면 앱 이름(스코프). 생략하면 전 스코프."}},
         "required": ["mods"]}},
    {"name": "shortcut_conflicts",
     "description": "글로벌 단축키와 앱 단축키가 겹치는(가려지는) 조합 목록.",
     "inputSchema": {"type": "object", "properties": {
         "scope": {"type": "string", "description": "특정 앱만 보려면 앱 이름."}}}},
    {"name": "shortcut_app",
     "description": "앱 하나의 단축키 목록 (스코프 이름 기준).",
     "inputSchema": {"type": "object", "properties": {
         "name": {"type": "string"}, "limit": {"type": "integer", "default": 40}},
         "required": ["name"]}},
    {"name": "hotkey_list",
     "description": "SV Hotkeys 데몬에 등록된 글로벌 핫키 목록 (id·조합·액션·활성 여부, 데몬 실행 여부 포함).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "hotkey_add",
     "description": "SV Hotkeys에 글로벌 핫키 등록. 파일 워처가 즉시 리로드하므로 재시작 불필요. "
                    "corpus와 충돌하면 거부되고 빈 대안 키를 제안한다(force로 강행 가능). "
                    "⚠️ action_type이 run_shell/applescript면 키 입력으로 임의 코드가 실행된다 — "
                    "반드시 사용자에게 명령 내용을 보여주고 명시적 동의를 받은 뒤에만 force=true로 호출할 것.",
     "inputSchema": {"type": "object", "properties": {
         "title": {"type": "string", "description": "사람이 읽는 설명"},
         "combo": combo_schema("등록할 조합."),
         "action_type": {"type": "string", "enum": list(sv_hotkeys.ACTION_TYPES)},
         "action_value": {"type": "string", "description": "앱 이름/URL/경로/셸 명령/붙여넣을 텍스트 등", "default": ""},
         "app": {"type": "string", "description": "이 앱이 앞일 때만 발동하려면 앱 이름/번들id"},
         "any_combo": {"type": "boolean", "default": False},
         "force": {"type": "boolean", "default": False,
                   "description": "충돌 무시·위험 액션 등록 강행 — 사용자 동의 후에만"}},
         "required": ["title", "combo", "action_type"]}},
    {"name": "hotkey_remove",
     "description": "등록된 핫키 삭제 (id는 hotkey_list로 확인).",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "hotkey_set_enabled",
     "description": "핫키 활성/비활성 토글.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string"}, "enabled": {"type": "boolean"}}, "required": ["id", "enabled"]}},
    {"name": "hotkey_preset",
     "description": "프리셋(레이어) 관리 — list(목록)/on/off(마스터는 거부)/solo(라디오 선택, "
                    "master 제외 나머지 다 끔)/assign(핫키를 다른 프리셋으로 이동).",
     "inputSchema": {"type": "object", "properties": {
         "op": {"type": "string", "enum": ["list", "on", "off", "solo", "assign"]},
         "name": {"type": "string", "description": "프리셋 id (on/off/solo/assign 대상)"},
         "hotkey_id": {"type": "string", "description": "assign일 때 옮길 핫키 id"}},
         "required": ["op"]}},
]


def call_tool(name, a):
    if name == "shortcut_lookup":
        return sv_query.lookup(a["combo"])
    if name == "shortcut_free":
        return sv_query.free(a["mods"], a.get("scope"))
    if name == "shortcut_conflicts":
        return sv_query.conflicts(a.get("scope"))
    if name == "shortcut_app":
        return sv_query.app_shortcuts(a["name"], a.get("limit", 40))
    if name == "hotkey_list":
        return sv_hotkeys.list_hotkeys()
    if name == "hotkey_add":
        return sv_hotkeys.add(a["title"], a["combo"], a["action_type"], a.get("action_value", ""),
                              a.get("app"), a.get("any_combo", False), None, a.get("force", False))
    if name == "hotkey_remove":
        return sv_hotkeys.remove(a["id"])
    if name == "hotkey_set_enabled":
        return sv_hotkeys.set_enabled(a["id"], a["enabled"])
    if name == "hotkey_preset":
        op = a["op"]
        if op == "list":
            return sv_hotkeys.presets_list()
        if op in ("on", "off"):
            return sv_hotkeys.preset_set(a["name"], op == "on")
        if op == "solo":
            return sv_hotkeys.preset_solo(a["name"])
        if op == "assign":
            return sv_hotkeys.assign(a["hotkey_id"], a["name"])
        raise ValueError(f"unknown preset op {op}")
    raise ValueError(f"unknown tool {name}")


def reply(id_, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": id_}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, id_ = req.get("method", ""), req.get("id")
        if method == "initialize":
            reply(id_, {"protocolVersion": req.get("params", {}).get("protocolVersion", PROTOCOL),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "shortcut-viewer", "version": "1.0.0"}})
        elif method == "tools/list":
            reply(id_, {"tools": TOOLS})
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                text = call_tool(p.get("name", ""), p.get("arguments", {}) or {})
                reply(id_, {"content": [{"type": "text", "text": text}], "isError": False})
            except SystemExit as e:   # sv_query/sv_hotkeys의 정상적 거부 사유 → 도구 에러로 전달
                reply(id_, {"content": [{"type": "text", "text": str(e)}], "isError": True})
            except Exception:
                reply(id_, {"content": [{"type": "text", "text": traceback.format_exc(limit=3)}],
                            "isError": True})
        elif method == "ping":
            reply(id_, {})
        elif id_ is not None:   # 모르는 요청(알림 제외)에만 에러 응답
            reply(id_, error={"code": -32601, "message": f"method not found: {method}"})


if __name__ == "__main__":
    main()
