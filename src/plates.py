"""Giai đoạn 9: bu lông và bản mã (đề xuất, người dùng đã duyệt).

Quy ước:
- Bu lông mỗi đầu thanh (trừ thanh cánh C/CĐ): số lượng và đường kính theo PDF, chọn phương án ít
  con nhất, bằng nhau lấy đường kính nhỏ hơn. Một hàng trên đường đinh (giữa cánh liên kết),
  bu lông ngoài cùng cách đầu thanh 1,5d, khoảng cách giữa các bu lông 3d.
- Bản mã đặt tại nút có ít nhất một thanh (không tính thanh cánh) hơn 2 bu lông.
  Tại mỗi nút, các đầu thanh có mặt tiếp xúc (mặt lưng cánh liên kết) trùng nhau thì chung một bản mã.
- Chiều dày bản mã: chiều dày nhỏ nhất của các thanh nối vào bản mã, làm tròn LÊN theo dãy thép tấm
  6, 8, 10, 12, 14, 16 mm.
- Hình bản mã: bao lồi các bu lông (và điểm nút) mở rộng thêm 1,5d tới mép.
- Nút trên thanh cánh, thanh mặt cột: bản mã áp vào cánh thanh cánh, nằm giữa cánh thanh cánh và
  các thanh nối; đầu các thanh nối được đẩy ra một đoạn bằng chiều dày bản mã.
  Nút khác: bản mã nằm phía lưng các thanh nối, không dịch thanh.
- Nút giao chữ X: thanh ngoài và thanh trong quay lưng vào nhau, hở đúng bằng chiều dày cánh thanh
  cánh. Hai bản mã phía lưng được gộp thành MỘT bản đệm lấp khe hở này (dày = khe hở, luôn >= chiều
  dày thanh nối nhỏ nhất vì cánh thanh cánh dày hơn), bu lông xuyên qua cả hai thanh.

Chạy sau orientation:  python3 src/plates.py out/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PLATE_SERIES = [6, 8, 10, 12, 14, 16]
LEG_TYPES = {"C", "CĐ"}
DENSITY = 7850.0


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def plate_thickness(tmin_mm: float) -> int:
    for t in PLATE_SERIES:
        if t >= tmin_mm - 1e-9:
            return t
    return int(math.ceil(tmin_mm / 2) * 2)


def hull(pts):
    pts = sorted(set(map(tuple, pts)))
    if len(pts) < 3:
        return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def poly_area(P):
    return abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))) / 2


def member_geom(m):
    """Đường tim thực vẽ (trên mặt lưng, đường đinh) sau khi dịch: P1, P2, u, e1, e2."""
    p1 = np.array(m.get("p1d", m["p1"]), float)
    p2 = np.array(m.get("p2d", m["p2"]), float)
    off = np.array(m.get("offs", {}).get(m["variant"], [0, 0, 0]), float)
    if m["rule"] == "leg":
        e1, e2 = np.array(m["e1"]), np.array(m["e2"])
    else:
        e1, e2 = (np.array(x) for x in m["frames"][m["variant"]])
    return p1 + off, p2 + off, unit(p2 - p1), e1, e2


def build(scene_members, lib):
    rep = {"warnings": []}
    leg_nodes = {tuple(p) for m in scene_members if m["type"] in LEG_TYPES for p in (m["p1"], m["p2"])}
    leg_t_at = {}
    for m in scene_members:
        if m["type"] in LEG_TYPES:
            for p in (m["p1"], m["p2"]):
                leg_t_at[tuple(p)] = max(leg_t_at.get(tuple(p), 0), lib[m["section"]]["t"])

    # 1) đầu thanh
    ends = []
    for m in scene_members:
        if m["type"] in LEG_TYPES or not m.get("bolt"):
            continue
        P1, P2, u, e1, e2 = member_geom(m)
        L = np.linalg.norm(P2 - P1)
        d = m["bolt"]["d_mm"] / 1000
        n = m["bolt"]["count"]
        need = 1.5 * d + (n - 1) * 3 * d
        if need > L / 2 + 1e-9:
            rep["warnings"].append(f"Thanh {m['id']}: {n} bu lông {m['bolt']['size']} cần {need*1000:.0f} mm "
                                   f"mỗi đầu > nửa chiều dài {L*500:.0f} mm")
        for k, (P, dirv) in enumerate(((P1, u), (P2, -u))):
            node = tuple(m["p1"] if k == 0 else m["p2"])
            bolts = [P + dirv * (1.5 * d + i * 3 * d) for i in range(n)]
            ends.append({"id": m["id"], "end": k, "node": node, "P": P, "n": e2, "bolts": bolts,
                         "d": d, "count": n, "t": lib[m["section"]]["t"], "rule": m["rule"]})

    # 2) gom theo nút + mặt phẳng tiếp xúc
    by_node: dict[tuple, list] = {}
    for e in ends:
        by_node.setdefault(e["node"], []).append(e)
    plates, end_shift = [], {}
    for node, es in by_node.items():
        node_plates = []
        groups = []
        for e in es:
            for g in groups:
                h = g[0]
                if abs(abs(np.dot(h["n"], e["n"])) - 1) < 1e-3 and abs(np.dot(e["P"] - h["P"], h["n"])) < 1.5e-3:
                    g.append(e)
                    break
            else:
                groups.append([e])
        for g in groups:
            if not any(e["count"] > 2 for e in g):
                continue
            nref = g[0]["n"]
            on_leg = node in leg_nodes and all(e["rule"] == "face" for e in g)
            tp = plate_thickness(min(e["t"] for e in g))
            same = [e for e in g if np.dot(e["n"], nref) > 0]
            if len(same) != len(g):
                rep["warnings"].append(f"Nút {node}: bản mã có thanh ở cả hai phía, kiểm tra lại")
            if on_leg:
                thick_dir = nref                       # bản mã giữa cánh thanh cánh và thanh nối
                for e in same:
                    end_shift[(e["id"], e["end"])] = (nref * tp / 1000).tolist()
            else:
                thick_dir = -nref                      # bản mã phía lưng thanh nối
            origin = g[0]["P"]
            a1 = unit(np.cross(nref, [0, 0, 1]))
            if np.linalg.norm(np.cross(nref, [0, 0, 1])) < 1e-6:
                a1 = np.array([1.0, 0, 0])
            a2 = unit(np.cross(nref, a1))
            dmax = max(e["d"] for e in g)
            pts = []
            for e in g:
                for b in e["bolts"]:
                    pts.append(b)
            pts.append(np.array(node, float))
            circ = []
            for p in pts:
                q = p - origin
                x, y = float(q @ a1), float(q @ a2)
                for k in range(16):
                    ang = 2 * math.pi * k / 16
                    circ.append((round(x + 1.5 * dmax * math.cos(ang), 5), round(y + 1.5 * dmax * math.sin(ang), 5)))
            poly = hull(circ)
            area = poly_area(poly)
            node_plates.append({"_g": g, "_pts": pts, "_dmax": dmax, "_n": nref,
                                "_tmin": min(e["t"] for e in g)})
            node_plates[-1].update({
                "node": list(node), "members": sorted({e["id"] for e in g}), "t_mm": tp,
                "on_leg": on_leg, "origin": origin.round(5).tolist(), "a1": a1.round(6).tolist(),
                "a2": a2.round(6).tolist(), "thick_dir": thick_dir.round(6).tolist(),
                "poly": [list(p) for p in poly], "area_m2": round(area, 5),
                "mass_kg": round(area * tp / 1000 * DENSITY, 2),
                "bolt_max": max(e["count"] for e in g), "d_max_mm": round(dmax * 1000),
            })
        # gộp hai bản mã quay lưng vào nhau (nút giao chữ X)
        used = set()
        for i, a in enumerate(node_plates):
            for j, b in enumerate(node_plates):
                if j <= i or i in used or j in used or a["on_leg"] or b["on_leg"]:
                    continue
                ta, tb = np.array(a["thick_dir"]), np.array(b["thick_dir"])
                if np.dot(ta, tb) > -0.999:
                    continue
                gap = float(np.dot(np.array(b["origin"]) - np.array(a["origin"]), ta))
                if not (0 < gap <= (a["t_mm"] + b["t_mm"]) / 1000 + 1e-6):
                    continue
                used.update((i, j))
                pts = a["_pts"] + b["_pts"]
                dmax = max(a["_dmax"], b["_dmax"])
                origin, a1, a2 = np.array(a["origin"]), np.array(a["a1"]), np.array(a["a2"])
                circ = []
                for p in pts:
                    q = p - origin
                    x, y = float(q @ a1), float(q @ a2)
                    for k in range(16):
                        ang = 2 * math.pi * k / 16
                        circ.append((round(x + 1.5 * dmax * math.cos(ang), 5), round(y + 1.5 * dmax * math.sin(ang), 5)))
                poly = hull(circ)
                tp = round(gap * 1000, 1)
                if tp < min(a["_tmin"], b["_tmin"]):
                    rep["warnings"].append(f"Nút {node}: khe hở {tp} mm < chiều dày thanh nối nhỏ nhất")
                area = poly_area(poly)
                merged = {**{k: v for k, v in a.items()}, "members": sorted(set(a["members"]) | set(b["members"])),
                          "t_mm": tp, "poly": [list(p) for p in poly], "area_m2": round(area, 5),
                          "mass_kg": round(area * tp / 1000 * DENSITY, 2), "filler_x": True,
                          "d_max_mm": round(dmax * 1000)}
                node_plates.append(merged)
        for k, pl in enumerate(node_plates):
            if k in used:
                continue
            plates.append({kk: v for kk, v in pl.items() if not kk.startswith("_")})

    # 3) bu lông (sau khi đẩy thanh ra khỏi bản mã)
    bolts = []
    for e in ends:
        sh = np.array(end_shift.get((e["id"], e["end"]), [0, 0, 0]))
        for b in e["bolts"]:
            bolts.append({"id": e["id"], "p": (b + sh).round(5).tolist(), "axis": e["n"].round(6).tolist(),
                          "d_mm": round(e["d"] * 1000), "t_mm": e["t"]})
    rep.update({
        "n_plates": len(plates), "n_plates_on_leg": sum(p["on_leg"] for p in plates),
        "n_filler_x": sum(1 for p in plates if p.get("filler_x")),
        "plate_mass_kg": round(sum(p["mass_kg"] for p in plates), 1),
        "plates_by_t": {t: sum(1 for p in plates if p["t_mm"] == t) for t in sorted({p["t_mm"] for p in plates})},
        "n_bolts": len(bolts),
        "bolts_by_size": {f"M{d}": sum(1 for b in bolts if b["d_mm"] == d) for d in sorted({b["d_mm"] for b in bolts})},
        "n_member_ends_shifted": len(end_shift),
    })
    return plates, bolts, end_shift, rep


def apply(scene: dict, lib: dict):
    plates, bolts, end_shift, rep = build(scene["members"], lib)
    for m in scene["members"]:
        for k in (0, 1):
            s = end_shift.get((m["id"], k))
            if s:
                m[f"poff{k + 1}"] = [round(x, 6) for x in s]
    scene["plates"] = plates
    scene["bolts"] = bolts
    return rep


def print_report(rep):
    print("=== BU LÔNG / BẢN MÃ ===")
    print(f"Bu lông (không tính thanh cánh): {rep['n_bolts']}  {rep['bolts_by_size']}")
    print(f"Bản mã: {rep['n_plates']} (trên thanh cánh: {rep['n_plates_on_leg']}, "
          f"bản đệm nút giao chữ X: {rep['n_filler_x']}), "
          f"theo chiều dày {rep['plates_by_t']}, khối lượng {rep['plate_mass_kg']} kg")
    print(f"Đầu thanh bị đẩy ra theo chiều dày bản mã: {rep['n_member_ends_shifted']}")
    for w in rep["warnings"]:
        print("CẢNH BÁO:", w)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    scene = json.loads((out / "scene.json").read_text())
    rep = apply(scene, scene["sections"])
    (out / "scene.json").write_text(json.dumps(scene, ensure_ascii=False))
    (out / "plates_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print_report(rep)
