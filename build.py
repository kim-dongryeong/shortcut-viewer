#!/usr/bin/env python3
# build.py — collect macOS keyboard shortcuts from every readable source, normalize to one
# canonical schema, and emit a self-contained interactive keyboard-grid viewer (viewer.html).
#
# Sources:
#   system     macOS system shortcuts  (defaults: com.apple.symbolichotkeys)
#   Karabiner  ~/.config/karabiner/karabiner.json
#   BTT        BetterTouchTool (bttcli export_preset — needs Socket Server enabled)
#   Raycast    raycast_manual.json (Raycast's DB is encrypted; list hotkeys here by hand)
#   app menu   ./axmenudump (Accessibility API; per-app menu shortcuts of running apps)
import json, subprocess, os, plistlib, datetime, re, sqlite3, glob, tempfile, shutil, base64, platform

HOME = os.path.expanduser("~")
PROJ = os.path.dirname(os.path.abspath(__file__))
def _scrub(s):   # strip home/username paths so action/detail (and the shared defaults/ + web corpus) carry no PII
    if not s: return s
    s = s.replace(HOME, "~")
    return re.sub(r"/Users/[^/\s'\"]+", "/Users/USER", s)

# ---------- lookup tables ----------
# Carbon/HID virtual key code -> label (kVK_*). Shared by symbolichotkeys & AX virtual keys.
KEYCODE = {
    0:'A',1:'S',2:'D',3:'F',4:'H',5:'G',6:'Z',7:'X',8:'C',9:'V',11:'B',12:'Q',13:'W',
    14:'E',15:'R',16:'Y',17:'T',18:'1',19:'2',20:'3',21:'4',22:'6',23:'5',24:'=',25:'9',
    26:'7',27:'-',28:'8',29:'0',30:']',31:'O',32:'U',33:'[',34:'I',35:'P',37:'L',38:'J',
    39:"'",40:'K',41:';',42:'\\',43:',',44:'/',45:'N',46:'M',47:'.',50:'`',
    36:'Return',48:'Tab',49:'Space',51:'Delete',53:'Escape',
    123:'Left',124:'Right',125:'Down',126:'Up',
    115:'Home',119:'End',116:'PageUp',121:'PageDown',117:'ForwardDelete',
    122:'F1',120:'F2',99:'F3',118:'F4',96:'F5',97:'F6',98:'F7',100:'F8',101:'F9',
    109:'F10',103:'F11',111:'F12',105:'F13',107:'F14',113:'F15',106:'F16',64:'F17',
    79:'F18',80:'F19',90:'F20',
}
# NSEvent device-independent modifier flags (used by symbolichotkeys & BTT)
MODMASK = [(0x20000,'shift'),(0x40000,'control'),(0x80000,'option'),(0x100000,'command'),(0x800000,'fn')]
# AX menu-item glyph code -> label (fallback; we prefer the virtual key)
GLYPH = {2:'Tab',3:'Tab',4:'Enter',9:'Space',10:'Delete',11:'Return',23:'Delete',27:'Escape',
         98:'PageUp',99:'PageDown',100:'Left',101:'Right',102:'Up',103:'Down',105:'F13'}
# symbolichotkey numeric id -> human name (community-maintained; best-effort)
SYMBOLIC = {
    7:'Toggle full keyboard access',10:'Move focus to menu bar',11:'Move focus to Dock',
    12:'Move focus to active/next window',13:'Move focus to window toolbar',
    15:'Move focus to floating window',27:'Toggle character viewer',
    28:'Screenshot: save screen to file',29:'Screenshot: copy screen',
    30:'Screenshot: save selection to file',31:'Screenshot: copy selection',
    32:'Mission Control',33:'Mission Control: Dashboard',34:'Mission Control: App windows (alt)',
    35:'Application windows',36:'Show Desktop',37:'Show Dashboard',
    52:'Toggle Dock hiding',57:'Toggle Mission Control',
    60:'Select previous input source',61:'Select next input source',
    62:'Toggle window full screen? ',64:'Spotlight: Show search',65:'Spotlight: Show Finder search',
    70:'Show Help menu',79:'Move left a space',80:'Move left a space (alt)',
    81:'Move right a space',82:'Move right a space (alt)',
    118:'Switch to Desktop 1',119:'Switch to Desktop 2',120:'Switch to Desktop 3',
    121:'Switch to Desktop 4',160:'Launchpad',162:'Show Launchpad',163:'Notification Center',
    175:'Dictation',179:'Siri',184:'Screenshot and recording options',190:'Quick Note',
    222:'Stage Manager',
}

# Well-known macOS default system shortcuts. The symbolichotkeys plist only stores combos the
# user explicitly *changed*, so defaults like Spotlight never appear there — we seed them here.
DEFAULTS = [
    (['cmd'],'Space','Spotlight 검색'),(['cmd','opt'],'Space','Finder 검색 창'),
    (['cmd','ctrl'],'Space','이모지 & 기호 보기'),
    (['cmd','shift'],'3','스크린샷: 전체(파일)'),(['cmd','shift'],'4','스크린샷: 영역(파일)'),
    (['cmd','shift'],'5','스크린샷/녹화 옵션'),
    (['cmd','ctrl','shift'],'3','스크린샷: 전체(클립보드)'),(['cmd','ctrl','shift'],'4','스크린샷: 영역(클립보드)'),
    (['ctrl'],'Up','Mission Control'),(['ctrl'],'Down','App Exposé'),
    (['ctrl'],'Left','왼쪽 공간으로'),(['ctrl'],'Right','오른쪽 공간으로'),
    (['ctrl'],'1','데스크탑 1'),(['ctrl'],'2','데스크탑 2'),(['ctrl'],'3','데스크탑 3'),
    (['cmd'],'Tab','앱 전환'),(['cmd'],'`','앱 내 창 전환'),
    (['cmd','ctrl'],'Q','화면 잠금'),(['cmd','opt'],'Escape','강제 종료'),
    (['cmd','ctrl'],'F','전체 화면 전환'),(['cmd','opt'],'D','Dock 자동 숨기기'),
    (['cmd','shift'],'/','도움말 검색'),
    (['cmd','ctrl'],'D','단어를 사전에서 찾기 (룩업)'),
    (['fn'],'E','이모지 & 기호 (Globe+E)'),(['fn'],'C','제어 센터'),(['fn'],'N','알림 센터'),
    (['fn'],'D','받아쓰기'),(['fn'],'A','Dock 포커스'),(['fn'],'F','전체 화면 전환'),
    (['fn'],'Q','빠른 메모'),(['fn'],'M','메뉴 막대 포커스'),
]

