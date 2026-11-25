"""Test bu lông / bản mã trên dữ liệu đã sinh (web/data/scene.json; chạy src/run_all.py trước)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import plates as PL  # noqa: E402

SCENE = ROOT / "web" / "data" / "scene.json"


@pytest.fixture(scope="module")
def scene():
    if not SCENE.exists():
        pytest.skip("chưa có web/data/scene.json")
    return json.loads(SCENE.read_text())


def test_plate_thickness_series():
    assert PL.plate_thickness(4) == 6 and PL.plate_thickness(7) == 8 and PL.plate_thickness(12) == 12


def test_plates_rule(scene):
    byid = {m["id"]: m for m in scene["members"]}
    secs = scene["sections"]
    assert scene["plates"], "phải có bản mã"
    for p in scene["plates"]:
        tmin = min(secs[byid[i]["section"]]["t"] for i in p["members"])
        assert p["t_mm"] >= tmin                                     # >= thanh nối mỏng nhất
        assert any(byid[i]["bolt"]["count"] > 2 for i in p["members"])   # chỉ khi có thanh > 2 bu lông
        assert all(byid[i]["type"] not in ("C", "CĐ") for i in p["members"])


def test_every_end_with_more_than_2_bolts_has_plate(scene):
    covered = {(i, tuple(p["node"])) for p in scene["plates"] for i in p["members"]}
    for m in scene["members"]:
        if m["type"] in ("C", "CĐ") or m["bolt"]["count"] <= 2:
            continue
        for k in ("p1", "p2"):
            assert (m["id"], tuple(m[k])) in covered, (m["id"], k)


def test_bolt_spacing(scene):
    by = {}
    for b in scene["bolts"]:
        by.setdefault(b["id"], []).append(np.array(b["p"]))
    for m in scene["members"]:
        if m["type"] in ("C", "CĐ"):
            continue
        n, d = m["bolt"]["count"], m["bolt"]["d_mm"] / 1000
        pts = by[m["id"]]
        assert len(pts) == 2 * n
        for end in (pts[:n], pts[n:]):
            for a, b in zip(end, end[1:]):
                assert abs(np.linalg.norm(b - a) - 3 * d) < 1e-4       # khoảng cách 3d
