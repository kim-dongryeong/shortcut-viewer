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
import json, subprocess, os, plistlib, datetime, re, sqlite3, glob, tempfile, shutil, base64

HOME = os.path.expanduser("~")
PROJ = os.path.dirname(os.path.abspath(__file__))

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
# macOS sets NSEvent's Function flag (0x800000) automatically on these keys — it does NOT mean
# the physical fn/Globe key was pressed — so strip 'fn' from their combos.
FN_INTRINSIC = {f"F{i}" for i in range(1, 21)} | {"Left","Right","Up","Down","Home","End","PageUp","PageDown","ForwardDelete"}
def add(mods, key, action, source, scope, detail="", group=None, cmods=None, ckey=None):
    if not key: return
    m = norm_mods(mods)
    if key in FN_INTRINSIC and "fn" in m: m = [x for x in m if x != "fn"]
    e = {"mods": m, "key": str(key), "action": (action or "").strip() or "(untitled)",
         "source": source, "scope": scope, "detail": detail, "group": group or source}
    if ckey:                                   # chord: 2nd press (예: ⌘K ⌘I) — only stored when present
        cm = norm_mods(cmods or [])
        if ckey in FN_INTRINSIC and "fn" in cm: cm = [x for x in cm if x != "fn"]
        e["cmods"] = cm; e["ckey"] = str(ckey)
    entries.append(e)

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
    for prof in data.get("profiles", []):
        for sm in prof.get("simple_modifications", []):
            kc = (sm.get("from") or {}).get("key_code")
            to = ",".join((t.get("key_code") or "?") for t in sm.get("to", []))
            add([], kara_key(kc), f"→ {to}", "Karabiner", "global", "simple_modification"); n += 1
        for rule in prof.get("complex_modifications", {}).get("rules", []):
            desc = rule.get("description", "")
            for man in rule.get("manipulators", []):
                frm = man.get("from") or {}; kc = frm.get("key_code")
                if not kc: continue
                mods = [kara_mod(x) for x in (frm.get("modifiers") or {}).get("mandatory", [])]
                add(mods, kara_key(kc), desc or "remap", "Karabiner", "global", "complex_modification"); n += 1
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

def collect_vscode():
    files = []
    user = os.path.join(HOME, "Library/Application Support/Code/User/keybindings.json")
    if os.path.exists(user): files.append((user, "user"))
    dump = os.path.join(PROJ, "vscode_default_keybindings.json")
    if os.path.exists(dump): files.append((dump, "default"))
    if not files:
        print("  VS Code: no keybindings.json and no exported defaults — "
              "in VS Code run ⇧⌘P ▸ 'Preferences: Open Default Keyboard Shortcuts (JSON)' "
              "and save it to ~/shortcut-viewer/vscode_default_keybindings.json")
        return 0
    n = 0
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
            add(mods, key, action, "app config", "Code", det, cmods=cmods, ckey=ckey); n += 1
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
        print("  Codex: no codex_keybindings.json — run ./dump_codex.sh to extract in-app shortcuts")
        return 0
    try: data = json.load(open(path))
    except Exception as e: print("  Codex: parse fail", e); return 0
    n = 0
    for it in data:
        mods, key = codex_accel(it.get("key", ""))
        if not key: continue
        label = (it.get("title") or it.get("id") or "").strip()
        add(mods, key, label, "app config", "Codex", "codex · " + it.get("id", ""), group="Codex"); n += 1
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

# Standard AppKit Edit-menu items whose REAL shortcut is a Globe/fn key that the Accessibility
# menu API can't encode (no Globe bit) — so they surface as a bare letter in EVERY app. Drop them;
# the system source already carries them correctly (🌐E / ⌃⌘Space, 🌐 Dictation).
_AX_GLOBE_ITEMS = ("Emoji & Symbols", "Start Dictation", "이모지 및 기호", "받아쓰기 시작")
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
                       if e.get("source") == "app menu" and not (not e.get("mods") and _is_globe_item(e.get("action")))]
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

# ---------- run ----------
print("Collecting…")
sys_n = collect_system() + collect_defaults() + collect_zoom()
kara_n = collect_karabiner(); btt_n = collect_btt(); ray_n = collect_raycast()
mg_n = collect_manual_globals()
sb_n = collect_shottr() + collect_screenbrush()
obs_n = collect_obsidian(); vsc_n = collect_vscode(); cdx_n = collect_codex()
menu_n = collect_menus(); appd_n = collect_app_defaults()   # menus first so curated defaults dedup against them
counts = {"system": sys_n, "Karabiner": kara_n, "BTT": btt_n, "Raycast": ray_n, "수동": mg_n,
          "Shottr/ScreenBrush": sb_n,
          "Obsidian": obs_n, "VS Code": vsc_n, "Codex": cdx_n, "app menu": menu_n, "app 기본": appd_n}
for k, v in counts.items(): print(f"  {k:12s} {v}")

apps = sorted({e["scope"] for e in entries if e["scope"] != "global"})
bttgroups = sorted({e["group"] for e in entries if e["source"] == "BTT" and e["group"] != "BTT"})
meta = {"generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "counts": counts, "apps": apps, "bttgroups": bttgroups, "total": len(entries)}

# Favorites/notes: bake annotations.json (exported from the viewer) into the data so they survive
# even if the browser's localStorage is cleared/blocked, and are portable across machines.
ann = {"fav": {}, "note": {}}
_ap = os.path.join(PROJ, "annotations.json")
if os.path.exists(_ap):
    try:
        _a = json.load(open(_ap)); ann = {"fav": _a.get("fav", {}), "note": _a.get("note", {})}
        print(f"  annotations  fav {len(ann['fav'])} · note {len(ann['note'])} (from annotations.json)")
    except Exception: pass

data = {"meta": meta, "entries": entries, "ann": ann}
json.dump(data, open(os.path.join(PROJ, "shortcuts.json"), "w"), ensure_ascii=False, indent=1)

html = open(os.path.join(PROJ, "viewer.template.html")).read()
html = html.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
open(os.path.join(PROJ, "viewer.html"), "w").write(html)
print(f"\nWrote shortcuts.json and viewer.html  ({len(entries)} shortcuts, {len(apps)} apps)")
print(f"Open: open {os.path.join(PROJ, 'viewer.html')}")
