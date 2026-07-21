"""sv_hotkeys 프리셋(레이어) 시스템: v1→v2 정규화, solo 라디오 의미, assign, add --preset,
master off 거부를 고정한다. 임시 CONFIG 경로로 실제 설정 파일은 건드리지 않는다."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sv_hotkeys as sh


class T(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)  # sh.load()는 없으면 빈 v1 문서로 시작
        self._orig_config = sh.CONFIG
        sh.CONFIG = self.path

    def tearDown(self):
        sh.CONFIG = self._orig_config
        if os.path.exists(self.path):
            os.unlink(self.path)

    def _write(self, doc):
        with open(self.path, "w") as f:
            json.dump(doc, f)

    def test_v1_to_v2_normalize(self):
        self._write({"version": 1, "hotkeys": [
            {"id": "a", "title": "A", "mods": ["opt"], "key": "A", "action": {"type": "open_app", "value": "X"}},
        ]})
        doc = sh.load()
        self.assertEqual(doc["version"], 2)
        self.assertIn("master", doc["presets"])
        self.assertTrue(doc["presets"]["master"]["always_on"])
        self.assertIn("base", doc["presets"])
        self.assertEqual(doc["hotkeys"][0]["preset"], "base")

    def test_missing_preset_reference_autocreated(self):
        self._write({"version": 2, "presets": {"master": {"always_on": True}},
                     "hotkeys": [{"id": "a", "preset": "ghost", "mods": [], "key": "A",
                                  "action": {"type": "open_app", "value": "X"}}]})
        doc = sh.load()
        self.assertIn("ghost", doc["presets"])
        self.assertTrue(doc["presets"]["ghost"].get("enabled", True))

    def test_preset_on_logic(self):
        doc = {"presets": {"master": {"always_on": True}, "base": {"enabled": True},
                            "mousebm": {"enabled": False}}}
        self.assertTrue(sh.preset_on(doc, "master"))
        self.assertTrue(sh.preset_on(doc, "base"))
        self.assertFalse(sh.preset_on(doc, "mousebm"))

    def test_master_off_rejected(self):
        self._write({"version": 1, "hotkeys": []})
        with self.assertRaises(SystemExit):
            sh.preset_set("master", False)

    def test_preset_solo_radio(self):
        self._write({"version": 2,
                      "presets": {"master": {"always_on": True}, "base": {"enabled": True},
                                  "datetime": {"enabled": True}, "mousebm": {"enabled": False}},
                      "hotkeys": []})
        sh.preset_solo("datetime")
        doc = sh.load()
        self.assertTrue(doc["presets"]["master"]["always_on"])  # master survives
        self.assertTrue(doc["presets"]["datetime"]["enabled"])
        self.assertFalse(doc["presets"]["base"]["enabled"])
        self.assertFalse(doc["presets"]["mousebm"]["enabled"])

    def test_assign_moves_hotkey_and_creates_preset(self):
        self._write({"version": 2, "presets": {"master": {"always_on": True}, "base": {"enabled": True}},
                      "hotkeys": [{"id": "h1", "preset": "base", "mods": ["opt"], "key": "A",
                                   "action": {"type": "open_app", "value": "X"}}]})
        sh.assign("h1", "datetime")
        doc = sh.load()
        self.assertEqual(doc["hotkeys"][0]["preset"], "datetime")
        self.assertIn("datetime", doc["presets"])

    def test_add_with_preset(self):
        self._write({"version": 1, "hotkeys": []})
        os.environ["SV_SHORTCUTS"] = tempfile.mkstemp(suffix=".json")[1]
        with open(os.environ["SV_SHORTCUTS"], "w") as f:
            json.dump({"entries": []}, f)
        sh.add("날짜 리더", "ctrl+opt+D", "paste_text", "test", preset="datetime")
        doc = sh.load()
        h = [x for x in doc["hotkeys"] if x["title"] == "날짜 리더"][0]
        self.assertEqual(h["preset"], "datetime")
        self.assertIn("datetime", doc["presets"])
        os.unlink(os.environ["SV_SHORTCUTS"])

    def test_presets_list_and_default_add_preset_is_base(self):
        self._write({"version": 1, "hotkeys": []})
        os.environ["SV_SHORTCUTS"] = tempfile.mkstemp(suffix=".json")[1]
        with open(os.environ["SV_SHORTCUTS"], "w") as f:
            json.dump({"entries": []}, f)
        sh.add("테스트", "opt+Z", "open_app", "X")
        doc = sh.load()
        h = [x for x in doc["hotkeys"] if x["title"] == "테스트"][0]
        self.assertEqual(h["preset"], "base")
        out = sh.presets_list()
        self.assertIn("base", out)
        self.assertIn("master", out)
        os.unlink(os.environ["SV_SHORTCUTS"])


if __name__ == "__main__":
    unittest.main()
