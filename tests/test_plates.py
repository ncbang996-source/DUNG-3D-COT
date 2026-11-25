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


def test_spacing_rules():
    assert PL.end_dist("G", 16) == 25 and PL.end_dist("X", 16) == 35 and PL.end_dist("X", 24) == 50
    assert PL.end_dist("G", 24) == 40 and PL.pitch(16) == 50 and PL.pitch(20) == 60 and PL.pitch(24) == 72


def leg_nodes(scene):
    return {tuple(p) for m in scene["members"] if m["type"] in ("C", "CĐ") for p in (m["p1"], m["p2"])}


def test_plates_rule(scene):
    byid = {m["id"]: m for m in scene["members"]}
    secs = scene["sections"]
    gus = [p for p in scene["plates"] if p["kind"] == "gusset"]
    assert gus, "phải có bản mã"
    for p in gus:
        tmin = min(secs[byid[i]["section"]]["t"] for i in p["members"])
        assert p["t_mm"] >= tmin                                     # >= thanh nối mỏng nhất
        many = any(byid[i]["bolt"]["count"] > 2 for i in p["members"])
        assert many or (p["on_leg"] and len(p["members"]) >= 2)
        assert all(byid[i]["type"] not in ("C", "CĐ") for i in p["members"])
        if p["on_leg"]:
            assert p["leg_bolts"] >= 3


def test_cross_nodes_one_bolt_and_filler(scene):
    fil = [p for p in scene["plates"] if p["kind"] == "filler"]
    cross = [b for b in scene["bolts"] if b["kind"] == "cross"]
    assert len(fil) == len(cross) == 64
    for p in fil:
        assert abs(p["area_m2"] - 0.045 ** 2) < 1e-9


def test_every_end_with_more_than_2_bolts_has_plate(scene):
    covered = {(i, tuple(p["node"])) for p in scene["plates"] for i in p["members"]}
    for m in scene["members"]:
        if m["type"] in ("C", "CĐ") or m["bolt"]["count"] <= 2:
            continue
        for k in ("p1", "p2"):
            assert (m["id"], tuple(m[k])) in covered, (m["id"], k)


def test_bolt_spacing(scene):
    cross = {tuple(p["node"]) for p in scene["plates"] if p["kind"] == "filler"}
    by = {}
    for b in scene["bolts"]:
        if b["kind"] == "member":
            by.setdefault(b["id"], []).append(np.array(b["p"]))
    for m in scene["members"]:
        if m["type"] in ("C", "CĐ"):
            continue
        n, d = m["bolt"]["count"], m["bolt"]["d_mm"]
        th = PL.through_index(scene["members"])
        n_ends = sum(1 for k in ("p1", "p2") if tuple(m[k]) not in cross and th.get((m["id"], k)) != "same")
        pts = by.get(m["id"], [])
        assert len(pts) == n * n_ends
        for k in range(n_ends):
            end = pts[k * n:(k + 1) * n]
            for a, b in zip(end, end[1:]):
                assert abs(np.linalg.norm(b - a) - PL.pitch(d) / 1000) < 1e-4


def test_nut_outward(scene):
    for b in scene["bolts"]:
        p, nut = np.array(b["p"]), np.array(b["nut"])
        r = np.array([p[0], p[1], 0.0])
        if np.linalg.norm(r) > 1e-6 and abs(np.dot(nut, r / np.linalg.norm(r))) > 0.3:
            assert np.dot(nut, r) > 0                                   # đai ốc ra ngoài cột


def test_no_chamfer_no_bolts_where_bar_continues(scene):
    """Không vát, không bu lông đầu thanh ở nút mà thanh thép liền qua (DXF chỉ chia đoạn)."""
    th = PL.through_index(scene["members"])
    cross = {tuple(p["node"]) for p in scene["plates"] if p["kind"] == "filler"}
    for m in scene["members"]:
        for k, f in (("p1", "chamfer1"), ("p2", "chamfer2")):
            if (m["id"], k) in th or (m.get("x_pair") and tuple(m[k]) in cross):
                assert m[f] is False, (m["id"], k)
    # ví dụ khung đỏ: 561 (L90X7) nối thẳng 585 (L90X7) tại (-1.2436, -2.4464, 21.4)
    assert th[(561, "p2")] == "same" and th[(585, "p1")] == "same"
    node = np.array([-1.2436, -2.4464, 21.4])
    for b in scene["bolts"]:
        if b["kind"] == "member" and b["id"] in (561, 585):
            assert np.linalg.norm(np.array(b["p"]) - node) > 0.2
