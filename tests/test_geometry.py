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
