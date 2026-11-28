"""Dựng xà X2 (tờ 2/6 "Xà X1 và Xà X2") và ghép vào cột N122.

Chạy: python3 tools/bvtc/xa.py <dxf> <scene cột vào> <scene ra>

Người dùng chốt (docs/THAM_KHAO_BVTC_N122.md, mục Xà):
- X2 giống nhau ở 3 cao độ có thanh L90x7 2840 của thân; tay phải đối xứng tay trái; mặt sau đối xứng mặt trước.
- Bề rộng xà theo mép cánh 2050: lưng các thanh mặt xà ở +-1025 (trùng lưng thanh cánh cột).
- Biên dưới X201 ốp chồng thanh 2840: bản mã có tai 123 nằm giữa (2840 NGOÀI, X201 TRONG áp mặt trong bản mã),
  4 bu lông 80/80/80/40 xuyên 3 lớp.
- Bản mã nằm ngang ở mặt bằng 3-3 (X213, X214, X215) nằm DƯỚI cánh nằm biên dưới; thanh nét liền chĩa lên nằm trên
  cánh nằm biên dưới, nét khuất chĩa xuống nằm dưới bản mã. 2 bản d6 không số hiệu (chỗ X201 gặp 2840) = X215.
Hệ toạ độ tay xà (trước khi đối xứng): tay TRÁI (x < 0), mặt TRƯỚC (y < 0); d = độ lệch ra ngoài so với mặt lưng
thanh cánh cột (y = -1,025 m), mm.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dt02_base as T  # noqa: E402
import check_dt02 as CK  # noqa: E402
import fixes as F  # noqa: E402

SC = 25.0
ED = {16: 25.0, 20: 30.0, 24: 40.0}
BACK = 1.025                                   # m: lưng thanh cánh cột = mép cánh ngoài xà (2050 / 2)
X2 = {
    "elev": (-2360, -119470, -2212, -119385),  # mặt đứng tay trái X2 (chỉ phần ngoài thanh cánh)
    "x_back": -2217.96,                        # x lưng thanh cánh trên tờ xà (đường đinh L100x7 -2215.96 - 50 mm)
    "y_ch": -119457.05,                        # y đường đinh biên dưới X201 (= thanh 2840)
    "plan": (-2350, -119630, -2214, -119505),  # mặt bằng 3-3 (phần tay xà)
    "plan_y_front": -119598.71, "plan_y_back": -119520.71,
    "p44": (-2350, -119785, -2210, -119670),
    "p66": (-2180, -119785, -2050, -119710),
    "details": {"X213": (-2030, -119571), "X214": (-1952, -119569), "X215": (-1959, -119666), "X216": (-2032, -119658)},
}


def U(x, cfg):
    return (x - cfg["x_back"]) * SC / 1000 - BACK        # x bản vẽ -> X mô hình (tay trái)


def unitv(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def gauge(m):
    """Đường đinh: theo nét vẽ nếu bề rộng vẽ khớp nhãn tiết diện, không thì b/2 (ghi chú chung)."""
    b = T.sec(m["section"])["b"]
    return m["heel_to_center"] if m.get("heel_to_center") and abs(m["width"] - b) < 6 else b / 2


def member(p1, p2, sec, e1, e2, g, side, view, extra=None):
    s = T.sec(sec)
    L = float(np.linalg.norm(np.array(p2) - np.array(p1)))
    m = {"p1": np.round(p1, 5).tolist(), "p2": np.round(p2, 5).tolist(), "length": round(L, 4), "section": sec,
         "A_cm2": s["A_geom_cm2"], "type": "X", "rule": "xa", "variant": "bv", "auto_variant": "bv",
         "frames": {"bv": [np.round(e1, 6).tolist(), np.round(e2, 6).tolist()]}, "offs": {"bv": [0, 0, 0]},
         "g": [float(g), 0.0], "group": 4, "bolts": {}, "bolt": None, "node1": None, "node2": None, "face_k": -1,
         "side": side, "xa_view": view, "mass_kg": round(s["A_geom_cm2"] * 1e-4 * L * 7850, 3)}
    if extra:
        m.update(extra)
    return m


def read_view(doc, msp, box):
    ms = T.R.members(doc, msp, box)
    T.R.assign_labels(ms, T.R.text_labels(msp, box))
    ins = lambda p: box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
    bolts = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name]) for e in msp.query("INSERT")
             if e.dxf.name in ("1", "2", "3") and ins(e.dxf.insert)]
    labs = []
    for t in msp.query("TEXT"):
        mt = re.fullmatch(r"(\d+)\.(\d+)_(\d+)", t.dxf.text.strip())
        if mt and ins(t.dxf.insert):
            labs.append((int(mt.group(2)), int(mt.group(3)), (t.dxf.insert[0], t.dxf.insert[1])))
    fl = []
    for t in msp.query("TEXT"):
        mt = re.fullmatch(r"(\d*)D\.(\d+)_(\d+)", t.dxf.text.strip())
        if mt and ins(t.dxf.insert):
            fl.append((int(mt.group(1) or 1), float(mt.group(3)), (t.dxf.insert[0], t.dxf.insert[1])))
    return ms, bolts, labs, fl


def ends_by_bolts(m, bolts):
    """Đầu thanh: đầu vẽ (b1, b2), kéo tới bu lông ngoài cùng trên đường đinh + 25/30/40 nếu bu lông nằm ngoài."""
    c1, c2 = np.array(m["c1"]), np.array(m["c2"])
    u = (c2 - c1) / np.linalg.norm(c2 - c1)
    n = np.array([-u[1], u[0]])
    s1, s2 = sorted((float(np.dot(np.array(m["b1"]) - c1, u)), float(np.dot(np.array(m["b2"]) - c1, u))))
    s1_, s2_ = s1 - 100 / SC, s2 + 100 / SC       # bu lông của bản mã thẳng hàng xa hơn: không thuộc thanh
    on = [(float(np.dot(np.array(q) - c1, u)), d) for q, d in bolts if abs(np.dot(np.array(q) - c1, n)) * SC < 8
          and s1_ < np.dot(np.array(q) - c1, u) < s2_]
    if on:
        lo, dl = min(on)
        hi, dh = max(on)
        s1 = min(s1, lo - ED[dl] / SC)
        s2 = max(s2, hi + ED[dh] / SC)
    return c1 + u * s1, c1 + u * s2, [q for q in on]


def fit_by_holes(D, H, B, c0, f=10.0 / SC, tol=12.0):
    """Đặt hình chi tiết (D, lỗ H; đơn vị chi tiết 1/10) lên hình chiếu theo LỖ: thử 8 hướng (xoay 90 độ, lật) và mọi
    cặp lỗ - bu lông; chọn phép đặt trùng nhiều bu lông nhất (sai số <= tol mm), rồi gần tâm đường bao nhất."""
    if not H or not B:
        return None
    Hc = np.array(H, float) * f
    Hc = Hc - Hc.mean(0)
    Dc0 = np.array(H, float).mean(0)
    Bv = np.array(B, float)
    best = None
    for k in range(4):
        R = np.array([[math.cos(k * math.pi / 2), -math.sin(k * math.pi / 2)],
                      [math.sin(k * math.pi / 2), math.cos(k * math.pi / 2)]])
        for mir in (1, -1):
            Q = (Hc * np.array([mir, 1.0])) @ R.T
            for i in range(len(Q)):
                for b in Bv:
                    t = b - Q[i]
                    d = np.min(np.linalg.norm(Bv[None, :, :] - (Q + t)[:, None, :], axis=2), axis=1) * SC
                    n = int(np.sum(d < tol))
                    sc = (n, -float(np.mean(np.sort(d)[:n])) if n else 0, -math.dist(tuple(Q.mean(0) + t), c0))
                    if best is None or sc > best[0]:
                        best = (sc, R, mir, t)
    if best[0][0] < min(2, len(H)):
        return None
    _, R, mir, t = best

    def Tf(q):
        v = ((np.array(q, float) - Dc0) * f * np.array([mir, 1.0])) @ R.T + t
        return (float(v[0]), float(v[1]))
    return Tf


def build_x2(doc, msp, cfg):
    """Tay trái X2 (cả mặt trước + sau + mặt bằng) ở cao độ biên dưới z = 0. Trả members, plates2d, bolts2d."""
    rep = {"canh_bao": []}
    E3 = lambda x, y: np.array([U(x, cfg), 0.0, (y - cfg["y_ch"]) * SC / 1000])          # mặt đứng -> (X, -, Z)
    yc = (cfg["plan_y_front"] + cfg["plan_y_back"]) / 2
    P3 = lambda x, y: np.array([U(x, cfg), (y - yc) * SC / 1000, 0.0])                      # mặt bằng -> (X, Y, -)
    out = []
    # ---------- mặt đứng (mặt trước): biên dưới X201, biên trên X203, đứng X206, chéo X205
    ms, eb, elab, efl = read_view(doc, msp, cfg["elev"])
    arm_eb = [(q, d) for q, d in eb if U(q[0], cfg) < -BACK - 0.02]
    el = {}
    for m in ms:
        a = m["ang"] % 180
        key = "X201" if a < 1 and m["section"] == "L90X7" else "X203" if 20 < a < 35 else \
            "X206" if abs(a - 90) < 1 else "X205" if 140 < a < 160 else None
        if key:
            el[key] = m
    rep["mat_dung"] = {k: v["section"] for k, v in el.items()}
    t_of = lambda k: T.sec(el[k]["section"])["t"]
    # độ sâu lưng (mm ra ngoài so với mặt lưng cột) mỗi đầu: TRONG áp mặt trong thép chủ/bản mã, NGOÀI áp mặt ngoài
    dep = {"X201": (0.0, 0.0), "X203": (0.0, 0.0), "X206": (-t_of("X201"), -t_of("X203")), "X205": (8.0, 0.0)}
    for k, m in el.items():
        b1, b2, _ = ends_by_bolts(m, arm_eb)
        p1, p2 = E3(*b1), E3(*b2)
        if k == "X205" and p1[2] < p2[2]:
            pass
        d1, d2 = dep[k]
        if k in ("X206",) and p1[2] > p2[2]:
            d1, d2 = d2, d1
        if k == "X205":                       # đầu thấp ở bản mã 123 (d8), đầu cao áp mặt ngoài X203
            d1, d2 = (8.0, 0.0) if p1[2] < p2[2] else (0.0, 8.0)
        out_ = m["vis"] == "S"                # nét liền = NGOÀI (cánh còn lại chĩa ra)
        p1[1] = -(BACK + d1 / 1000)
        p2[1] = -(BACK + d2 / 1000)
        hd = np.array(m["heel_dir"])
        e1 = unitv([-hd[0], 0.0, -hd[1]])
        e2 = np.array([0, -1.0, 0]) if out_ else np.array([0, 1.0, 0])
        if out_:
            # NGOÀI: lưng (mặt áp) ở phía trong -> điểm thanh trên mặt áp phía trong, cánh còn lại chĩa ra
            pass
        g_ = m["heel_to_center"] if abs(m["width"] - T.sec(m["section"])["b"]) < 6 else T.sec(m["section"])["b"] / 2
        out.append(member(p1, p2, m["section"], e1, e2, g_, ("NGOAI" if out_ else "TRONG"),
                          "mat_dung", {"mark": k}))
    # ---------- bản mã (mặt đứng: X216 đầu xà; mặt bằng 3-3: X213, X214, X215 nằm DƯỚI cánh nằm biên dưới)
    t201 = T.sec(el["X201"]["section"])["t"] / 1000
    g201 = el["X201"]["heel_to_center"] / 1000
    z_fb = -g201                               # mặt dưới cánh nằm biên dưới (lưng ở dưới)
    z_ft = -g201 + t201                        # mặt trên cánh nằm
    plates = []
    banma = T.banma_loops(msp)
    allb = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name]) for e in msp.query("INSERT")
            if e.dxf.name in ("1", "2", "3")]
    nums = [(t.dxf.text.strip(), (t.dxf.insert[0], t.dxf.insert[1])) for t in msp.query("TEXT")
            if re.fullmatch(r"X\d{3}a?", t.dxf.text.strip())]
    thk = [(int(t.dxf.text.split()[-1]), (t.dxf.insert[0], t.dxf.insert[1])) for t in msp.query("TEXT")
           if re.fullmatch(r"d\s*\d+", t.dxf.text.strip())]
    cen = lambda P: (sum(q[0] for q in P) / len(P), sum(q[1] for q in P) / len(P))

    def detail(mark):
        c = cfg["details"][mark]
        P = min(banma, key=lambda P: math.dist(cen(P), c))
        return P, [q for q, _ in allb if T.point_in_poly(q, P)]

    def place_plate(P, view_box, bolts_v, to3, origin_fn, a1, a2, td, mark_default=None):
        c = cen(P)
        lab = min(((tx, q) for tx, q in nums if view_box[0] <= q[0] <= view_box[2] and view_box[1] <= q[1] <= view_box[3]),
                  key=lambda z: math.dist(z[1], c))
        mark = lab[0] if math.dist(lab[1], c) < 35 else mark_default
        t_mm = min(thk, key=lambda z: math.dist(z[1], c))[0]
        here = [q for q, _ in bolts_v if T.point_in_poly(q, P) or T.dist_to_poly(q, np.array(P)) * SC < 8]
        D, H = detail(mark)
        Tf = fit_by_holes(D, H, [q for q, _ in bolts_v if math.dist(q, c) * SC < 350], c)
        if Tf is None:
            Tf = T.fit_detail(D, P, 10.0 / SC, H, here)[1]
        here = [q for q, _ in bolts_v if any(math.dist(Tf(h), q) * SC < 15 for h in H)]
        # khớp cứng theo lỗ (như thân): lỗ chi tiết trùng bu lông vẽ
        if here and H:
            A_ = np.array([Tf(q) for q in H])
            B_ = np.array(here)
            idx = [int(np.argmin(np.linalg.norm(B_ - a, axis=1))) for a in A_]
            ok = [i for i, j in enumerate(idx) if np.linalg.norm(B_[j] - A_[i]) * SC < 40]
            if len(ok) >= 2:
                Aa, Bb = A_[ok], B_[[idx[i] for i in ok]]
                ca, cb = Aa.mean(0), Bb.mean(0)
                Hm = (Aa - ca).T @ (Bb - cb)
                th = math.atan2(Hm[0, 1] - Hm[1, 0], Hm[0, 0] + Hm[1, 1])
                Rr = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
                Tf = (lambda T0, Rr, ca, cb: (lambda q: tuple(Rr @ (np.array(T0(q)) - ca) + cb)))(Tf, Rr, ca, cb)
        pts = [to3(*Tf(q)) for q in D]
        hole_err = max([min(math.dist(Tf(h), b) for b in here) * SC for h in H] or [0]) if here else None
        o = origin_fn(pts[0])
        poly = [[round(float(np.dot(q - pts[0], a1)), 5), round(float(np.dot(q - pts[0], a2)), 5)] for q in pts]
        area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                       for i in range(len(poly)))) / 2
        plates.append({"kind": "gusset", "node": np.round(o, 4).tolist(), "members": [], "t_mm": t_mm, "on_leg": False,
                       "origin": np.round(o, 5).tolist(), "a1": list(a1), "a2": list(a2), "thick_dir": list(td),
                       "poly": poly, "area_m2": round(area, 5), "mass_kg": round(area * t_mm / 1000 * 7850, 2),
                       "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0, "mark": mark,
                       "reason": "bản mã xà %s d%d theo hình chi tiết (lỗ lệch bu lông vẽ max %s mm)" % (
                           mark, t_mm, None if hole_err is None else round(hole_err, 1))})
        return mark, t_mm, P

    ev = cfg["elev"]
    for P in banma:
        if all(ev[0] <= q[0] <= ev[2] and ev[1] <= q[1] <= ev[3] for q in P) and U(cen(P)[0], cfg) < -BACK - 0.3:
            # bản mã đầu xà (mặt đứng): mặt trong áp lưng biên dưới / biên trên (d = 0), dày ra ngoài
            place_plate(P, ev, eb, lambda x, y: E3(x, y) + np.array([0, -BACK, 0]),
                        lambda p0: p0, [1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0])
    pv = cfg["plan"]
    plan_pl = []
    for P in banma:
        if all(pv[0] <= q[0] <= pv[2] and pv[1] <= q[1] <= pv[3] for q in P) and U(cen(P)[0], cfg) < -BACK + 0.01:
            mk, t_, P2 = place_plate(P, pv, read_view(doc, msp, pv)[1], lambda x, y: P3(x, y) + np.array([0, 0, z_fb]),
                                     lambda p0: p0, [1.0, 0, 0], [0, 1.0, 0], [0, 0, -1.0], "X215")
            plan_pl.append((P2, t_))
    rep["ban_ma"] = [(p["mark"], p["t_mm"], p["reason"].split("(")[-1].rstrip(")")) for p in plates]

    # ---------- mặt bằng 3-3: thanh ngang đầu xà L75x6, giữa L65x5, 4 thanh chéo L60x5 (nằm ngang)
    pms, pb, plab, pfl = read_view(doc, msp, cfg["plan"])
    arm_pb = [(q, d) for q, d in pb if U(q[0], cfg) < -BACK + 0.01]
    plan_m = [m for m in pms if m["section"] and not (m["section"] == "L90X7") and
              U(min(m["c1"][0], m["c2"][0]), cfg) < -BACK - 0.05]
    def pt_plate(q):
        """Chiều dày bản mã nằm ngang (đã khớp chi tiết) ngay trên điểm q của mặt bằng (0 nếu không có)."""
        Q = P3(*q) + np.array([0, 0, z_fb - 0.001])
        return max([p["t_mm"] for p in plates if p["thick_dir"][2] < -0.5 and plate_inside(p, Q[None, :])[0]] or [0])
    for m in plan_m:
        b1, b2, _ = ends_by_bolts(m, arm_pb)
        up = m["vis"] == "S"
        hd = np.array(m["heel_dir"])
        e1 = unitv([-hd[0], -hd[1], 0.0])
        e2 = np.array([0, 0, 1.0 if up else -1.0])
        p1, p2 = P3(*b1), P3(*b2)
        if up:
            p1[2] = p2[2] = z_ft                       # LÊN: trên cánh nằm biên dưới
        else:
            p1[2] = z_fb - pt_plate(tuple(b1)) / 1000  # XUỐNG: dưới bản mã (bản mã dưới cánh nằm)
            p2[2] = z_fb - pt_plate(tuple(b2)) / 1000
        g = m["heel_to_center"] if abs(m["width"] - T.sec(m["section"])["b"]) < 6 else T.sec(m["section"])["b"] / 2
        out.append(member(p1, p2, m["section"], e1, e2, g, "LEN" if up else "XUONG", "mat_bang_3_3"))
    rep["mat_bang_3_3"] = [(m["section"], m["vis"]) for m in plan_m]
    bolts3 = []                                  # (điểm trên trục, trục, d, nhãn L ứng viên, nguồn)

    def Lc(view_labs, q, d):
        return sorted({L for dd, L, pp in view_labs if dd == d and math.dist(pp, q) < 40})
    for q, d in arm_eb:
        bolts3.append((E3(*q) + np.array([0, -BACK, 0]), np.array([0, -1.0, 0]), d, Lc(elab, q, d), "mat_dung"))
    for q, d in arm_pb:
        bolts3.append((P3(*q) + np.array([0, 0, z_fb]), np.array([0, 0, 1.0]), d, Lc(plab, q, d), "mat_bang_3_3"))
    # ---------- 4-4: 2 thanh L65x5 nối 2 biên trên (mặt phẳng biên trên), áp mặt trên cánh còn lại của X203
    m203 = next(m for m in out if m.get("mark") == "X203")
    e1_203 = np.array(m203["frames"]["bv"][0])
    c1d, c2d = np.array(el["X203"]["c1"]), np.array(el["X203"]["c2"])
    a44, b44, l44, f44 = read_view(doc, msp, cfg["p44"])
    ch = [m for m in a44 if m["section"] == "L70X6"]
    x0_44 = min(m["c1"][0] for m in ch)
    L44 = max(m["c2"][0] for m in ch) - x0_44
    yc44 = sum(m["c1"][1] for m in ch) / len(ch)
    half44 = abs(ch[0]["c1"][1] - yc44)
    g203 = m203["g"][0] / 1000
    yb203 = BACK - g203                                     # đường đinh cánh còn lại X203 (|Y|)

    def on44(x, y):
        f = (x - x0_44) / L44
        q = c1d + (c2d - c1d) * f
        P = E3(*q)
        P = P + (-e1_203) * g203                             # lên lưng (mép trên) X203: mặt ngoài cánh còn lại
        P[1] = (y - yc44) / half44 * yb203
        return P
    for m in a44:
        if m["section"] == "L70X6":
            continue
        b1, b2, _ = ends_by_bolts(m, b44)
        p1, p2 = on44(*b1), on44(*b2)
        hd = np.array(m["heel_dir"])
        u203 = unitv(np.array(m203["p2"]) - np.array(m203["p1"]))
        e1 = -np.sign(hd[0]) * u203 if abs(hd[0]) > 0.5 else u203
        out.append(member(p1, p2, m["section"], e1, -e1_203, gauge(m), "LEN", "mat_cat_4_4"))
    for q, d in b44:
        if abs(abs(q[1] - yc44) - half44) * SC < 60:
            bolts3.append((on44(*q), -(-e1_203), d, Lc(l44, q, d), "mat_cat_4_4"))
    # ---------- 6-6: 2 thanh L50x4 chéo giữa 2 thanh đứng X206 (mặt trước/sau), 2 mặt của cánh còn lại X206
    m206 = next(m for m in out if m.get("mark") == "X206")
    X206 = m206["p1"][0]
    g206 = m206["g"][0] / 1000
    t206 = T.sec(m206["section"])["t"] / 1000
    Xh = X206 - g206                                       # mặt lưng cánh còn lại X206 (e1 = +X)
    a66, b66, l66, f66 = read_view(doc, msp, cfg["p66"])
    vv = sorted([m for m in a66 if abs(m["ang"] - 90) < 1], key=lambda m: m["c1"][0])
    xc66 = (vv[0]["c1"][0] + vv[-1]["c1"][0]) / 2
    half66 = abs(vv[0]["c1"][0] - xc66)
    yb206 = BACK + m206["p1"][1] - 0 if False else abs(m206["p1"][1]) - T.sec(m206["section"])["b"] / 2000
    ylo66 = min(vv[0]["c1"][1], vv[0]["c2"][1])
    z_lo206 = min(m206["p1"][2], m206["p2"][2])
    on66 = lambda x, y, X: np.array([X, (x - xc66) / half66 * yb206, z_lo206 + (y - ylo66) * SC / 1000])
    k66 = 0
    for m in a66:
        if abs(m["ang"] - 90) < 1:
            continue
        up = m["vis"] == "S"
        X_ = Xh if up else Xh + t206                        # nét liền: mặt ngoài (phía đầu xà); khuất: mặt trong
        b1, b2, _ = ends_by_bolts(m, b66)
        hd = np.array(m["heel_dir"])
        e1 = unitv([0.0, -hd[0], -hd[1]])
        e2 = np.array([-1.0, 0, 0]) if up else np.array([1.0, 0, 0])
        out.append(member(on66(*b1, X_), on66(*b2, X_), m["section"], e1, e2, gauge(m),
                          "NGOAI" if up else "TRONG", "mat_cat_6_6"))
        k66 += 1
    for q, d in b66:
        bolts3.append((on66(*q, Xh), np.array([1.0, 0, 0]), d, Lc(l66, q, d), "mat_cat_6_6"))
    # ký hiệu tấm đệm (nD.F_T) -> bu lông gần nhất cùng hình chiếu (chữ ghi cạnh bu lông)
    def crossing(b):
        """Bu lông ở chỗ >= 2 thanh mặt bằng giao nhau (đường tâm qua bu lông)."""
        n_ = 0
        for m in out:
            if m["xa_view"] != "mat_bang_3_3":
                continue
            P1, P2 = np.array(m["p1"])[:2], np.array(m["p2"])[:2]
            ab = P2 - P1
            t_ = np.clip((b[0][:2] - P1) @ ab / (ab @ ab), 0.05, 0.95)
            n_ += np.linalg.norm(b[0][:2] - (P1 + ab * t_)) < 0.01
        return n_ >= 2
    for n, t, q in pfl:
        i = min((i for i, b in enumerate(bolts3) if b[4] == "mat_bang_3_3" and crossing(b)),
                key=lambda i: math.hypot(*(bolts3[i][0][:2] - P3(*q)[:2])))
        bolts3[i] = bolts3[i][:5] + ((n, t),)
    for n, t, q in f66:
        i = min((i for i, b in enumerate(bolts3) if b[4] == "mat_cat_6_6"),
                key=lambda i: np.linalg.norm(bolts3[i][0][1:] - on66(*q, Xh)[1:]))
        bolts3[i] = bolts3[i][:5] + ((n, t),)
    bolts3 = [b if len(b) == 6 else b + (None,) for b in bolts3]
    return el, out, plates, bolts3, [], rep, (E3, P3, z_fb, z_ft)


X1 = {
    "elev": (-2360, -119355, -2212, -119255),   # mặt đứng tay trái X1 (hình thật mặt bên xoay 18,1 độ)
    "x_back": -2217.96, "y_top": -119277.05,    # lưng thanh cánh; đường đinh biên trên (= thanh L70x6 đỉnh)
    "p11": (-2085, -119375, -1958, -119250),    # mặt bằng 1-1 (biên trên)
    "p22": (-2075, -119495, -1915, -119385),    # mặt cắt 2-2 (mặt phẳng biên dưới)
    "p55": (-1860, -119465, -1765, -119400),    # mặt cắt 5-5 (qua thanh đứng)
    "x_bend": 1.040, "slope": 0.327,            # chỗ bẻ đầu thanh L70x6 đỉnh DN-01 (mặt cắt 1-1 DN-01)
    "details": {"X113": (-1804, -119269), "X114": (-1806, -119358)},
    "plan_labels": {"p11": {90: "L50X4", 54.9: "L60X5"}},
}


def build_x1(doc, msp, cfg, z_top):
    """Tay trái X1, mặt trước + mặt bằng 1-1 / 2-2 / 5-5. Mặt bên X1 = mặt đứng xoay th = atan(0,327) quanh trục
    đứng tại x = -x_bend, mặt lưng cột (y = -BACK) (người dùng chốt); mặt đứng tờ xà là hình thật của mặt này."""
    rep = {}
    th = math.atan(cfg["slope"])
    sb = cfg["x_bend"] - BACK
    A = np.array([-cfg["x_bend"], -BACK])
    dirv = np.array([-math.cos(th), math.sin(th)])       # dọc mặt xà ra đầu xà (tay trái, mặt trước)
    nout = np.array([-math.sin(th), -math.cos(th)])      # pháp tuyến ra ngoài mặt xà

    def E(x, y, d=0.0):
        s_ = -(x - cfg["x_back"]) * SC / 1000
        z = z_top + (y - cfg["y_top"]) * SC / 1000
        if s_ <= sb:
            xy = np.array([-(BACK + s_), -(BACK + d / 1000)])
        else:
            xy = A + dirv * (s_ - sb) + nout * d / 1000
        return np.array([xy[0], xy[1], z])
    along = np.array([-dirv[0], -dirv[1], 0.0])            # x bản vẽ tăng -> về phía cột
    out = []
    ms, eb, elab, efl = read_view(doc, msp, cfg["elev"])
    el = {}
    for m in ms:
        a = m["ang"] % 180
        key = "X1_tren" if a < 1 else "X1_duoi" if 140 < a < 170 else "X1_dung" if abs(a - 90) < 1 else \
            "X1_cheo" if 20 < a < 45 else None
        if key:
            el[key] = m
    t_of = lambda k: T.sec(el[k]["section"])["t"]
    dep = {"X1_tren": (0.0, 0.0), "X1_duoi": (0.0, 0.0), "X1_dung": (-t_of("X1_duoi"), -t_of("X1_tren")),
           "X1_cheo": (0.0, 8.0)}
    # nét đầu thanh vẽ rõ ở đầu xà (đoạn ngắn vuông góc trục, dài ~ bề rộng vẽ, nằm trong dải thanh) - VD biên trên
    # thò ra ngoài bản X113 20 mm (góp ý 28/11: thanh ra khỏi bản mã nằm ngang): kéo đầu thanh tới nét đó
    bx = cfg["elev"]
    shorts = []
    for e in msp.query("LINE"):
        a_, b_ = (e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])
        if all(bx[0] <= q[0] <= bx[2] and bx[1] <= q[1] <= bx[3] for q in (a_, b_)) and 0.5 < math.dist(a_, b_) < 6:
            shorts.append((np.array(a_), np.array(b_)))

    def tip_end_line(m, b1, b2):
        c1_, c2_ = np.array(m["c1"]), np.array(m["c2"])
        u_ = (c2_ - c1_) / np.linalg.norm(c2_ - c1_)
        n_ = np.array([-u_[1], u_[0]])
        bt = np.array(b1 if b1[0] < b2[0] else b2)          # đầu phía đầu xà (x bản vẽ nhỏ)
        sgn = -1.0 if np.dot(u_, [1.0, 0]) > 0 else 1.0       # hướng về đầu xà dọc trục
        best = None
        for a_, b_ in shorts:
            v_ = (b_ - a_) / np.linalg.norm(b_ - a_)
            if abs(np.dot(v_, u_)) > 0.1 or abs(np.linalg.norm(b_ - a_) * SC - m["width"]) > 15:
                continue
            mid = (a_ + b_) / 2
            ext = sgn * np.dot(mid - bt, u_)
            off = np.dot(mid - c1_, n_)
            if 0 < ext * SC < 400 and abs(off) * SC < m["width"]:
                if best is None or ext > best[0]:
                    best = (ext, bt + sgn * u_ * ext)
        return best
    for k, m in el.items():
        b1, b2, _ = ends_by_bolts(m, eb)
        if k in ("X1_tren", "X1_duoi"):
            te = tip_end_line(m, b1, b2)
            if te:
                if b1[0] < b2[0]:
                    b1 = tuple(te[1])
                else:
                    b2 = tuple(te[1])
                rep.setdefault("keo_dau_xa_mm", {})[k] = round(te[0] * SC)
        out_ = m["vis"] == "S"
        d1, d2 = dep[k]
        if k == "X1_dung" and b1[1] > b2[1]:
            d1, d2 = d2, d1
        if k == "X1_cheo":                     # đầu sát cột (x lớn) áp mặt ngoài tai bản mã 117 (d8), đầu kia áp biên dưới
            d1, d2 = (8.0, 0.0) if b1[0] > b2[0] else (0.0, 8.0)
        p1, p2 = E(*b1, d1), E(*b2, d2)
        hd = np.array(m["heel_dir"])
        e1 = unitv(-(hd[0] * along + np.array([0, 0, 1.0]) * hd[1]))
        e2 = np.r_[nout, 0.0] if out_ else -np.r_[nout, 0.0]
        out.append(member(p1, p2, m["section"], e1, e2, gauge(m), "NGOAI" if out_ else "TRONG", "mat_dung",
                          {"mark": k, "xa_bo": "X1"}))
    rep["mat_dung"] = {k: v["section"] for k, v in el.items()}
    mt = next(m for m in out if m["mark"] == "X1_tren")
    md = next(m for m in out if m["mark"] == "X1_duoi")
    bolts3 = []
    Lc = lambda labs, q, d: sorted({L for dd, L, pp in labs if dd == d and math.dist(pp, q) < 40})
    for q, d in eb:
        if -(q[0] - cfg["x_back"]) * SC / 1000 > sb + 0.02:
            bolts3.append((E(*q), -np.r_[nout, 0.0], d, Lc(elab, q, d), "mat_dung", None))

    def flange_line(m):
        """Cánh còn lại (chĩa vào trong tay xà) của biên: điểm lưng + hướng cánh (e2) + hướng dày (e1)."""
        P1, P2, e1, e2 = CK.frame(m)
        H1, H2 = P1 - e1 * m["g"][0] / 1000, P2 - e1 * m["g"][0] / 1000
        return H1, H2, e1, e2
    # ---------- mặt bằng 1-1: 2 thanh nối 2 biên trên (nằm ngang) - nét liền: trên mặt trên cánh nằm biên trên
    H1, H2, e1t, e2t = flange_line(mt)
    a11, b11, l11, f11 = read_view(doc, msp, cfg["p11"])
    ch = sorted([m for m in a11 if m["section"] == "L70X6"], key=lambda m: m["c1"][1])
    xe = max(max(m["c1"][0], m["c2"][0]) for m in ch)                      # đầu cột trên mặt bằng
    yc = (min(m["c1"][1] for m in ch) + max(m["c2"][1] for m in ch)) / 2
    Xe = mt["p2"][0] if abs(mt["p2"][0]) < abs(mt["p1"][0]) else mt["p1"][0]
    t_t = T.sec(mt["section"])["t"] / 1000
    z_up = max(H1[2], H1[2] + e1t[2] * t_t)                                 # mặt trên cánh nằm biên trên
    z_dn = min(H1[2], H1[2] + e1t[2] * t_t)
    P11 = lambda x, y, z: np.array([Xe + (x - xe) * SC / 1000, (y - yc) * SC / 1000, z])
    for m in a11:
        if m["section"] == "L70X6":
            continue
        a_ = m["ang"] % 180
        secn = "L50X4" if abs(a_ - 90) < 2 else "L60X5"                   # nhãn trên hình (bộ đọc gán nhầm L60x5)
        m["section"] = secn
        b1, b2, _ = ends_by_bolts(m, b11)
        up = m["vis"] == "S"
        z_ = z_up if up else z_dn
        hd = np.array(m["heel_dir"])
        out.append(member(P11(*b1, z_), P11(*b2, z_), secn, unitv([-hd[0], -hd[1], 0.0]),
                          np.array([0, 0, 1.0 if up else -1.0]), gauge(m), "LEN" if up else "XUONG", "mat_bang_1_1",
                          {"xa_bo": "X1"}))
    xtip11 = min(min(m["c1"][0], m["c2"][0]) for m in ch)
    for q, d in b11:
        if d == 16 and abs(q[1] - yc) * SC < 60 and (q[0] - xtip11) * SC < 600:
            continue        # người dùng (góp ý 28/11): bỏ cụm 4 lỗ M16 giữa bản X114 (không bu lông, không lỗ)
        bolts3.append((P11(*q, z_dn), np.array([0, 0, 1.0]), d, Lc(l11, q, d), "mat_bang_1_1", None))
    # ---------- 2-2: mặt phẳng 2 biên dưới (xiên) - ánh xạ song tuyến theo đường lưng cánh còn lại 2 biên dưới
    G1, G2, e1d, e2d = flange_line(md)
    a22, b22, l22, f22 = read_view(doc, msp, cfg["p22"])
    cd = sorted([m for m in a22 if m["section"] == "L70X6"], key=lambda m: m["c1"][1] + m["c2"][1])
    fr, bk = cd[0], cd[1]                                                   # mặt trước (y nhỏ), mặt sau
    colf = max((fr["c1"], fr["c2"]), key=lambda q: q[0])
    tipf = min((fr["c1"], fr["c2"]), key=lambda q: q[0])
    colb = max((bk["c1"], bk["c2"]), key=lambda q: q[0])
    tipb = min((bk["c1"], bk["c2"]), key=lambda q: q[0])
    gd = gauge({"section": md["section"], "width": 70, "heel_to_center": 35})
    # đường đinh cánh còn lại biên dưới (3D), mặt trước; mặt sau = đối xứng y
    Gc = G2 if abs(G2[0]) < abs(G1[0]) else G1
    Gt = G1 if abs(G2[0]) < abs(G1[0]) else G2
    Lf_c, Lf_t = Gc + e2d * gd / 1000, Gt + e2d * gd / 1000
    MYv = np.array([1, -1, 1.0])
    t_d = T.sec(md["section"])["t"] / 1000
    in_side = e1d if e1d[2] > 0 else -e1d                                  # mặt cánh còn lại phía trong tay xà (trên)
    off_in = t_d if np.dot(in_side, e1d) > 0 else 0.0

    def P22(x, y):
        tf = (x - colf[0]) / (tipf[0] - colf[0])
        yf = colf[1] + (tipf[1] - colf[1]) * tf
        yb = colb[1] + (tipb[1] - colb[1]) * tf
        v = (y - yf) / (yb - yf)
        F_ = Lf_c + (Lf_t - Lf_c) * tf
        B_ = F_ * MYv
        return F_ + (B_ - F_) * v + e1d * off_in
    n22 = unitv(np.cross(Lf_t - Lf_c, np.array([0, 1.0, 0])))
    if np.dot(n22, in_side) < 0:
        n22 = -n22
    # góp ý 28/11: thanh ngang 2-2 phía cột (L50x4, sát thanh đứng) dời 50 mm DỌC BIÊN về phía đầu xà (kèm bu lông):
    # mỗi đầu trượt dọc đường biên của nó trên hình 2-2 (2 biên chụm dần về đầu xà)
    k50 = 0.050 / float(np.linalg.norm(Lf_t - Lf_c))
    dF = (np.array(tipf) - np.array(colf)) * k50
    dB = (np.array(tipb) - np.array(colb)) * k50
    tr22 = [m for m in a22 if m["section"] != "L70X6" and abs(m["ang"] % 180 - 90) < 5]
    m_mv = max(tr22, key=lambda m: m["c1"][0] + m["c2"][0]) if len(tr22) > 1 else None

    def slide(q):
        tf = (q[0] - colf[0]) / (tipf[0] - colf[0])
        yf = colf[1] + (tipf[1] - colf[1]) * tf
        yb = colb[1] + (tipb[1] - colb[1]) * tf
        d_ = dF if abs(q[1] - yf) < abs(q[1] - yb) else dB
        return (q[0] + d_[0], q[1] + d_[1])
    if m_mv is not None:
        c1_, c2_ = np.array(m_mv["c1"]), np.array(m_mv["c2"])
        uu = (c2_ - c1_) / np.linalg.norm(c2_ - c1_)
        moved_b = {tuple(q): slide(q) for q, d in b22
                   if abs(uu[0] * (q[1] - c1_[1]) - uu[1] * (q[0] - c1_[0])) * SC < 40}
        for k_ in ("c1", "c2", "b1", "b2"):
            m_mv[k_] = slide(m_mv[k_])
        b22 = [(moved_b.get(tuple(q), q), d) for q, d in b22]
        rep["X1_doi_2_2_mm"] = {"thanh": m_mv["section"], "doc_bien_mm": 50, "bu_long": len(moved_b)}
    for m in a22:
        if m["section"] == "L70X6":
            continue
        if not m["section"]:
            m["section"] = "L50X4"
        b1, b2, _ = ends_by_bolts(m, b22)
        p1, p2 = P22(*b1), P22(*b2)
        under = m["section"] == "L60X5"     # góp ý 28/11: thanh chéo L60x5 úp xuống MẶT DƯỚI cánh biên dưới
        if under:
            p1, p2 = p1 - n22 * t_d, p2 - n22 * t_d
        u_ = unitv(p2 - p1)
        hd = np.array(m["heel_dir"])
        hd3 = P22(b1[0] + hd[0], b1[1] + hd[1]) - p1
        e1 = unitv(-(hd3 - np.dot(hd3, u_) * u_ - np.dot(hd3, n22) * n22))
        mm = member(p1, p2, m["section"], e1, -n22 if under else n22, gauge(m), "XUONG" if under else "LEN",
                    "mat_cat_2_2", {"xa_bo": "X1"})
        # 2 cánh nằm biên dưới nghiêng ngược nhau (+-8 độ, mỗi biên vuông góc mặt bên xoay của nó): nâng thanh theo pháp
        # tuyến mặt 2-2 tới khi không lấn vào biên (khe còn lại: tấm đệm vừa khe khi xếp bu lông) - thanh ép sát
        chords = [md, mir_m(md, MYv)]
        for k_ in range(0, 15):
            sp_ = CK.samples(mm, {mm["section"]: T.sec(mm["section"])})
            if not any(np.any(CK.where_v(c_, {md["section"]: T.sec(md["section"])}, sp_, 0.0005) > 0) for c_ in chords):
                break
            sg_ = -1.0 if under else 1.0
            mm["p1"] = (np.array(mm["p1"]) + sg_ * n22 * 0.001).round(5).tolist()
            mm["p2"] = (np.array(mm["p2"]) + sg_ * n22 * 0.001).round(5).tolist()
        out.append(mm)
    for q, d in b22:
        pq = P22(*q)
        # bu lông trên cánh biên dưới: trục theo pháp tuyến cánh biên đó (trước / sau), còn lại theo mặt 2-2
        tf = (q[0] - colf[0]) / (tipf[0] - colf[0])
        yf = colf[1] + (tipf[1] - colf[1]) * tf
        yb = colb[1] + (tipb[1] - colb[1]) * tf
        ax_ = n22
        if abs(q[1] - yf) * SC < 60:
            ax_ = in_side
        elif abs(q[1] - yb) * SC < 60:
            ax_ = in_side * MYv
        bolts3.append((pq - ax_ * 0.035, ax_, d, Lc(l22, q, d), "mat_cat_2_2", None))
    # ---------- 5-5: thanh chéo L50x4 giữa 2 thanh đứng. Người dùng: bẻ cục bộ cánh còn lại thanh đứng (18,1°) cho
    # nằm trong mặt phẳng ngang x = lưng thanh đứng; thanh chéo áp phẳng trên mặt đó (mặt phẳng x = const)
    mv = next(m for m in out if m["mark"] == "X1_dung")
    P1v, P2v, e1v, e2v = CK.frame(mv)
    gv = mv["g"][0] / 1000
    tv = T.sec(mv["section"])["t"] / 1000
    a55, b55, l55, f55 = read_view(doc, msp, cfg["p55"])
    vv = sorted([m for m in a55 if abs(m["ang"] - 90) < 2], key=lambda m: m["c1"][0])
    xc5 = (vv[0]["c1"][0] + vv[-1]["c1"][0]) / 2
    half5 = abs(vv[0]["c1"][0] - xc5)
    ylo5 = min(vv[0]["c1"][1], vv[0]["c2"][1])
    zlo = min(P1v[2], P2v[2])
    Hv = (P1v if P1v[2] < P2v[2] else P2v) - e1v * gv                       # lưng thanh đứng (mặt trước)
    hx = Hv[0]
    sx = -np.sign(hx)                                                       # hướng vào trong xà theo x
    yb5 = abs(Hv[1]) - gv                                                   # đường đinh cánh bẻ (cánh chĩa vào trong)

    def P55(x, y, xoff):
        return np.array([hx + sx * xoff, (x - xc5) / half5 * yb5, zlo + (y - ylo5) * SC / 1000])
    bend55 = []
    for m in a55:
        if abs(m["ang"] - 90) < 2:
            continue
        up = m["vis"] == "S"
        off = 0.0 if up else tv
        b1, b2, on55 = ends_by_bolts(m, b55)
        p1 = P55(*b1, off)
        p2 = P55(*b2, off)
        dd_ = (np.array(b2) - b1) / np.linalg.norm(np.array(b2) - b1)
        diag_b55 = [(q, d) for q, d in b55 if abs(dd_[0] * (q[1] - b1[1]) - dd_[1] * (q[0] - b1[0])) * SC < 8]
        u_ = unitv(p2 - p1)
        hd = np.array(m["heel_dir"])
        e1 = np.array([0.0, -hd[0], -hd[1]])
        e1 = unitv(e1 - np.dot(e1, u_) * u_)
        e2 = np.array([-sx if up else sx, 0.0, 0.0])
        out.append(member(p1, p2, m["section"], e1, e2, gauge(m), "NGOAI" if up else "TRONG", "mat_cat_5_5",
                          {"xa_bo": "X1"}))
        sphi = max(float(np.linalg.norm(np.cross(u_, [0, 0, 1.0]))), 0.2)
        cphi = abs(u_[2])
        half = 0.5 * (T.sec(m["section"])["b"] / sphi + T.sec(mv["section"])["b"] * cphi / sphi) + 10
        for P in (p1, p2):
            bend55.append({"z": float(P[2]), "front": bool(P[1] < 0), "half_mm": round(half, 1)})
    # chỉ bu lông trên thanh chéo; 2 bu lông còn lại của hình 5-5 = bu lông thanh đứng - biên (đã có ở mặt đứng)
    for q, d in diag_b55:
        pq = P55(*q, 0.0)
        ax_ = np.array([sx, 0.0, 0.0])
        bolts3.append((pq - ax_ * 0.02, ax_, d, Lc(l55, q, d), "mat_cat_5_5", None))
    # ---------- bản mã: X113 (đầu xà, mặt bên, d8 ngoài biên) - X114 (đầu xà, nằm ngang d12, dưới cánh nằm biên trên)
    plates = []
    banma = T.banma_loops(msp)
    allb = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name]) for e in msp.query("INSERT")
            if e.dxf.name in ("1", "2", "3")]
    cen = lambda P: (sum(q[0] for q in P) / len(P), sum(q[1] for q in P) / len(P))

    def detail(mark):
        c = cfg["details"][mark]
        P = min(banma, key=lambda P: math.dist(cen(P), c))
        return P, [q for q, _ in allb if T.point_in_poly(q, P)]

    def put(mark, box, bolts_v, to3, a1, a2, td, t_mm):
        D, Hh = detail(mark)
        inb = lambda q: box[0] <= q[0] <= box[2] and box[1] <= q[1] <= box[3]
        Ps = [P for P in banma if all(inb(q) for q in P)]
        tip_ = min(Ps, key=lambda P: cen(P)[0])
        Tf = fit_by_holes(D, Hh, [q for q, _ in bolts_v if math.dist(q, cen(tip_)) * SC < 350], cen(tip_))
        pts = [to3(*Tf(q)) for q in D]
        o = pts[0]
        poly = [[round(float(np.dot(q - o, a1)), 5), round(float(np.dot(q - o, a2)), 5)] for q in pts]
        area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                       for i in range(len(poly)))) / 2
        here = [q for q, _ in bolts_v if any(math.dist(Tf(h), q) * SC < 15 for h in Hh)]
        plates.append({"kind": "gusset", "node": np.round(o, 4).tolist(), "members": [], "t_mm": t_mm, "on_leg": False,
                       "origin": np.round(o, 5).tolist(), "a1": np.round(a1, 6).tolist(), "a2": np.round(a2, 6).tolist(),
                       "thick_dir": np.round(td, 6).tolist(), "poly": poly, "area_m2": round(area, 5),
                       "mass_kg": round(area * t_mm / 1000 * 7850, 2), "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0,
                       "mark": mark, "reason": "bản mã xà %s d%d theo hình chi tiết (khớp %d/%d lỗ)" % (
                           mark, t_mm, len(here), len(Hh))})
    put("X113", cfg["elev"], eb, lambda x, y: E(x, y, 0.0), np.r_[-dirv, 0.0], np.array([0, 0, 1.0]),
        np.r_[nout, 0.0], 8)
    # X114: biên trên có lưng ở TRÊN (cánh đứng thõng xuống) -> bản nằm TRÊN cánh nằm (hình 1-1 vẽ nét liền)
    put("X114", cfg["p11"], b11, lambda x, y: P11(x, y, z_up), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
        np.array([0, 0, 1.0]), 12)
    rep["thanh"] = len(out)
    rep["bend55"] = bend55
    return out, plates, bolts3, rep


# ---------------------------------------------------------------- đối xứng, cao độ, bu lông, ghép vào cột
def mir_m(m, M):
    m = json.loads(json.dumps(m))
    m["p1"] = (np.array(m["p1"]) * M).round(5).tolist()
    m["p2"] = (np.array(m["p2"]) * M).round(5).tolist()
    m["frames"]["bv"] = [(np.array(v) * M).round(6).tolist() for v in m["frames"]["bv"]]
    return m


def mir_p(p, M):
    p = json.loads(json.dumps(p))
    for k in ("origin", "node", "a1", "a2", "thick_dir"):
        p[k] = (np.array(p[k]) * M).round(6).tolist()
    return p


def plate_inside(pl, Q, eps=0.0):
    o, a1, a2, td = (np.array(pl[k], float) for k in ("origin", "a1", "a2", "thick_dir"))
    t = pl["t_mm"] / 1000
    R = Q - o
    u, v, w = R @ a1, R @ a2, R @ td
    poly = np.array(pl["poly"])
    ins = np.zeros(len(Q), bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        c = ((yi > v) != (yj > v)) & (u < (xj - xi) * (v - yi) / ((yj - yi) if yj != yi else 1e-12) + xi)
        ins ^= c
        j = i
    return ins & (w > eps) & (w < t - eps)


def stack(p0, ax, members, plates, S, span=0.12):
    """Các lớp thép dọc trục bu lông qua p0: trả danh sách đoạn (s0, s1, tên) đã gộp (khe <= 0,6 mm)."""
    s = np.arange(-span, span, 0.0004)
    Q = p0[None, :] + np.outer(s, ax)
    occ = []
    for m in members:
        P1, P2 = np.array(m["p1"]), np.array(m["p2"])
        ab = P2 - P1
        t = np.clip((p0 - P1) @ ab / (ab @ ab), 0, 1)
        if np.linalg.norm(p0 - (P1 + ab * t)) > 0.3:
            continue
        hit = CK.where_v(m, S, Q, 0.0) > 0
        if hit.any():
            occ.append((s[hit], m.get("mark") or m["section"]))
    for pl in plates:
        if np.linalg.norm(np.array(pl["origin"]) - p0) > 1.0:
            continue
        hit = plate_inside(pl, Q, 0.0)
        if hit.any():
            occ.append((s[hit], "bản mã " + str(pl.get("mark", pl.get("reason", "")[:12]))))
    runs = []
    for ss, nm in occ:
        runs.append((float(ss.min()) - 0.0002, float(ss.max()) + 0.0002, nm))
    return sorted(runs)


def main(dxf, scene_in, scene_out):
    doc = T.read_dxf_cached(dxf)
    msp = doc.modelspace()
    sc = json.load(open(scene_in))
    S = sc["sections"]
    el, out, plates, bolts3, fills, rep, _ = build_x2(doc, msp, X2)
    for m in out:
        S.setdefault(m["section"], T.sec(m["section"]))
    MY = np.array([1, -1, 1.0])
    MX = np.array([-1, 1, 1.0])
    # mặt sau = đối xứng mặt trước (chỉ phần mặt đứng); thanh/bản mã mặt bằng, 4-4, 6-6 đã đủ 2 bên
    arm_m = out + [mir_m(m, MY) for m in out if m["xa_view"] == "mat_dung"]
    arm_p = plates + [mir_p(p, MY) for p in plates if abs(p["thick_dir"][1]) > 0.5]
    arm_b = bolts3 + [(b[0] * MY, b[1] * MY, b[2], b[3], b[4], b[5]) for b in bolts3 if b[4] == "mat_dung"]
    arm_f = fills
    # cao độ X2: thanh L90x7 2840 mặt có xà (thân)
    zs = sorted({round((m["p1"][2] + m["p2"][2]) / 2, 3) for m in sc["members"] if m["section"] == "L90X7"
                 and m["rule"] == "face" and abs(m["p1"][2] - m["p2"][2]) < 0.002 and m["length"] > 2.7})
    rep["cao_do_X2_m"] = zs
    nid = max(m["id"] for m in sc["members"])
    new_m, new_p, new_b, new_f = [], [], [], []
    for lv, z in enumerate(zs):
        Z = np.array([0, 0, z])
        for side, M in (("trái", np.array([1, 1, 1.0])), ("phải", MX)):
            for m in arm_m:
                mm = mir_m(m, M)
                mm["p1"] = (np.array(mm["p1"]) + Z).round(5).tolist()
                mm["p2"] = (np.array(mm["p2"]) + Z).round(5).tolist()
                nid += 1
                mm["id"] = nid
                mm["xa"] = "X2 cao độ %.3f, tay %s" % (z, side)
                new_m.append(mm)
            for p in arm_p:
                pp = mir_p(p, M)
                pp["origin"] = (np.array(pp["origin"]) + Z).round(5).tolist()
                pp["node"] = pp["origin"]
                new_p.append(pp)
            for b in arm_b:
                new_b.append((b[0] * M + Z, b[1] * M, b[2], b[3], b[4], b[5]))
            for n, t, v, q in arm_f:
                new_f.append((n, t, v, q * M + Z))
    # ---------- xà X1 (1 bộ ở đỉnh DN-01): cao độ = đường đinh thanh L70x6 đỉnh (đã bẻ 2 đầu)
    ztop = [m["p1"][2] for m in sc["members"] if m["section"] == "L70X6" and m.get("prof") and m["rule"] == "face"]
    if ztop:
        z_top = max(ztop)
        o1, p1_, b1_, r1 = build_x1(doc, msp, X1, z_top)
        for m in o1:
            S.setdefault(m["section"], T.sec(m["section"]))
        arm1_m = o1 + [mir_m(m, MY) for m in o1 if m["xa_view"] == "mat_dung"]
        arm1_p = p1_ + [mir_p(p, MY) for p in p1_ if abs(p["thick_dir"][2]) < 0.5]
        arm1_b = b1_ + [(b[0] * MY, b[1] * MY, b[2], b[3], b[4], b[5]) for b in b1_ if b[4] == "mat_dung"]
        for side, M in (("trái", np.array([1, 1, 1.0])), ("phải", MX)):
            for m in arm1_m:
                mm = mir_m(m, M)
                nid += 1
                mm["id"] = nid
                mm["xa"] = "X1, tay %s" % side
                new_m.append(mm)
            new_p.extend(mir_p(p, M) for p in arm1_p)
            new_b.extend((b[0] * M, b[1] * M, b[2], b[3], b[4], b[5]) for b in arm1_b)
        bend55 = r1.pop("bend55", [])
        rep["X1_be_canh_5_5"] = []
        for mm in new_m:
            if mm.get("mark") != "X1_dung":
                continue
            P1v, P2v, e1v, e2v = CK.frame(mm)
            Lv = float(np.linalg.norm(P2v - P1v))
            u_ = (P2v - P1v) / Lv
            tgt = np.array([0.0, np.sign(e2v[1]), 0.0])          # cánh còn lại xoay về mặt phẳng x = const
            th = math.atan2(float(np.dot(np.cross(e2v, tgt), u_)), float(np.dot(e2v, tgt)))
            for bz in bend55:
                if bz["front"] != bool(P1v[1] < 0):
                    continue
                xb = (bz["z"] - P1v[2]) / u_[2] * 1000
                x0, x1 = max(0.0, xb - bz["half_mm"]), min(Lv * 1000, xb + bz["half_mm"])
                mm.setdefault("bends", []).append({"x0": round(x0, 1), "x1": round(x1, 1), "ramp": 40.0,
                                                   "theta_deg": round(math.degrees(th), 3), "plan": "5-5 X1"})
                rep["X1_be_canh_5_5"].append({"thanh": mm["id"], "x0": round(x0), "x1": round(x1),
                                              "deg": round(math.degrees(th), 2)})
        rep["X1"] = dict(r1, cao_do_m=round(z_top, 3))
    # đầu dưới X205 áp mặt ngoài bản mã có tai của thân: chiều dày thật từng cao độ (DN-01: 123 d8; DN-02: 226 d10)
    face_pl = [p for p in sc["plates"] if abs(p["thick_dir"][1]) > 0.9 and p.get("kind") != "filler"]
    for m in new_m:
        if m.get("mark") != "X205":
            continue
        k = "p1" if m["p1"][2] < m["p2"][2] else "p2"
        q = np.array(m[k])
        for p in face_pl:
            Q = np.array([[q[0], p["origin"][1] + p["thick_dir"][1] * 0.001, q[2]]])
            if np.sign(p["origin"][1]) == np.sign(q[1]) and plate_inside(p, Q, -0.002)[0]:
                q[1] = np.sign(q[1]) * (BACK + p["t_mm"] / 1000)
                m[k] = q.round(5).tolist()
                break
    allm = sc["members"] + new_m
    allp = sc["plates"] + new_p
    # gỡ chạm còn lại trong xà: vát góc đầu thanh xà (bội 5 mm, diện tích nhỏ nhất) - ĐỀ XUẤT
    vat = []
    near = lambda a, b: CK.seg_dist(*CK.frame(a)[:2], *CK.frame(b)[:2]) < 0.15
    for m in [x for _pass in range(3) for x in new_m]:      # lặp: dời đầu thanh này có thể sinh chạm ở đầu kia
        if m.get("mark") in ("X201", "X203"):
            continue                                         # biên giữ nguyên, vát thanh bắt vào biên
        oth = [o for o in allm if o is not m and near(m, o)]
        hitters = [o for o in oth if np.any(CK.where_v(o, S, CK.samples(m, S), 0.001) > 0)
                   or np.any(CK.where_v(m, S, CK.samples(o, S), 0.001) > 0)]
        if not hitters:
            continue
        ends = {}
        for o in hitters:
            sp = CK.samples(m, S)
            h = sp[CK.where_v(o, S, sp, 0.001) > 0]
            if not len(h):
                so = CK.samples(o, S)
                h = so[CK.where_v(m, S, so, 0.001) > 0]
            cp = h.mean(0)
            key = "cut1" if np.linalg.norm(np.array(m["p1"]) - cp) < np.linalg.norm(np.array(m["p2"]) - cp) else "cut2"
            ends.setdefault(key, []).append(o)
        for key, hs in ends.items():
            if m.get(key):
                continue
            # bu lông của thanh (chưa xếp lớp): dùng trục vẽ, xuyên +-40 mm quanh mặt tham chiếu
            pb = [{"p": (b[0] - b[1] * 0.04).tolist(), "axis": b[1].tolist(), "grip_mm": 80, "d_mm": b[2]} for b in new_b]
            spots = F.bolt_spots(m, S, pb)
            touch = (lambda ec: (lambda: ec.touching()))(F.EndContact(S, [(m, key, x, None, 0.001) for x in hs]))
            best = F.tri_search([(m, key, spots, touch)], S)              # 1. vát tam giác (góp ý: không vát vuông)
            how = "tam giác"
            if not best:
                # 2. dời bu lông đầu thanh + đầu thanh vào trong dọc trục (bước 5 mm), bu lông vẫn đủ khoảng cách mép
                pk = "p1" if key == "cut1" else "p2"
                P0 = np.array(m[pk])
                uo = P0 - np.array(m["p2" if pk == "p1" else "p1"])
                uo = uo / np.linalg.norm(uo)
                bi = min(range(len(new_b)), key=lambda i: np.linalg.norm(np.cross(new_b[i][0] - (P0 - uo * 0.03),
                                                                                  new_b[i][1])))
                b0 = new_b[bi]
                orig = {id(x): F.bolt_spots(x, S, [pb[bi]]) for x in allm if near(x, m)}
                for sh in range(5, 30, 5):
                    m[pk] = (P0 - uo * sh / 1000).round(5).tolist()
                    nb = (b0[0] - uo * sh / 1000,) + tuple(b0[1:])
                    pbn = {"p": (nb[0] - nb[1] * 0.04).tolist(), "axis": nb[1].tolist(), "grip_mm": 80, "d_mm": nb[2]}
                    ok_e = True
                    for x in allm:
                        if x is m or not near(x, m):
                            continue
                        for (xx, w, fl, d), o0 in zip(F.bolt_spots(x, S, [pbn]), orig.get(id(x), []) or [None]):
                            bw_ = S[x["section"]]["b"]
                            lim = min(F.EDGE.get(d, 21), bw_ - o0[1]) if o0 else F.EDGE.get(d, 21)
                            if bw_ - w < lim - 0.5:
                                ok_e = False
                    if not ok_e:
                        break
                    ec2 = F.EndContact(S, [(m, key, x, None, 0.001) for x in hs])
                    if not ec2.touching():
                        best, how = (0, m, key, None), "dời bu lông %d mm" % sh
                    else:
                        spots2 = F.bolt_spots(m, S, [pbn] + pb)
                        best = F.tri_search([(m, key, spots2, (lambda ec: (lambda: ec.touching()))(ec2))], S)
                        how = "dời bu lông %d mm + tam giác" % sh
                    if best:
                        new_b[bi] = nb
                        m["length"] = round(float(np.linalg.norm(np.array(m["p2"]) - np.array(m["p1"]))), 4)
                        m.setdefault("notes", []).append("dời bu lông + đầu thanh vào %d mm (ĐỀ XUẤT - tránh cấn thép)" % sh)
                        break
                if not best:
                    m[pk] = P0.round(5).tolist()
            if not best:
                best = F.tri_search([(m, key, spots, touch)], S, flanges=("heel",), bmax=150)   # 3. góc lưng - CẦN XEM
                how = "góc lưng (CẦN XEM)"
            if best and best[3]:
                cut = best[3]
                cut["note"] = "vát %s %dx%dmm (ĐỀ XUẤT - tránh chạm %s)" % (
                    {"out": "tam giác cánh còn lại", "conn": "tam giác mép cánh liên kết",
                     "heel": "góc lưng (cánh còn lại lùi b) - CẦN XEM"}[cut["flange"]], cut["a"], cut["b"],
                    "/".join(sorted({x.get("mark") or x["section"] for x in hs})))
                best[1][best[2]] = cut
            vat.append((m.get("mark") or m["section"], m["xa_view"],
                        (how + (" %sx%s %s" % (best[3]["a"], best[3]["b"], best[3]["flange"]) if best[3] else ""))
                        if best else "không gỡ được"))
    # bỏ dòng "không gỡ được" nếu chỗ đó đã hết chạm (do vát thanh kia)
    def still(mk, view):
        for m in new_m:
            if (m.get("mark") or m["section"]) == mk and m["xa_view"] == view:
                for o in allm:
                    if o is not m and near(m, o) and (np.any(CK.where_v(o, S, CK.samples(m, S), 0.001) > 0)):
                        return True
        return False
    vat = [v for v in vat if v[2] != "không gỡ được" or still(v[0], v[1])]
    import collections as _c
    rep["vat_goc"] = [list(k) + [n] for k, n in _c.Counter(vat).items()]
    bolts_out, waiting, removed = [], [], 0
    col_b = list(sc["bolts"])
    for p0, ax, d, Ls, view, fl in new_b:
        runs = stack(p0, ax, allm, allp, S)
        # cụm lớp liền nhau gần p0 nhất; bu lông có ký hiệu tấm đệm: khe <= 40 mm giữa 2 lớp -> đặt tấm đệm
        if not runs:
            waiting.append({"p": np.round(p0, 3).tolist(), "nguon": view, "lop": []})
            continue
        runs.sort()
        groups = [[runs[0]]]
        for r in runs[1:]:
            gap = r[0] - max(x[1] for x in groups[-1])
            if gap <= 0.0008 or gap <= (0.04 if fl else 0.025 if view == "mat_cat_2_2" else 0.012):
                groups[-1].append(r)
            else:
                groups.append([r])
        g = min(groups, key=lambda G: 0 if G[0][0] <= 0 <= max(x[1] for x in G) else
                min(abs(G[0][0]), abs(max(x[1] for x in G))))
        names = [r[2] for r in g]
        if len(names) < 2:
            # lỗ chỉ qua 1 lớp thép = lỗ treo (người dùng xác nhận): tai bản X213 -> bu lông M20 treo chuỗi sứ; lỗ trên
            # biên dưới sát đầu xà và 2 lỗ giữa L75x6 -> bu lông M20 treo chuỗi đỡ lèo dây dẫn
            if len(names) == 1:
                s0, s1 = g[0][0], g[0][1]
                if any(np.linalg.norm(np.array(b["p"]) - (p0 + ax * s0)) < 0.004 for b in bolts_out):
                    continue                                   # lỗ vẽ 2 vòng chồng nhau: 1 bu lông
                grip = (s1 - s0) * 1000
                L = next((x for x in Ls if x >= grip + 0.8 * d + 7), None) or int(math.ceil((grip + 0.8 * d + 7) / 10) * 10)
                bolts_out.append({"id": 0, "p": np.round(p0 + ax * s0, 5).tolist(), "axis": np.round(ax, 6).tolist(),
                                  "nut": np.round(ax, 6).tolist(), "d_mm": d, "grip_mm": round(grip, 1), "L_mm": L,
                                  "L_from": "ký hiệu bản vẽ" if Ls else "tính", "t_mm": 8, "kind": "lo",
                                  "lop": names, "note": ("lỗ treo chuỗi sứ" if "X213" in names[0]
                                  else "lỗ treo chuỗi đỡ lèo dây dẫn") + " (chỉ thể hiện lỗ - góp ý 28/11)"})
                continue
            waiting.append({"p": np.round(p0, 3).tolist(), "nguon": view, "lop": names})
            continue
        s0, s1 = g[0][0], max(x[1] for x in g)
        if True:
            # khe giữa 2 lớp: tấm đệm n x t theo ký hiệu (giảm dày cho vừa khe); không ký hiệu (khe <= 12 mm, VD đầu
            # thanh chéo nét liền qua mép cánh biên dưới - bản vẽ ghi 1D.20_6) -> 1 tấm dày bằng khe
            cov = sorted((r[0], r[1]) for r in g)
            gaps = []
            e = cov[0][1]
            for a_, b_ in cov[1:]:
                if a_ > e + 0.0008:
                    gaps.append((e, a_))
                e = max(e, b_)
            if view == "mat_cat_2_2":
                gaps = []                 # người dùng: mặt cắt 2-2 bỏ vòng đệm (bu lông qua khe)
            for a_, b_ in gaps:
                gp = (b_ - a_) * 1000
                n, t = fl if fl else (1, gp)
                tt = min(t, gp / n)
                for i in range(n):
                    c = p0 + ax * (a_ + i * tt / 1000)
                    e1 = unitv(np.cross(ax, [0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.cross(ax, [1.0, 0, 0]))
                    e2 = np.cross(ax, e1)
                    rr = 0.0185                      # tấm đệm tròn cỡ vòng đệm (vuông 44 lấn sang thanh bên)
                    o = c
                    new_p.append({"kind": "filler", "node": np.round(c, 4).tolist(), "members": [], "t_mm": round(tt, 2),
                                  "on_leg": False, "origin": np.round(o, 5).tolist(), "a1": np.round(e1, 6).tolist(),
                                  "a2": np.round(e2, 6).tolist(), "thick_dir": np.round(ax, 6).tolist(),
                                  "poly": [[round(rr * math.cos(2 * math.pi * k / 16), 5), round(rr * math.sin(2 * math.pi * k / 16), 5)]
                                           for k in range(16)], "area_m2": 0.00108,
                                  "mass_kg": round(0.00194 * tt / 1000 * 7850, 2), "bolt_max": 1, "d_max_mm": d,
                                  "leg_bolts": 0, "reason": "tấm đệm xà %d x %g (khe %.1f mm)" % (n, tt, gp)})
        grip = (s1 - s0) * 1000
        need = grip + 0.8 * d + 7
        L = next((x for x in Ls if x >= need), None) or int(math.ceil(need / 10) * 10)
        head = p0 + ax * s0
        # bu lông thân trùng lỗ (VD 4 bu lông 2840 - bản mã 123): thay bằng bu lông mới xuyên đủ lớp
        keep = []
        for b in col_b:
            q = np.array(b["p"])
            if abs(np.dot(np.array(b["axis"]), ax)) > 0.95 and np.linalg.norm((q - head) - ax * np.dot(q - head, ax)) < 0.012 \
                    and abs(np.dot(q - head, ax)) < 0.08:
                removed += 1
                continue
            keep.append(b)
        col_b = keep
        bolts_out.append({"id": 0, "p": np.round(head, 5).tolist(), "axis": np.round(ax, 6).tolist(),
                          "nut": np.round(ax, 6).tolist(), "d_mm": d, "grip_mm": round(grip, 1), "L_mm": L,
                          "L_from": "ký hiệu bản vẽ" if Ls else "tính", "t_mm": 8, "kind": "xa", "lop": names})
        if view == "mat_cat_2_2":
            bolts_out[-1]["no_filler"] = True
    sc["members"] = allm
    sc["plates"] = allp + [p for p in new_p if p["kind"] == "filler"]
    sc["bolts"] = col_b + bolts_out
    rep["thanh_xa"] = len(new_m)
    rep["ban_ma_xa"] = len(new_p)
    rep["bu_long_xa"] = len(bolts_out)
    rep["bu_long_than_thay"] = removed
    rep["lo_treo"] = sum(1 for b in bolts_out if b["kind"] == "lo")
    rep["lo_khong_bat"] = len(waiting)
    rep["lo_khong_bat_mau"] = waiting[:12]
    sc["title"] = sc["title"].replace("(ghép)", "+ xà X2 (ghép)")
    sc["report"]["build"]["xa"] = rep
    sc["report"]["total_mass_kg"] = round(sum(m.get("mass_kg", 0) for m in allm), 1)
    json.dump(sc, open(scene_out, "w"), ensure_ascii=False)
    print(json.dumps({k: v for k, v in rep.items() if k != "lo_khong_bat_mau"}, ensure_ascii=False)[:1500])
    for w in waiting[:12]:
        print("  lỗ không bắt:", w)


if __name__ == "__main__":
    main(*sys.argv[1:4])
