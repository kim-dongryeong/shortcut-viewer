#!/usr/bin/env python3
# build_win.py — Windows 단축키 수집기.
# macOS의 build.py에 대응하는 Windows판. Windows 소스에서 단축키를 긁어 **공유 스키마**
# (mods, key, action, source, scope)로 shortcuts.json을 만들고, 그걸 공유 뷰어(render.py +
# viewer.template.html)로 렌더한다. → 맥과 "같은 키보드 그리드"에 Windows 단축키를 통합.
#
# ⚠️ Windows에서 실행. 파이썬 표준 라이브러리만.
#
# 실행 흐름:  python build_win.py [out.json]   →  shortcuts.json  →  python ../render.py  →  ../viewer.html
#
# 수식키 매핑(윈→공유 스키마): Ctrl→ctrl · Alt→opt · Shift→shift · Win→cmd
#   (기존 뷰어 그리드/빈조합 로직을 그대로 쓰려고 맥 토큰에 매핑. 뷰어는 meta.platform=="windows"를 보고
#    자동으로 Windows 키보드로 전환 — ⊞Win·Alt·Ctrl 키캡, 104키 하단행·넘패드, "Ctrl+Shift+S" 표기.)
#
# 수집 소스:
#   1) 시스템 기본 시드 + 파일 탐색기 시드 (맥 DEFAULTS 대응)
#   2) 실행 중인 앱 메뉴 스캔 (맥 axmenudump 대응) — Win32 HMENU(GetMenu/GetMenuStringW)의
#      "라벨\tCtrl+S" accelerator 텍스트. 클래식 메뉴 앱만(메모장++·7-Zip 등; Chrome/Office/UWP는 메뉴가 커스텀이라 불가)
#   3) AutoHotKey 스크립트 (^!+# 접두 핫키)
#   4) PowerToys Keyboard Manager (키/단축키 리맵 — VK 코드 디코드)
#   5) .lnk 바로 가기 키 (시작 메뉴·바탕화면의 "바로 가기 키" — [MS-SHLLINK] 헤더 0x40 HotKey)
#   6) Windows Terminal settings.json (actions/keybindings, JSONC — 기본 키는 패키지 내부 defaults.json이라 사용자 지정만 잡힘)
#   7) VS Code — repo 루트의 vscode_default_keybindings.json(기본 키맵 덤프) + %APPDATA% 사용자 keybindings.json
#   8) 수동 글로벌 win/manual_globals_win.json (gitignored)

import datetime, glob, json, os, platform, re, struct, sys

PROJ = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PROJ)   # repo 루트(공유 뷰어 템플릿 위치)
entries = []

def add(mods, key, action, source, scope="global", detail="", group=None, **extra):
    if not key:
        return
    e = {"mods": sorted(set(mods)), "key": key, "action": action, "source": source,
         "scope": scope, "detail": detail, "group": group or scope}
    e.update(extra)
    entries.append(e)

# ── VK 가상 키코드 → 공유 스키마 키 (PowerToys·.lnk 공용) ────────────────────
VK = {8:"Delete",9:"Tab",13:"Return",19:"Pause",20:"CapsLock",27:"Escape",32:"Space",
      33:"PageUp",34:"PageDown",35:"End",36:"Home",37:"Left",38:"Up",39:"Right",40:"Down",
      44:"PrintScreen",45:"Insert",46:"ForwardDelete",93:"Menu",144:"KeypadClear",145:"ScrollLock",
      186:";",187:"=",188:",",189:"-",190:".",191:"/",192:"`",219:"[",220:"\\",221:"]",222:"'"}