# Curated default shortcuts for frequently-used apps, so they appear without the Accessibility scan.
# Scope strings match each app's NSWorkspace localizedName so the live menu scan merges/dedups cleanly.
APP_DEFAULTS = {
  "Finder": [
    (['cmd','shift'],'.','숨김 파일 표시 토글'),(['cmd','shift'],'N','새 폴더'),(['cmd','shift'],'G','폴더로 이동…'),
    (['cmd','shift'],'A','응용 프로그램'),(['cmd','shift'],'U','유틸리티'),(['cmd','shift'],'H','홈'),
    (['cmd','shift'],'D','데스크탑'),(['cmd','shift'],'O','문서'),(['cmd','shift'],'C','컴퓨터'),
    (['cmd','shift'],'R','AirDrop'),(['cmd','shift'],'I','iCloud Drive'),(['cmd','shift'],'K','네트워크'),
    (['cmd'],'Delete','휴지통으로 이동'),(['cmd','shift'],'Delete','휴지통 비우기'),
    (['cmd'],'I','정보 가져오기'),(['cmd'],'D','복제'),(['cmd'],'Up','상위 폴더'),(['cmd'],'Down','열기'),
    (['cmd'],'N','새 윈도우'),(['cmd'],'T','새 탭'),
    (['cmd'],'1','아이콘 보기'),(['cmd'],'2','목록 보기'),(['cmd'],'3','계층 보기'),(['cmd'],'4','갤러리 보기'),
  ],
  "Google Chrome": [
    (['cmd'],'T','새 탭'),(['cmd'],'W','탭 닫기'),(['cmd','shift'],'T','닫은 탭 다시 열기'),
    (['cmd'],'N','새 창'),(['cmd','shift'],'N','새 시크릿 창'),(['cmd'],'L','주소창 포커스'),
    (['cmd'],'R','새로고침'),(['cmd','shift'],'R','강력 새로고침'),(['cmd'],'F','페이지 내 찾기'),
    (['cmd'],'D','북마크 추가'),(['cmd','shift'],'B','북마크바 토글'),(['cmd'],'Y','방문 기록'),
    (['cmd','shift'],'J','다운로드'),(['cmd','opt'],'I','개발자 도구'),(['cmd','opt'],'J','콘솔'),
    (['cmd','opt'],'C','요소 검사'),(['cmd','opt'],'U','소스 보기'),
    (['cmd','opt'],'Right','다음 탭'),(['cmd','opt'],'Left','이전 탭'),
    (['cmd','shift'],'A','탭 검색'),(['cmd','shift'],'Delete','인터넷 기록 삭제'),
    (['cmd'],'=','확대'),(['cmd'],'-','축소'),(['cmd'],'0','기본 배율'),
  ],
  "Safari": [
    (['cmd'],'T','새 탭'),(['cmd'],'W','탭 닫기'),(['cmd','shift'],'T','닫은 탭 다시 열기'),
    (['cmd'],'N','새 윈도우'),(['cmd','shift'],'N','새 개인정보 윈도우'),(['cmd'],'L','스마트 검색창'),
    (['cmd'],'R','새로고침'),(['cmd','shift'],'R','리더 보기 토글'),(['cmd'],'F','페이지 내 찾기'),
    (['cmd'],'D','책갈피 추가'),(['cmd','shift'],'\\','모든 탭 보기'),
    (['cmd','shift'],']','다음 탭'),(['cmd','shift'],'[','이전 탭'),
    (['cmd','opt'],'I','웹 속성 보기(인스펙터)'),(['cmd','opt'],'C','자바스크립트 콘솔'),
    (['cmd'],'=','확대'),(['cmd'],'-','축소'),(['cmd'],'0','기본 배율'),
  ],
  "Google Drive (웹)": [
    ([],'/','검색 포커스 (웹 전용)'),(['shift'],'/','단축키 도움말 (웹)'),(['cmd'],'A','전체 선택 (웹)'),
  ],
}

CANON = {'command':'cmd','cmd':'cmd','option':'opt','opt':'opt','alt':'opt',
         'control':'ctrl','ctrl':'ctrl','shift':'shift','fn':'fn',
         '⌘':'cmd','⌥':'opt','⌃':'ctrl','⇧':'shift'}
ORDER = ['ctrl','opt','shift','cmd','fn']

def norm_mods(mods):
    s = {CANON.get(str(m).lower(), str(m).lower()) for m in mods}
    return [m for m in ORDER if m in s]

def decode_modmask(m):
    m = int(m or 0)
    return [name for bit,name in MODMASK if m & bit]

entries = []
gestures = []   # non-static triggers (no regular key): tap-count/hold modifier gestures, L/R-specific.
def addg(mod, action, source, scope, detail="", side="either", count=1, hold=False, group=None):
    # mod: cmd|opt|ctrl|shift|fn|caps · side: either|left|right · count: tap count · hold: hold final press
    try: count = int(count)
    except Exception: count = 1   # tolerate a bad hand-edited manual_gestures.json without aborting the whole build
    gestures.append({"mod": mod, "side": side, "count": count, "hold": bool(hold),
                     "action": (action or "").strip() or "(untitled)", "source": source,
                     "scope": scope, "detail": detail, "group": group or source})
# macOS sets NSEvent's Function flag (0x800000) automatically on these keys — it does NOT mean
# the physical fn/Globe key was pressed — so strip 'fn' from their combos.
FN_INTRINSIC = {f"F{i}" for i in range(1, 21)} | {"Left","Right","Up","Down","Home","End","PageUp","PageDown","ForwardDelete"}
def add(mods, key, action, source, scope, detail="", group=None, cmods=None, ckey=None):
    if not key: return
    m = norm_mods(mods)
    if key in FN_INTRINSIC and "fn" in m: m = [x for x in m if x != "fn"]
    e = {"mods": m, "key": str(key), "action": _scrub((action or "").strip()) or "(untitled)",
         "source": source, "scope": scope, "detail": _scrub(detail), "group": group or source}
    if ckey:                                   # chord: 2nd press (예: ⌘K ⌘I) — only stored when present
        cm = norm_mods(cmods or [])
        if ckey in FN_INTRINSIC and "fn" in cm: cm = [x for x in cm if x != "fn"]
        e["cmods"] = cm; e["ckey"] = str(ckey)
    entries.append(e)
    return e

def norm_keytoken(tok):
    if not tok: return None
    t = tok.strip()
    low = t.lower()
    named = {'space':'Space','spacebar':'Space','return':'Return','enter':'Return','tab':'Tab',
             'delete':'Delete','backspace':'Delete','escape':'Escape','esc':'Escape',
             'left':'Left','right':'Right','up':'Up','down':'Down','home':'Home','end':'End',
             'pageup':'PageUp','pagedown':'PageDown','capslock':'CapsLock','grave':'`','tilde':'`'}
    if low in named: return named[low]
    if low.startswith('f') and low[1:].isdigit(): return 'F'+low[1:]
    if len(t)==1: return t.upper()
    return t

def parse_combo(s):
    parts = [p for p in str(s).replace(' ','').split('+') if p]
    if not parts: return [], None
    mods, key = [], parts[-1]
    for p in parts[:-1]:
        if p.lower()=='hyper': mods += ['ctrl','opt','shift','cmd']
        elif p.lower()=='meh': mods += ['ctrl','opt','shift']
        else: mods.append(p)
    return mods, norm_keytoken(key)

# ---------- collectors ----------
def collect_system():
    try:
        raw = subprocess.run(["defaults","export","com.apple.symbolichotkeys","-"],
                             capture_output=True).stdout
        d = plistlib.loads(raw).get("AppleSymbolicHotKeys", {})
    except Exception as e:
        print("  system: skip (", e, ")"); return 0
    n = 0
    for k, v in d.items():
        if not isinstance(v, dict) or not v.get("enabled"): continue
        val = v.get("value") or {}
        if val.get("type") != "standard": continue
        p = val.get("parameters") or []
        if len(p) < 3 or p[1] == 65535: continue
        key = KEYCODE.get(int(p[1]))
        if key is None:
            key = chr(p[0]).upper() if isinstance(p[0],int) and 32 < p[0] < 127 else f"kc{p[1]}"
        add(decode_modmask(p[2]), key, SYMBOLIC.get(int(k), f"System #{k}"),
            "system", "global", f"symbolichotkey id={k}")
        n += 1
    return n

KARA_KEY = {'grave_accent_and_tilde':'`','caps_lock':'CapsLock','spacebar':'Space',
            'return_or_enter':'Return','delete_or_backspace':'Delete','escape':'Escape',
            'hyphen':'-','equal_sign':'=','open_bracket':'[','close_bracket':']',
            'backslash':'\\','semicolon':';','quote':"'",'comma':',','period':'.','slash':'/',
            'left_arrow':'Left','right_arrow':'Right','up_arrow':'Up','down_arrow':'Down'}
def kara_key(kc):
    if kc in KARA_KEY: return KARA_KEY[kc]
    if len(kc)==1: return kc.upper()
    if kc.isdigit(): return kc
    return kc
def kara_mod(m):
    m = m.replace('left_','').replace('right_','')
    return {'command':'cmd','option':'opt','control':'ctrl','shift':'shift'}.get(m, m)

def collect_defaults():
    have = {(frozenset(e["mods"]), e["key"]) for e in entries if e["source"] == "system"}
    n = 0
    for mods, key, name in DEFAULTS:
        if (frozenset(norm_mods(mods)), key) in have: continue
        add(mods, key, name, "system", "global", "macOS 기본 단축키"); n += 1
    return n

