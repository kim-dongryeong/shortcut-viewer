# tests/test_keys.py — svkeys 키 정규화 계약 잠금 (코덱스 리뷰: keypad canonicalization).
#   실행:  python3 -m unittest discover tests   (외부 의존성 0)
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from svkeys import canon_key, KEYPAD_KEY


class TestKeypadCanon(unittest.TestCase):
    def test_numpad_and_keypad_aliases(self):
        self.assertEqual(canon_key("numpad_add"), "KeypadPlus")
        self.assertEqual(canon_key("keypad_plus"), "KeypadPlus")
        self.assertEqual(canon_key("numpad_subtract"), "KeypadMinus")
        self.assertEqual(canon_key("numpad0"), "Keypad0")
        self.assertEqual(canon_key("keypad_slash"), "KeypadDivide")

    def test_nav_aliases_map_to_number_keys(self):
        # PC 넘패드 numlock-off 물리 위치 기준 (After Effects 등이 이 이름으로 내보냄)
        self.assertEqual(canon_key("keypad_home"), "Keypad7")
        self.assertEqual(canon_key("keypad_end"), "Keypad1")
        self.assertEqual(canon_key("keypad_pageup"), "Keypad9")
        self.assertEqual(canon_key("keypad_pagedown"), "Keypad3")
        self.assertEqual(canon_key("keypad_insert"), "Keypad0")
        self.assertEqual(canon_key("keypad_delete"), "KeypadDecimal")

    def test_passthrough_non_keypad(self):
        self.assertEqual(canon_key("A"), "A")
        self.assertEqual(canon_key("Escape"), "Escape")
        self.assertEqual(canon_key("F13"), "F13")
        self.assertEqual(canon_key(""), "")
        self.assertEqual(canon_key(None), None)

    def test_idempotent_on_canonical(self):
        # 이미 canonical 인 값은 그대로 (뷰어/normalize_packs 반복 적용 안전)
        for canonical in set(KEYPAD_KEY.values()):
            self.assertEqual(canon_key(canonical), canonical)


if __name__ == "__main__":
    unittest.main()