VK.update({k: chr(k) for k in range(48, 58)})            # 0-9
VK.update({k: chr(k) for k in range(65, 91)})            # A-Z
VK.update({112 + i: f"F{i+1}" for i in range(24)})       # F1-F24
VK.update({96 + i: f"Keypad{i}" for i in range(10)})
VK.update({106:"KeypadMultiply",107:"KeypadPlus",109:"KeypadMinus",110:"KeypadDecimal",111:"KeypadDivide"})
VK_MOD = {16:"shift",160:"shift",161:"shift",17:"ctrl",162:"ctrl",163:"ctrl",
          18:"opt",164:"opt",165:"opt",91:"cmd",92:"cmd"}   # L/R 구분 코드 포함

def vk_seq(s):   # PowerToys "162;67" (VK 세미콜론 구분) → (mods, key)
    mods, key = [], None
    for tok in str(s or "").split(";"):
        tok = tok.strip()
        if not tok.isdigit():
            continue
        v = int(tok)
        if v in VK_MOD:
            mods.append(VK_MOD[v])
        else:
            key = VK.get(v, key)
    return mods, key

def vk_disp(s):   # 리맵 "대상" 표시용 — "Ctrl+C" (뷰어 win 표기와 동일)
    mods, key = vk_seq(s)
    lab = {"cmd":"Win","ctrl":"Ctrl","opt":"Alt","shift":"Shift"}
    return "+".join([lab[m] for m in ("cmd","ctrl","opt","shift") if m in mods] + ([key] if key else []))

# ── "ctrl+shift+t" 문자열 파서 (VS Code·Windows Terminal 공용) ───────────────
MOD_TOKEN = {"ctrl":"ctrl","control":"ctrl","shift":"shift","alt":"opt","opt":"opt","option":"opt",
             "win":"cmd","meta":"cmd","cmd":"cmd"}
KEYSTR = {"enter":"Return","return":"Return","escape":"Escape","esc":"Escape","space":"Space","tab":"Tab",
          "backspace":"Delete","delete":"ForwardDelete","del":"ForwardDelete","insert":"Insert","ins":"Insert",
          "home":"Home","end":"End","pageup":"PageUp","pgup":"PageUp","pagedown":"PageDown","pgdn":"PageDown",
          "up":"Up","down":"Down","left":"Left","right":"Right","capslock":"CapsLock","menu":"Menu","apps":"Menu",
          "printscreen":"PrintScreen","scrolllock":"ScrollLock","pause":"Pause","plus":"=",
          "numpad_add":"KeypadPlus","numpad_subtract":"KeypadMinus","numpad_multiply":"KeypadMultiply",
          "numpad_divide":"KeypadDivide","numpad_decimal":"KeypadDecimal"}
KEYSTR.update({f"numpad{i}": f"Keypad{i}" for i in range(10)})
KEYSTR.update({f"numpad_{i}": f"Keypad{i}" for i in range(10)})

def parse_keystr(tok):   # "ctrl+shift+t" → (mods, key) · 모르는 키/수식키-단독이면 None
    parts = [p for p in tok.strip().lower().split("+") if p]
    if not parts:
        return None
    *ms, k = parts
    mods = []
    for m in ms:
        if m not in MOD_TOKEN:
            return None
        mods.append(MOD_TOKEN[m])
    if k in MOD_TOKEN:
        return None
    if len(k) == 1:
        key = k.upper()
    elif re.fullmatch(r"f\d{1,2}", k):
        key = k.upper()
    else:
        key = KEYSTR.get(k)
    return (mods, key) if key else None

def _jsonc(text):   # JSONC → JSON: 문자열 밖의 //·/*..*/ 주석과 트레일링 콤마 제거
    out, i, instr = [], 0, False
    while i < len(text):
        c = text[i]
        if instr:
            out.append(c)
            if c == "\\" and i + 1 < len(text):
                out.append(text[i+1]); i += 1
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True; out.append(c)
        elif text[i:i+2] == "//":
            j = text.find("\n", i); i = len(text) if j < 0 else j; continue
        elif text[i:i+2] == "/*":
            j = text.find("*/", i + 2); i = len(text) if j < 0 else j + 2; continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(out))

