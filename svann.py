# svann.py — shared annotation loader. build.py / render.py 가 함께 import.
# (코덱스 리뷰 P0: annotations.json 라운드트립 5필드 보존을 한 곳으로 — 이전엔 fav/note만 구워
#  enote/custom/ghk 가 유실됐다. build·render·viewer import 세 경로가 같은 계약을 쓰게 한다.)
#   fav/note/enote = dict · custom/ghk = list. 타입이 안 맞는 필드는 조용히 무시(부분 허용·멱등).
import json, os

ANN_KEYS = {"fav": {}, "note": {}, "enote": {}, "custom": [], "ghk": []}

def blank():
    """빈 5필드 구조(기본값의 독립 복사본)."""
    return {k: (v.copy() if isinstance(v, dict) else list(v)) for k, v in ANN_KEYS.items()}

def merge(ann, raw):
    """raw(dict)에서 타입이 맞는 필드만 ann에 채운다. dict↔dict, list↔list만 허용."""
    if not isinstance(raw, dict):
        return ann
    for k, default in ANN_KEYS.items():
        v = raw.get(k)
        if isinstance(default, dict) and isinstance(v, dict):
            ann[k] = v
        elif isinstance(default, list) and isinstance(v, list):
            ann[k] = v
    return ann

def load_annotations(path):
    """annotations.json → 5필드 dict. 파일이 없거나 깨졌으면 빈 구조를 돌려준다."""
    ann = blank()
    if not path or not os.path.exists(path):
        return ann
    try:
        with open(path) as f:
            raw = json.load(f)
    except Exception:
        return ann
    return merge(ann, raw)
