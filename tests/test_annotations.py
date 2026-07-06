# tests/test_annotations.py — svann 라운드트립 5필드 보존 잠금 (코덱스 리뷰 P0: 데이터 유실 방지).
#   실행:  python3 -m unittest discover tests
import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from svann import load_annotations, blank, merge, ANN_KEYS


class TestAnnotations(unittest.TestCase):
    def test_blank_has_five_fields(self):
        self.assertEqual(set(blank()), {"fav", "note", "enote", "custom", "ghk"})
        self.assertEqual(set(blank()), set(ANN_KEYS))

    def test_roundtrip_preserves_all_five_fields(self):
        raw = {
            "fav": {"entry-id": 1},
            "note": {"cmd|K": "combo note"},
            "enote": {"entry-id": "entry note"},
            "custom": [{"mods": ["opt"], "key": "F", "action": "Finder", "scope": "global"}],
            "ghk": [{"title": "Finder", "mods": ["opt"], "key": "F",
                     "action": {"type": "open_app", "value": "Finder"}}],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(raw, f)
            path = f.name
        try:
            self.assertEqual(load_annotations(path), raw)
        finally:
            os.unlink(path)

    def test_partial_input_keeps_defaults(self):
        ann = merge(blank(), {"fav": {"a": 1}})   # only fav present
        self.assertEqual(ann["fav"], {"a": 1})
        self.assertEqual(ann["note"], {})
        self.assertEqual(ann["custom"], [])

    def test_wrong_types_ignored(self):
        ann = merge(blank(), {"fav": [1, 2], "custom": {"x": 1}})   # dict/list swapped
        self.assertEqual(ann["fav"], {})
        self.assertEqual(ann["custom"], [])

    def test_missing_or_broken_file_is_blank(self):
        self.assertEqual(load_annotations("/nonexistent/xyz.json"), blank())
        self.assertEqual(load_annotations(None), blank())
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{ not valid json ")
            path = f.name
        try:
            self.assertEqual(load_annotations(path), blank())
        finally:
            os.unlink(path)

    def test_blank_returns_independent_copies(self):
        a, b = blank(), blank()
        a["fav"]["x"] = 1
        a["custom"].append(1)
        self.assertEqual(b["fav"], {})   # no shared mutable state
        self.assertEqual(b["custom"], [])


if __name__ == "__main__":
    unittest.main()
