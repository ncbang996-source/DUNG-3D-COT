"""Test giai đoạn 4-5: thư viện tiết diện và hệ trục / hướng cánh (không chạy kiểm tra cấn)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import merge as MG  # noqa: E402
import orientation as OR  # noqa: E402
import parse_dxf as PD  # noqa: E402
import parse_pdf as PP  # noqa: E402
import section_library as SL  # noqa: E402


@pytest.fixture(scope="module")
def data():
    d = PD.parse(ROOT / "data" / "NC111-32.dxf")
    p = PP.parse_text(PP.pdf_text(ROOT / "data" / "TIET_DIEN_NC111-32.pdf"))
    groups, secs = PP.build(p)
    model, _ = MG.merge(d["members"], groups)
    lib, problems = SL.build(secs)
    return model, lib, problems


def test_section_area_within_1pct(data):
    _, lib, problems = data
    assert problems == []
    assert len(lib) == 11
    for s in lib.values():
        assert abs(s["A_dev_pct"]) < 1
        assert abs(s["A_poly_cm2"] - s["A_geom_cm2"]) / s["A_geom_cm2"] < 0.005


def test_section_centroid_jis(data):
    _, lib, _ = data
    # Cx theo bảng JIS G3192 (cm)
    ref = {"L50X4": 1.37, "L90X7": 2.46, "L100X7": 2.71, "HL175X12": 4.73}
    for k, v in ref.items():
        assert abs(lib[k]["cx"] / 10 - v) < 0.02


def test_frames(data):
    model, lib, _ = data
    OR.by_id = {m["id"]: m for m in model}
    res, _ = OR.solve(model, lib, check_clash=False)
    body = OR.Body(model)
    assert len(res) == 664
    for m in model:
        r = res[m["id"]]
        frames = [(r["e1"], r["e2"])] if r["rule"] == "leg" else list(r["frames"].values())
        for e1, e2 in frames:
            M = np.stack([r["u"], e1, e2])
            assert np.allclose(M @ M.T, np.eye(3), atol=1e-6), m["id"]
        if r["rule"] == "leg":
            p = np.array(m["p1"])
            heel = p - r["g"][0] * r["e1"] - r["g"][1] * r["e2"]
            assert np.hypot(*heel[:2]) > np.hypot(*p[:2])          # lưng ra ngoài góc
        elif r["rule"] == "face":
            n = body.normal(r["face"], m["p1"][2], m["p2"][2])
            e1, e2 = r["frames"]["in+"]
            assert abs(np.dot(e1, n)) < 1e-6                         # cánh liên kết nằm trong mặt cột
            assert np.dot(e2, n) < -0.999                            # cánh còn lại vào trong
        elif r.get("follows"):
            continue                                                  # đoạn nối dài theo khung đoạn dẫn
        elif r.get("vertical"):
            e1, e2 = r["frames"]["in+"]
            assert e2[1] * np.sign(m["p1"][1]) < -0.999                # chĩa về trục giữa xà
        else:
            e1, e2 = r["frames"]["in+"]
            assert abs(e1[2]) < 1e-6                                 # cánh liên kết nằm ngang
            if m["type"] == "XAD":
                assert e2[2] > 0                                     # XAD: cánh hướng lên
            else:
                assert e2[2] < 0                                     # cánh còn lại chĩa xuống


def test_rule_counts(data):
    model, lib, _ = data
    OR.by_id = {m["id"]: m for m in model}
    res, _ = OR.solve(model, lib, check_clash=False)
    rules = {}
    for r in res.values():
        rules[r["rule"]] = rules.get(r["rule"], 0) + 1
    assert rules["leg"] == 88
    assert sum(rules.values()) == 664


def test_face_members_against_leg_flange(data):
    """Thanh mặt cột ép sát cánh thanh cánh: trong = mặt trong (b/2 - t), ngoài = mặt ngoài (b/2)."""
    model, lib, _ = data
    OR.by_id = {m["id"]: m for m in model}
    res, log = OR.solve(model, lib, check_clash=False)
    body = OR.Body(model)
    xs = log["x_members"]
    assert len(xs["outside"]) == len(xs["inside"]) == 128
    for m in model:
        r = res[m["id"]]
        if r["rule"] != "face":
            continue
        n = body.normal(r["face"], m["p1"][2], m["p2"][2])
        bc, tc = OR.leg_section_at(model, lib, r["leg_ref_z"])
        off = float(np.dot(r["offs"][r["variant"]], n))
        chain = next((c for c in log["chains"] if m["id"] in c), [m["id"]])
        if any(i in xs["outside"] for i in chain):            # thanh liền với thanh X nằm ngoài
            assert r["variant"].startswith("out") and abs(off - bc / 2) < 1e-4
        else:
            assert r["variant"].startswith("in") and abs(off - (bc / 2 - tc)) < 1e-4


def test_x_pair_gap_equals_leg_thickness(data):
    """Tại nút giao chữ X: hai thanh (ngoài, trong) quay lưng vào nhau, hở đúng t thanh cánh."""
    model, lib, _ = data
    OR.by_id = {m["id"]: m for m in model}
    res, log = OR.solve(model, lib, check_clash=False)
    body = OR.Body(model)
    out_ids, in_ids = set(log["x_members"]["outside"]), set(log["x_members"]["inside"])
    leg_nodes = {tuple(p) for m in model if m["type"] in ("C", "CĐ") for p in (m["p1"], m["p2"])}
    by_node = {}
    for m in model:
        if m["id"] in out_ids | in_ids:
            for k in ("p1", "p2"):
                by_node.setdefault(tuple(m[k]), []).append(m)
    checked = 0
    for nd, ms in by_node.items():
        o = [m for m in ms if m["id"] in out_ids]
        i = [m for m in ms if m["id"] in in_ids]
        if nd not in leg_nodes and len(o) == 2 and len(i) == 2:
            n = body.normal(res[o[0]["id"]]["face"], nd[2], nd[2] + 0.1)
            assert len({res[m["id"]]["leg_ref_z"] for m in o + i}) == 1   # cả cụm X cùng chuẩn
            _, tc = OR.leg_section_at(model, lib, nd[2])
            gap = np.dot(res[o[0]["id"]]["offs"][res[o[0]["id"]]["variant"]], n) - \
                np.dot(res[i[0]["id"]]["offs"][res[i[0]["id"]]["variant"]], n)
            assert abs(gap - tc) < 1e-4
            checked += 1
    assert checked == 64


def test_ceil5():
    assert OR.ceil5(48) == 50 and OR.ceil5(72) == 75 and OR.ceil5(60) == 60


def test_continuous_bars_same_orientation():
    """Thanh liền (các đoạn cùng tiết diện nối thẳng hàng): cùng hướng, cùng độ dịch -> không gãy khúc."""
    import json
    p = ROOT / "web" / "data" / "scene.json"
    if not p.exists():
        pytest.skip("chưa có web/data/scene.json")
    sc = json.loads(p.read_text())
    by = {m["id"]: m for m in sc["members"]}
    chains = sc["report"]["orientation"]["chains"]
    assert chains
    for c in chains:
        v = {by[i]["variant"] for i in c}
        assert len(v) == 1, (c, v)
        offs = [np.array(by[i]["offs"].get(by[i]["variant"], [0, 0, 0])) for i in c]
        assert all(np.allclose(o, offs[0], atol=5e-4) for o in offs), (c, offs)   # <= 0,5 mm
    m561, m585 = by[561], by[585]
    assert m561["variant"] == m585["variant"]