# ── 0) 실행 중인 앱 메뉴 스캔 (맥 axmenudump 대응) ──────────────────────────
# 클래식 Win32 메뉴(HMENU)의 항목 라벨은 "저장(&S)\tCtrl+S" 꼴 — \t 뒤가 accelerator.
# GetMenu → GetSubMenu 재귀 → GetMenuStringW 로 긁는다. 메모장++·7-Zip·IrfanView 등
# 클래식 앱만 가능(Chrome/Electron/Office/UWP는 메뉴를 자체 렌더링해서 HMENU가 없음).
def parse_accel(acc):   # 메뉴 accelerator 텍스트 "Ctrl + Shift+S" → (mods, key)
    return parse_keystr(re.sub(r"\s*\+\s*", "+", acc.strip()))

SCANNED = set()    # 이번 실행에서 메뉴를 실제 스캔한 앱 (scope명 + exe명) — 이전 스캔 재사용 판단용
MENU_SCAN = {}     # 뷰어 🩺 진단용 스캔 신선도 (맥 build.py의 meta.menu_scan 대응)
ICON_PATHS = {}    # scope → exe 경로 (아이콘 추출용)
PREV_ICONS = {}    # 재사용된 앱의 이전 아이콘 (data URI)

def collect_win32_menus():
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.GetMenu.restype = ctypes.c_void_p;    user32.GetMenu.argtypes = [wintypes.HWND]   # 핸들은 포인터 크기 — 기본 c_int면 64비트에서 잘림
    user32.GetSubMenu.restype = ctypes.c_void_p; user32.GetSubMenu.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetMenuItemCount.argtypes = [ctypes.c_void_p]
    user32.GetMenuStringW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, ctypes.c_int, wintypes.UINT]
    ver = ctypes.windll.version
    ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p]
    ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    MF_BYPOSITION = 0x400

    def exe_path_of(hwnd):   # 창 → 프로세스 exe 전체 경로
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = kernel32.OpenProcess(0x1000, False, pid.value)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        buf = ctypes.create_unicode_buffer(260); sz = wintypes.DWORD(260)
        ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz))
        kernel32.CloseHandle(h)
        return buf.value if ok else None

    def file_desc(path):   # exe 버전 리소스의 FileDescription — "AfterFX"→"Adobe After Effects" 같은 표시 이름
        try:
            sz = ver.GetFileVersionInfoSizeW(path, None)
            if not sz:
                return None
            buf = ctypes.create_string_buffer(sz)
            if not ver.GetFileVersionInfoW(path, 0, sz, buf):
                return None
            ptr, ln = ctypes.c_void_p(), wintypes.UINT()
            if not ver.VerQueryValueW(buf, r"\VarFileInfo\Translation", ctypes.byref(ptr), ctypes.byref(ln)) or ln.value < 4:
                return None
            lang, cp = struct.unpack("<HH", ctypes.string_at(ptr, 4))
            if not ver.VerQueryValueW(buf, rf"\StringFileInfo\{lang:04x}{cp:04x}\FileDescription",
                                      ctypes.byref(ptr), ctypes.byref(ln)) or not ln.value:
                return None
            return (ctypes.wstring_at(ptr) or "").strip() or None
        except Exception:
            return None

    stats = {}
    def walk(hmenu, path, scope, exe, depth=0):
        if depth > 6:
            return
        for i in range(max(0, user32.GetMenuItemCount(hmenu))):
            buf = ctypes.create_unicode_buffer(256)
            n = user32.GetMenuStringW(hmenu, i, buf, 256, MF_BYPOSITION)
            label = buf.value.replace("&", "").strip() if n else ""
            sub = user32.GetSubMenu(hmenu, i)
            if sub:
                walk(sub, path + ([label] if label else []), scope, exe, depth + 1)
            elif "\t" in label:
                name, acc = label.split("\t", 1)
                pk = parse_accel(acc)
                if pk:
                    add(pk[0], pk[1], " ▸ ".join(path + [name.strip()]), source="app menu",
                        scope=scope, detail=f"Win32 메뉴 스캔 · {exe}", group=scope)   # detail의 exe명 = 재사용 매칭 키
                    stats[scope] = stats.get(scope, 0) + 1

    seen = set()
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            hm = user32.GetMenu(hwnd)
            if not hm:
                return True
            path = exe_path_of(hwnd)
            exe = os.path.splitext(os.path.basename(path))[0] if path else "?"
            if (exe, hm) in seen:   # 같은 앱의 창 여러 개 → 메뉴 한 번만
                return True
            seen.add((exe, hm))
            desc = file_desc(path) if path else None
            scope = desc if desc and len(desc) <= 32 else exe   # 표시 이름이 없거나 장황하면 exe명
            SCANNED.update({scope, exe})
            if path:
                ICON_PATHS.setdefault(scope, path)
            walk(hm, [], scope, exe)
        except Exception:
            pass
        return True
    user32.EnumWindows(cb, 0)
    if stats:
        print("  앱 메뉴 스캔:", " · ".join(f"{k} {v}" for k, v in sorted(stats.items())))
    else:
        print("  앱 메뉴 스캔: 0개 — 클래식 Win32 메뉴 앱(메모장++·7-Zip·IrfanView 등)이 떠 있어야 잡힙니다 (Chrome/Office/UWP는 메뉴가 커스텀이라 불가)")