def collect_app_defaults():
    # Seed curated app shortcuts, skipping any combo already present for that app (e.g. from the menu scan).
    have = {(e["scope"], frozenset(e["mods"]), e["key"]) for e in entries}
    n = 0
    for app, lst in APP_DEFAULTS.items():
        for mods, key, name in lst:
            nk = norm_keytoken(key)
            if (app, frozenset(norm_mods(mods)), nk) in have: continue
            add(mods, nk, name, "app config", app, "기본(curated)")
            have.add((app, frozenset(norm_mods(mods)), nk)); n += 1
    return n

def collect_karabiner():
    p = os.path.join(HOME, ".config/karabiner/karabiner.json")
    if not os.path.exists(p): print("  Karabiner: no config"); return 0
    data = json.load(open(p)); n = 0
    # scope는 'global'이 정직하다(리맵은 모든 앱에서 동작). 대신 group="Karabiner-Elements"로 그 칩에 묶는다 —
    # 뷰어 inCtx가 e.group도 매칭하므로 Global에도, Karabiner-Elements 컨텍스트에도 뜬다(BTT가 쓰는 방식과 동일).
    KGROUP = "Karabiner-Elements"
    profs = data.get("profiles", [])
    active = [pr for pr in profs if pr.get("selected")] or profs[:1]   # only the SELECTED profile is live; ignore inactive profiles
    for prof in active:
        for sm in prof.get("simple_modifications", []):
            kc = (sm.get("from") or {}).get("key_code")
            to = ",".join((t.get("key_code") or "?") for t in sm.get("to", []))
            add([], kara_key(kc), f"→ {to}", "Karabiner", "global", "simple_modification", group=KGROUP); n += 1
        KSYM = {'cmd': '⌘', 'opt': '⌥', 'ctrl': '⌃', 'shift': '⇧', 'fn': '🌐'}
        for rule in prof.get("complex_modifications", {}).get("rules", []):
            if rule.get("enabled", True) is False: continue   # Karabiner UI로 끈 규칙(enabled:false)은 실제 비활성 → 제외
            desc = rule.get("description", "")
            for man in rule.get("manipulators", []):
                frm = man.get("from") or {}; kc = frm.get("key_code")
                if not kc: continue
                mods = [kara_mod(x) for x in (frm.get("modifiers") or {}).get("mandatory", [])]
                to_parts = []                                  # 어디로 매핑되는지 (예: → ⌘Space)
                for t in (man.get("to") or []):
                    tk = t.get("key_code")
                    if tk:
                        tm = [kara_mod(x) for x in (t.get("modifiers") or [])]
                        to_parts.append("".join(KSYM.get(x, x) for x in tm) + kara_key(tk))
                    elif t.get("shell_command"): to_parts.append("셸 명령")
                    elif t.get("set_variable"): to_parts.append("변수:" + (t["set_variable"].get("name") or ""))
                to_str = " ".join(to_parts)
                action = (f"{desc} → {to_str}" if desc and to_str else (f"→ {to_str}" if to_str else (desc or "remap")))
                add(mods, kara_key(kc), action, "Karabiner", "global", "complex_modification", group=KGROUP); n += 1
    return n

# BTTPredefinedActionType (ZACTION on the child action row) → human name. Partial enum
# (BTT-internal; from the developer's community list). Unknown codes shown as "#<code>".
# BTTPredefinedActionType (child row's ZACTION) → name. From the official action-definitions doc
# + forum thread 14116 + this user's live-DB key inference (codex/agy cross-check). Unknown → "#code".
BTT_ACTIONS = {
    3:"Left Click", 17:"Move Window Left", 18:"Move Window Right", 19:"Maximize Left Half",
    20:"Maximize Right Half", 21:"Maximize Window", 49:"Launch / Open", 54:"Double Left Click",
    57:"Open BTT Preferences", 59:"Open URL", 61:"Page Down", 90:"Top-Left Quarter",
    91:"Top-Right Quarter", 92:"Bottom-Left Quarter", 93:"Bottom-Right Quarter", 105:"Show BTT Preferences",
    128:"Send Shortcut to Specific App", 139:"Switch To Preset", 153:"Move Mouse To Position",
    154:"Save Mouse Position", 155:"Restore Mouse Position", 172:"Run AppleScript", 193:"Type / Paste Text",
    206:"Execute Shell Script", 216:"Move Window to Desktop 1", 217:"Move Window to Desktop 2",
    218:"Move Window to Desktop 3", 248:"Trigger Named Trigger", 251:"Custom Move/Resize Window",
    254:"Show HUD", 258:"Toggle Preset", 264:"Send Keyboard Shortcut", 281:"Run JavaScript",
    329:"Start Repeat / For Loop", 332:"If Condition", 337:"Pin/Unpin Window",
    345:"Delay Next Action", 364:"Activate Specific Window", 403:"Ask For Input, Save To Variable",
    421:"Left Click", 446:"Move Window to Size/Position", 522:"Window Action",
}
def btt_param(code, ad, launchpath):
    # pull the salient parameter BTT shows after the action name (ZACTIONDATA is JSON, not bplist)
    j = {}
    if ad:
        try: j = json.loads(ad.decode("utf-8", "replace") if isinstance(ad, bytes) else ad)
        except Exception: j = {}
    if code == 49 and launchpath:
        return os.path.basename(str(launchpath).rstrip("/")) or str(launchpath)
    if code == 403: return j.get("BTTActionAskForInputVariableName", "")
    if code == 329: return j.get("BTTActionForLoopRepeatVariable", "")
    if code == 153 and ("BTTMouseMoveX" in j or "BTTMouseMoveY" in j):
        rnd = lambda v: (str(round(float(v))) if str(v).replace('.', '', 1).lstrip('-').isdigit() else str(v))
        return f"X:{rnd(j.get('BTTMouseMoveX', 0))} Y:{rnd(j.get('BTTMouseMoveY', 0))}"
    if launchpath and str(launchpath).startswith("/"):
        return os.path.basename(str(launchpath).rstrip("/"))
    return ""
