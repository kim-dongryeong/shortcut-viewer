"""SPEC-windowdrag §6: sv_hotkeys의 load()/save() 라운드트립이 top-level "window_drag" 필드를
드롭하지 않는지 고정한다. 임시 CONFIG 경로로 실제 설정 파일은 건드리지 않는다."""
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

    def test_window_drag_survives_load_and_save(self):
        self._write({"version": 2, "hotkeys": [],
                     "window_drag": {"enabled": True, "modifier": "fn"}})
        doc = sh.load()
        self.assertEqual(doc["window_drag"], {"enabled": True, "modifier": "fn"})
        sh.save(doc)
        doc2 = sh.load()
        self.assertEqual(doc2["window_drag"], {"enabled": True, "modifier": "fn"})

    def test_window_drag_absent_stays_absent(self):
        self._write({"version": 1, "hotkeys": []})
        doc = sh.load()
        self.assertNotIn("window_drag", doc)


if __name__ == "__main__":
    unittest.main()