def reuse_prev_menus():   # 이번에 안 뜬 앱의 메뉴 단축키는 이전 스캔에서 유지 (맥 collect_menus 재사용 대응)
    p = os.path.join(ROOT, "shortcuts.json")
    if not os.path.exists(p):
        return
    try:
        prev = json.load(open(p, encoding="utf-8"))
    except Exception:
        return
    if (prev.get("meta") or {}).get("platform") != "windows":   # 맥 데이터와는 절대 안 섞음
        return
    kept = {}
    for e in prev.get("entries") or []:
        if e.get("source") != "app menu":
            continue
        exe = (e.get("detail") or "").split("·")[-1].strip()
        if e.get("scope") in SCANNED or exe in SCANNED:   # 이번에 새로 스캔된 앱 → 새 결과 사용
            continue
        entries.append(e); kept[e["scope"]] = kept.get(e["scope"], 0) + 1
    if kept:
        MENU_SCAN.update(reused=sum(kept.values()), kept_apps=sorted(kept),
                         as_of=(prev.get("meta") or {}).get("generated"))
        for s, u in ((prev.get("meta") or {}).get("icons") or {}).items():   # 유지된 앱은 아이콘도 유지
            if s in kept:
                PREV_ICONS[s] = u
        print("  이전 스캔 재사용:", " · ".join(f"{k} {v}" for k, v in sorted(kept.items())),
              "— 앱을 다시 띄우고 실행하면 갱신")

def extract_icons():   # {scope: exe} → {scope: data URI PNG} — PowerShell System.Drawing으로 exe 아이콘 추출
    icons = {}
    if os.name != "nt" or not ICON_PATHS:
        return icons
    import base64, subprocess, tempfile
    ICON_PATHS.setdefault("파일 탐색기", os.path.expandvars(r"%WINDIR%\explorer.exe"))
    for c in (r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe", r"%ProgramFiles%\Microsoft VS Code\Code.exe"):
        c = os.path.expandvars(c)
        if os.path.exists(c):
            ICON_PATHS.setdefault("Code", c); break
    with tempfile.TemporaryDirectory() as td:
        lines, outs = ["Add-Type -AssemblyName System.Drawing"], {}
        for i, (scope, exe) in enumerate(ICON_PATHS.items()):
            if not exe or not os.path.exists(exe) or "'" in exe:
                continue
            out = os.path.join(td, f"i{i}.png"); outs[scope] = out
            lines.append(f"try{{[System.Drawing.Icon]::ExtractAssociatedIcon('{exe}').ToBitmap()"
                         f".Save('{out}',[System.Drawing.Imaging.ImageFormat]::Png)}}catch{{}}")
        try:
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ";".join(lines)],
                           capture_output=True, timeout=120)
        except Exception as e:
            print("  아이콘 추출 실패:", e); return icons
        for scope, out in outs.items():
            if os.path.exists(out):
                icons[scope] = "data:image/png;base64," + base64.b64encode(open(out, "rb").read()).decode()
    if icons:
        print(f"  앱 아이콘 {len(icons)}개")
    return icons

