"""Giai đoạn 9: bu lông và bản mã (đề xuất, người dùng đã duyệt).

Quy ước (người dùng duyệt; tham khảo bản vẽ chế tạo N122, xem docs/THAM_KHAO_BVTC_N122.md):
- Bu lông mỗi đầu thanh (trừ thanh cánh C/CĐ): số lượng, đường kính theo PDF (ít con nhất, bằng nhau
  lấy đường kính nhỏ hơn). Một hàng trên đường đinh (b/2).
  Khoảng cách tới đầu thanh = max(1,5d, tối thiểu bản vẽ): thanh giằng (G) 25/30/40, thanh chính
  (X, XĐ, XAD, XAT, XCS) 35/45/50 cho M16/M20/M24. Khoảng cách 2 bu lông = max(3d, 50/60/70).
- Nút giao chữ X: 1 bu lông xuyên 2 thanh + tấm đệm vuông 45x45 dày bằng khe hở (không bản mã).
  Đường kính bu lông giao = lớn nhất của các thanh tại nút giao.
- Bản mã tại nút thanh cánh có >= 2 thanh (mặt cột) bắt cùng một mặt tiếp xúc, hoặc tại nút có thanh
  > 2 bu lông. Bản mã bắt vào thanh cánh bằng số bu lông = max(số bu lông thanh lớn nhất, 3), đường
  kính lớn nhất của các thanh nối, trên đường đinh cánh thanh cánh, căn giữa nút, khoảng cách theo
  thanh chính.
- Chiều dày bản mã = thanh nối mỏng nhất làm tròn lên 6/8/10/12/14/16. Hình = bao lồi bu lông + 1,5d.
- Bản mã trên thanh cánh nằm giữa cánh thanh cánh và thanh nối; đầu thanh nối đẩy ra bằng chiều dày
  bản mã. Nút khác: bản mã phía lưng thanh nối.
- Đai ốc quay ra ngoài cột (thanh vách ngang/xà: quay xuống).

Chạy sau orientation:  python3 src/plates.py out/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PLATE_SERIES = [6, 8, 10, 12, 14, 16]
MAIN_TYPES = {"X", "XĐ", "XAD", "XAT", "XCS"}           # thanh chính (không kể thanh cánh)
END_MIN = {"brace": {16: 25, 20: 30, 24: 40}, "main": {16: 35, 20: 45, 24: 50}}   # mm
PITCH_MIN = {16: 50, 20: 60, 24: 70}
EDGE_MIN = {16: 21, 20: 29, 24: 32}
FILLER = 45.0                                            # mm, tấm đệm vuông


def end_dist(type_: str, d_mm: int) -> float:
    kind = "main" if type_ in MAIN_TYPES else "brace"
    return max(1.5 * d_mm, END_MIN[kind][d_mm])


def pitch(d_mm: int) -> float:
    return max(3.0 * d_mm, PITCH_MIN[d_mm])
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


def circles_hull(pts, origin, a1, a2, r):
    circ = []
    for p in pts:
        q = np.asarray(p) - origin
        x, y = float(q @ a1), float(q @ a2)
        for k in range(16):
            ang = 2 * math.pi * k / 16
            circ.append((round(x + r * math.cos(ang), 5), round(y + r * math.sin(ang), 5)))
    return hull(circ)


def plane_axes(nrm):
    a1 = np.cross(nrm, [0, 0, 1])
    a1 = unit(a1) if np.linalg.norm(a1) > 1e-6 else np.array([1.0, 0, 0])
    return a1, unit(np.cross(nrm, a1))


def nut_dir(axis, at):
    """Hướng đặt đai ốc: ra ngoài cột (theo phương bán kính); thanh nằm ngang thì quay xuống."""
    axis = unit(axis)
    radial = np.array([at[0], at[1], 0.0])
    if np.linalg.norm(radial) > 1e-6 and abs(np.dot(axis, unit(radial))) > 0.3:
        return axis if np.dot(axis, radial) > 0 else -axis
    return axis if axis[2] < 0 else -axis


def build(scene_members, lib):
    rep = {"warnings": []}
    by_id = {m["id"]: m for m in scene_members}
    legs = [m for m in scene_members if m["type"] in LEG_TYPES]
    leg_nodes = {tuple(p) for m in legs for p in (m["p1"], m["p2"])}

    def leg_at(node):
        """Thanh cánh tại nút (lấy đoạn phía trên nếu có)."""
        cand = [m for m in legs if tuple(m["p1"]) == node or tuple(m["p2"]) == node]
        cand.sort(key=lambda m: -max(m["p1"][2], m["p2"][2]))
        return cand[0] if cand else None

    # nút giao chữ X: nút không thuộc thanh cánh, có thanh cặp chữ X
    cross_nodes = {}
    for m in scene_members:
        if m.get("x_pair"):
            for k in ("p1", "p2"):
                if tuple(m[k]) not in leg_nodes:
                    cross_nodes.setdefault(tuple(m[k]), []).append(m)
    cross_nodes = {k: v for k, v in cross_nodes.items() if len(v) >= 4}

    # 1) đầu thanh (bỏ đầu tại nút giao chữ X)
    ends = []
    for m in scene_members:
        if m["type"] in LEG_TYPES or not m.get("bolt"):
            continue
        P1, P2, u, e1, e2 = member_geom(m)
        L = np.linalg.norm(P2 - P1)
        dmm = m["bolt"]["d_mm"]
        d = dmm / 1000
        n = m["bolt"]["count"]
        e0, pt = end_dist(m["type"], dmm) / 1000, pitch(dmm) / 1000
        b = lib[m["section"]]["b"]
        if b / 2 < EDGE_MIN[dmm]:
            rep["warnings"].append(f"Thanh {m['id']} {m['section']}: đường đinh b/2={b/2} < mép tối thiểu {EDGE_MIN[dmm]} ({m['bolt']['size']})")
        need = e0 + (n - 1) * pt
        if need > L / 2 + 1e-9:
            rep["warnings"].append(f"Thanh {m['id']}: {n} bu lông {m['bolt']['size']} cần {need*1000:.0f} mm "
                                   f"mỗi đầu > nửa chiều dài {L*500:.0f} mm")
        for k, (P, dirv) in enumerate(((P1, u), (P2, -u))):
            node = tuple(m["p1"] if k == 0 else m["p2"])
            if node in cross_nodes:
                continue
            bolts = [P + dirv * (e0 + i * pt) for i in range(n)]
            ends.append({"id": m["id"], "end": k, "node": node, "P": P, "n": e2, "bolts": bolts,
                         "d": d, "dmm": dmm, "count": n, "t": lib[m["section"]]["t"], "rule": m["rule"],
                         "type": m["type"]})

    # 2) gom theo nút + mặt phẳng tiếp xúc -> bản mã
    by_node: dict[tuple, list] = {}
    for e in ends:
        by_node.setdefault(e["node"], []).append(e)
    plates, end_shift, extra_bolts = [], {}, []
    for node, es in by_node.items():
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
            on_leg = node in leg_nodes and all(e["rule"] == "face" for e in g)
            many = any(e["count"] > 2 for e in g)
            if not (many or (on_leg and len(g) >= 2)):
                continue
            nref = g[0]["n"]
            tp = plate_thickness(min(e["t"] for e in g))
            if any(np.dot(e["n"], nref) < 0 for e in g):
                rep["warnings"].append(f"Nút {node}: bản mã có thanh ở cả hai phía, kiểm tra lại")
            origin = g[0]["P"]
            a1, a2 = plane_axes(nref)
            pts = [b for e in g for b in e["bolts"]]
            dmax_mm = max(e["dmm"] for e in g)
            leg_bolts = []
            if on_leg:
                thick_dir = nref
                for e in g:
                    end_shift[(e["id"], e["end"])] = (nref * tp / 1000).tolist()
                # bu lông bắt bản mã vào thanh cánh: trên đường đinh cánh thanh cánh nằm trong mặt này
                lg = leg_at(node)
                ls = lib[lg["section"]]
                bl, ul = ls["b"] / 1000, unit(np.subtract(lg["p2"], lg["p1"]))
                le1, le2 = np.array(lg["e1"]), np.array(lg["e2"])
                # cánh có pháp tuyến lưng gần nref nhất: cánh 1 lưng -e2, cánh 2 lưng -e1
                back = -le2 if abs(np.dot(-le2, nref)) >= abs(np.dot(-le1, nref)) else -le1
                gauge_pt = np.array(node) + back * (bl / 2)          # trên mặt lưng cánh, cách lưng b/2
                gauge_pt = gauge_pt + nref * float(np.dot(origin - gauge_pt, nref))   # chiếu lên mặt tiếp xúc
                nb = max(3, max(e["count"] for e in g))
                pt = pitch(dmax_mm) / 1000
                for i in range(nb):
                    leg_bolts.append(gauge_pt + ul * (i - (nb - 1) / 2) * pt)
                for bpos in leg_bolts:
                    extra_bolts.append({"id": lg["id"], "p": bpos, "axis": nref, "d_mm": dmax_mm,
                                        "t_mm": ls["t"] + tp, "kind": "plate_leg"})
                pts += leg_bolts
            else:
                thick_dir = -nref
            pts.append(np.array(node, float))
            poly = circles_hull(pts, origin, a1, a2, 1.5 * dmax_mm / 1000)
            area = poly_area(poly)
            plates.append({
                "kind": "gusset", "node": list(node), "members": sorted({e["id"] for e in g}), "t_mm": tp,
                "on_leg": on_leg, "origin": origin.round(5).tolist(), "a1": a1.round(6).tolist(),
                "a2": a2.round(6).tolist(), "thick_dir": unit(thick_dir).round(6).tolist(),
                "poly": [list(p) for p in poly], "area_m2": round(area, 5),
                "mass_kg": round(area * tp / 1000 * DENSITY, 2),
                "bolt_max": max(e["count"] for e in g), "d_max_mm": dmax_mm,
                "leg_bolts": len(leg_bolts), "reason": ">2 bu lông" if many else ">=2 thanh tại nút thanh cánh",
            })

    # 3) nút giao chữ X: 1 bu lông + tấm đệm 45x45 dày bằng khe hở
    for node, ms in cross_nodes.items():
        geo = {m["id"]: member_geom(m) for m in ms}
        nrm = unit(geo[ms[0]["id"]][4])
        planes = sorted({round(float(np.dot(g[0], nrm)), 5) for g in geo.values()})
        dmm = max(m["bolt"]["d_mm"] for m in ms)
        base = np.array(node, float)
        lo_p, hi_p = planes[0], planes[-1]
        gap = hi_p - lo_p
        center = base + nrm * ((lo_p + hi_p) / 2 - float(np.dot(base, nrm)))
        tsum = sum(lib[by_id[i]["section"]]["t"] for i in {ms[0]["id"], ms[-1]["id"]})
        extra_bolts.append({"id": ms[0]["id"], "p": center, "axis": nrm, "d_mm": dmm,
                            "t_mm": gap * 1000 + tsum, "kind": "cross", "centered": True})
        if gap > 1e-4:
            a1, a2 = plane_axes(nrm)
            h = FILLER / 2000
            origin = base + nrm * (lo_p - float(np.dot(base, nrm)))
            sq = [(-h, -h), (h, -h), (h, h), (-h, h)]
            plates.append({
                "kind": "filler", "node": list(node), "members": sorted(m["id"] for m in ms),
                "t_mm": round(gap * 1000, 1), "on_leg": False, "origin": origin.round(5).tolist(),
                "a1": a1.round(6).tolist(), "a2": a2.round(6).tolist(), "thick_dir": nrm.round(6).tolist(),
                "poly": [list(p) for p in sq], "area_m2": round((FILLER / 1000) ** 2, 7),
                "mass_kg": round((FILLER / 1000) ** 2 * gap * DENSITY, 3), "bolt_max": 1, "d_max_mm": dmm,
                "leg_bolts": 0, "reason": "tấm đệm nút giao chữ X",
            })

    # 4) bu lông (sau khi đẩy thanh ra khỏi bản mã)
    bolts = []
    for e in ends:
        sh = np.array(end_shift.get((e["id"], e["end"]), [0, 0, 0]))
        for b in e["bolts"]:
            p = b + sh
            bolts.append({"id": e["id"], "p": p.round(5).tolist(), "axis": unit(e["n"]).round(6).tolist(),
                          "d_mm": e["dmm"], "t_mm": e["t"], "kind": "member",
                          "nut": nut_dir(e["n"], p).round(6).tolist()})
    for b in extra_bolts:
        p = np.asarray(b["p"])
        bolts.append({**{k: v for k, v in b.items() if k not in ("p", "axis")}, "p": p.round(5).tolist(),
                      "axis": unit(b["axis"]).round(6).tolist(), "nut": nut_dir(b["axis"], p).round(6).tolist()})
    gus = [p for p in plates if p["kind"] == "gusset"]
    fil = [p for p in plates if p["kind"] == "filler"]
    rep.update({
        "n_plates": len(gus), "n_plates_on_leg": sum(p["on_leg"] for p in gus),
        "n_fillers": len(fil), "plate_mass_kg": round(sum(p["mass_kg"] for p in gus), 1),
        "filler_mass_kg": round(sum(p["mass_kg"] for p in fil), 2),
        "plates_by_t": {t: sum(1 for p in gus if p["t_mm"] == t) for t in sorted({p["t_mm"] for p in gus})},
        "plates_by_reason": {r: sum(1 for p in gus if p["reason"] == r) for r in sorted({p["reason"] for p in gus})},
        "n_cross_nodes": len(cross_nodes),
        "n_bolts": len(bolts),
        "bolts_by_kind": {k: sum(1 for b in bolts if b["kind"] == k) for k in ("member", "plate_leg", "cross")},
        "bolts_by_size": {f"M{d}": sum(1 for b in bolts if b["d_mm"] == d) for d in sorted({b["d_mm"] for b in bolts})},
        "n_member_ends_shifted": len(end_shift),
    })
    return plates, bolts, end_shift, rep


def apply(scene: dict, lib: dict):
    plates, bolts, end_shift, rep = build(scene["members"], lib)
    n_ch = 0
    for m in scene["members"]:
        # Thanh giằng chéo vát góc 45° cánh không khoan lỗ (bản vẽ N122): mọi thanh không phải thanh
        # cánh và không song song trục X/Y/Z.
        u = unit(np.subtract(m["p2"], m["p1"]))
        m["chamfer"] = bool(m["type"] not in LEG_TYPES and np.max(np.abs(u)) < 1 - 1e-6)
        n_ch += m["chamfer"]
        for k in (0, 1):
            s = end_shift.get((m["id"], k))
            if s:
                m[f"poff{k + 1}"] = [round(x, 6) for x in s]
    scene["plates"] = plates
    scene["bolts"] = bolts
    rep["n_chamfered"] = n_ch
    return rep


def print_report(rep):
    print("=== BU LÔNG / BẢN MÃ ===")
    print(f"Bu lông (không tính mối nối thanh cánh): {rep['n_bolts']}  {rep['bolts_by_size']}  {rep['bolts_by_kind']}")
    print(f"Bản mã: {rep['n_plates']} (trên thanh cánh: {rep['n_plates_on_leg']}), lý do {rep['plates_by_reason']}, "
          f"theo chiều dày {rep['plates_by_t']}, khối lượng {rep['plate_mass_kg']} kg")
    print(f"Nút giao chữ X: {rep['n_cross_nodes']} nút, {rep['n_fillers']} tấm đệm 45x45 ({rep['filler_mass_kg']} kg)")
    print(f"Đầu thanh bị đẩy ra theo chiều dày bản mã: {rep['n_member_ends_shifted']}")
    print(f"Thanh giằng chéo vát 45° hai đầu: {rep.get('n_chamfered', 0)}")
    for w in rep["warnings"]:
        print("CẢNH BÁO:", w)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    scene = json.loads((out / "scene.json").read_text())
    rep = apply(scene, scene["sections"])
    (out / "scene.json").write_text(json.dumps(scene, ensure_ascii=False))
    (out / "plates_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print_report(rep)
