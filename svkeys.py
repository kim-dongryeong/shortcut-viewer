# svkeys.py — 공유 키 정규화 테이블. build.py / render.py / normalize_packs.py 가 함께 import.
# (코덱스 리뷰: keypad 정규화가 build.py·viewer·gen_hotkeys·Swift에 흩어져 있던 것을 한 곳으로.)
# keypad_*/numpad* 를 canonical Keypad* 이름으로. nav 별칭(home/end/pageup/…)은 물리적으로 같은
# 숫자 키에 매핑(PC 넘패드 numlock-off 기준) — After Effects 등이 이 이름으로 내보냄.

KEYPAD_KEY = {
    "numpad0": "Keypad0", "keypad_0": "Keypad0", "keypad_insert": "Keypad0",
    "keypad_1": "Keypad1", "keypad_end": "Keypad1",
    "keypad_2": "Keypad2", "keypad_down": "Keypad2",
    "keypad_3": "Keypad3", "keypad_pagedown": "Keypad3",
    "keypad_4": "Keypad4", "keypad_left": "Keypad4",
    "keypad_5": "Keypad5",
    "keypad_6": "Keypad6", "keypad_right": "Keypad6",
    "keypad_7": "Keypad7", "keypad_home": "Keypad7",
    "keypad_8": "Keypad8", "keypad_up": "Keypad8",
    "keypad_9": "Keypad9", "keypad_pageup": "Keypad9",
    "numpad_add": "KeypadPlus", "keypad_plus": "KeypadPlus",
    "numpad_subtract": "KeypadMinus", "keypad_minus": "KeypadMinus",
    "keypad_multiply": "KeypadMultiply",
    "keypad_slash": "KeypadDivide",
    "keypad_decimal": "KeypadDecimal", "keypad_comma": "KeypadComma", "keypad_delete": "KeypadDecimal",
    "keypad_enter": "KeypadEnter",
    "keypad_clear": "KeypadClear",
    "keypad_equals": "KeypadEquals",
}

def canon_key(k):
    """단일 키 이름을 canonical로 (지금은 keypad만; 필요시 PUA/shifted도 여기로 통합)."""
    return KEYPAD_KEY.get(k, k) if isinstance(k, str) else k