# ── 1) AutoHotKey 스크립트 파싱 ─────────────────────────────────────────────
# AHK 핫키 문법: 접두 기호(^Ctrl !Alt +Shift #Win) + 키 + "::" + 액션.  예:  ^!c::Run calc.exe
AHK_MOD = {"^": "ctrl", "!": "opt", "+": "shift", "#": "cmd"}   # Alt→opt, Win→cmd
AHK_KEYNAME = {  # AHK 키 이름 → 공유 스키마 키
    "space": "Space", "enter": "Return", "return": "Return", "tab": "Tab", "esc": "Escape", "escape": "Escape",
    "delete": "ForwardDelete", "backspace": "Delete", "left": "Left", "right": "Right", "up": "Up", "down": "Down",
    "home": "Home", "end": "End", "pgup": "PageUp", "pgdn": "PageDown",
}
_AHK_LINE = re.compile(r'^\s*([\^!+#<>*~$]*)([A-Za-z0-9]|[a-z]+|F\d{1,2})::(.+?)\s*(?:;.*)?$')

def collect_ahk(paths):
    files = [f for p in paths for f in glob.glob(os.path.expandvars(p))]   # %USERPROFILE% 등 확장 (expanduser는 %VAR%를 못 푼다)
    if not files:
        print("  AutoHotKey: *.ahk 스크립트 없음"); return
    for f in files:
        try:
            n = 0
            for line in open(f, encoding="utf-8-sig", errors="ignore"):
                m = _AHK_LINE.match(line)
                if not m:
                    continue
                pre, rawkey, action = m.groups()
                mods = [AHK_MOD[c] for c in pre if c in AHK_MOD]
                key = AHK_KEYNAME.get(rawkey.lower())
                if key is None:
                    key = rawkey.upper() if len(rawkey) == 1 else (rawkey if re.match(r"F\d", rawkey, re.I) else None)
                add(mods, key, action.strip(), source="AutoHotKey",
                    detail=f"AHK: {os.path.basename(f)}", group="AutoHotKey")
                n += 1
            print(f"  AutoHotKey {n}개 ({os.path.basename(f)})")
        except Exception as e:
            print("  ahk parse fail", f, e)

# ── 2) PowerToys Keyboard Manager — 키/단축키 리맵 (VK 코드 디코드) ─────────
def collect_powertoys():
    p = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\PowerToys\Keyboard Manager\default.json")
    if not os.path.exists(p):
        print("  PowerToys: Keyboard Manager 설정 없음(미설치/미사용)"); return
    try:
        d = json.load(open(p, encoding="utf-8-sig"))
    except Exception as e:
        print("  powertoys parse fail", e); return
    def target(r):   # 리맵 "대상" 설명
        if r.get("runProgramFilePath"): return "실행: " + os.path.basename(r["runProgramFilePath"])
        if r.get("openUri"):            return "열기: " + r["openUri"]
        txt = r.get("newRemapString") or r.get("unicodeText")
        if txt:                          return "텍스트 입력: " + str(txt)[:40]
        if r.get("newRemapKeys") is not None: return "리맵 → " + (vk_disp(r["newRemapKeys"]) or "?")
        return "리맵"
    n = 0
    for sec in ("remapKeys", "remapKeysToText"):         # 단일 키 리맵 (예: CapsLock→Esc)
        for r in (d.get(sec) or {}).get("inProcess", []) or []:
            mods, key = vk_seq(r.get("originalKeys"))
            if key:
                add(mods, key, target(r), source="PowerToys", detail="Keyboard Manager 키 리맵", group="PowerToys"); n += 1
    for sec in ("remapShortcuts", "remapShortcutsToText"):   # 단축키 리맵 (global/appSpecific)
        for lst in (d.get(sec) or {}).values():
            for r in lst or []:
                mods, key = vk_seq(r.get("originalKeys"))
                app = (r.get("targetApp") or "").strip()
                if key:
                    add(mods, key, target(r), source="PowerToys", scope=app or "global",
                        detail="Keyboard Manager 단축키 리맵", group="PowerToys"); n += 1
    if n:
        print(f"  PowerToys 리맵 {n}개")