def collect_btt():
    # BTT 6+ stores everything in a Core Data SQLite store — read keyboard-shortcut triggers
    # directly (no Socket Server / bttcli needed). ZMODIFIERKEYS is the standard NSEvent mask.
    base = os.path.join(HOME, "Library/Application Support/BetterTouchTool")
    dbs = [p for p in glob.glob(os.path.join(base, "btt_data_store.version_*"))
           if not p.endswith("-wal") and not p.endswith("-shm")]
    if not dbs:
        return _collect_btt_cli()
    src = max(dbs, key=os.path.getmtime)
    tmp = tempfile.mkdtemp(prefix="bttdb_")
    try:
        dst = os.path.join(tmp, "btt.sqlite")
        shutil.copy(src, dst)
        for ext in ("-wal", "-shm"):
            if os.path.exists(src + ext): shutil.copy(src + ext, dst + ext)
        con = sqlite3.connect(dst); con.text_factory = lambda b: b.decode("utf-8", "replace")
        # App-scoped triggers link to an APP entity via the Z_2APPS_GESTURES junction (NOT ZBELONGSTOAPP).
        # BT.* bundles are BTT's own pseudo-apps (Global/Trash/…) → treat as global.
        appmap = {}
        for tpk, aname, abundle in con.execute(
                "SELECT jx.Z_9APPS_GESTURES, app.ZNAME, app.ZBUNDLEIDENTIFIER "
                "FROM Z_2APPS_GESTURES jx JOIN ZBTTBASEENTITY app ON jx.Z_2GESTURES = app.Z_PK"):
            if abundle and not str(abundle).startswith("BT."):
                appmap[tpk] = aname or abundle
        # The real action(s) live in CHILD rows (ZPARENT=trigger); the trigger's own ZACTION is generic.
        # Primary = the lowest-ZORDER child; also count the chain for "and N more".
        primary, chaincnt = {}, {}
        for ppk, zact, ad, lp in con.execute(
                "SELECT ZPARENT, ZACTION, ZACTIONDATA, ZLAUNCHPATH FROM ZBTTBASEENTITY "
                "WHERE ZPARENT IS NOT NULL AND ZACTION IS NOT NULL AND ZACTION > 0 "
                "ORDER BY ZPARENT, COALESCE(ZORDER, ZORDER1, 0), Z_PK"):
            chaincnt[ppk] = chaincnt.get(ppk, 0) + 1
            if ppk not in primary: primary[ppk] = (zact, ad, lp)
        rows = con.execute("""
            SELECT t.Z_PK, t.ZKEYCODE, t.ZMODIFIERKEYS,
                   COALESCE(NULLIF(t.ZDESC,''), NULLIF(t.ZTRIGGERLABEL,''), NULLIF(t.ZACTIONLABEL,''), '') AS label,
                   COALESCE(p.ZNAME3, '') AS preset, COALESCE(p.ZACTIVATED, 0) AS activ
            FROM ZBTTBASEENTITY t
            LEFT JOIN ZBTTBASEENTITY p ON t.ZBELONGSTOPRESET2 = p.Z_PK
            WHERE t.ZKEYCODE IS NOT NULL AND t.ZKEYCODE >= 0
              AND t.ZBELONGSTOKEYSEQUENCEDOWN IS NULL AND t.ZBELONGSTOKEYSEQUENCEMIXED IS NULL
              AND t.ZBELONGSTOKEYSEQUENCEUP IS NULL AND t.ZASSOCIATEDGESTURE IS NULL
              AND COALESCE(t.ZENABLEDNEW, t.ZISENABLED, 1) != 0
        """).fetchall()
        con.close()
    except Exception as e:
        print("  BTT: sqlite read failed (", e, ") — trying CLI")
        shutil.rmtree(tmp, ignore_errors=True); return _collect_btt_cli()
    shutil.rmtree(tmp, ignore_errors=True)
    n = 0
    for pk, kc, mod, label, preset, activ in rows:
        key = KEYCODE.get(int(kc), f"kc{kc}")
        scope = appmap.get(pk, "global")
        if not label:  # no user description → reconstruct a BTT-style action label
            prim = primary.get(pk)
            if prim:
                code, ad, lp = prim
                name = BTT_ACTIONS.get(code, f"#{code}")
                p = btt_param(code, ad, lp)
                cnt = chaincnt.get(pk, 1)
                more = f" and {cnt - 1} more" if cnt > 1 else ""
                label = "Action: " + name + (f": {p}" if p else "") + more
            else:
                label = "BTT 단축키"
        det = (f"BTT 프리셋: {preset}" + (" ✓활성" if (activ or 0) > 0 else " (비활성)")) if preset else "BTT 단축키 (DB 직접 읽음)"
        if scope != "global": det += f" · {scope} 전용"
        add(decode_modmask(mod or 0), key, label, "BTT", scope, det,
            group=(f"BTT · {preset}" if preset else "BTT")); n += 1
    return n

def _collect_btt_cli():
    # Fallback for older BTT (no sqlite store): needs the Socket Server enabled + bttcli.
    bttcli = "/Applications/BetterTouchTool.app/Contents/SharedSupport/bin/bttcli"
    if not os.path.exists(bttcli): print("  BTT: not installed"); return 0
    out = os.path.join(PROJ, "btt_export.json")
    r = subprocess.run([bttcli, "export_preset", "compress=false", "outputPath=" + out],
                       capture_output=True, text=True)
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        print("  BTT: db not found and socket server off —", (r.stdout + r.stderr).strip()[:100]); return 0
    data = json.load(open(out)); triggers = []
    def walk(o):
        if isinstance(o, dict):
            kc = o.get("BTTShortcutKeyCode")
            if isinstance(kc, int) and kc >= 0: triggers.append(o)
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(data); n = 0
    for t in triggers:
        kc = int(t["BTTShortcutKeyCode"]); key = KEYCODE.get(kc, f"kc{kc}")
        name = (t.get("BTTTriggerName") or t.get("BTTShortcutName") or "BTT action")
        add(decode_modmask(t.get("BTTShortcutModifierKeys", 0)), key, name, "BTT", "global", "BTT keyboard shortcut"); n += 1
    return n

def collect_raycast():
    p = os.path.join(PROJ, "raycast_manual.json")
    if not os.path.exists(p):
        json.dump({"_comment": "Raycast's DB is encrypted — list your Raycast hotkeys here by hand. "
                               "combo examples: 'opt+space', 'cmd+shift+k', 'hyper+j'.",
                   "hotkeys": [{"combo": "opt+space", "action": "Raycast 실행 (예시 — 실제로 맞게 고치세요)"}]},
                  open(p, "w"), ensure_ascii=False, indent=2)
        print("  Raycast: created template raycast_manual.json (fill it in)")
    data = json.load(open(p)); n = 0
    for h in data.get("hotkeys", []):
        mods, key = parse_combo(h.get("combo", ""))
        add(mods, key, h.get("action", "Raycast"), "Raycast", "global", "manual entry"); n += 1
    return n

def collect_manual_globals():
    # App-registered OS-global hotkeys no auto-collector can read (e.g. Google Drive desktop search).
    p = os.path.join(PROJ, "manual_globals.json")
    if not os.path.exists(p):
        json.dump({"_comment": "앱이 등록한 OS-글로벌 핫키 중 자동 수집 불가한 것들을 손으로 적으세요. "
                               "combo: 'hyper+g', 'cmd+opt+g'. scope 'global'=어디서나, 또는 앱 이름.",
                   "hotkeys": [{"combo": "hyper+g", "action": "Google Drive 데스크탑 검색", "scope": "global"}]},
                  open(p, "w"), ensure_ascii=False, indent=2)
        print("  manual globals: created manual_globals.json")
    data = json.load(open(p)); n = 0
    for h in data.get("hotkeys", []):
        mods, key = parse_combo(h.get("combo", ""))
        add(mods, key, h.get("action", "manual"), "app config", h.get("scope", "global"),
            "수동 등록(manual_globals.json)"); n += 1
    return n

# Carbon modifier mask (cmdKey/shiftKey/optionKey/controlKey) — used by the KeyboardShortcuts library (Shottr).
CARBON_MODS = [(0x100, 'cmd'), (0x200, 'shift'), (0x800, 'opt'), (0x1000, 'ctrl')]
def decode_carbon(m):
    m = int(m or 0)
    return [name for bit, name in CARBON_MODS if m & bit]

def collect_zoom():
    # macOS Accessibility ▸ Zoom shortcuts are DEFAULTS (not stored in symbolichotkeys) — seed when enabled.
    try:
        ua = plistlib.loads(subprocess.run(["defaults", "export", "com.apple.universalaccess", "-"],
                                            capture_output=True).stdout)
    except Exception: return 0
    if not ua.get("closeViewHotkeysEnabled"): return 0
    have = {(frozenset(e["mods"]), e["key"]) for e in entries if e["source"] == "system"}
    n = 0
    for mods, key, name in [(['cmd','opt'],'8','확대/축소 켜기·끄기 (Zoom)'),
                            (['cmd','opt'],'=','확대 (Zoom in)'),
                            (['cmd','opt'],'-','축소 (Zoom out)')]:
        if (frozenset(norm_mods(mods)), key) in have: continue
        add(mods, key, name, "system", "global", "macOS 손쉬운 사용 ▸ 확대/축소"); n += 1
    return n

SHOTTR_NAMES = {"area":"영역 캡처","fullscreen":"전체 화면 캡처","window":"창 캡처","anyWindow":"임의 창 캡처",
                "scrolling":"스크롤 캡처","ocr":"OCR 텍스트 인식","repeatArea":"직전 영역 다시 캡처",
                "color":"색 추출","selfTimer":"타이머 캡처"}
