"""Giai đoạn 3: ghép thanh (DXF) với nhóm/tiết diện (PDF).

Chạy:  python3 src/merge.py out/      (cần out/members.json, out/groups.json)
Đầu ra: out/model.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STEEL_DENSITY = 7850.0  # kg/m3


BOLT_ORDER = ["M16", "M20", "M24"]


def pick_bolt(bolts: dict) -> dict | None:
    """Ưu tiên số lượng ít nhất; bằng số lượng thì lấy đường kính nhỏ hơn (người dùng chốt)."""
    opts = [(n, BOLT_ORDER.index(k), k) for k, n in bolts.items() if n is not None]
    if not opts:
        return None
    n, _, k = min(opts)
    return {"size": k, "d_mm": int(k[1:]), "count": n}


def merge(members: list[dict], groups: list[dict]) -> tuple[list[dict], dict]:
    grp_of: dict[int, dict] = {}
    dup = []
    for g in groups:
        for m in g["members"]:
            if m in grp_of:
                dup.append(m)
            grp_of[m] = g
    out, missing = [], []
    for m in members:
        g = grp_of.get(m["id"])
        if g is None or "section" not in g:
            missing.append(m["id"])
            continue
        mass = g["A_cm2"] * 1e-4 * m["length"] * STEEL_DENSITY
        out.append({**{k: m[k] for k in ("id", "p1", "p2", "length", "node1", "node2")},
                    "group": g["group"], "section": g["section"], "type": g["type"],
                    "A_cm2": g["A_cm2"], "bolts": g["bolts"], "bolt": pick_bolt(g["bolts"]), "mass_kg": round(mass, 3)})
    dxf_ids = {m["id"] for m in members}
    pdf_only = sorted(set(grp_of) - dxf_ids)
    by_sec: dict[str, dict] = {}
    for m in out:
        s = by_sec.setdefault(m["section"], {"count": 0, "length_m": 0.0, "mass_kg": 0.0})
        s["count"] += 1
        s["length_m"] += m["length"]
        s["mass_kg"] += m["mass_kg"]
    rep = {
        "n_members_dxf": len(members), "n_merged": len(out),
        "dxf_without_section": missing, "pdf_not_in_dxf": pdf_only, "duplicate_in_groups": dup,
        "by_section": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in sorted(by_sec.items())},
        "total_mass_kg": round(sum(m["mass_kg"] for m in out), 2),
    }
    return out, rep


def print_report(r: dict) -> None:
    print("=== GHÉP ===")
    print(f"Thanh DXF / đã ghép  : {r['n_members_dxf']} / {r['n_merged']}")
    print(f"Thanh thiếu tiết diện: {r['dxf_without_section'] or 'không'}")
    print(f"Thanh PDF không có DXF: {r['pdf_not_in_dxf'] or 'không'}")
    print(f"{'Tiết diện':<10}{'SL':>5}{'Dài (m)':>10}{'KL (kg)':>11}")
    for k, v in r["by_section"].items():
        print(f"{k:<10}{v['count']:>5}{v['length_m']:>10.2f}{v['mass_kg']:>11.1f}")
    print(f"Tổng khối lượng thanh (A×L×7850, chưa bản mã/bu lông): {r['total_mass_kg']:.1f} kg")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    members = json.loads((out / "members.json").read_text())
    groups = json.loads((out / "groups.json").read_text())
    model, rep = merge(members, groups)
    (out / "model.json").write_text(json.dumps(model, indent=1, ensure_ascii=False))
    (out / "merge_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print_report(rep)