# ── 3) .lnk 바로 가기 키 — 시작 메뉴·바탕화면 (탐색기가 글로벌로 등록) ───────
def collect_lnk_hotkeys():
    roots = [r"%APPDATA%\Microsoft\Windows\Start Menu\Programs",
             r"%ProgramData%\Microsoft\Windows\Start Menu\Programs",
             r"%USERPROFILE%\Desktop", r"%PUBLIC%\Desktop"]
    LNK_MOD = {1: "shift", 2: "ctrl", 4: "opt"}   # [MS-SHLLINK] HotKeyFlags 상위 바이트
    n = 0
    for root in roots:
        root = os.path.expandvars(root)
        if not os.path.isdir(root):
            continue
        for dp, _, fs in os.walk(root):
            for f in fs:
                if not f.lower().endswith(".lnk"):
                    continue
                try:
                    with open(os.path.join(dp, f), "rb") as fh:
                        head = fh.read(0x4C)
                    if len(head) < 0x4C or head[:4] != b"L\x00\x00\x00":
                        continue
                    hk = struct.unpack_from("<H", head, 0x40)[0]   # HotKey 필드 (0=없음)
                    if not hk:
                        continue
                    key = VK.get(hk & 0xFF)
                    mods = [m for b, m in LNK_MOD.items() if (hk >> 8) & b]
                    if key:
                        add(mods, key, f"{os.path.splitext(f)[0]} 실행", source=".lnk",
                            detail="바로 가기 키(.lnk)", group="바로 가기"); n += 1
                except Exception:
                    pass
    print(f"  .lnk 바로 가기 키 {n}개" + ("" if n else " (바로 가기 키를 지정한 .lnk 없음)"))

# ── 4) Windows Terminal — settings.json의 actions/keybindings (JSONC) ───────
def collect_terminal():
    cands = [r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json",
             r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe\LocalState\settings.json",
             r"%LOCALAPPDATA%\Microsoft\Windows Terminal\settings.json"]
    for c in cands:
        p = os.path.expandvars(c)
        if not os.path.exists(p):
            continue
        try:
            d = json.loads(_jsonc(open(p, encoding="utf-8-sig").read()))
        except Exception as e:
            print("  terminal parse fail", e); return
        n = 0
        for r in (d.get("actions") or []) + (d.get("keybindings") or []):
            if not isinstance(r, dict):
                continue
            keys = r.get("keys")
            keys = keys[0] if isinstance(keys, list) and keys else keys
            if not isinstance(keys, str):
                continue
            pk = parse_keystr(keys)
            cmd = r.get("command")
            if isinstance(cmd, dict):
                cmd = " ".join(str(v) for v in [cmd.get("action")] + [cmd.get(k) for k in ("direction", "target")] if v)
            if not pk or cmd in (None, "unbound"):
                continue
            add(pk[0], pk[1], str(cmd), source="app config", scope="Windows Terminal",
                detail="settings.json", group="Windows Terminal"); n += 1
        print(f"  Windows Terminal {n}개" + ("" if n else " (사용자 지정 키 없음 — 기본 키는 패키지 내부 defaults.json이라 settings.json엔 안 나옴)"))
        return
    print("  Windows Terminal: settings.json 없음")