def collect_shottr():
    try:
        d = plistlib.loads(subprocess.run(["defaults", "export", "cc.ffitch.shottr", "-"],
                                          capture_output=True).stdout)
    except Exception: return 0
    n = 0
    for k, v in d.items():
        if not k.startswith("KeyboardShortcuts_"): continue
        try: cfg = json.loads(v) if isinstance(v, str) else v
        except Exception: continue
        kc = cfg.get("carbonKeyCode")
        if kc is None: continue
        fn = k[len("KeyboardShortcuts_"):]
        add(decode_carbon(cfg.get("carbonModifiers")), KEYCODE.get(int(kc), f"kc{kc}"),
            "Shottr: " + SHOTTR_NAMES.get(fn, fn), "app config", "global",
            "Shottr 글로벌 핫키 (cc.ffitch.shottr)", group="Shottr"); n += 1
    return n

def collect_screenbrush():
    try:
        d = plistlib.loads(subprocess.run(["defaults", "export", "com.imagestudiopro.ScreenBrush", "-"],
                                          capture_output=True).stdout)
    except Exception: return 0
    labels = {"runScreenBrush":"켜기", "runScreenBrushWithoutToolbar":"툴바 없이 켜기"}
    n = 0
    for k, v in d.items():
        if not k.startswith("Shortcut"): continue
        try: parts = base64.b64decode(v).decode("utf-8", "replace").split(",")
        except Exception: continue
        if len(parts) < 4: continue
        name = parts[0].rstrip(":")
        try: nsmask, kc, enabled = int(parts[1]), int(parts[2]), int(parts[3])
        except Exception: continue
        if not enabled: continue
        add(decode_modmask(nsmask), KEYCODE.get(kc, f"kc{kc}"),
            "ScreenBrush: " + labels.get(name, name), "app config", "global",
            "ScreenBrush 글로벌 핫키 (com.imagestudiopro.ScreenBrush)", group="ScreenBrush"); n += 1
    return n

# ----- per-app keymap collectors (the full keymaps that the menu-bar scan can't see) -----
OBS_KEY = {'ArrowUp':'Up','ArrowDown':'Down','ArrowLeft':'Left','ArrowRight':'Right',
           'Backspace':'Delete','Enter':'Return',' ':'Space'}
def obs_mod(m):
    return {'Mod':'cmd','Meta':'cmd','Alt':'opt','Ctrl':'ctrl','Shift':'shift'}.get(m, m.lower())

def collect_obsidian():
    paths = []
    cfg = os.path.join(HOME, "Library/Application Support/obsidian/obsidian.json")
    if os.path.exists(cfg):
        try:
            paths = [v.get("path") for v in json.load(open(cfg)).get("vaults", {}).values() if v.get("path")]
        except Exception: pass
    if not paths: paths = [os.path.join(HOME, "notes/brain")]
    n = 0
    for vp in paths:
        hk = os.path.join(vp, ".obsidian/hotkeys.json")
        if not os.path.exists(hk): continue
        try: data = json.load(open(hk))
        except Exception: continue
        vault = os.path.basename(vp.rstrip("/"))
        for cmd, binds in data.items():
            for b in (binds or []):
                key = b.get("key", "")
                key = OBS_KEY.get(key, key.upper() if len(key) == 1 else key)
                add([obs_mod(m) for m in b.get("modifiers", [])], key, cmd,
                    "app config", "Obsidian", f"obsidian hotkey · {vault}"); n += 1
    return n

def _strip_jsonc(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'(^|\s)//[^\n]*', '', s)
    s = re.sub(r',(\s*[}\]])', r'\1', s)   # trailing commas
    return s
def vsc_key(combo):
    chords = combo.split(' ')
    mmap = {'cmd':'cmd','meta':'cmd','win':'cmd','ctrl':'ctrl','control':'ctrl',
            'alt':'opt','option':'opt','shift':'shift'}
    def seg(s):
        parts = s.split('+')
        return [mmap[p] for p in parts[:-1] if p in mmap], norm_keytoken(parts[-1])
    m1, k1 = seg(chords[0])
    if len(chords) > 1:                        # ⌘K ⌘I → first press lives on grid, second press = chord
        m2, k2 = seg(chords[1])
        rest = ' '.join(chords[2:])            # 3+ presses (예: ctrl+k ctrl+j ctrl+l): 2nd press is NOT terminal
        return m1, k1, m2, k2, rest
    return m1, k1, None, None, ''

# ---------- shared default-keybinding corpus: defaults/<app>/<version>.json ----------
# The ASSET: app DEFAULTS (not user customizations, no PII) keyed by app+version. A scan with the
# app installed SAVES its defaults here (grows the DB); a machine WITHOUT the app SEEDS from the DB
# so the viewer still shows that app's shortcuts. This dir is committed (open dataset).
DEFAULTS_DIR = os.path.join(PROJ, "defaults")
VSCODE_APP = "/Applications/Visual Studio Code.app"
CODEX_APP = "/Applications/Codex.app"
def app_ver(bundle):
    try:
        d = plistlib.load(open(os.path.join(bundle, "Contents/Info.plist"), "rb"))
        return d.get("CFBundleShortVersionString") or d.get("CFBundleVersion")
    except Exception: return None
def _verkey(v): return tuple(int(x) for x in re.findall(r"\d+", v or ""))
def save_app_defaults(app, version, ents):
    if not version or not ents: return
    d = os.path.join(DEFAULTS_DIR, app); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, str(version) + ".json")
    new = json.dumps({"app": app, "version": str(version), "scope": ents[0]["scope"], "entries": ents},
                     ensure_ascii=False, indent=1, sort_keys=True)
    if os.path.exists(path) and open(path).read() == new: return   # unchanged → no git churn
    open(path, "w").write(new)
def seed_app_defaults(app):
    files = glob.glob(os.path.join(DEFAULTS_DIR, app, "*.json"))
    if not files: return [], None
    path = max(files, key=lambda p: _verkey(os.path.basename(p)[:-5]))   # newest known version
    try:
        data = json.load(open(path)); return data.get("entries", []), data.get("version")
    except Exception: return [], None
def seed_into(app):   # app not installed/scanned on this machine → fill in from the shared DB
    ents, ver = seed_app_defaults(app)
    if not ents: return 0
    for e in ents:
        e2 = dict(e); e2["detail"] = (e2.get("detail", "") + " · seed").strip(" ·")
        entries.append(e2)
    print(f"  {app}: not installed here → seeded {len(ents)} from defaults/{app}/{ver}.json")
    return len(ents)
def collect_community():
    # seed app-menu packs shared from OTHER machines (defaults/<app>/menu-*.json, made by share_menus.py)
    # for apps NOT scanned on this machine — so you see them without installing the app. Call LAST.
    n, have = 0, {e["scope"] for e in entries if e.get("source") != "web"}  # web is complementary reference, not a local scan → still seed the shared menu pack (union), the viewer dedups exact overlaps
    packs = glob.glob(os.path.join(DEFAULTS_DIR, "*", "menu-*.json")) + glob.glob(os.path.join(DEFAULTS_DIR, "*", "keymap-*.json"))
    best = {}   # (app, menu|keymap) → newest pack; 앱당 menu팩 + keymap팩 각각 seeding (메뉴/전체 키맵은 상호보완, 겹침은 viewer가 dedup)
    for path in sorted(packs):
        try: data = json.load(open(path))
        except Exception: continue
        app = data.get("app") or data.get("scope")
        if not app or app in have: continue           # already have it from a local scan → skip (no dup)
        k = (app, os.path.basename(path).split("-")[0])
        if k not in best or _verkey(data.get("version")) > _verkey(best[k].get("version")): best[k] = data
    for data in best.values():
        for e in data.get("entries", []):
            e2 = dict(e); e2["detail"] = ("공유 · 타 기기 · " + (e2.get("detail") or "")).strip(" ·")  # keep original provenance (e.g. .kys commandname)
            entries.append(e2); n += 1
    return n

