#!/usr/bin/env python3
# winkeys.py — Windows 키 문자열 파서, win/build_win.py와 (repo 루트) gen_seo.py가 공유.
# "ctrl+shift+t" 같은 텍스트 표기를 공유 스키마(mods,key)로 바꾼다 — VS Code/Windows Terminal
# 설정 파일, 메뉴 accelerator, 공식 문서 팩(win/packs/*.json)까지 전부 이 한 파서를 거친다.
import re

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
KEYSTR.update({f"num{i}": f"Keypad{i}" for i in range(10)})
KEYSTR.update({"num+": "KeypadPlus", "num-": "KeypadMinus", "num*": "KeypadMultiply", "num/": "KeypadDivide", "num.": "KeypadDecimal"})

SHIFTED_SYM = {"~":"`","!":"1","@":"2","#":"3","$":"4","%":"5","^":"6","&":"7","*":"8","(":"9",")":"0",
               "_":"-","+":"=","{":"[","}":"]","|":"\\",":":";","\"":"'","<":",",">":".","?":"/"}   # 시프트 기호 → 물리 키+shift (맥 build.py 최종 정규화 대응)

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
        if k in SHIFTED_SYM:
            key = SHIFTED_SYM[k]
            if "shift" not in mods:
                mods = mods + ["shift"]
        else:
            key = k.upper()
    elif re.fullmatch(r"f\d{1,2}", k):
        key = k.upper()
    else:
        key = KEYSTR.get(k)
    return (mods, key) if key else None