# ── 5) VS Code — 기본 키맵 덤프(repo 루트) + 사용자 keybindings.json ─────────
# 기본 키맵: VS Code에서 Ctrl+Shift+P → "Preferences: Open Default Keyboard Shortcuts (JSON)"
#           → 내용 전체를 repo 루트에 vscode_default_keybindings.json 으로 저장 (gitignored).
def collect_vscode():
    cands = [(os.path.join(ROOT, "vscode_default_keybindings.json"), "기본"),
             (os.path.expandvars(r"%APPDATA%\Code\User\keybindings.json"), "사용자 지정")]
    for p, kind in cands:
        if not os.path.exists(p):
            if kind == "기본":
                print("  VS Code 기본 키맵: 덤프 없음 — VS Code에서 Ctrl+Shift+P → 'Preferences: Open Default Keyboard"
                      " Shortcuts (JSON)' 내용을 repo 루트에 vscode_default_keybindings.json 으로 저장하면 ~1200개가 들어옵니다")
            continue
        try:
            rows = json.loads(_jsonc(open(p, encoding="utf-8-sig").read()))
        except Exception as e:
            print("  vscode parse fail", p, e); continue
        n = 0
        for r in rows if isinstance(rows, list) else []:
            cmd = r.get("command", "")
            if not cmd or cmd.startswith("-"):   # "-command" = 바인딩 해제
                continue
            ks = (r.get("key") or "").split()
            pk = parse_keystr(ks[0]) if ks else None
            if not pk:
                continue
            extra = {}
            if len(ks) > 1:                      # chord: 1st press 그리드 + 2nd press cmods/ckey
                ck = parse_keystr(ks[1])
                if ck:
                    extra = {"cmods": ck[0], "ckey": ck[1]}
            when = r.get("when", "")
            add(pk[0], pk[1], cmd, source="app config", scope="Code",
                detail=(f"when: {when}" if when else f"VS Code {kind}"), group="Code", **extra); n += 1
        if n:
            print(f"  VS Code {kind} {n}개 ({os.path.basename(p)})")