def collect_vscode():
    files = []
    user = os.path.join(HOME, "Library/Application Support/Code/User/keybindings.json")
    if os.path.exists(user): files.append((user, "user"))
    dump = os.path.join(PROJ, "vscode_default_keybindings.json")
    if os.path.exists(dump): files.append((dump, "default"))
    n = 0; def_ents = []
    for path, kind in files:
        try: data = json.loads(_strip_jsonc(open(path).read()))
        except Exception as e: print("  VS Code: parse fail", kind, e); continue
        for it in data:
            cmd = it.get("command", "")
            combo = it.get("key", "")
            if not cmd or cmd.startswith("-") or not combo: continue
            mods, key, cmods, ckey, rest = vsc_key(combo)
            if not key: continue
            when = (it.get("when") or "").strip()
            det = f"vscode {kind} · {combo}" + (f" · when: {when}" if when else "")
            action = cmd + (f"  (그다음 {rest})" if rest else "")   # 3+ 연속이면 2nd가 끝이 아님을 명시
            e = add(mods, key, action, "app config", "Code", det, cmods=cmods, ckey=ckey)
            if e:
                n += 1
                if kind == "default": def_ents.append(e)   # only DEFAULTS feed the shared DB (user customs stay local)
    if def_ents:
        save_app_defaults("VS Code", app_ver(VSCODE_APP), def_ents)
    elif not any(k == "default" for _, k in files):        # no local defaults → seed from the shared DB
        n += seed_into("VS Code")
    return n

CODEX_MODS = {'cmdorctrl':'cmd','commandorcontrol':'cmd','cmd':'cmd','command':'cmd','super':'cmd','meta':'cmd',
              'ctrl':'ctrl','control':'ctrl','alt':'opt','option':'opt','altgr':'opt','shift':'shift'}
def codex_accel(accel):                         # Electron accelerator → (mods, key); CmdOrCtrl=⌘ on macOS, Alt=⌥
    mods, key = [], None
    for p in accel.split('+'):
        lp = p.lower()
        if lp in CODEX_MODS: mods.append(CODEX_MODS[lp])
        elif p: key = p
    return mods, norm_keytoken(key)
def collect_codex():                            # in-app shortcuts (Settings ▸ Keyboard Shortcuts), not in the menu bar
    path = os.path.join(PROJ, "codex_keybindings.json")
    if not os.path.exists(path):
        return seed_into("Codex")               # not installed / not dumped → seed from the shared DB
    try: data = json.load(open(path))
    except Exception as e: print("  Codex: parse fail", e); return 0
    n = 0; ents = []
    for it in data:
        mods, key = codex_accel(it.get("key", ""))
        if not key: continue
        label = (it.get("title") or it.get("id") or "").strip()
        e = add(mods, key, label, "app config", "Codex", "codex · " + it.get("id", ""), group="Codex")
        if e: n += 1; ents.append(e)
    if ents: save_app_defaults("Codex", app_ver(CODEX_APP), ents)   # all Codex shortcuts are app defaults
    return n
def collect_codex_gestures():
    # Appshots: reverse-engineered from Codex app.asar. The default for stored `appshotHotkey` is `DoubleCommand`,
    # and the input map is `leftcommand+rightcommand`→`DoubleCommand` (label "⌘ + ⌘") — i.e. press BOTH ⌘ keys
    # together (NOT a double-tap). Options ⌥+⌥ / ⇧+⇧ / off; macOS-only; command id `capture-appshot`.
    if not os.path.exists(CODEX_APP): return 0
    addg("cmd", "Appshots — 최상위 창을 캡처해 Codex에 첨부", "app config", "Codex",
         "codex · capture-appshot · app.asar DoubleCommand = 좌·우 ⌘ 동시 (설정에서 ⌥+⌥/⇧+⇧/끄기)",
         side="both", count=1, hold=False, group="Codex")
    return 1
def collect_manual_gestures():
    # User-listed non-static triggers across apps (Claude Desktop / KeyClu / their AutoHotKey CapsLock multi-tap…).
    path = os.path.join(PROJ, "manual_gestures.json")
    if not os.path.exists(path): return 0
    try: data = json.load(open(path))
    except Exception as e: print("  gestures: parse fail", e); return 0
    n = 0
    for it in (data.get("gestures") or []):
        if not it.get("mod"): continue
        addg(it["mod"], it.get("action", ""), it.get("source", "수동"), it.get("scope", "global"),
             it.get("detail", ""), it.get("side", "either"), it.get("count", 1), it.get("hold", False), it.get("group"))
        n += 1
    return n

WEB_MODSYM = {'⌘':'cmd','⌥':'opt','⌃':'ctrl','⇧':'shift'}
WEB_KEYNAME = {'Space':'Space','Enter':'Return','Return':'Return','Esc':'Escape','Tab':'Tab',
               'Backspace':'Delete','Delete':'Delete','ForwardDelete':'ForwardDelete','→':'Right','←':'Left','↑':'Up','↓':'Down',
               'Home':'Home','End':'End','PageUp':'PageUp','PageDown':'PageDown'}
def web_key(spec):
    # parse a Google-style mac shortcut string "⌘⇧ Space" / "⌃⌘ e then p" → (mods, key, sequence_or_None)
    s = (spec or "").strip(); mods = []; i = 0
    while i < len(s):
        c = s[i]
        if c in WEB_MODSYM: mods.append(WEB_MODSYM[c]); i += 1
        elif c == ' ': i += 1
        elif c == '+' and i + 1 < len(s): i += 1          # "Fn+Delete"의 구분자 (끝의 '+'는 키 자체: "⌘+")
        elif s[i:i+2] == 'Fn': mods.append('fn'); i += 2
        else: break
    rest = s[i:].strip()
    seq = rest if (' then ' in rest or 'press' in rest or (',' in rest and len(rest) > 1)) else None  # bare "," is a key, not a sequence separator
    if seq: rest = re.split(r'[ ,]', rest)[0]            # first key of the sequence drives grid placement
    if ' or ' in rest: rest = rest.split(' or ')[0].strip()          # "Delete or #" → first alternative (full in detail)
    if '/' in rest and rest != '/': rest = rest.split('/')[0].strip()  # "↑/↓" → first; keep bare "/"
    rest = re.sub(r'(?i)\bpage\s*up\b', 'PageUp', rest); rest = re.sub(r'(?i)\bpage\s*down\b', 'PageDown', rest)  # MS "Page down"
    if ' ' in rest: rest = rest.split()[0]                           # "→ ← ↑ ↓" (multi-key for one action) → first
    if rest in WEB_KEYNAME: return mods, WEB_KEYNAME[rest], seq
    if len(rest) == 1: return mods, (rest.upper() if rest.isalpha() else rest), seq
    return mods, norm_keytoken(rest), seq
def collect_web():
    # Web-app shortcuts (Google Sheets/Docs/Drive…) — no local source, so pulled from the vendor's OFFICIAL
    # shortcut docs into web_shortcuts.json (authoritative, not guessed). These apply only inside the browser tab.
    path = os.path.join(PROJ, "web_shortcuts.json")
    if not os.path.exists(path): return 0
    try: data = json.load(open(path))
    except Exception as e: print("  web: parse fail", e); return 0
    n = 0
    for scope, items in data.items():
        if scope.startswith("_"): continue
        for it in (items or []):
            mods, key, seq = web_key(it.get("keys", ""))
            if not key: continue
            det = f"공식문서 웹 fetch·파싱 (로컬 스캔 아님) · {it.get('keys','')}" + (" (시퀀스)" if seq else "")
            add(mods, key, it.get("action", ""), "web", scope, det); n += 1
    return n

def decode_ax_mods(m):
    m = int(m)
    if m < 0: return []
    out = []
    if not (m & 8): out.append('command')   # Command is implied unless the "no command" bit is set
    if m & 1: out.append('shift')
    if m & 2: out.append('option')
    if m & 4: out.append('control')
    return out

def ax_key(m):
    c = m.get("cmdChar")
    if c and len(c) >= 1 and ord(c[0]) >= 32 and ord(c[0]) != 127:
        return c.upper()
    vk = m.get("cmdVirtualKey", -1)
    if isinstance(vk, int) and vk in KEYCODE: return KEYCODE[vk]
    g = m.get("cmdGlyph", -1)
    if isinstance(g, int) and g in GLYPH: return GLYPH[g]
    return None

