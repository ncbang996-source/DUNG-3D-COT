"""Test tự động cho parser DXF, parser PDF và bước ghép (giai đoạn 1-3)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import merge as MG  # noqa: E402
import parse_dxf as PD  # noqa: E402
import parse_pdf as PP  # noqa: E402

DXF = ROOT / "data" / "NC111-32.dxf"
PDF = ROOT / "data" / "TIET_DIEN_NC111-32.pdf"


@pytest.fixture(scope="module")
def dxf():
    return PD.parse(DXF)


@pytest.fixture(scope="module")
def pdf():
    return PP.parse_text(PP.pdf_text(PDF))


def test_dxf_counts(dxf):
    r = dxf["report"]
    assert r["n_lines"] == 664 and r["n_beam_texts"] == 664 and r["n_members"] == 664
    assert r["ids_unique"] and r["id_min"] == 561 and r["id_max"] == 1224
    assert r["ids_missing"] == [] and r["lines_unmatched"] == []
    assert r["errors"] == []


def test_dxf_text_offset_exact(dxf):
    r = dxf["report"]
    assert r["beam_text_offset"] == [-0.4, -0.4, -0.4]
    assert r["max_text_dist"] < 1e-3


def test_dxf_nodes(dxf):
    r = dxf["report"]
    assert r["n_node_texts"] == 238
    assert r["n_nodes_from_geometry"] == 238
    assert r["node_labels_unmatched"] == [] and r["nodes_without_label"] == []


def test_dxf_member_561(dxf):
    m = next(x for x in dxf["members"] if x["id"] == 561)
    assert m["p1"] == [-2.5694, -2.5694, 20.0]
    assert m["p2"] == [-1.2436, -2.4464, 21.4]


def test_pdf_groups(pdf):
    c = PP.check(pdf)
    assert c["n_groups"] == 146 and c["group_ids_contiguous"]
    assert c["n_members"] == 664 and c["duplicate_members"] == []
    assert c["n_result_rows"] == 146 and c["rep_not_first_of_group"] == []
    assert c["groups_without_result"] == [] and c["errors"] == []


def test_pdf_types_normalized(pdf):
    assert {r["type"] for r in pdf["results"]} == {"G", "X", "XĐ", "XAT", "XAD", "XCS", "C", "CĐ"}


def test_pdf_rows(pdf):
    by = {r["rep_member"]: r for r in pdf["results"]}
    assert by[561]["section"] == "L90X7" and by[561]["type"] == "XĐ" and by[561]["A_cm2"] == 12.22
    assert by[561]["bolts"] == {"M16": 3, "M20": 2, "M24": None}
    assert by[569]["section"] == "HL175X12" and by[569]["bolts"] == {"M16": 21, "M20": 14, "M24": 10}
    assert by[573]["bolts"] == {"M16": 1, "M20": None, "M24": None}


def test_pdf_section_area_consistent(pdf):
    _, secs = PP.build(pdf)
    assert all(v["A_consistent"] for v in secs.values())
    assert len(secs) == 11


def test_merge(dxf, pdf):
    groups, _ = PP.build(pdf)
    model, rep = MG.merge(dxf["members"], groups)
    assert rep["n_merged"] == 664
    assert rep["dxf_without_section"] == [] and rep["pdf_not_in_dxf"] == []
    # Khối lượng tính độc lập bằng tổng theo nhóm.
    by_id = {m["id"]: m for m in dxf["members"]}
    indep = sum(g["A_cm2"] * 1e-4 * by_id[i]["length"] * 7850 for g in groups for i in g["members"])
    assert abs(indep - rep["total_mass_kg"]) < 0.5


def test_pick_bolt():
    assert MG.pick_bolt({"M16": 21, "M20": 14, "M24": 10}) == {"size": "M24", "d_mm": 24, "count": 10}
    assert MG.pick_bolt({"M16": 4, "M20": 2, "M24": 2})["size"] == "M20"       # bằng nhau -> nhỏ hơn
    assert MG.pick_bolt({"M16": 1, "M20": None, "M24": None})["size"] == "M16"