# ── 6) 시스템 기본 단축키 시드 (맥 build.py의 DEFAULTS 대응) ──────────────────
def collect_system_defaults():
    W = [  # (mods, key, action) — Win→cmd, Alt→opt
        (["cmd"], "E", "파일 탐색기"), (["cmd"], "R", "실행(Run)"), (["cmd"], "D", "바탕화면 표시"),
        (["cmd"], "L", "화면 잠금"), (["cmd"], "Tab", "작업 보기"), (["cmd", "shift"], "S", "영역 캡처"),
        (["ctrl", "shift"], "Escape", "작업 관리자"), (["cmd"], "V", "클립보드 기록"),
        (["opt"], "Tab", "앱 전환"), (["opt"], "F4", "창/앱 닫기"),
        (["cmd"], "I", "설정"), (["cmd"], "A", "빠른 설정"), (["cmd"], "N", "알림 센터"),
        (["cmd"], "X", "빠른 링크 메뉴"), (["cmd"], "S", "검색"), (["cmd"], ".", "이모지 패널"),
        (["cmd"], "P", "디스플레이 전환(프로젝션)"), (["cmd"], "K", "캐스트/장치 연결"),
        (["cmd"], "G", "게임 바"), (["cmd"], "H", "음성 입력"), (["cmd"], "U", "접근성 설정"),
        (["cmd"], "M", "모든 창 최소화"), (["cmd"], ",", "바탕화면 훔쳐보기(Peek)"),
        (["cmd"], "W", "위젯"), (["cmd"], "Z", "스냅 레이아웃"),
        (["cmd"], "Left", "창 왼쪽 스냅"), (["cmd"], "Right", "창 오른쪽 스냅"),
        (["cmd"], "Up", "창 최대화"), (["cmd"], "Down", "창 최소화/복원"),
        (["cmd"], "Home", "활성 창 외 모두 최소화"),
        (["cmd", "ctrl"], "D", "새 가상 데스크톱"), (["cmd", "ctrl"], "F4", "가상 데스크톱 닫기"),
        (["cmd", "ctrl"], "Left", "이전 가상 데스크톱"), (["cmd", "ctrl"], "Right", "다음 가상 데스크톱"),
        ([], "PrintScreen", "화면 캡처(캡처 도구)"), (["cmd"], "PrintScreen", "스크린샷을 파일로 저장"),
    ]
    for mods, key, action in W:
        add(mods, key, action, source="system", detail="Windows 기본 단축키", group="Windows 시스템")
    E = [  # 파일 탐색기 (Delete=⌫백스페이스 토큰이므로 Del 키는 ForwardDelete)
        ([], "F2", "이름 바꾸기"), ([], "F4", "주소 표시줄 목록"), ([], "F5", "새로 고침"), ([], "F6", "창 요소 간 이동"),
        ([], "F11", "전체 화면"), (["ctrl", "shift"], "N", "새 폴더"), (["opt"], "Return", "속성"),
        (["opt"], "Up", "상위 폴더"), (["opt"], "Left", "뒤로"), (["opt"], "Right", "앞으로"),
        (["ctrl"], "L", "주소 표시줄"), (["ctrl"], "E", "검색 상자"), (["ctrl"], "N", "새 창"),
        (["ctrl"], "T", "새 탭"), (["ctrl"], "W", "탭/창 닫기"), (["ctrl", "shift"], "T", "닫은 탭 다시 열기"),
        ([], "ForwardDelete", "휴지통으로 삭제"), (["shift"], "ForwardDelete", "영구 삭제"),
        (["ctrl", "shift"], "C", "경로 복사"),
    ]
    for mods, key, action in E:
        add(mods, key, action, source="system", scope="파일 탐색기", detail="탐색기 기본 단축키", group="파일 탐색기")

# ── 7) 수동 글로벌 (맥 manual_globals.json 대응) ───────────────────────────
def collect_manual():
    p = os.path.join(PROJ, "manual_globals_win.json")
    if not os.path.exists(p):
        return
    for e in json.load(open(p, encoding="utf-8")):
        add(e.get("mods", []), e.get("key", ""), e.get("action", ""),
            source=e.get("source", "manual"), scope=e.get("scope", "global"), group=e.get("group"))

def main():
    collect_system_defaults()
    collect_win32_menus()
    collect_ahk([r"%USERPROFILE%\Documents\AutoHotkey\*.ahk", r"%USERPROFILE%\*.ahk"])
    collect_powertoys()
    collect_lnk_hotkeys()
    collect_terminal()
    collect_vscode()
    collect_manual()
    reuse_prev_menus()

    # 정확 중복 제거 (같은 조합+동작+소스+스코프)
    seen, uniq = set(), []
    for e in entries:
        k = (tuple(e["mods"]), e["key"], e["action"], e["source"], e["scope"], e.get("ckey"))
        if k not in seen:
            seen.add(k); uniq.append(e)
    entries[:] = uniq

    from collections import Counter
    apps = sorted({e["scope"] for e in entries if e["scope"].lower() != "global"})
    meta = {"generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "platform": "windows",
            "counts": dict(Counter(e["source"] for e in entries)), "apps": apps, "bttgroups": [],
            "total": len(entries), "icons": {**PREV_ICONS, **extract_icons()},
            "env": {"os": platform.platform()}, "menu_scan": MENU_SCAN}
    data = {"meta": meta, "entries": entries, "gestures": [], "ann": {"fav": {}, "note": {}, "enote": {}, "custom": [], "ghk": []}}
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "shortcuts.json")   # 테스트용: 다른 경로에 쓸 수 있게
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{out} — {len(entries)}개 (Windows). 이제: python render.py 로 viewer.html 생성")

if __name__ == "__main__":
    main()