# Standard AppKit menu items whose REAL shortcut is a Globe/fn key that the Accessibility menu
# API can't encode (no Globe bit) — so they surface as a BARE letter in EVERY app. Drop those
# bare-letter artifacts; the system/DEFAULTS source already carries them correctly:
#   Emoji & Symbols 🌐E · Start Dictation 🌐 · Enter Full Screen 🌐F (전체 화면 전환).
_AX_GLOBE_ITEMS = ("Emoji & Symbols", "Start Dictation", "이모지 및 기호", "받아쓰기 시작",
                   "Enter Full Screen", "Exit Full Screen", "전체 화면 시작", "전체 화면 종료", "전체 화면 시작하기")
def _is_globe_item(text):
    return any(g in (text or "") for g in _AX_GLOBE_ITEMS)

def collect_menus():
    binp = os.path.join(PROJ, "axmenudump")
    if not os.path.exists(binp): print("  app menus: axmenudump not compiled"); return 0
    r = subprocess.run([binp], capture_output=True, text=True)
    if r.returncode == 2:
        # No Accessibility permission this run — preserve the previous scan's menu entries so a
        # rebuild (e.g. for a template/code change) doesn't wipe the last good menu scan.
        prev = os.path.join(PROJ, "shortcuts.json")
        if os.path.exists(prev):
            try:
                old = [e for e in json.load(open(prev)).get("entries", [])
                       if e.get("source") == "app menu" and "공유" not in e.get("detail", "")   # don't re-absorb community seeds (collect_community re-adds them fresh)
                       and not (not e.get("mods") and _is_globe_item(e.get("action")))]
                for e in old:
                    e["group"] = e.get("group") or "app menu"; entries.append(e)
                print(f"  app menus: no Accessibility this run — reused {len(old)} from last scan"); return len(old)
            except Exception: pass
        print("  app menus: Accessibility not granted, no previous scan to reuse"); return 0
    try:
        arr = json.loads(r.stdout or "[]")
    except Exception as e:
        print("  app menus: parse error", e); return 0
    n = 0
    for m in arr:
        key = ax_key(m)
        if not key: continue
        mods = decode_ax_mods(m.get("cmdModifiers", -1))
        action = m.get("path") or m.get("title")
        if not mods and _is_globe_item(action): continue  # AX can't encode the Globe/fn key → bare-letter artifact
        add(mods, key, action, "app menu", m.get("app", "?"), m.get("bundle", "")); n += 1
    return n

