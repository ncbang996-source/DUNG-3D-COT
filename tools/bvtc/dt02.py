"""Dựng 3D đầy đủ đoạn thân DT-02 cột N122 từ bản vẽ chế tạo (BVTC) để người dùng soát.

Nguồn: tờ DT-02 (mặt đứng 1 mặt, 4 mặt giống nhau xoay 90°; mặt cắt 1-1..4-4).
Quy ước đọc mặt đứng (nhìn từ NGOÀI vào, tỉ lệ 1/25):
- đường tâm (CENTER) = đường đinh; nét chiều dày cánh còn lại sát mép LƯNG;
- nét chiều dày KHUẤT -> cánh còn lại chĩa vào trong (thanh TRONG); LIỀN -> chĩa ra ngoài (NGOÀI).
Độ sâu (δ, dương = ra ngoài, gốc = mặt phẳng qua đường tim thanh cánh) tính theo THANH CHỦ mà đầu
thanh bắt vào:
- thanh cánh: mặt ngoài cánh δ = g (đường tim cách lưng g), mặt trong δ = g - t;
- thanh TRONG áp mặt trong của thanh chủ, thanh NGOÀI áp mặt ngoài;
- nút có bản mã: bản mã áp mặt ngoài thanh chủ (hình cắt A-A), thanh NGOÀI áp mặt ngoài bản mã,
  thanh TRONG áp mặt trong bản mã.
Mỗi đầu thanh có độ sâu riêng (poff1/poff2).

Chạy:  python3 tools/bvtc/dt02.py <BVTC.dxf> <thư mục ra>
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import ezdxf  # noqa: E402
import bvtc_read as R  # noqa: E402
import check_dt02 as CK  # noqa: E402
import section_library as SL  # noqa: E402

SC = R.SC
SL.JIS_G3192.update({"L75X6": (75, 6, 8.5, 4), "L130X9": (130, 9, 12, 6), "L150X15": (150, 15, 14, 10)})
BOX = (-2380, -122110, -2040, -121674)          # mặt đứng DT-02 (không lấy hình khai triển thanh cánh)
PLANS = {   # tên: (y vạch cắt trên mặt đứng, khung đọc mặt cắt)
    "1-1": (-121780.0, (-1980, -121766, -1880, -121680)),
    "2-2": (-121852.3, (-1980, -122063, -1812, -121905)),
    "3-3": (-121935.3, (-1980, -121880, -1867, -121785)),
    "4-4": (-122015.4, (-1875, -122170, -1805, -122092)),
}
TOL = 0.6                                        # đơn vị bản vẽ (15 mm) để coi là chạm


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def rot(k):
    c, s = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def dist_seg(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    t = 0.0 if L2 == 0 else ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2
    tc = max(0.0, min(1.0, t))
    return math.dist(p, (a[0] + tc * ax, a[1] + tc * ay)), t


def dist_line(p, a, b):
    return abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / math.dist(a, b)


def inter(a1, a2, b1, b2):
    d = (a1[0] - a2[0]) * (b1[1] - b2[1]) - (a1[1] - a2[1]) * (b1[0] - b2[0])
    if abs(d) < 1e-9:
        return None
    t = ((a1[0] - b1[0]) * (b1[1] - b2[1]) - (a1[1] - b1[1]) * (b1[0] - b2[0])) / d
    return (a1[0] + t * (a2[0] - a1[0]), a1[1] + t * (a2[1] - a1[1]))


def point_in_poly(p, poly):
    x, y = p
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


LIB = {}


def sec(name):
    if name not in LIB:
        b, t, r1, r2 = SL.JIS_G3192[SL.base_name(name)]
        pts = SL.profile(b, t, r1, r2)
        A, cx, cy = SL.poly_props(pts)
        LIB[name] = {"name": name, "base": SL.base_name(name), "standard": "JIS G3192", "b": b, "t": t,
                     "r1": r1, "r2": r2, "A_geom_cm2": round(A / 100, 3), "A_pdf_cm2": round(A / 100, 3),
                     "cx": round(cx, 2), "cy": round(cy, 2), "gauge": b / 2,
                     "profile": [[round(x, 3), round(y, 3)] for x, y in pts]}
    return LIB[name]


# ---------------------------------------------------------------- mặt đứng
def read_elevation(doc, msp):
    ms = R.members(doc, msp, BOX)
    segs = R.segments(doc, msp, BOX)
    wide = [m for m in ms if m["width"] >= 120 and 60 < m["ang"] < 120]
    braces = [m for m in ms if m["width"] < 120]
    # điểm làm việc = giao điểm các cặp đường tâm thanh giằng
    wps = []
    for i, a in enumerate(braces):
        for b in braces[i + 1:]:
            if abs(a["ang"] - b["ang"]) > 3 and (p := inter(a["c1"], a["c2"], b["c1"], b["c2"])):
                wps.append(p)

    def score(c1, c2, ylo, yhi):
        return -sum(min(dist_line(p, c1, c2), 3.0) for p in wps
                    if ylo - 2 <= p[1] <= yhi + 2 and dist_line(p, c1, c2) < 3.0)

    def best_line(leg):
        ylo, yhi = sorted((leg["p1"][1], leg["p2"][1]))
        nx = leg["nvec"]
        cands = []
        for off in leg["centers_rel"]:
            o = off / SC
            c1 = (leg["c1"][0] + nx[0] * o, leg["c1"][1] + nx[1] * o)
            c2 = (leg["c2"][0] + nx[0] * o, leg["c2"][1] + nx[1] * o)
            cands.append((score(c1, c2, ylo, yhi), off, c1, c2))
        s_, off, c1, c2 = max(cands)
        return s_, off, c1, c2

    # thanh cánh: thanh rộng có nhiều đầu thanh giằng chạm (cách < 2,5 đơn vị) nhất, mỗi phía một thanh.
    # Đường tim = đường tâm chính (dài nhất) của thanh cánh (bản vẽ ghi cách lưng 80).
    # Ở DT-02 các thanh KHÔNG đồng quy một điểm trên thanh cánh (bắt so le, cách nhau 100 mm).
    def touches(m):
        return sum(1 for b_ in braces for p in (b_["c1"], b_["c2"]) if dist_line(p, m["c1"], m["c2"]) < 2.5
                   and min(m["p1"][1], m["p2"][1]) - 2 <= p[1] <= max(m["p1"][1], m["p2"][1]) + 2)
    scored = [(touches(m), m, 0.0, m["c1"], m["c2"]) for m in wide]
    left = max((x for x in scored if x[1]["ang"] <= 90), key=lambda x: x[0])
    right = max((x for x in scored if x[1]["ang"] > 90), key=lambda x: x[0])
    legs = []
    for n_on, m, off, c1, c2 in (left, right):
        g = abs(m["heel_signed"] - off) if m.get("heel_signed") is not None else 80.0
        # chiều dài thật: mọi nét thẳng hàng trong bề rộng thanh cánh
        L = math.dist(c1, c2)
        ux, uy = (c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L
        ss = []
        for sg in segs:
            if abs(((math.degrees(sg["ang"]) - m["ang"]) + 90) % 180 - 90) > 1.0:
                continue
            if all(dist_line(p, c1, c2) <= 170 / SC for p in (sg["a"], sg["b"])):
                ss += [(p[0] - c1[0]) * ux + (p[1] - c1[1]) * uy for p in (sg["a"], sg["b"])]
        a = (c1[0] + ux * min(ss), c1[1] + uy * min(ss))
        b = (c1[0] + ux * max(ss), c1[1] + uy * max(ss))
        legs.append({"m": m, "w1": c1, "w2": c2, "a": a, "b": b, "g": g, "n_wp": n_on})
    return ms, segs, braces, legs, wps


def main(dxf, outdir):
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    rep = {"warnings": []}
    ms, segs, braces, legs, wps = read_elevation(doc, msp)
    Lg, Rg = legs
    xline = lambda leg, y: leg["w1"][0] + (y - leg["w1"][1]) * (leg["w2"][0] - leg["w1"][0]) / (leg["w2"][1] - leg["w1"][1])
    ymid = (Lg["w1"][1] + Lg["w2"][1]) / 2
    xc = (xline(Lg, ymid) + xline(Rg, ymid)) / 2
    halfw = lambda y: (xline(Rg, y) - xline(Lg, y)) / 2 * SC           # mm
    labs = R.text_labels(msp, BOX)
    R.assign_labels(ms, labs, xc)
    for leg in legs:
        leg["section"] = leg["m"].get("section") or "HL150X12"

    # chỉ giữ thanh giằng trong thân, có nét thấy (không phải toàn khuất), có tiết diện
    keep, dropped = [], []
    for m in braces:
        inside = all(abs(p[0] - xc) * SC <= halfw(p[1]) + 60 for p in (m["c1"], m["c2"]))
        if m["all_hidden"] or not inside:
            dropped.append(m)
            continue
        if not m.get("section"):
            freq = {}
            for t, _ in labs:
                freq[t] = freq.get(t, 0) + 1
            best = min(freq, key=lambda t: (abs(int(re.match(r"H?L(\d+)", t).group(1)) - m["width"]), -freq[t]))
            m["section"], m["section_from"] = best, "đoán theo bề rộng"
        keep.append(m)
    rep["n_brace_drawing"] = len(braces)
    rep["n_brace_kept"] = len(keep)
    rep["dropped"] = [{"ang": round(m["ang"], 1), "w": m["width"], "edges": m["edges"]} for m in dropped]

    # --- gốc cao độ: đầu dưới thanh cánh
    y0 = min(Lg["a"][1], Lg["b"][1])
    zf = lambda y: (y - y0) * SC                                          # mm

    # --- bản mã (lớp Banma) có nút liên kết bên trong, độ dày theo nhãn "d N"
    x0, ya, x1, yb = BOX
    inb = lambda p: x0 <= p[0] <= x1 and ya <= p[1] <= yb
    thk = [(int(t.dxf.text.split()[-1]), (t.dxf.insert[0], t.dxf.insert[1])) for t in msp.query("TEXT")
           if re.fullmatch(r"d\s*\d+", t.dxf.text.strip()) and inb(t.dxf.insert)]
    nodes = []
    lines2d = [(m["c1"], m["c2"]) for m in keep] + [(L_["a"], L_["b"]) for L_ in legs]
    for i, (a1, a2) in enumerate(lines2d):
        for b1, b2 in lines2d[i + 1:]:
            p = inter(a1, a2, b1, b2)
            if p and dist_seg(p, a1, a2)[0] < TOL and dist_seg(p, b1, b2)[0] < TOL:
                nodes.append(p)
    plates2d = []
    for e in msp.query('LWPOLYLINE[layer=="Banma"]'):
        pts = [(q[0], q[1]) for q in e.get_points()]
        if not pts or not all(inb(q) for q in pts):
            continue
        inside_nodes = [n for n in nodes if point_in_poly(n, pts)]
        on_leg_plate = any(dist_line(q, L_["w1"], L_["w2"]) < 3.0 for q in pts for L_ in legs) and \
            any(min(L_["a"][1], L_["b"][1]) <= q[1] <= max(L_["a"][1], L_["b"][1]) for q in pts for L_ in legs)
        if not inside_nodes and not on_leg_plate:
            continue                       # hình chi tiết vẽ riêng trong khung
        if not inside_nodes:
            inside_nodes = [(sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))]
        c = (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))
        near = sorted(thk, key=lambda t: math.dist(t[1], c))
        t_mm = near[0][0] if near and math.dist(near[0][1], c) < 45 else 8
        plates2d.append({"pts": pts, "t": t_mm, "nodes": inside_nodes})

    # --- bản vẽ đứng thấy cạnh (dải hẹp < 1 đơn vị nằm trong bản mã khác) = bản hàn VUÔNG GÓC mặt bản mã
    bbox = lambda P: (min(q[0] for q in P), min(q[1] for q in P), max(q[0] for q in P), max(q[1] for q in P))
    for pl in list(plates2d):
        x0_, y0_, x1_, y1_ = bbox(pl["pts"])
        if min(x1_ - x0_, y1_ - y0_) < 1.0:
            par = next((o for o in plates2d if o is not pl and point_in_poly(((x0_ + x1_) / 2, (y0_ + y1_) / 2), o["pts"])), None)
            if par is not None:
                plates2d.remove(pl)
                par["strip"] = {"pts": pl["pts"], "x": (x0_ + x1_) / 2}
    # --- hình chi tiết bản mã (tỉ lệ 1/10) theo số hiệu ghi cạnh bản mã trên mặt đứng (VD "418", "419"):
    #     hình dạng + lỗ lấy đúng chi tiết, đặt tâm chi tiết trùng tâm bản mã trên mặt đứng.
    nums = [(t.dxf.text.strip(), (t.dxf.insert[0], t.dxf.insert[1])) for t in msp.query("TEXT")
            if re.fullmatch(r"\d{3}", t.dxf.text.strip())]
    thk_all = [(int(t.dxf.text.split()[-1]), (t.dxf.insert[0], t.dxf.insert[1])) for t in msp.query("TEXT")
               if re.fullmatch(r"d\s*\d+", t.dxf.text.strip())]
    banma = [[(q[0], q[1]) for q in e.get_points()] for e in msp.query('LWPOLYLINE[layer=="Banma"]')]
    bolt_ins = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name])
                for e in msp.query("INSERT") if e.dxf.name in ("1", "2", "3")]

    def detail_of(label, exclude):
        best = None
        for tx, p in nums:
            if tx != label:
                continue
            for P in banma:
                if any(P is ex or P == ex for ex in exclude):
                    continue
                bx = bbox(P)
                d_ = math.hypot(max(bx[0] - p[0], 0, p[0] - bx[2]), max(bx[1] - p[1], 0, p[1] - bx[3]))
                if d_ < 30 and (best is None or d_ < best[0]):
                    best = (d_, P)
        return best[1] if best else None
    rep["plate_details"] = []
    elev_polys = [pl["pts"] for pl in plates2d] + [pl["strip"]["pts"] for pl in plates2d if "strip" in pl]
    for pl in plates2d:
        bx = bbox(pl["pts"])
        cxy = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        if any(dist_line(cxy, L_["w1"], L_["w2"]) < 12 for L_ in legs):
            continue                              # bản mã tại thanh cánh: giữ như mặt đứng (đã soát)
        labs_ = [(tx, p) for tx, p in nums if math.dist(p, cxy) < 35]
        if not labs_:
            continue
        cands = []
        for tx, p in labs_:
            P = detail_of(tx, elev_polys)
            if P is not None:
                db = bbox(P)
                cands.append((tx, p, P, (db[2] - db[0]) / (db[3] - db[1])))
        if not cands:
            continue
        asp = (bx[2] - bx[0]) / (bx[3] - bx[1])
        main_ = min(cands, key=lambda c: abs(c[3] - asp))
        tx, p, P, _ = main_
        db = bbox(P)
        dc = ((db[0] + db[2]) / 2, (db[1] + db[3]) / 2)
        f = 10.0 / SC                                         # 1 đơn vị chi tiết = 10 mm
        pl["pts"] = [(cxy[0] + (q[0] - dc[0]) * f, cxy[1] + (q[1] - dc[1]) * f) for q in P]
        pl["holes"] = [((cxy[0] + (q[0] - dc[0]) * f, cxy[1] + (q[1] - dc[1]) * f), d_)
                       for q, d_ in bolt_ins if point_in_poly(q, P)]
        pl["t"] = min(thk_all, key=lambda t_: math.dist(t_[1], p))[0]
        pl["mark"] = tx
        info = {"mark": tx, "size_mm": [round((db[2] - db[0]) * 10), round((db[3] - db[1]) * 10)], "t": pl["t"],
                "holes": len(pl["holes"])}
        if "strip" in pl:
            rest = [c for c in cands if c is not main_]
            if rest:
                tx2, p2, P2, _ = rest[0]
                d2 = bbox(P2)
                pl["strip"].update({"mark": tx2, "w_mm": round(min(d2[2] - d2[0], d2[3] - d2[1]) * 10),
                                    "L_mm": round(max(d2[2] - d2[0], d2[3] - d2[1]) * 10),
                                    "t": min(thk_all, key=lambda t_: math.dist(t_[1], p2))[0]})
                info["strip"] = {k: pl["strip"][k] for k in ("mark", "w_mm", "L_mm", "t")}
        rep["plate_details"].append(info)
    rep["n_plates_face"] = len(plates2d)

    # --- thanh vẽ liền một đường tâm nhưng nét mép bị ngắt tại bản mã (VD thanh ngang L80x6 qua bản mã giữa):
    #     thực tế là 2 thanh, mỗi thanh dừng ở bản mã. Tách tại giữa chỗ ngắt.
    rep["split_at_plate"] = []
    for m in list(keep):
        iv = sorted(m["edge_iv"])
        if not iv:
            continue
        merged = [list(iv[0])]
        for a_, b_ in iv[1:]:
            if a_ > merged[-1][1] + 1e-6:
                merged.append([a_, b_])
            else:
                merged[-1][1] = max(merged[-1][1], b_)
        for (a0, a1_), (b0, b1_) in zip(merged, merged[1:]):
            if b0 - a1_ < 4.0:
                continue
            smid = (a1_ + b0) / 2
            pm_ = (m["ref_a"][0] + m["ref_u"][0] * smid, m["ref_a"][1] + m["ref_u"][1] * smid)
            if not any(point_in_poly(pm_, pl["pts"]) for pl in plates2d):
                continue
            P = lambda s_: (m["ref_a"][0] + m["ref_u"][0] * s_, m["ref_a"][1] + m["ref_u"][1] * s_)
            sof = lambda q: (q[0] - m["ref_a"][0]) * m["ref_u"][0] + (q[1] - m["ref_a"][1]) * m["ref_u"][1]
            sc1, sc2 = sorted((sof(m["c1"]), sof(m["c2"])))
            sb1, sb2 = merged[0][0], merged[-1][1]
            parts = []
            for (cs, ce, bs, be) in ((sc1, smid, sb1, a1_), (smid, sc2, b0, sb2)):
                n_ = dict(m)
                n_["c1"], n_["c2"], n_["b1"], n_["b2"] = P(cs), P(ce), P(bs), P(be)
                n_["p1"], n_["p2"] = P(min(cs, bs)), P(max(ce, be))
                n_["edge_iv"] = [x for x in iv if bs - 1e-6 <= x[0] <= be + 1e-6]
                n_["split_from"] = True
                parts.append(n_)
            keep.remove(m)
            keep.extend(parts)
            rep["split_at_plate"].append({"section": m["section"], "ang": round(m["ang"], 1),
                                          "gap_mm": round((b0 - a1_) * SC)})
            break

    # --- thanh chủ của từng đầu thanh
    def host_of(m, p):
        for L_ in legs:
            if dist_line(p, L_["w1"], L_["w2"]) < 2.5:          # đầu thanh bắt vào cánh thanh cánh
                return ("leg", L_)
        best = None
        for o in keep:
            if o is m:
                continue
            d_, t = dist_seg(p, o["c1"], o["c2"])
            if d_ < 2.5 and 0.02 < t < 0.98 and (best is None or d_ < best[0]):   # <= 62 mm
                best = (d_, o)
        return ("brace", best[1]) if best else (None, None)

    def plate_at(p):
        for pl in plates2d:
            if point_in_poly(p, pl["pts"]) or any(math.dist(p, n) < TOL for n in pl["nodes"]):
                return pl
        return None

    for m in keep:
        m["out"] = m["vis"] == "S"
        m["t_mm"] = sec(m["section"])["t"]
        m["delta"] = [None, None]
        m["host"] = [host_of(m, m["c1"]), host_of(m, m["c2"])]
        m["plate"] = [plate_at(m["c1"]), plate_at(m["c2"])]

    tl = sec(Lg["section"])["t"]
    gl = Lg["g"]
    for pl in plates2d:                       # bản mã áp mặt ngoài cánh thanh cánh (A-A) nếu nằm trên thanh cánh
        on_leg_ = any(dist_line(n, L_["w1"], L_["w2"]) < 3.0 for n in pl["nodes"] for L_ in legs)
        pl["delta0"] = gl if on_leg_ else None
        pl["on_leg_fixed"] = on_leg_
    pt_k = lambda m, k: m["c1"] if k == 0 else m["c2"]

    def delta_at(h, p):
        """Độ sâu lưng thanh h tại điểm p (nội suy tuyến tính giữa 2 đầu: thanh thẳng)."""
        d0, d1 = h["delta"]
        if d0 is None or d1 is None:
            return d0 if d1 is None else d1
        _, t = dist_seg(p, h["c1"], h["c2"])
        return d0 + (d1 - d0) * max(0.0, min(1.0, t))

    def free_plate_delta(pl):
        """Bản mã giữa mặt (không trên thanh cánh): mặt trong bản mã áp lưng các thanh TRONG; vị trí lấy theo
        đầu kia (đầu đã cố định) của các thanh đó - thanh thẳng nên bản mã nằm thấp nhất trong các giá trị."""
        ds = []
        for m in keep:
            for k in (0, 1):
                if m["plate"][k] is pl and not m["out"] and m["delta"][1 - k] is not None and m["plate"][1 - k] is not pl:
                    ds.append(m["delta"][1 - k])
        return min(ds) if ds else None

    # lan truyền độ sâu: lặp tới khi ổn định; đầu bắt vào thanh giằng lấy độ sâu thanh chủ ĐÚNG TẠI điểm bắt
    rep["depth_iterations"] = 0
    for it in range(80):
        rep["depth_iterations"] = it + 1
        changed = 0.0
        for pl in plates2d:
            if pl.get("on_leg_fixed"):
                continue
            if pl["delta0"] is None or pl.get("free"):
                v = free_plate_delta(pl)
                if v is not None:
                    pl["free"] = True
                    changed = max(changed, abs((pl["delta0"] or 0) - v) if pl["delta0"] is not None else 1e9)
                    pl["delta0"] = v
        for m in keep:
            for k in (0, 1):
                kind, h = m["host"][k]
                pl = m["plate"][k]
                pk = pt_k(m, k)
                in_base = (pk[1] - min(Lg["a"][1], Lg["b"][1])) * SC < 560 and \
                    any(dist_line(pk, L_["w1"], L_["w2"]) < 12 for L_ in legs)
                if in_base:
                    # chân cột: đầu thanh ép sát sườn d12 (sườn nằm ngoài lưng cánh thanh cánh, mặt trong δ = g)
                    lo, hi = gl, gl + 12
                elif pl is not None and pl["delta0"] is not None:
                    lo, hi = pl["delta0"], pl["delta0"] + pl["t"]
                elif kind == "leg":
                    lo, hi = gl - tl, gl
                elif kind == "brace" and h is not None and any(v is not None for v in h["delta"]):
                    db = delta_at(h, pk)
                    lo, hi = sorted((db, db + (h["t_mm"] if h["out"] else -h["t_mm"])))
                else:
                    continue
                v = hi if m["out"] else lo
                old = m["delta"][k]
                changed = max(changed, 1e9 if old is None else abs(old - v))
                m["delta"][k] = v
        if changed < 0.01:
            break
    for m in keep:                             # đầu tự do (giao chữ X không thanh chủ): lấy theo đầu kia
        if m["delta"][0] is None and m["delta"][1] is not None:
            m["delta"][0] = m["delta"][1]
        if m["delta"][1] is None and m["delta"][0] is not None:
            m["delta"][1] = m["delta"][0]
        if m["delta"][0] is None:
            m["delta"] = [gl if m["out"] else gl - tl] * 2
            rep["warnings"].append(f"thanh {m['section']} góc {m['ang']:.1f}: không tìm được thanh chủ")
            rep.setdefault("no_host", []).append(m)
    for pl in plates2d:
        if pl["delta0"] is None:
            pl["delta0"] = gl

    # --- vát cánh theo ghi chú bản vẽ (mặt đứng: 40x60 đầu dưới thanh xiên chính bắt sườn chân cột;
    #     45x45 đầu 4 thanh xiên tại bản mã giữa). Vát trên cánh liên kết (thấy trên mặt đứng).
    base_y0 = min(Lg["a"][1], Lg["b"][1])
    for m in keep:
        for k in (0, 1):
            p_ = pt_k(m, k)
            kind_, _h = m["host"][k]
            near_leg = any(dist_line(p_, L_["w1"], L_["w2"]) < 12 for L_ in legs)
            if near_leg and (p_[1] - base_y0) * SC < 560:
                m.setdefault("cuts", {})[k] = {"flange": "conn", "a": 40, "b": 60, "note": "vát cánh 40x60mm"}
            # bản mã giữa có bản hàn vuông góc (419): ghi chú "vát cánh 45x45mm" chỉ vào đầu 4 thanh xiên tại
            # bản mã (góc mép cánh sát bản hàn), không phải thanh ngang
            plk = m["plate"][k]
            if plk is not None and "strip" in plk and 3 < m["ang"] % 180 < 177:
                # góc nào của đầu thanh sát bản hàn thì vát góc đó: góc LƯNG (cánh còn lại gắn ở lưng cũng bị cắt
                # lùi) hoặc góc MÉP cánh liên kết
                be = m["b1"] if k == 0 else m["b2"]
                b_ = sec(m["section"])["b"]
                hs = m["heel_signed"] if m["heel_signed"] is not None else b_ / 2
                toe = hs - math.copysign(b_, hs)
                cx_ = lambda o: abs(be[0] + m["nvec"][0] * o / SC - plk["strip"]["x"])
                fl_ = "heel" if cx_(hs) < cx_(toe) else "conn"
                m.setdefault("cuts", {})[k] = {"flange": fl_, "a": 45, "b": 45,
                                              "note": "vát cánh 45x45mm góc %s (sát bản hàn %s)" % (
                                                  "lưng" if fl_ == "heel" else "mép", plk["strip"].get("mark", ""))}
    # mặt cắt: vát cánh 30x30 (1-1, 3-3, 4-4) và 45x45 (2-2) ở đầu thanh ngang mặt cột tại thanh cánh (cánh nằm ngang)
    level_cut = {"1-1": 30, "2-2": 45, "3-3": 30, "4-4": 30}
    for pname, (ymark, _box) in PLANS.items():
        for m in keep:
            ang = m["ang"] % 180
            if (ang < 3 or ang > 177) and abs(m["c1"][1] - ymark) < 12:
                for k in (0, 1):
                    if m["host"][k][0] == "leg":
                        m.setdefault("cuts", {})[k] = {"flange": "out", "a": level_cut[pname], "b": level_cut[pname],
                                                      "note": f"vát cánh {level_cut[pname]}x{level_cut[pname]}mm (mặt cắt {pname})"}

    # --- bu lông vẽ (khối 1/2/3): độ sâu = mặt tiếp xúc của thanh dưới nó
    bolts2d = []
    # ký hiệu bu lông "S.F_D": S con, M F, dài D (mm)
    blabs = []
    for t_ in msp.query("TEXT"):
        mt = re.fullmatch(r"(\d+)\.(\d+)_(\d+)", t_.dxf.text.strip())
        if mt and inb(t_.dxf.insert):
            blabs.append((int(mt.group(1)), int(mt.group(2)), int(mt.group(3)), (t_.dxf.insert[0], t_.dxf.insert[1])))

    def bolt_len(q, dmm, grip):
        """Chiều dài theo ký hiệu bản vẽ gần nhất cùng đường kính: chọn L ngắn nhất >= kẹp + đai ốc + vòng đệm."""
        need = grip + 0.8 * dmm + 4 + 3
        cand = sorted({L for (n_, d_, L, pp) in blabs if d_ == dmm and math.dist(pp, q) < 40})
        if not cand:
            return None, need
        ok = [L for L in cand if L >= need]
        return (ok[0] if ok else cand[-1]), need

    base_y = min(Lg["a"][1], Lg["b"][1])
    for e in msp.query("INSERT"):
        if e.dxf.name not in ("1", "2", "3") or not inb(e.dxf.insert):
            continue
        q = (e.dxf.insert[0], e.dxf.insert[1])
        if (q[1] - base_y) * SC < 560 and any(dist_line(q, L_["w1"], L_["w2"]) < 16 for L_ in legs):
            continue                                   # chân cột: lấy đúng theo lỗ trên chi tiết sườn
        if any("holes" in pl and point_in_poly(q, pl["pts"]) for pl in plates2d):
            continue                                   # bản mã có hình chi tiết: lấy lỗ theo chi tiết
        if not any(point_in_poly(q, pl["pts"]) for pl in plates2d) and \
                any(point_in_poly(q, P) for P in banma if P not in [pl["pts"] for pl in plates2d]):
            continue                                   # lỗ trên hình chi tiết vẽ riêng
        bolts2d.append({"p": q, "d": {"1": 16, "2": 20, "3": 24}[e.dxf.name], "src": "mặt đứng"})
    for pl in plates2d:
        for q, d_ in pl.get("holes", []):
            bolts2d.append({"p": q, "d": d_, "src": "chi tiết bản mã " + pl.get("mark", "")})

    # --- đầu thanh: tối thiểu = tim bu lông ngoài cùng + khoảng cách tới đầu thanh (thanh giằng 25/30/40 mm cho
    #     M16/M20/M24 - ghi chú chung). Cần khi phần đầu thanh nằm sau thanh cánh, nét vẽ bị khuất/không vẽ.
    ED = {16: 25.0, 20: 30.0, 24: 40.0}
    rep["ends_extended"] = 0
    rep["ends_drawn_kept"] = 0
    # nét đầu thanh vẽ rõ (đoạn ngắn vuông góc trục thanh tại đầu thanh): đầu thanh đã xác định, KHÔNG kéo dài
    short_lines = []
    for e in msp.query("LINE"):
        a_, b_ = (e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])
        if inb(a_) and inb(b_) and 30 <= math.dist(a_, b_) * SC <= 160:
            short_lines.append((a_, b_))

    def end_drawn(m, pe):
        L = math.dist(m["c1"], m["c2"])
        u_ = ((m["c2"][0] - m["c1"][0]) / L, (m["c2"][1] - m["c1"][1]) / L)
        for a_, b_ in short_lines:
            d_ = ((b_[0] - a_[0]) / math.dist(a_, b_), (b_[1] - a_[1]) / math.dist(a_, b_))
            if abs(d_[0] * u_[0] + d_[1] * u_[1]) < 0.1 and \
                    min(dist_seg(pe, a_, b_)[0], math.dist(pe, a_), math.dist(pe, b_)) < 0.3:
                return True
        return False

    def in_flange(m, q, margin=5.0):
        """Bu lông q (2D) có xuyên cánh liên kết thanh m: nằm trong đoạn đường tim (c1..c2, dư 10 mm) và trong
        bề rộng cánh (từ lưng tới mép, cách mép >= margin mm)."""
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        sq = (q[0] - c1[0]) * u_[0] + (q[1] - c1[1]) * u_[1]
        if not (-0.4 <= sq <= L + 0.4):
            return False
        o = ((q[0] - c1[0]) * m["nvec"][0] + (q[1] - c1[1]) * m["nvec"][1]) * SC
        b_ = sec(m["section"])["b"]
        hs = m["heel_signed"] if m["heel_signed"] is not None else b_ / 2
        toe = hs - math.copysign(b_, hs)
        return min(hs, toe) + margin <= o <= max(hs, toe) - margin
    for m in keep:
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        sof = lambda p_: (p_[0] - c1[0]) * u_[0] + (p_[1] - c1[1]) * u_[1]
        # bu lông của thanh: nằm trên đường đinh (đường tâm) của thanh (lệch <= 8 mm) và trong cánh; bu lông nối
        # thanh cánh nằm trong vùng đầu thanh nhưng không trên đường đinh thanh giằng -> không tính
        offs_ = m.get("centers_rel") or [0.0]
        on = [(sof(b["p"]), b["d"]) for b in bolts2d if in_flange(m, b["p"]) and
              min(abs(((b["p"][0] - c1[0]) * m["nvec"][0] + (b["p"][1] - c1[1]) * m["nvec"][1]) * SC - o_)
                  for o_ in offs_) <= 8]
        s1, s2 = sof(m["b1"]), sof(m["b2"])
        lo_side = [x for x in on if x[0] < (s1 + s2) / 2]
        hi_side = [x for x in on if x[0] >= (s1 + s2) / 2]
        if lo_side and end_drawn(m, m["b1"]):
            rep["ends_drawn_kept"] += 1
            lo_side = []
        if hi_side and end_drawn(m, m["b2"]):
            rep["ends_drawn_kept"] += 1
            hi_side = []
        if lo_side:
            sb, dd = min(lo_side)
            need = sb - ED[dd] / SC
            if need < s1 - 0.04:
                m["b1"] = (c1[0] + u_[0] * need, c1[1] + u_[1] * need)
                rep["ends_extended"] += 1
        if hi_side:
            sb, dd = max(hi_side)
            need = sb + ED[dd] / SC
            if need > s2 + 0.04:
                m["b2"] = (c1[0] + u_[0] * need, c1[1] + u_[1] * need)
                rep["ends_extended"] += 1

    # --- chồng lớp thép tại mỗi bu lông (theo hình học đã dựng, không đoán theo thanh gần nhất):
    #     mọi cánh liên kết của thanh / bản mã / cánh thanh cánh có lỗ trùng tim bu lông -> bu lông kẹp từ lớp
    #     trong cùng tới lớp ngoài cùng; kiểm tra các lớp phải liền nhau (không hở).
    def layers_at(q):
        lay = []
        for m in keep:
            c1, c2 = m["c1"], m["c2"]
            L = math.dist(c1, c2)
            u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
            sq = (q[0] - c1[0]) * u_[0] + (q[1] - c1[1]) * u_[1]
            sb = sorted(((m["b1"][0] - c1[0]) * u_[0] + (m["b1"][1] - c1[1]) * u_[1],
                         (m["b2"][0] - c1[0]) * u_[0] + (m["b2"][1] - c1[1]) * u_[1]))
            if not (sb[0] + 0.2 <= sq <= sb[1] - 0.2):          # cách đầu thanh >= 5 mm
                continue
            o = ((q[0] - c1[0]) * m["nvec"][0] + (q[1] - c1[1]) * m["nvec"][1]) * SC
            b_ = sec(m["section"])["b"]
            hs = m["heel_signed"] if m["heel_signed"] is not None else b_ / 2
            toe = hs - math.copysign(b_, hs)
            if not (min(hs, toe) + 5 <= o <= max(hs, toe) - 5):
                continue
            # độ sâu nội suy theo 2 đầu thanh THẬT (b1 <-> δ đầu 1, b2 <-> δ đầu 2), giống hình 3D
            s1_ = (m["b1"][0] - c1[0]) * u_[0] + (m["b1"][1] - c1[1]) * u_[1]
            s2_ = (m["b2"][0] - c1[0]) * u_[0] + (m["b2"][1] - c1[1]) * u_[1]
            t = max(0.0, min(1.0, (sq - s1_) / (s2_ - s1_)))
            d_ = m["delta"][0] + (m["delta"][1] - m["delta"][0]) * t
            rng = (d_, d_ + m["t_mm"]) if m["out"] else (d_ - m["t_mm"], d_)
            lay.append((rng[0], rng[1], m["section"] + (" NGOAI" if m["out"] else " TRONG")))
        for pl in plates2d:
            if point_in_poly(q, pl["pts"]):
                lay.append((pl["delta0"], pl["delta0"] + pl["t"], "bản mã d%d" % pl["t"]))
        for L_ in legs:
            ylo, yhi = sorted((L_["a"][1], L_["b"][1]))
            if not (ylo <= q[1] <= yhi):
                continue
            # cánh thanh cánh trên mặt: từ lưng (cách đường tim g, phía ngoài) tới mép (150 - g, phía trong)
            sgn = 1 if L_ is Lg else -1                      # phía trong mặt = +x với thanh cánh trái
            off = (q[0] - xline(L_, q[1])) * SC * sgn
            if -L_["g"] + 5 <= off <= sec(L_["section"])["b"] - L_["g"] - 5:
                lay.append((gl - tl, gl, L_["section"]))
        if lay and all(n_.startswith(Lg["section"]) for _, _, n_ in lay):
            # mối nối thanh cánh: thép góc nối trong HL130x9 + bản nối ngoài d10 (hình cắt A-A)
            lay += [(gl - tl - 9, gl - tl, "HL130X9 nối trong"), (gl, gl + 10, "bản nối ngoài d10")]
        return lay

    rep["bolt_gaps"] = []
    rep["bolts_dropped"] = 0
    keepb2 = []
    for bb in bolts2d:
        lay = layers_at(bb["p"])
        if not lay:
            rep["bolts_dropped"] += 1
            rep.setdefault("bolts_dropped_pts", []).append(bb["p"])
            continue
        lay.sort()
        lo, hi = lay[0][0], max(x[1] for x in lay)
        cur = lay[0][1]
        for a_, b_, n_ in lay[1:]:
            if a_ > cur + 0.5:
                rep["bolt_gaps"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                         "gap_mm": round(a_ - cur, 1), "layers": [x[2] for x in lay]})
            cur = max(cur, b_)
        L_b, need = bolt_len(bb["p"], bb["d"], hi - lo)
        bb.update({"lo": lo, "hi": hi, "layers": [x[2] for x in lay], "L": L_b or math.ceil(need / 10) * 10,
                   "L_from": "ký hiệu bản vẽ" if L_b else "tính (không thấy ký hiệu)"})
        keepb2.append(bb)
    bolts2d[:] = keepb2

    # --- chiếu sang 3D (mặt trước y = -h), xoay 4 mặt
    def to3(p, delta_mm=0.0):
        z = zf(p[1])
        h = halfw(p[1])
        return np.array([(p[0] - xc) * SC, -h, z]) / 1000.0, delta_mm

    ybot, ytop = Lg["w1"][1], Lg["w2"][1]
    slope = (halfw(ytop) - halfw(ybot)) / ((ytop - ybot) * SC)           # dh/dz
    tup = unit([0, -slope, 1])
    nf = unit(np.cross([1.0, 0, 0], tup))
    if nf[1] > 0:
        nf = -nf
    ex = np.array([1.0, 0, 0])
    members, plates, bolts = [], [], []
    mid = 0
    for k in range(4):
        Rk = rot(k)
        n = Rk @ nf
        # thanh cánh (góc trái mặt trước, xoay ra 4 góc)
        L_ = Lg
        P1, P2 = Rk @ to3(L_["a"])[0], Rk @ to3(L_["b"])[0]
        u = unit(P2 - P1)
        fa, fb = Rk @ np.array([0, -1.0, 0]), Rk @ np.array([-1.0, 0, 0])
        e1 = unit(-fb - np.dot(-fb, u) * u)
        e2 = unit(-fa - np.dot(-fa, u) * u - np.dot(-fa, e1) * e1)
        s_ = sec(L_["section"])
        mid += 1
        members.append({"id": mid, "p1": P1.round(5).tolist(), "p2": P2.round(5).tolist(),
                        "length": round(float(np.linalg.norm(P2 - P1)), 4), "section": L_["section"],
                        "A_cm2": s_["A_geom_cm2"], "type": "C", "rule": "leg", "e1": e1.round(6).tolist(),
                        "e2": e2.round(6).tolist(), "g": [L_["g"], L_["g"]], "variant": "leg",
                        "auto_variant": "leg", "frames": {}, "offs": {}, "group": 1, "bolts": {}, "bolt": None,
                        "node1": None, "node2": None, "face_k": k, "side": "thanh cánh"})
        for m in keep:
            # đầu thanh THẬT theo nét bản vẽ (đã cách bu lông ngoài cùng đúng khoảng cách), không kéo tới nút
            P1, P2 = Rk @ to3(m["b1"])[0], Rk @ to3(m["b2"])[0]
            u = unit(P2 - P1)
            nn = unit(n - np.dot(n, u) * u)
            hv = m["heel_dir"]
            tu = Rk @ tup
            hv3 = unit(hv[0] * (Rk @ ex) + hv[1] * tu) if hv else tu
            hv3 = unit(hv3 - np.dot(hv3, u) * u - np.dot(hv3, nn) * nn)
            e1 = -hv3
            e2 = nn if m["out"] else -nn
            s_ = sec(m["section"])
            ang = m["ang"] % 180
            mid += 1
            members.append({
                "id": mid, "p1": P1.round(5).tolist(), "p2": P2.round(5).tolist(),
                "length": round(float(np.linalg.norm(P2 - P1)), 4), "section": m["section"],
                "A_cm2": s_["A_geom_cm2"], "type": "G" if (ang < 3 or ang > 177) else "X", "rule": "face",
                "face": "", "variant": "bv", "auto_variant": "bv",
                "frames": {"bv": [e1.round(6).tolist(), e2.round(6).tolist()]}, "offs": {"bv": [0, 0, 0]},
                "poff1": (nn * m["delta"][0] / 1000).round(6).tolist(),
                "poff2": (nn * m["delta"][1] / 1000).round(6).tolist(),
                "g": [m["heel_to_center"] or s_["b"] / 2, 0.0], "group": 2, "bolts": {}, "bolt": None,
                "node1": None, "node2": None, "face_k": k, "x_pair": False, "default_up": False,
                "side": "NGOAI" if m["out"] else "TRONG",
                "plate_end": [bool(m["plate"][kk] is not None and not m["plate"][kk].get("on_leg_fixed")) for kk in (0, 1)],
                **({f"cut{kk + 1}": v for kk, v in m.get("cuts", {}).items()}),
                "drawing": {"edges": m["edges"], "width": m["width"], "section_from": m.get("section_from", "nhãn"),
                            "delta_mm": [round(v, 1) for v in m["delta"]]}})
        for pl in plates2d:
            P = [Rk @ to3(q)[0] + n * pl["delta0"] / 1000 for q in pl["pts"]]
            o, a1, a2 = P[0], Rk @ ex, Rk @ tup
            poly = [[round(float(np.dot(q - o, a1)), 5), round(float(np.dot(q - o, a2)), 5)] for q in P]
            area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                           for i in range(len(poly)))) / 2
            plates.append({"kind": "gusset", "node": o.round(4).tolist(), "members": [], "t_mm": pl["t"],
                           "on_leg": True, "origin": o.round(5).tolist(), "a1": a1.round(6).tolist(),
                           "a2": a2.round(6).tolist(), "thick_dir": n.round(6).tolist(), "poly": poly,
                           "area_m2": round(area, 5), "mass_kg": round(area * pl["t"] / 1000 * 7850, 2),
                           "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0,
                           "reason": ("bản mã %s theo hình chi tiết (DT-02)" % pl["mark"]) if pl.get("mark")
                           else "bản vẽ DT-02 (mặt đứng)"})
            st = pl.get("strip")
            if st and st.get("L_mm"):
                # bản hàn vuông góc: dài L dọc mặt cột (tâm = tâm bản mã), rộng w, dày t
                bxs = [q[1] for q in pl["pts"]]
                ymid_ = (min(bxs) + max(bxs)) / 2
                # người dùng chốt: bản 419 chĩa RA NGOÀI, bắt đầu từ mặt ngoài bản mã 418
                cen = Rk @ to3((st["x"], ymid_))[0] + n * (pl["delta0"] + pl["t"]) / 1000
                a1s, a2s = Rk @ tup, n
                o = cen - a1s * st["L_mm"] / 2000 - (Rk @ ex) * st["t"] / 2000
                Ls, Ws = st["L_mm"] / 1000, st["w_mm"] / 1000
                plates.append({"kind": "gusset", "node": cen.round(4).tolist(), "members": [], "t_mm": st["t"],
                               "on_leg": False, "origin": o.round(5).tolist(), "a1": a1s.round(6).tolist(),
                               "a2": a2s.round(6).tolist(), "thick_dir": (Rk @ ex).round(6).tolist(),
                               "poly": [[0, 0], [round(Ls, 5), 0], [round(Ls, 5), round(Ws, 5)], [0, round(Ws, 5)]],
                               "area_m2": round(Ls * Ws, 5), "mass_kg": round(Ls * Ws * st["t"] / 1000 * 7850, 2),
                               "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0,
                               "reason": "bản %s %dx%d d%d hàn vuông góc giữa bản mã %s" % (
                                   st["mark"], st["w_mm"], st["L_mm"], st["t"], pl.get("mark", ""))})
        for b in bolts2d:
            p = Rk @ to3(b["p"])[0] + n * b["lo"] / 1000          # mặt tựa đầu bu lông (phía trong)
            bolts.append({"id": 0, "p": p.round(5).tolist(), "axis": n.round(6).tolist(), "grip_mm": round(b["hi"] - b["lo"], 1),
                          "L_mm": b["L"], "L_from": b["L_from"],
                          "nut": n.round(6).tolist(), "d_mm": b["d"], "t_mm": 10, "kind": "drawing"})

    # --- mặt cắt vách ngang
    plan_rep = {}
    plan_chk = {}
    plan_bolts, plan_plates = [], []
    plan_members = []
    for pname, (ymark, box) in PLANS.items():
        hor = [m for m in ms if (m["ang"] % 180 < 1 or m["ang"] % 180 > 179)]
        ycut = min((m["c1"][1] for m in hor), key=lambda y: abs(y - ymark))
        if abs(ycut - ymark) > 12:
            ycut = ymark
        z = zf(ycut)
        h = halfw(ycut)
        pm = R.members(doc, msp, box)
        pl_labs = R.text_labels(msp, box)
        # góc cột = giao đường tâm thanh dọc trái nhất và thanh ngang thấp nhất (góc dưới-trái)
        vx = [(m["c1"][0] + m["c2"][0]) / 2 for m in pm if 88 < m["ang"] < 92]
        hy = [(m["c1"][1] + m["c2"][1]) / 2 for m in pm if m["ang"] < 2 or m["ang"] > 178]
        cxp, cyp = min(vx), min(hy)
        R.assign_labels(pm, pl_labs, None)
        # Đường tâm thanh ngang mặt cột trên mặt cắt = đường đinh CÁNH NẰM NGANG của nó (nơi bắt thanh giằng),
        # không phải mặt phẳng mặt cột. Lệch vào trong: hp = h + (độ sâu lưng thanh ngang - đường đinh).
        fh2 = [m for m in keep if (m["ang"] % 180 < 3 or m["ang"] % 180 > 177) and abs(m["c1"][1] - ycut) < 12]
        if fh2:
            mh = min(fh2, key=lambda m: abs(m["c1"][1] - ycut))
            dback = min(mh["delta"])
            # đường đinh cánh nằm ngang cách lưng bao nhiêu: đọc ngay trên mặt cắt (thanh mặt cột vẽ tại góc),
            # không lấy theo mặt đứng (mặt đứng chỉ cho đường đinh cánh đứng)
            fm = [m for m in pm if 88 < m["ang"] < 92 and abs((m["c1"][0] + m["c2"][0]) / 2 - cxp) < 0.2
                  and m.get("heel_to_center")]
            fm += [m for m in pm if (m["ang"] < 2 or m["ang"] > 178) and abs((m["c1"][1] + m["c2"][1]) / 2 - cyp) < 0.2
                   and m.get("heel_to_center")]
            g_plan = fm[0]["heel_to_center"] if fm else (mh["heel_to_center"] or sec(mh["section"])["b"] / 2)
            plan_off = dback - g_plan
            plan_rep_g = {"g_plan_mm": g_plan, "dback_mm": round(dback, 1)}
        else:
            plan_off = 0.0
        hp = h + plan_off
        # 1/4 vách đối xứng qua đường chéo góc: thanh chưa nhãn lấy nhãn thanh đối xứng (đổi x <-> y)
        mir = lambda p: (cxp + (p[1] - cyp), cyp + (p[0] - cxp))
        for m in pm:
            if m.get("section"):
                continue
            for o in pm:
                if o.get("section") and min(math.dist(mir(m["c1"]), o["c1"]) + math.dist(mir(m["c2"]), o["c2"]),
                                            math.dist(mir(m["c1"]), o["c2"]) + math.dist(mir(m["c2"]), o["c1"])) < 3:
                    m["section"], m["section_from"] = o["section"], "đối xứng qua đường chéo góc"
                    break
        allx = [p[0] for m in pm for p in (m["c1"], m["c2"])]
        ally = [p[1] for m in pm for p in (m["c1"], m["c2"])]
        span = ((max(allx) - cxp) * SC, (max(ally) - cyp) * SC)
        kept = []
        for m in pm:
            if m["width"] >= 120:
                continue
            # mặt bằng: thanh vẽ toàn nét khuất là thanh nằm DƯỚI thanh khác, vẫn giữ
            q1 = ((m["b1"][0] - cxp) * SC - hp, (m["b1"][1] - cyp) * SC - hp)   # mm, gốc = tâm cột, đầu thanh thật
            q2 = ((m["b2"][0] - cxp) * SC - hp, (m["b2"][1] - cyp) * SC - hp)
            ax_ = unit([q2[0] - q1[0], q2[1] - q1[1], 0])
            on_face = (abs(ax_[1]) > 0.999 and abs(q1[0] + h) < 120 and abs(q2[0] + h) < 120) or \
                      (abs(ax_[0]) > 0.999 and abs(q1[1] + h) < 120 and abs(q2[1] + h) < 120)
            if on_face:
                continue                                    # thanh mặt cột: đã dựng từ mặt đứng
            # mặt cắt chỉ vẽ 1/4 vách (góc dưới-trái): cắt thanh theo 1/4 đó (x <= 0, y <= 0) rồi mới xoay
            def clip(a_, b_):
                t0, t1 = 0.0, 1.0
                for i in (0, 1):
                    da = b_[i] - a_[i]
                    if abs(da) < 1e-9:
                        if a_[i] > 5:
                            return None
                        continue
                    t = (0 - a_[i]) / da
                    if da > 0:
                        t1 = min(t1, t)
                    else:
                        t0 = max(t0, t)
                if t1 - t0 <= 0:
                    return None
                f = lambda t: (a_[0] + t * (b_[0] - a_[0]), a_[1] + t * (b_[1] - a_[1]))
                return f(t0), f(t1)
            cl = clip(q1, q2)
            if cl is None or math.dist(*cl) < 50:
                continue
            q1, q2 = cl
            if not m.get("section"):
                pool = [t for t, _ in pl_labs] or [t for t, _ in labs]
                best = min(pool, key=lambda t: abs(int(re.match(r"H?L(\d+)", t).group(1)) - m["width"]))
                m["section"], m["section_from"] = best, "đoán theo bề rộng"
                rep["warnings"].append(f"mặt cắt {pname}: thanh rộng {m['width']} không có nhãn, đoán {best}")
            kept.append((m, q1, q2))
        # bu lông (khối 1/2/3) và bản mã (lớp Banma) vẽ trên mặt cắt: lấy trong 1/4 vách, trục đứng
        bx0, by0, bx1, by1 = box
        inbox = lambda p: bx0 <= p[0] <= bx1 and by0 <= p[1] <= by1
        loc = lambda p: ((p[0] - cxp) * SC - hp, (p[1] - cyp) * SC - hp)
        pb, pp = 0, 0
        for e in msp.query("INSERT"):
            if e.dxf.name in ("1", "2", "3") and inbox(e.dxf.insert):
                q = loc(e.dxf.insert)
                if q[0] <= 5 and q[1] <= 5:
                    dmm_ = {"1": 16, "2": 20, "3": 24}[e.dxf.name]
                    labsP = []
                    for t_ in msp.query("TEXT"):
                        mt = re.fullmatch(r"(\d+)\.(\d+)_(\d+)", t_.dxf.text.strip())
                        if mt and inbox(t_.dxf.insert) and int(mt.group(2)) == dmm_:
                            labsP.append((math.dist(t_.dxf.insert, e.dxf.insert), int(mt.group(3))))
                    Lp = min(labsP)[1] if labsP else None
                    plan_bolts.append((q, z, dmm_, Lp))
                    pb += 1
        for e in msp.query('LWPOLYLINE[layer=="Banma"]'):
            pts = [(q_[0], q_[1]) for q_ in e.get_points()]
            if pts and all(inbox(q_) for q_ in pts):
                Q = [loc(q_) for q_ in pts]
                cxq, cyq = sum(q_[0] for q_ in Q) / len(Q), sum(q_[1] for q_ in Q) / len(Q)
                if cxq <= 5 and cyq <= 5:
                    plan_plates.append((Q, z))
                    pp += 1
        plan_rep_extra = {"bolts": pb, "plates": pp}
        plan_rep[pname] = {**plan_rep_extra, **(plan_rep_g if fh2 else {}), "z_mm": round(z), "h_mm": round(h),
                           "n_read": len(pm), "n_kept": len(kept),
                           "span_mm": [round(span[0]), round(span[1])]}
        plan_chk[pname] = {"cad": [[[(sg["a"][0] - cxp) * SC - h, (sg["a"][1] - cyp) * SC - h],
                                    [(sg["b"][0] - cxp) * SC - h, (sg["b"][1] - cyp) * SC - h], sg["k"]]
                                   for sg in R.segments(doc, msp, box)],
                           "kept": [[list(q1), list(q2), m["section"], m["vis"]] for m, q1, q2 in kept], "h": h}
        # đầu thanh vách: tim bu lông ngoài cùng trên đường đinh + khoảng cách tới đầu thanh (25/30/40 mm)
        EDp = {16: 25.0, 20: 30.0, 24: 40.0}
        my_bolts = [(q, d_) for (q, z_, d_, _L) in plan_bolts if abs(z_ - z) < 1e-6]
        kept2 = []
        for m, q1, q2 in kept:
            q1, q2 = np.array(q1, float), np.array(q2, float)
            Lq = np.linalg.norm(q2 - q1)
            uq = (q2 - q1) / Lq
            for q, d_ in my_bolts:
                v = np.array(q) - q1
                sq = float(np.dot(v, uq))
                if abs(v[0] * uq[1] - v[1] * uq[0]) > 8 or not (-60 < sq < Lq + 60):
                    continue
                if sq - EDp[d_] < 0:
                    q1 = q1 + uq * (sq - EDp[d_])
                    rep.setdefault("plan_ends_extended", []).append({"plan": pname, "section": m["section"],
                                                                     "mm": round(EDp[d_] - sq, 1)})
                    Lq = np.linalg.norm(q2 - q1); uq = (q2 - q1) / Lq
                elif sq + EDp[d_] > Lq:
                    rep.setdefault("plan_ends_extended", []).append({"plan": pname, "section": m["section"],
                                                                     "mm": round(sq + EDp[d_] - Lq, 1)})
                    q2 = q1 + uq * (sq + EDp[d_])
                    Lq = np.linalg.norm(q2 - q1); uq = (q2 - q1) / Lq
            kept2.append((m, tuple(q1), tuple(q2)))
        kept = kept2
        for m, q1, q2 in kept:
            up = m["vis"] == "S"          # nét chiều dày LIỀN nhìn từ trên = cánh còn lại chĩa LÊN
            hv = m["heel_dir"]
            for k in range(4):
                Rk = rot(k)
                P1 = Rk @ np.array([q1[0], q1[1], z]) / 1000
                P2 = Rk @ np.array([q2[0], q2[1], z]) / 1000
                u = unit(P2 - P1)
                hv3 = Rk @ unit([hv[0], hv[1], 0]) if hv else unit(np.cross([0, 0, 1.0], u))
                hv3 = unit(hv3 - np.dot(hv3, u) * u)
                e2 = np.array([0, 0, 1.0 if up else -1.0])
                e1 = unit(-hv3 - np.dot(-hv3, e2) * e2)
                s_ = sec(m["section"])
                plan_members.append({
                    "p1": P1.round(5).tolist(), "p2": P2.round(5).tolist(),
                    "length": round(float(np.linalg.norm(P2 - P1)), 4), "section": m["section"],
                    "A_cm2": s_["A_geom_cm2"], "type": "G", "rule": "plan", "variant": "bv", "auto_variant": "bv",
                    "frames": {"bv": [e1.round(6).tolist(), e2.round(6).tolist()]}, "offs": {"bv": [0, 0, 0]},
                    "g": [m["heel_to_center"] or s_["b"] / 2, 0.0], "group": 3, "bolts": {}, "bolt": None,
                    "node1": None, "node2": None, "face_k": -1, "x_pair": False, "default_up": up,
                    "side": "LEN" if up else "XUONG", "plan": pname})
    # thanh vách đặt TRÊN (hoặc dưới) cánh nằm ngang của thanh ngang mặt cột mà nó bắt vào (theo mặt cắt)
    face_h = [m for m in members if m["rule"] == "face" and m["type"] == "G"]

    def seg_d3(p_, a_, b_):
        a_, b_, p_ = np.asarray(a_), np.asarray(b_), np.asarray(p_)
        ab = b_ - a_
        t_ = np.clip(np.dot(p_ - a_, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
        return np.linalg.norm(p_ - (a_ + t_ * ab))
    rep["plan_ends_on_flange"] = 0
    for pm_ in plan_members:
        tm = sec(pm_["section"])["t"] / 1000
        for key in ("p1", "p2"):
            P_ = np.array(pm_[key])
            best = None
            for fh in face_h:
                a_ = np.array(fh["p1"]) + np.array(fh["poff1"]); b_ = np.array(fh["p2"]) + np.array(fh["poff2"])
                if abs(a_[2] - P_[2]) > 0.2:
                    continue
                dd = seg_d3(P_ * [1, 1, 0] + [0, 0, a_[2]], a_, b_)
                if dd < 0.15 and (best is None or dd < best[0]):
                    best = (dd, fh, a_[2])
            if best is None:
                continue
            fh, zax = best[1], best[2]
            e1h = np.array(fh["frames"]["bv"][0])
            th = sec(fh["section"])["t"] / 1000
            gh = fh["g"][0] / 1000
            heel_up = -e1h[2] > 0
            if heel_up:
                z_top = zax + gh                          # mặt trên cánh nằm ngang (lưng ở trên)
                zc = z_top if pm_["default_up"] else z_top - th
            else:
                z_bot = zax - gh
                zc = z_bot + th if pm_["default_up"] else z_bot
            pm_[key] = [pm_[key][0], pm_[key][1], round(zc, 5)]
            pm_.setdefault("contact", {})[key] = {"z": zc, "t_host": th * 1000, "host_id": fh["id"]}
            rep["plan_ends_on_flange"] += 1
        pm_["length"] = round(float(np.linalg.norm(np.array(pm_["p2"]) - np.array(pm_["p1"]))), 4)

    # mặt cắt vẽ 1/4 vách nên thanh chạy qua trục đối xứng bị cắt đôi; ghép lại thành 1 thanh (VD L70x6 vách 2-2
    # dài 1406 + 1406 trên bản vẽ)
    rep["plan_merged"] = 0
    merged_any = True
    while merged_any:
        merged_any = False
        for i, a_ in enumerate(plan_members):
            for b_ in plan_members[i + 1:]:
                if a_["section"] != b_["section"] or a_["plan"] != b_["plan"] or a_["side"] != b_["side"]:
                    continue
                A1, A2, B1, B2 = (np.array(a_[k_]) for k_ in ("p1", "p2")), None, None, None
                A1, A2 = np.array(a_["p1"]), np.array(a_["p2"])
                B1, B2 = np.array(b_["p1"]), np.array(b_["p2"])
                ua, ub = unit(A2 - A1), unit(B2 - B1)
                if abs(abs(np.dot(ua, ub)) - 1) > 1e-4:
                    continue
                pairs = [(A2, B1, A1, B2), (A2, B2, A1, B1), (A1, B1, A2, B2), (A1, B2, A2, B1)]
                hit = next(((s1, s2) for j1, j2, s1, s2 in pairs if np.linalg.norm(j1 - j2) < 0.002), None)
                if hit is None:
                    continue
                s1, s2 = hit
                if np.linalg.norm(np.cross(unit(s2 - s1), ua)) > 1e-3:
                    continue
                a_["p1"], a_["p2"] = s1.round(5).tolist(), s2.round(5).tolist()
                a_["length"] = round(float(np.linalg.norm(s2 - s1)), 4)
                a_["merged_halves"] = True
                plan_members.remove(b_)
                rep["plan_merged"] += 1
                merged_any = True
                break
            if merged_any:
                break

    # đầu thanh vách bắt vào THANH VÁCH khác (giao giữa vách): thanh có cánh còn lại chĩa LÊN đặt TRÊN cánh nằm
    # ngang của thanh chủ, chĩa XUỐNG đặt SÁT MÉP DƯỚI thanh chủ (bản vẽ 2-2: thanh xiên từ góc nằm trên thanh
    # xiên lớn, 2 thanh L70x6 nằm sát dưới thanh xiên lớn)
    rep["plan_on_plan"] = []
    for _ in range(3):
        for pm_ in plan_members:
            for key in ("p1", "p2"):
                if key in pm_.get("contact", {}):
                    continue
                P_ = np.array(pm_[key])
                best = None
                for h_ in plan_members:
                    if h_ is pm_ or h_["plan"] != pm_["plan"]:
                        continue
                    H1, H2 = np.array(h_["p1"]), np.array(h_["p2"])
                    d2 = H2[:2] - H1[:2]
                    t_ = float(np.dot(P_[:2] - H1[:2], d2) / np.dot(d2, d2))
                    dd = float(np.linalg.norm(P_[:2] - (H1[:2] + t_ * d2)))
                    if 0.02 < t_ < 0.98 and dd < 0.08 and (best is None or dd < best[0]):
                        best = (dd, h_, t_)
                if best is None:
                    continue
                h_, t_ = best[1], best[2]
                zh = h_["p1"][2] + (h_["p2"][2] - h_["p1"][2]) * t_
                th = sec(h_["section"])["t"] / 1000
                lo_, hi_ = (zh, zh + th) if h_["default_up"] else (zh - th, zh)
                zc = hi_ if pm_["default_up"] else lo_
                pm_[key] = [pm_[key][0], pm_[key][1], round(zc, 5)]
                pm_.setdefault("on_plan", {})[key] = {"host": h_["section"], "z": zc, "t_host": th * 1000,
                                                      "above": bool(pm_["default_up"])}
        for pm_ in plan_members:
            pm_["length"] = round(float(np.linalg.norm(np.array(pm_["p2"]) - np.array(pm_["p1"]))), 4)
    for pm_ in plan_members:
        for key, v in pm_.get("on_plan", {}).items():
            rep["plan_on_plan"].append({"plan": pm_["plan"], "section": pm_["section"], "host": v["host"],
                                        "vi_tri": "trên" if v["above"] else "sát dưới"})

    # bỏ trùng (mặt cắt vẽ cả 2 phía tâm thì xoay sẽ trùng)
    seen = set()
    for m in plan_members:
        key = tuple(sorted([tuple(np.round(m["p1"], 2)), tuple(np.round(m["p2"], 2))]))
        if key in seen:
            continue
        seen.add(key)
        mid += 1
        m["id"] = mid
        members.append(m)
    rep["plans"] = plan_rep
    seenb = set()
    for (q, z, dmm, Lp) in plan_bolts:
        for k in range(4):
            p = rot(k) @ np.array([q[0], q[1], z]) / 1000
            key = tuple(np.round(p, 3))
            if key in seenb:
                continue
            seenb.add(key)
            # thanh vách nằm ngang: đầu bu lông phía trên, đai ốc phía dưới; kẹp 2 cánh nằm ngang
            # bu lông nằm ở đầu thanh vách: đầu bu lông ở mặt trên lớp thép trên cùng, kẹp thanh vách + cánh ngang
            ph = p + np.array([0, 0, 0.006])
            bestp = None
            for pm_ in plan_members:
                for key in ("p1", "p2"):
                    P_ = np.array(pm_[key])
                    dxy = np.linalg.norm((P_ - p)[:2])
                    if dxy < 0.15 and (bestp is None or dxy < bestp[0]):
                        bestp = (dxy, pm_, key)
            grip_ = 12
            if bestp and "contact" in bestp[1] and bestp[2] in bestp[1]["contact"]:
                pm_, key = bestp[1], bestp[2]
                c_ = pm_["contact"][key]
                tm = sec(pm_["section"])["t"]
                top = c_["z"] + (tm / 1000 if pm_["default_up"] else 0)
                ph = np.array([p[0], p[1], top])
                grip_ = tm + c_["t_host"]
            bolts.append({"id": 0, "p": ph.round(5).tolist(), "axis": [0, 0, -1.0], "nut": [0, 0, -1.0],
                          "d_mm": dmm, "grip_mm": grip_, "L_mm": Lp or 40,
                          "L_from": "ký hiệu bản vẽ" if Lp else "tính", "t_mm": 8, "kind": "plan"})
    for (Q, z) in plan_plates:
        for k in range(4):
            P = [rot(k) @ np.array([q[0], q[1], z]) / 1000 for q in Q]
            o, a1, a2 = P[0], rot(k) @ np.array([1.0, 0, 0]), rot(k) @ np.array([0, 1.0, 0])
            poly = [[round(float(np.dot(q - o, a1)), 5), round(float(np.dot(q - o, a2)), 5)] for q in P]
            area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                           for i in range(len(poly)))) / 2
            plates.append({"kind": "gusset", "node": o.round(4).tolist(), "members": [], "t_mm": 8,
                           "on_leg": False, "origin": o.round(5).tolist(), "a1": a1.round(6).tolist(),
                           "a2": a2.round(6).tolist(), "thick_dir": [0, 0, -1.0], "poly": poly,
                           "area_m2": round(area, 5), "mass_kg": round(area * 8 / 1000 * 7850, 2),
                           "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0, "reason": "bản vẽ DT-02 (mặt cắt)"})

    # --- chân cột: số liệu đọc từ DXF (tờ DT-02, chi tiết tỉ lệ 1/10)
    # Sườn d12 (đường bao lớp Banma, mm, gốc = góc dưới-trái hình chi tiết):
    RIB1 = [(0, 100), (0, 0), (545, 0), (545, 350), (435, 490), (220, 490)]      # 13 lỗ: 10 thanh cánh + 3 thanh xiên
    RIB2 = [(0, 100), (0, 0), (157, 0), (192, 30), (260, 490), (220, 490)]      # không lỗ, cắt góc 30x30
    RIB3 = [(0, 30), (30, 0), (345, 0), (345, 350), (235, 490), (73, 490)]      # 13 lỗ
    # Vị trí (khớp lỗ sườn với bu lông chân thanh cánh trên mặt đứng, lệch <= 5 mm):
    #   sườn 1 nằm trên cánh thanh cánh ở mặt đang xét (thanh cánh trái): x = -3971 + u, đáy sườn z = 11
    #   sườn 3 trên cánh thứ hai (thấy ở thanh cánh phải, đối xứng gương):  x = 3771 - u
    #   => góc lưng thanh cánh ở |x| = 3771; mặt bằng bản đế: lưng cách mép ngoài 200, bản 450x450x40,
    #      sườn 1 bắt đầu từ mép bản (3771 + 200 = 3971 khớp); sườn 2 nối tiếp sườn 3 ra ngoài, sau sườn 1.
    HEEL = 3771.0
    RIB1_H = [(265, 98), (277, 177), (289, 256), (300, 335), (312, 415), (315, 131), (327, 210), (339, 289), (351, 368),
              (362, 448), (430, 213), (468, 272), (505, 331)]      # lỗ sườn D322 đọc từ DXF (mm)
    RIB3_H = [(71, 138), (83, 217), (95, 296), (106, 375), (110, 91), (118, 454), (122, 171), (133, 250), (145, 329),
              (157, 408), (230, 213), (268, 272), (305, 331)]      # lỗ sườn D323
    slope_abs = abs(slope)
    Z0 = 11.0
    T_RIB = 12.0
    rib_specs = [(RIB1, lambda u: -3971.0 + u, "sườn 1 (545x490, 13 lỗ)"),
                 (RIB3, lambda u: HEEL - u, "sườn 3 (345x490, 13 lỗ)"),
                 # cạnh xiên (192,30)-(260,490) của sườn 2 có độ dốc = độ nghiêng thanh cánh -> áp dọc mặt ngoài sườn 1
                 (RIB2, lambda u: HEEL + T_RIB - slope_abs * 490 * tup[2] + (260 - u),
                  "sườn 2 (260x490, không lỗ; mặt bằng bản đế vẽ 188 - cần kiểm)")]
    rep["base_note"] = "mặt đứng: mặt trên bản đế = đầu dưới thanh cánh = đáy sườn (cao độ 0)"
    h_base = halfw(y0)
    rep["base_heel_minus_working_mm"] = round(HEEL - h_base, 1)
    for k in range(4):
        Rk = rot(k)
        n = Rk @ nf
        tu = Rk @ tup
        for poly, xf, label in rib_specs:
            pts3 = []
            for u, v in poly:
                xface = xf(u)
                # đáy sườn nằm trên mặt phẳng lưng cánh thanh cánh (δ = g) tại cao độ 0 (mặt trên bản đế)
                p0 = np.array([xface, -h_base, 0.0]) / 1000 + nf * gl / 1000
                p0 = p0 - tup * (p0[2] / tup[2])
                p = p0 + tup * v / 1000
                pts3.append(Rk @ p)
            o = pts3[0]
            a1 = Rk @ ex
            poly2 = [[round(float(np.dot(q - o, a1)), 5), round(float(np.dot(q - o, tu)), 5)] for q in pts3]
            area = abs(sum(poly2[i][0] * poly2[(i + 1) % len(poly2)][1] - poly2[(i + 1) % len(poly2)][0] * poly2[i][1]
                           for i in range(len(poly2)))) / 2
            plates.append({"kind": "gusset", "node": o.round(4).tolist(), "members": [], "t_mm": T_RIB,
                           "on_leg": True, "origin": o.round(5).tolist(), "a1": a1.round(6).tolist(),
                           "a2": tu.round(6).tolist(), "thick_dir": n.round(6).tolist(), "poly": poly2,
                           "area_m2": round(area, 5), "mass_kg": round(area * T_RIB / 1000 * 7850, 2),
                           "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0, "reason": "chân cột: " + label})
        # bu lông chân cột theo đúng lỗ chi tiết sườn (D322 = sườn 1, D323 = sườn 3): 10 lỗ thanh cánh (12.20_70:
        # kẹp sườn 12 + cánh 12) và 3 lỗ thanh xiên (3.20_60: kẹp sườn 12 + thanh xiên 7, áp mặt trong sườn)
        for holes, xf, ndiag in ((RIB1_H, lambda u: -3971.0 + u, 430), (RIB3_H, lambda u: HEEL - u, 230)):
            for u, v in holes:
                p0 = np.array([xf(u), -h_base, 0.0]) / 1000 + nf * gl / 1000
                p0 = p0 - tup * (p0[2] / tup[2]) + tup * v / 1000
                diag = u >= ndiag
                lo = gl - 7 if diag else gl - tl
                p_head = Rk @ (p0 + nf * (lo - gl) / 1000)
                bolts.append({"id": 0, "p": p_head.round(5).tolist(), "axis": n.round(6).tolist(),
                              "nut": n.round(6).tolist(), "d_mm": 20, "grip_mm": (gl + T_RIB) - lo,
                              "L_mm": 60 if diag else 70, "L_from": "ký hiệu bản vẽ " + ("3.20_60" if diag else "12.20_70"),
                              "t_mm": 12, "kind": "chân cột"})
        # bản đế 450x450x40: lưng thanh cánh tại (200, 200) tính từ góc ngoài; 4 lỗ neo Ø64 tại 100/350
        heel3 = np.array([-HEEL, -HEEL, 0.0]) / 1000
        ex_, ey_ = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
        corner = heel3 - 0.2 * ex_ - 0.2 * ey_
        plates.append({"kind": "gusset", "node": (Rk @ heel3).round(4).tolist(), "members": [], "t_mm": 40,
                       "on_leg": False, "origin": (Rk @ corner).round(5).tolist(), "a1": (Rk @ ex_).round(6).tolist(),
                       "a2": (Rk @ ey_).round(6).tolist(), "thick_dir": [0, 0, -1.0],
                       "poly": [[0, 0], [0.45, 0], [0.45, 0.45], [0, 0.45]], "area_m2": 0.2025,
                       "mass_kg": round(0.2025 * 0.04 * 7850, 2), "bolt_max": 4, "d_max_mm": 56, "leg_bolts": 0,
                       "reason": "bản đế 450x450x40 (chi tiết DT-02)"})
        for du in (0.1, 0.35):
            for dv in (0.1, 0.35):
                p = Rk @ (corner + du * ex_ + dv * ey_)
                bolts.append({"id": 0, "p": p.round(5).tolist(), "axis": [0, 0, 1.0], "nut": [0, 0, 1.0],
                              "d_mm": 56, "t_mm": 40, "kind": "neo"})
    rep["base"] = "4 bản đế 450x450x40, 12 sườn d12 (đúng hình chi tiết), 16 bu lông neo Ø56"

    # --- bỏ bu lông mặt cắt không nằm trên thanh nào (cách trục thanh > 100 mm)
    def seg_d(p, a_, b_):
        a_, b_, p = np.asarray(a_), np.asarray(b_), np.asarray(p)
        ab = b_ - a_
        t = np.clip(np.dot(p - a_, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
        return np.linalg.norm(p - (a_ + t * ab))
    axes = [(np.array(m["p1"]) + np.array(m.get("poff1", [0, 0, 0])), np.array(m["p2"]) + np.array(m.get("poff2", [0, 0, 0])))
            for m in members]
    keepb, lostb = [], 0
    for b_ in bolts:
        if b_["kind"] == "plan" and min(seg_d(b_["p"], a_, c_) for a_, c_ in axes) > 0.10:
            lostb += 1
            continue
        keepb.append(b_)
    bolts[:] = keepb
    rep["plan_bolts_floating_removed"] = lostb

    # --- Đầu thanh giằng vách tại đầu NGOÀI thanh ngang mặt cột (mặt cắt ghi "140 | 55"): tim bu lông cách
    #     đầu thanh ngang 55 mm. Nếu thanh giằng còn chạm thép thanh khác thì tăng 60, 65... (dời bu lông + đầu
    #     thanh giằng vào phía góc) tới khi hết chạm. Kiểm tra chạm bằng mô hình khối thép góc (2 cánh).
    byid = {m["id"]: m for m in members}

    def frame(m):
        if m["rule"] == "leg":
            e1, e2 = np.array(m["e1"]), np.array(m["e2"])
        else:
            e1, e2 = (np.array(v) for v in m["frames"]["bv"])
        P1 = np.array(m["p1"]) + np.array(m.get("poff1", [0, 0, 0]))
        P2 = np.array(m["p2"]) + np.array(m.get("poff2", [0, 0, 0]))
        return P1, P2, e1, e2

    def inside(m, pts, eps=0.0015):
        # đúng hình thanh như app dựng (khung lệch khi 2 đầu khác độ sâu, có tính phần vát)
        return list(CK.where_v(m, LIB, np.array(pts), eps) > 0)

    def end_samples(m, key, length=0.12):
        P1, P2, e1, e2 = frame(m)
        L = np.linalg.norm(P2 - P1)
        u = (P2 - P1) / L
        s_ = sec(m["section"])
        b_, t_ = s_["b"] / 1000, s_["t"] / 1000
        g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
        xs = np.linspace(0, min(length, L), 13) if key == "p1" else np.linspace(L - min(length, L), L, 13)
        pts = []
        for x in xs:
            base = P1 + u * x
            for a in np.linspace(0, b_, 7):
                for c in (0, t_):
                    pts.append(base + e1 * (a - g1) + e2 * (c - g2))           # cánh 1
                    pts.append(base + e1 * (c - g1) + e2 * (a - g2))           # cánh 2
        return pts

    rep["plan_brace_end_55"] = []
    for pm_ in [m for m in members if m["rule"] == "plan" and "contact" in m]:
        for key, c_ in pm_["contact"].items():
            fh = byid.get(c_["host_id"])
            if fh is None:
                continue
            A, B, _, _ = frame(fh)
            Pk = np.array(pm_[key])
            # đầu thanh ngang gần đầu thanh giằng hơn; bỏ qua nếu đó là đầu bắt vào thanh cánh (góc tam giác)
            E, F = (A, B) if np.linalg.norm(Pk[:2] - A[:2]) < np.linalg.norm(Pk[:2] - B[:2]) else (B, A)
            if np.linalg.norm(Pk[:2] - E[:2]) > 0.25:
                continue
            legs3 = [o for o in members if o["rule"] == "leg"]
            if any(np.linalg.norm(np.cross(np.array(o["p2"]) - np.array(o["p1"]), np.array(o["p1"]) - E))
                   / np.linalg.norm(np.array(o["p2"]) - np.array(o["p1"])) < 0.35 for o in legs3):
                continue                                   # đầu thanh ngang tại thanh cánh (góc): không áp quy tắc 55
            kE0 = "p1" if np.allclose(E, A) else "p2"
            if fh.get("plate_end", [False, False])[0 if kE0 == "p1" else 1]:
                continue                                   # thanh ngang dừng ở bản mã giữa: bu lông giữ theo bản vẽ
            uh = (E - F) / np.linalg.norm(E - F)                                 # hướng ra đầu thanh ngang
            # bu lông vách gần đầu thanh giằng
            bi = min(range(len(bolts)), key=lambda i: np.linalg.norm(np.array(bolts[i]["p"])[:2] - Pk[:2])
                     if bolts[i]["kind"] == "plan" else 9e9)
            Bp = np.array(bolts[bi]["p"])
            if np.linalg.norm(Bp[:2] - Pk[:2]) > 0.15:
                continue
            # các thanh khác gần đó để kiểm tra chạm (trừ chính thanh ngang chủ)
            near = [o for o in members if o is not pm_ and o is not fh and o["rule"] != "plan"
                    and min(np.linalg.norm(np.array(o["p1"]) - Pk), np.linalg.norm(np.array(o["p2"]) - Pk),
                            np.linalg.norm(np.cross(np.array(o["p2"]) - np.array(o["p1"]), np.array(o["p1"]) - Pk))
                            / max(np.linalg.norm(np.array(o["p2"]) - np.array(o["p1"])), 1e-9)) < 0.4]
            orig_end, orig_b = list(pm_[key]), list(bolts[bi]["p"])
            Dused, clash_names = None, []
            # điểm mẫu thép các thanh lân cận quanh đầu thanh giằng (kiểm tra 2 chiều: thép thanh giằng lọt vào
            # thanh khác, và thép thanh khác lọt vào thanh giằng)
            near_pts = {}
            for o in near:
                sp_ = CK.samples(o, LIB)
                near_pts[id(o)] = sp_[np.linalg.norm(sp_ - Pk, axis=1) < 0.35] if len(sp_) else sp_
            for D in range(55, 125, 5):
                target = E - uh * D / 1000
                cur = np.array(orig_b)
                dlt = uh * np.dot(target - cur, uh)                              # chỉ dời dọc thanh ngang
                pm_[key] = (np.array(orig_end) + dlt).round(5).tolist()
                sp_b = CK.samples(pm_, LIB)
                sp_b = sp_b[np.linalg.norm(sp_b - np.array(pm_[key]), axis=1) < 0.2]
                hit = [o for o in near if any(inside(o, sp_b, 0.001))
                       or (len(near_pts[id(o)]) and any(inside(pm_, near_pts[id(o)], 0.001)))]
                if not hit:
                    Dused = D
                    bolts[bi]["p"] = (cur + dlt).round(5).tolist()
                    break
                clash_names = [o["section"] for o in hit]
            if Dused is None:
                pm_[key] = orig_end
                Dused = "không gỡ được"
            pm_["length"] = round(float(np.linalg.norm(np.array(pm_["p2"]) - np.array(pm_["p1"]))), 4)
            pm_.setdefault("end_dist_55", {})[key] = {"mm": Dused, "clash_at_55": clash_names if Dused != 55 else []}
            # góc cánh nằm ngang của thanh ngang (đầu ngoài) còn chạm thanh khác -> vát góc (a = b, bội 5 mm)
            if fh.get("_cut_checked_" + str(id(E))) is None:
                kE = "p1" if np.allclose(E, A) else "p2"
                ck = "cut1" if kE == "p1" else "cut2"
                Pf1, Pf2, fe1, fe2 = frame(fh)
                Lf = np.linalg.norm(Pf2 - Pf1)
                uf = (Pf2 - Pf1) / Lf
                sf = sec(fh["section"])
                bf, tf = sf["b"] / 1000, sf["t"] / 1000
                gf1, gf2 = fh["g"][0] / 1000, fh["g"][1] / 1000
                nearh = [o for o in members if o is not fh and o["rule"] == "face" and o["type"] != "G"
                         and np.linalg.norm(np.cross(np.array(o["p2"]) - np.array(o["p1"]), np.array(o["p1"]) - E))
                         / np.linalg.norm(np.array(o["p2"]) - np.array(o["p1"])) < 0.3]
                def out_flange_pts(cut):
                    pts = []
                    for xx in np.linspace(0, 0.12, 13):
                        x = xx if kE == "p1" else Lf - xx
                        for a in np.linspace(tf, bf, 7):
                            if cut and (xx < cut / 1000 and a > bf - (cut / 1000 - xx)):
                                continue                       # phần đã vát
                            base = Pf1 + uf * x
                            for c in (0, tf):
                                pts.append(base + fe1 * (c - gf1) + fe2 * (a - gf2))
                    return pts
                if any(any(inside(o, out_flange_pts(0))) for o in nearh):
                    for cut in range(20, 85, 5):
                        if not any(any(inside(o, out_flange_pts(cut))) for o in nearh):
                            fh[ck] = {"flange": "out", "a": cut, "b": cut,
                                      "note": f"vát góc thừa {cut}x{cut}mm (đầu ngoài thanh ngang, tránh chạm)"}
                            break
            rep["plan_brace_end_55"].append({"plan": pm_["plan"], "section": pm_["section"], "D_mm": Dused,
                                             "cham_khi_55": clash_names if Dused != 55 else []})
    # --- gỡ chạm còn lại (theo hình học thép đã dựng):
    #  (a) đầu thanh vách lấn vào cánh thanh cánh: lùi đầu thanh từng 5 mm (bản vẽ vẽ đầu thanh chạm sát mặt trong
    #      cánh thanh cánh, sai số đặt hình vài mm)
    #  (b) 2 thanh mặt kề nhau cùng bắt vào thanh cánh tại một cao độ: cánh còn lại (chĩa vào trong) của 2 thanh
    #      đâm nhau ở góc cột -> vát góc mép cánh còn lại ở đầu thanh (a = b, bội 5 mm) - ĐỀ XUẤT, bản vẽ không ghi
    legs3 = [o for o in members if o["rule"] == "leg"]
    rep["clash_fix"] = []

    def touching(a_, b_):
        sp = CK.samples(a_, LIB)
        if len(sp) and np.any(CK.where_v(b_, LIB, sp, 0.001) > 0):
            return True
        sp = CK.samples(b_, LIB)
        return bool(len(sp) and np.any(CK.where_v(a_, LIB, sp, 0.001) > 0))
    for pm_ in [m for m in members if m["rule"] == "plan"]:
        for key in ("p1", "p2"):
            P_ = np.array(pm_[key])
            lg = [o for o in legs3 if CK.seg_dist(P_, P_ + 1e-6, *CK.frame(o)[:2]) < 0.25]
            pls = [pp for pp in (CK.plate_points(pl) for pl in plates
                                 if np.linalg.norm(np.array(pl["node"]) - P_) < 0.6) if len(pp)]
            if not lg and not pls:
                continue

            def blocked():
                return any(touching(pm_, o) for o in lg) or \
                    any(np.any(CK.where_v(pm_, LIB, pp, 0.001) > 0) for pp in pls)
            if not blocked():
                continue
            # góc đầu thanh lấn sang thép khác -> vát góc đó (giữ nguyên đầu thanh và bu lông theo bản vẽ);
            # thử vát góc mép rồi góc lưng, bội 5 mm, lấy nhỏ nhất
            ck = "cut1" if key == "p1" else "cut2"
            done = None
            for cmm in range(10, 50, 5):
                for fl_ in ("conn", "heel"):
                    pm_[ck] = {"flange": fl_, "a": cmm, "b": cmm}
                    if not blocked():
                        done = (fl_, cmm)
                        break
                if done:
                    break
            if done:
                pm_[ck]["note"] = "vát góc %s %dx%dmm (góc đầu thanh lấn vào %s)" % (
                    "mép" if done[0] == "conn" else "lưng", done[1], done[1], "thanh cánh" if lg else "bản mã")
                rep["clash_fix"].append({"loai": "vát góc đầu thanh vách (góc lấn vào thanh cánh / bản mã)",
                                         "plan": pm_["plan"], "section": pm_["section"],
                                         "mm": f"{done[1]}x{done[1]} góc {'mép' if done[0] == 'conn' else 'lưng'}"})
            else:
                pm_.pop(ck, None)
                rep["warnings"].append(f"{pm_['plan']} {pm_['section']}: đầu thanh còn chạm, chưa gỡ được")
    # --- bu lông vách: xếp lại theo các lớp thép THỰC (sau khi đặt chồng thanh/vát): quét dọc trục bu lông,
    #     lấy mọi thép có lỗ tại đó; đầu bu lông ở mặt trên lớp trên cùng, kẹp tới mặt dưới lớp dưới cùng
    # --- BẺ CÁNH CỤC BỘ (người dùng chốt, theo ảnh cột mẫu): cánh nằm ngang của thanh ngang mặt cột vuông góc mặt
    #     cột nên nghiêng theo độ xiên mặt cột; tại chỗ thanh giằng vách bắt vào, cánh được bẻ cục bộ quanh mép lưng
    #     thành mặt phẳng song song mặt đất -> thanh giằng tựa phẳng, hết hở. Vùng phẳng = vết thanh giằng trên cánh
    #     + 10 mm mỗi bên, đoạn chuyển tiếp 40 mm.
    rep["flange_bends"] = []
    RAMP = 40.0
    for pm_ in [m for m in members if m["rule"] == "plan" and "contact" in m]:
        for key, c_ in pm_["contact"].items():
            fh = byid.get(c_["host_id"])
            if fh is None:
                continue
            P1, P2, e1, e2 = CK.frame(fh)
            L = np.linalg.norm(P2 - P1)
            u_ = (P2 - P1) / L
            # bu lông vách của đầu thanh giằng này
            Pk = np.array(pm_[key])
            bb = [b_ for b_ in bolts if b_["kind"] == "plan" and np.linalg.norm(np.array(b_["p"])[:2] - Pk[:2]) < 0.2]
            cen = np.array(min(bb, key=lambda b_: np.linalg.norm(np.array(b_["p"])[:2] - Pk[:2]))["p"]) if bb else Pk
            xb = float(np.linalg.solve(np.c_[P2 - P1, e1, e2], cen - P1)[0] * L * 1000)
            ub = unit(np.array(pm_["p2"]) - np.array(pm_["p1"]))
            sphi = max(abs(float(np.linalg.norm(np.cross(ub, u_)))), 0.2)
            cphi = abs(float(np.dot(ub, u_)))
            half = 0.5 * (sec(pm_["section"])["b"] / sphi + sec(fh["section"])["b"] * cphi / sphi) + 10
            # góc xoay quanh trục thanh để cánh còn lại (theo e2) nằm ngang
            w_ = np.cross(u_, e2)
            th = math.atan2(-e2[2], w_[2])
            if abs(th) > math.pi / 2:
                th -= math.copysign(math.pi, th)
            x0, x1 = max(0.0, xb - half), min(L * 1000, xb + half)
            fh.setdefault("bends", []).append({"x0": round(x0, 1), "x1": round(x1, 1), "ramp": RAMP,
                                               "theta_deg": round(math.degrees(th), 3), "plan": pm_["plan"]})
            rep["flange_bends"].append({"plan": pm_["plan"], "host": fh["section"], "brace": pm_["section"],
                                        "len_mm": round(x1 - x0), "deg": round(math.degrees(th), 2)})

    rep["plan_bolt_layers"] = []
    zs_ = np.arange(-0.12, 0.12, 0.0005)
    for b_ in bolts:
        if b_["kind"] != "plan":
            continue
        p0 = np.array(b_["p"])
        Q = np.c_[np.full(len(zs_), p0[0]), np.full(len(zs_), p0[1]), p0[2] + zs_]
        inside_any = np.zeros(len(zs_), bool)
        names = []
        for o in members:
            if o["rule"] == "leg":
                continue
            if CK.seg_dist(p0, p0 + 1e-6, *CK.frame(o)[:2]) > 0.2:
                continue
            w = CK.where_v(o, LIB, Q, 0.0002) > 0
            if w.any():
                inside_any |= w
                names.append(o["section"] + " " + o.get("side", ""))
        if not inside_any.any():
            rep["warnings"].append(f"bu lông vách tại {np.round(p0, 3).tolist()}: không xuyên thép")
            b_["_drop"] = True
            continue
        # các đoạn thép liên tục dọc trục; giữ chuỗi đoạn quanh cao độ vách (hở giữa các đoạn <= 8 mm)
        idx = np.where(inside_any)[0]
        runs = []
        for i_ in idx:
            if runs and i_ == runs[-1][1] + 1:
                runs[-1][1] = i_
            else:
                runs.append([i_, i_])
        i0 = int(np.argmin(np.abs(zs_)))
        cur = min(runs, key=lambda r: 0 if r[0] <= i0 <= r[1] else min(abs(r[0] - i0), abs(r[1] - i0)))
        grp = [cur]
        for r in sorted(runs):
            if r is cur:
                continue
            if r[0] > grp[-1][1] and (r[0] - max(g[1] for g in grp)) * 0.5 <= 8:
                grp.append(r)
        for r in sorted(runs, reverse=True):
            if r[1] < min(g[0] for g in grp) and (min(g[0] for g in grp) - r[1]) * 0.5 <= 8:
                grp.append(r)
        lo_i, hi_i = min(g[0] for g in grp), max(g[1] for g in grp)
        names = [o["section"] + " " + o.get("side", "") for o in members if o["rule"] != "leg"
                 and CK.seg_dist(p0, p0 + 1e-6, *CK.frame(o)[:2]) <= 0.2
                 and np.any(CK.where_v(o, LIB, Q[lo_i:hi_i + 1], 0.0002) > 0)]
        top, bot = p0[2] + zs_[hi_i] + 0.00025, p0[2] + zs_[lo_i] - 0.00025
        gap = float(sum((b2_[0] - b1_[1] - 1) * 0.5 for b1_, b2_ in zip(sorted(grp), sorted(grp)[1:])))
        b_["p"] = [round(float(p0[0]), 5), round(float(p0[1]), 5), round(float(top), 5)]
        b_["grip_mm"] = round((top - bot) * 1000, 1)
        b_["layers"] = names
        rep["plan_bolt_layers"].append({"xy": np.round(p0[:2], 3).tolist(), "layers": names,
                                        "grip_mm": b_["grip_mm"], "gap_mm": gap})
        if len(names) < 2:
            # lỗ chỉ xuyên 1 thanh (bản vẽ vẽ lỗ đối xứng; ký hiệu bu lông ghi 1 con): không có bu lông
            b_["_drop"] = True
            rep.setdefault("plan_holes_no_bolt", []).append({"xy": np.round(p0[:2], 3).tolist(), "layers": names})
    bolts[:] = [b_ for b_ in bolts if not b_.pop("_drop", False)]

    # --- đầu dưới thanh xiên chính tại sườn chân cột: lỗ lấy theo chi tiết sườn -> đầu thanh phải cách lỗ thấp
    #     nhất >= 30 mm (M20, ghi chú chung); kéo dài đầu thanh nếu thiếu
    rep["base_end_extended"] = []
    for m in [o for o in members if o["rule"] == "face"]:
        for key, pk in (("p1", "poff1"), ("p2", "poff2")):
            if m[key][2] > 0.6:
                continue
            P1, P2, e1, e2 = CK.frame(m)
            L = np.linalg.norm(P2 - P1)
            u_ = (P2 - P1) / L
            xs = []
            for b_ in bolts:
                if b_["kind"] != "chân cột" or "3.20_60" not in b_.get("L_from", ""):
                    continue                           # chỉ 3 lỗ thanh xiên trên sườn (3.20_60)
                q = np.array(b_["p"]) + np.array(b_["nut"]) * (b_.get("grip_mm", 20) / 2000)
                sol = np.linalg.solve(np.c_[P2 - P1, e1, e2], q - P1)
                a_ = sol[1] * 1000 + m["g"][0]
                if 15 < a_ < sec(m["section"])["b"] - 15 and abs(sol[2]) < 0.03:
                    xs.append(sol[0] * L * 1000 if key == "p1" else (1 - sol[0]) * L * 1000)
            if not xs:
                continue
            need = ED[20] - min(xs)
            if need > 0.5:
                sign = -1 if key == "p1" else 1
                m[key] = (np.array(m[key]) + sign * u_ * need / 1000).round(5).tolist()
                m["length"] = round(float(np.linalg.norm(np.array(m["p2"]) - np.array(m["p1"]))), 4)
                rep["base_end_extended"].append({"section": m["section"], "mm": round(need, 1)})

    face_m = [m for m in members if m["rule"] == "face"]
    for i, a_ in enumerate(face_m):
        for b_ in face_m[i + 1:]:
            if a_["face_k"] == b_["face_k"] or (a_["face_k"] - b_["face_k"]) % 2 == 0:
                continue
            if CK.seg_dist(*CK.frame(a_)[:2], *CK.frame(b_)[:2]) > 0.15 or not touching(a_, b_):
                continue
            # đầu thanh gần góc cột của mỗi thanh
            keys = []
            for m_ in (a_, b_):
                lgd = [min(np.linalg.norm(np.cross(np.array(o["p2"]) - np.array(o["p1"]), np.array(o["p1"]) - np.array(m_[k_])))
                           / np.linalg.norm(np.array(o["p2"]) - np.array(o["p1"])) for o in legs3) for k_ in ("p1", "p2")]
                keys.append("cut1" if lgd[0] < lgd[1] else "cut2")
            if a_.get(keys[0]) or b_.get(keys[1]):
                continue
            # vát cả 2 thanh như nhau, chọn (ngang cánh a, dọc thanh b) bội 5 mm có diện tích cắt nhỏ nhất
            best = None
            for A_ in range(15, 70, 5):
                for B_ in range(15, 130, 5):
                    if best and A_ * B_ >= best[0]:
                        break
                    for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                        m_[k_] = {"flange": "out", "a": A_, "b": B_}
                    if not touching(a_, b_):
                        best = (A_ * B_, A_, B_)
                        break
            for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                m_.pop(k_, None)
                if best:
                    m_[k_] = {"flange": "out", "a": best[1], "b": best[2],
                              "note": f"vát góc mép cánh còn lại {best[1]}x{best[2]}mm (ĐỀ XUẤT - bản vẽ không ghi; "
                                      "tránh chạm thanh mặt kề tại góc cột)"}
            rep["clash_fix"].append({"loai": "vát góc mép cánh còn lại đầu thanh tại góc cột (đề xuất)",
                                     "section": a_["section"] + "/" + b_["section"],
                                     "mm": f"{best[1]}x{best[2]}" if best else "không gỡ được"})

    for m in members:
        m["mass_kg"] = round(m["A_cm2"] * 1e-4 * m["length"] * 7850, 3)
    zs = [c for m in members for c in (m["p1"][2], m["p2"][2])]
    rep["z_range_m"] = [round(min(zs), 3), round(max(zs), 3)]
    rep["leg"] = {"section": Lg["section"], "g_mm": Lg["g"], "n_brace_ends_on_leg": Lg["n_wp"]}
    scene = {"title": "Đoạn thân DT-02 cột N122 (dựng từ BVTC)", "members": members, "sections": LIB,
             "nodes": [], "plates": plates, "bolts": bolts,
             "report": {"total_mass_kg": round(sum(m["mass_kg"] for m in members), 1),
                        "orientation": {"x_members": {"outside": [], "inside": []}, "clash_other": [],
                                        "clash_coplanar_overlap": [], "overridden": []}, "build": rep}}
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dt02_scene.json").write_text(json.dumps(scene, ensure_ascii=False))
    # dữ liệu kiểm tra chồng hình (mặt trước, hệ x-z mm)
    chk = {"cad": [[[(sg["a"][0] - xc) * SC, zf(sg["a"][1])], [(sg["b"][0] - xc) * SC, zf(sg["b"][1])], sg["k"]]
                   for sg in segs],
           "plates": [[[(q[0] - xc) * SC, zf(q[1])] for q in pl["pts"]] for pl in plates2d],
           "bolts": [[(b["p"][0] - xc) * SC, zf(b["p"][1])] for b in bolts2d], "plans": plan_chk,
           "dropped_bolts": [[(q[0] - xc) * SC, zf(q[1])] for q in rep.pop("bolts_dropped_pts", [])],
           "no_host": [{"section": m["section"], "p1": [(m["c1"][0] - xc) * SC, zf(m["c1"][1])],
                        "p2": [(m["c2"][0] - xc) * SC, zf(m["c2"][1])], "side": "NGOAI" if m["out"] else "TRONG"}
                       for m in rep.pop("no_host", [])]}
    (out / "dt02_check.json").write_text(json.dumps(chk))
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:3000])
    return scene


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
