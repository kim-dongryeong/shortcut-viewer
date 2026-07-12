"""sv_query의 조합 파싱 canon + 충돌/빈키 판정 로직을 고정한다 (에이전트 skill/MCP가 의존)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sv_query


FIXTURE = {"entries": [
    {"mods": ["shift", "cmd"], "key": "K", "action": "Delete Lines", "source": "app config", "scope": "Code"},
    {"mods": ["cmd"], "key": "Space", "action": "Spotlight", "source": "system", "scope": "Global"},
    {"mods": ["ctrl"], "key": "F", "action": "Window ▸ Fill", "source": "app menu", "scope": "macOS 창 관리"},
    {"mods": ["ctrl"], "key": "F", "action": "Find", "source": "app menu", "scope": "SomeApp"},
]}


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(FIXTURE, f)
        os.environ["SV_SHORTCUTS"] = cls.path

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.path)
        os.environ.pop("SV_SHORTCUTS", None)

    def test_parse_combo_canon(self):
        self.assertEqual(sv_query.parse_combo("cmd+shift+k"), (["cmd", "shift"], "K"))
        self.assertEqual(sv_query.parse_combo("⌘⇧K"), (["cmd", "shift"], "K"))
        self.assertEqual(sv_query.parse_combo("Alt+Command+esc"), (["cmd", "opt"], "Escape"))
        self.assertEqual(sv_query.parse_combo("hyper+j"), (["cmd", "ctrl", "opt", "shift"], "J"))
        self.assertEqual(sv_query.parse_combo("ctrl-space"), (["ctrl"], "Space"))

    def test_lookup_hits_and_misses(self):
        self.assertIn("Delete Lines", sv_query.lookup("shift+cmd+K"))
        self.assertIn("0 binding(s)", sv_query.lookup("shift+cmd+J"))

    def test_free_excludes_taken(self):
        out = sv_query.free("cmd")
        self.assertNotIn("Space", out.splitlines()[1].split())
        self.assertIn("J", out.splitlines()[1].split())

    def test_conflicts_global_vs_app(self):
        out = sv_query.conflicts()
        self.assertIn("ctrl+F", out)          # 창 관리(글로벌) ↔ SomeApp
        self.assertNotIn("cmd+Space", out)    # 글로벌만 → 충돌 아님

    def test_combo_str_order(self):
        self.assertEqual(sv_query.combo_str(["cmd", "shift"], "K"), "shift+cmd+K")


if __name__ == "__main__":
    unittest.main()