def collect_env():   # provenance: OS/app versions + locale, so each scan is a versioned datapoint. NO PII (no host/user/serial).
    env = {"macos": platform.mac_ver()[0], "arch": platform.machine()}
    def sh(*a):
        try: return subprocess.check_output(a, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception: return None
    for k, v in (("build", sh("sw_vers", "-buildVersion")),
                 ("model", sh("sysctl", "-n", "hw.model")),
                 ("locale", sh("defaults", "read", "-g", "AppleLocale"))):
        if v: env[k] = v
    apps, cand = {}, {
        "BTT": "/Applications/BetterTouchTool.app", "VS Code": "/Applications/Visual Studio Code.app",
        "Codex": "/Applications/Codex.app", "Google Chrome": "/Applications/Google Chrome.app",
        "Safari": "/Applications/Safari.app", "Obsidian": "/Applications/Obsidian.app",
        "Shottr": "/Applications/Shottr.app", "ScreenBrush": "/Applications/ScreenBrush.app",
        "Karabiner-Elements": "/Applications/Karabiner-Elements.app", "Raycast": "/Applications/Raycast.app",
    }
    for name, p in cand.items():
        pl = os.path.join(p, "Contents/Info.plist")
        if not os.path.exists(pl): continue
        try:
            d = plistlib.load(open(pl, "rb"))
            v = d.get("CFBundleShortVersionString") or d.get("CFBundleVersion")
            if v: apps[name] = str(v)
        except Exception: pass
    env["apps"] = apps
    return env

# ---------- run ----------
print("Collecting…")
sys_n = collect_system() + collect_defaults() + collect_zoom()
kara_n = collect_karabiner(); btt_n = collect_btt(); ray_n = collect_raycast()
mg_n = collect_manual_globals()
sb_n = collect_shottr() + collect_screenbrush()
obs_n = collect_obsidian(); vsc_n = collect_vscode(); cdx_n = collect_codex()
menu_n = collect_menus(); appd_n = collect_app_defaults()   # menus first so curated defaults dedup against them
gst_n = collect_codex_gestures() + collect_manual_gestures()   # non-static triggers (double/hold/multi-tap)
web_n = collect_web()                                          # web-app shortcuts (Google Sheets/Docs/Drive…)
com_n = collect_community()                                    # menu packs shared from other machines (last → knows local scopes)

# ---------- 최종 정규화 + 완전중복 제거 ----------
# collect_menus의 재사용 경로와 collect_community는 add()를 거치지 않으므로, 여기가 전 소스를 커버하는 유일한 지점.
# (keep in sync with normalize_packs.py)
PUA_KEY = {chr(0xF700): "Up", chr(0xF701): "Down", chr(0xF702): "Left", chr(0xF703): "Right",   # NSEvent function-key PUA chars (AX cmdChar가 그대로 내보냄 → 그리드에 안 보이는 tofu)
           chr(0xF728): "ForwardDelete", chr(0xF729): "Home", chr(0xF72B): "End", chr(0xF72C): "PageUp", chr(0xF72D): "PageDown",
           "⎋": "Escape", "⌫": "Delete", "⌦": "ForwardDelete", "⇥": "Tab", "↩": "Return", "⏎": "Return", "Esc": "Escape",
           "↖": "Home", "↘": "End", "⇞": "PageUp", "⇟": "PageDown"}
PUA_KEY.update({chr(0xF704 + i): "F" + str(i + 1) for i in range(20)})   # NSF1FunctionKey(0xF704)…NSF20
SHIFTED = {'+': '=', '_': '-', '~': '`', '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8',
           '(': '9', ')': '0', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'}   # 물리 키 = base + shift (원 표기는 detail에 남음)
def _norm_entry_keys(e):
    for kf, mf in (("key", "mods"), ("ckey", "cmods")):
        k = e.get(kf)
        if not k: continue
        k = PUA_KEY.get(k, k)
        if k in SHIFTED:
            k = SHIFTED[k]
            if "shift" not in (e.get(mf) or []): e[mf] = (e.get(mf) or []) + ["shift"]
        e[kf] = k
        e[mf] = norm_mods(e.get(mf) or [])
# macOS가 '모든 앱'의 Window 메뉴에 주입하는 시스템 창-타일링 항목(Move & Resize·Fill·Center·Full Screen Tile…).
# → 앱마다 26개씩 중복 + OneNote 등으로 오태깅되는 걸, 하나의 'macOS 창 관리' 스코프로 재분류(중복 제거).
# 또 AX 메뉴 API는 Globe(🌐) 비트를 못 줘서 ⌃⇧↑처럼 오는데, 이 단축키들은 실제로 ⌃⇧🌐+화살표라 fn을 복원한다.
WIN_MGMT_MARKERS = ("Move & Resize", "Full Screen Tile", "Return to Previous Size")
WIN_MGMT_LEAVES = {"Fill", "Center", "Left & Right", "Top & Bottom"}
def _is_window_mgmt(action):
    a = action or ""
    if not a.startswith("Window"): return False
    if any(m in a for m in WIN_MGMT_MARKERS): return True
    return "▸" in a and a.split("▸")[-1].strip() in WIN_MGMT_LEAVES
def _reclass_window_mgmt(e):
    if e.get("source") != "app menu" or not _is_window_mgmt(e.get("action")): return
    e["scope"] = "macOS 창 관리"; e["group"] = "macOS 창 관리"; e["detail"] = "macOS 시스템 창 타일링 (모든 앱 공통)"
    if e.get("key") in ("Up", "Down", "Left", "Right") and "fn" not in (e.get("mods") or []):
        e["mods"] = (e.get("mods") or []) + ["fn"]   # AX가 못 읽는 Globe 복원 (아래 norm_mods가 정렬)
# macOS는 '모든 앱'의 메뉴바에 Apple(🍎) 메뉴도 주입 → Force Quit·Lock·Log Out·Sleep…이 앱마다 중복되고
# 'Log Out <이름>'·'Force Quit <앱>'엔 사용자 이름/앱명까지 박힌다. 하나의 'macOS 시스템' 스코프로 재분류 +
# 뒤따르는 이름/앱명 스크럽(→ 중복 병합). BTT 앱 메뉴가 'BetterTouchTool' 스코프로 뜨던 잡음도 이걸로 걷힌다.
def _reclass_apple_menu(e):
    a = e.get("action") or ""
    if e.get("source") != "app menu" or not a.startswith("Apple ▸"): return
    a = re.sub(r"(Log Out|Force Quit|로그아웃|강제 종료) .+", r"\1 …", a)  # 뒤 이름/앱명 제거 → dedup + PII 스크럽
    e["action"] = a; e["scope"] = "macOS 시스템"; e["group"] = "macOS 시스템"; e["detail"] = "macOS Apple 메뉴 (모든 앱 공통)"
# 전용 설정 소스가 따로 있는 앱은 앱-메뉴 스캔(전부 표준 boilerplate: Settings/Hide/Quit·Undo/Copy/Paste)을 버려
# '앱 vs 설정' 이중 스코프 혼란을 없앤다. BetterTouchTool(앱 메뉴) ↔ BTT(설정 100개) 공존 → 앱 메뉴 쪽 드롭.
_APP_MENU_SUPPRESS = {"BetterTouchTool"}
_seen, _uniq = set(), []
for e in entries:
    if e.get("source") == "app menu" and e.get("scope") in _APP_MENU_SUPPRESS:
        continue   # 전용 설정 소스가 커버 (BTT) — 껍데기 앱-메뉴 스코프 제거
    if e.get("source") == "app menu" and not e.get("mods") and _is_globe_item(e.get("action")):
        continue   # bare-letter Globe artifact (Enter Full Screen 🌐F 등) — community packs bypass collect_menus, so drop here too
    _reclass_window_mgmt(e)
    _reclass_apple_menu(e)
    _norm_entry_keys(e)
    fp = json.dumps(e, sort_keys=True, ensure_ascii=False)
    if fp not in _seen: _seen.add(fp); _uniq.append(e)
if len(_uniq) < len(entries): print(f"  정규화: 완전중복 {len(entries) - len(_uniq)}건 제거")
entries[:] = _uniq

counts = {"system": sys_n, "Karabiner": kara_n, "BTT": btt_n, "Raycast": ray_n, "수동": mg_n,
          "Shottr/ScreenBrush": sb_n, "공유": com_n,
          "Obsidian": obs_n, "VS Code": vsc_n, "Codex": cdx_n, "web": web_n, "app menu": menu_n, "app 기본": appd_n,
          "제스처": gst_n}
for k, v in counts.items(): print(f"  {k:12s} {v}")

apps = sorted({e["scope"] for e in entries + gestures if e["scope"] != "global"})
bttgroups = sorted({e["group"] for e in entries if e["source"] == "BTT" and e["group"] != "BTT"})

# ---------- 앱 아이콘 추출 (컨텍스트 칩에 표시할 옵션용) — 각 앱의 .icns → 작은 PNG data URI ----------
def _app_icon_datauri(bundle):
    try:
        paths = subprocess.check_output(["mdfind", f"kMDItemCFBundleIdentifier == '{bundle}'"], text=True, stderr=subprocess.DEVNULL).splitlines()
    except Exception: return None
    app = next((p.strip() for p in paths if p.strip().endswith(".app")), None)
    if not app: return None
    try: pl = plistlib.load(open(os.path.join(app, "Contents/Info.plist"), "rb"))
    except Exception: return None
    res = os.path.join(app, "Contents/Resources"); icns = None
    icon = pl.get("CFBundleIconFile")
    if icon:
        cand = os.path.join(res, icon if icon.lower().endswith(".icns") else icon + ".icns")
        if os.path.exists(cand): icns = cand
    if not icns:
        g = glob.glob(os.path.join(res, "*.icns"))
        icns = next((x for x in g if "AppIcon" in x or "icon" in os.path.basename(x).lower()), (g[0] if g else None))
    if not icns: return None
    tmp = os.path.join(tempfile.gettempdir(), "_svicon.png")
    try:
        subprocess.run(["sips", "-s", "format", "png", "-Z", "40", icns, "--out", tmp], capture_output=True, check=True)
        return "data:image/png;base64," + base64.b64encode(open(tmp, "rb").read()).decode()
    except Exception: return None
# 앱-메뉴 스캔이 없어 번들 id가 안 잡히는 스코프/칩 → 알맞은 실제 앱(또는 macOS 시스템 앱) 아이콘을 직접 지정.
SCOPE_ICON_BUNDLE = {
    "macOS 시스템": "com.apple.systempreferences",   # System Settings (톱니) — Apple 메뉴 항목 모음
    "macOS 창 관리": "com.apple.exposelauncher",      # Mission Control — 창/스페이스 관리
}
def collect_app_icons():
    _cache = {}
    def geti(bundle):                                 # 번들당 한 번만 추출(캐시)
        if bundle not in _cache: _cache[bundle] = _app_icon_datauri(bundle)
        return _cache[bundle]
    scope_bundle = {}
    for e in entries:
        if e.get("source") == "app menu":
            d = (e.get("detail") or "").strip()
            if "." in d and " " not in d and re.fullmatch(r"[A-Za-z0-9][\w.\-]+", d): scope_bundle.setdefault(e["scope"], d)
    scope_bundle.update({"Code": "com.microsoft.VSCode", "Sublime Text": "com.sublimetext.4", "Obsidian": "md.obsidian", "Codex": "com.openai.codex"})
    scope_bundle.update(SCOPE_ICON_BUNDLE)
    icons = {}
    for scope, bundle in scope_bundle.items():
        u = geti(bundle)
        if u: icons[scope] = u
    # 로컬에 없는(공유·타 기기) 앱은 defaults/<scope>/icon.png 에서 — save_icon.py로 그 앱 있는 맥에서 넣어둔 것
    for scope in {e["scope"] for e in entries}:
        if scope in icons: continue
        p = os.path.join(DEFAULTS_DIR, scope, "icon.png")
        if os.path.exists(p):
            try: icons[scope] = "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
            except Exception: pass
    # BTT는 '설정' 소스라 앱 메뉴가 없음 → BetterTouchTool 앱 아이콘을 'BTT (전체)'+모든 프리셋 칩에 부여
    btt = geti("com.hegenberg.BetterTouchTool")
    if btt:
        for k in ["BTT (전체)"] + list(bttgroups): icons.setdefault(k, btt)
    return icons
app_icons = collect_app_icons()
print(f"  앱 아이콘 {len(app_icons)}개 추출")

meta = {"generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "counts": counts, "apps": apps, "bttgroups": bttgroups, "total": len(entries),
        "icons": app_icons, "env": collect_env()}

# Favorites/notes: bake annotations.json (exported from the viewer) into the data so they survive
# even if the browser's localStorage is cleared/blocked, and are portable across machines.
ann = {"fav": {}, "note": {}}
_ap = os.path.join(PROJ, "annotations.json")
if os.path.exists(_ap):
    try:
        _a = json.load(open(_ap)); ann = {"fav": _a.get("fav", {}), "note": _a.get("note", {})}
        print(f"  annotations  fav {len(ann['fav'])} · note {len(ann['note'])} (from annotations.json)")
    except Exception: pass

data = {"meta": meta, "entries": entries, "gestures": gestures, "ann": ann}
json.dump(data, open(os.path.join(PROJ, "shortcuts.json"), "w"), ensure_ascii=False, indent=1)

html = open(os.path.join(PROJ, "viewer.template.html")).read()
html = html.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
open(os.path.join(PROJ, "viewer.html"), "w").write(html)
print(f"\nWrote shortcuts.json and viewer.html  ({len(entries)} shortcuts, {len(apps)} apps)")
print(f"Open: open {os.path.join(PROJ, 'viewer.html')}")
