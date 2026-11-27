"""Phần chung của bộ dựng (hàm hình học, đọc DXF, thanh cánh). Trước đây đầu file dt02.py.

Dựng 3D đầy đủ đoạn thân cột N122 (DT-02, DT-01) từ bản vẽ chế tạo (BVTC) để người dùng soát.

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

Chạy:  python3 tools/bvtc/dt02.py <BVTC.dxf> <thư mục ra> [DT-02|DT-01]
"""
from __future__ import annotations

import json  # noqa: F401
import math
import re  # noqa: F401
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import ezdxf  # noqa: E402
import bvtc_read as R  # noqa: E402
import check_dt02 as CK  # noqa: E402,F401  (các bước dùng qua import *)
from fixes import corner_fix, top_bend  # noqa: E402,F401
import section_library as SL  # noqa: E402

SC = R.SC
SL.JIS_G3192.update({"L75X6": (75, 6, 8.5, 4), "L130X9": (130, 9, 12, 6), "L150X15": (150, 15, 14, 10)})
from sheets import SHEETS  # noqa: E402,F401  (cấu hình từng tờ: tools/bvtc/sheets.py)
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
        # "L90X7-NOI": tiết diện riêng cho thép góc nối (vát góc lưng) - không đổi hình tiết diện thanh cùng cỡ
        b, t, r1, r2 = SL.JIS_G3192[SL.base_name(name.split("-")[0])]
        pts = SL.profile(b, t, r1, r2)
        A, cx, cy = SL.poly_props(pts)
        LIB[name] = {"name": name, "base": SL.base_name(name.split("-")[0]), "standard": "JIS G3192", "b": b, "t": t,
                     "r1": r1, "r2": r2, "A_geom_cm2": round(A / 100, 3), "A_pdf_cm2": round(A / 100, 3),
                     "cx": round(cx, 2), "cy": round(cy, 2), "gauge": b / 2,
                     "profile": [[round(x, 3), round(y, 3)] for x, y in pts]}
    return LIB[name]


def banma_loops(msp, tol=0.05, ents=None):
    """Đường bao bản mã (lớp Banma): polyline kín giữ nguyên; các polyline hở nối đầu-cuối thành vòng kín."""
    closed, opens, pending = [], [], []
    src_ = list(ents if ents is not None else msp.query('LWPOLYLINE[layer=="Banma"]'))
    if ents is None and ST.CFG.get("banma_join_gap"):
        src_ += list(msp.query('LINE[layer=="Banma"]'))          # bản mã vẽ bằng nét LINE rời (DN-02)
    for e in src_:
        pts = [(q[0], q[1]) for q in e.get_points()] if e.dxftype() == "LWPOLYLINE" else \
            [(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])]
        if len(pts) < 2:
            continue
        if getattr(e, "closed", False) or math.dist(pts[0], pts[-1]) < tol:
            closed.append(pts[:-1] if math.dist(pts[0], pts[-1]) < tol and len(pts) > 3 else pts)
        else:
            opens.append(pts)
    # nét bao bị che một đoạn (thanh vẽ đè lên): nối các đoạn hở có đầu mút gần nhau (< 8 đơn vị = 200 mm)
    def join_close(chains, gap):
        out = list(chains)
        changed = True
        while changed:
            changed = False
            for i in range(len(out)):
                for j in range(i + 1, len(out)):
                    a_, b_ = out[i], out[j]
                    if math.dist(a_[0], a_[-1]) < tol or math.dist(b_[0], b_[-1]) < tol:
                        continue
                    opts = [(math.dist(a_[-1], b_[0]), a_ + b_), (math.dist(a_[-1], b_[-1]), a_ + b_[::-1]),
                            (math.dist(a_[0], b_[-1]), b_ + a_), (math.dist(a_[0], b_[0]), b_[::-1] + a_)]
                    d_, new = min(opts, key=lambda z: z[0])
                    if d_ < gap:
                        out[i] = new
                        out.pop(j)
                        changed = True
                        break
                if changed:
                    break
        return out
    while opens:
        ch = opens.pop()
        grown = True
        while grown and math.dist(ch[0], ch[-1]) >= tol:
            grown = False
            for i, o in enumerate(opens):
                if math.dist(ch[-1], o[0]) < tol:
                    ch = ch + o[1:]
                elif math.dist(ch[-1], o[-1]) < tol:
                    ch = ch + o[::-1][1:]
                elif math.dist(ch[0], o[-1]) < tol:
                    ch = o[:-1] + ch
                elif math.dist(ch[0], o[0]) < tol:
                    ch = o[::-1][:-1] + ch
                else:
                    continue
                opens.pop(i)
                grown = True
                break
        if math.dist(ch[0], ch[-1]) < tol and len(ch) > 3:
            closed.append(ch[:-1])
        else:
            pending.append(ch)
    if ST.CFG.get("banma_join_gap"):
        # nối cặp đầu nét GẦN NHẤT trước (bản mã bị thanh che một đoạn dài, VD nút 2-2 DN-02)
        pend = list(pending)
        while True:
            best_ = None
            for i in range(len(pend)):
                for j in range(i + 1, len(pend)):
                    a_, b_ = pend[i], pend[j]
                    for d_, mk in ((math.dist(a_[-1], b_[0]), lambda a_, b_: a_ + b_),
                                   (math.dist(a_[-1], b_[-1]), lambda a_, b_: a_ + b_[::-1]),
                                   (math.dist(a_[0], b_[-1]), lambda a_, b_: b_ + a_),
                                   (math.dist(a_[0], b_[0]), lambda a_, b_: b_[::-1] + a_)):
                        if d_ < ST.CFG["banma_join_gap"] and (best_ is None or d_ < best_[0]):
                            best_ = (d_, i, j, mk)
            if best_ is None:
                break
            _, i, j, mk = best_
            nw = mk(pend[i], pend[j])
            pend = [c for k, c in enumerate(pend) if k not in (i, j)] + [nw]
        # cạnh khép còn thiếu: nếu 2 cạnh kề đều vuông góc trục (ngang/đứng) thì khép bằng góc vuông như bản mã
        # cùng loại vẽ đủ (VD nút 1-1 DN-02), không kẻ chéo
        for k_, ch in enumerate(pend):
            if len(ch) >= 3 and math.dist(ch[0], ch[-1]) > 1.0:
                a0, a1, b0, b1 = ch[0], ch[1], ch[-2], ch[-1]
                hz = lambda p_, q_: abs(p_[1] - q_[1]) < 0.05
                vt = lambda p_, q_: abs(p_[0] - q_[0]) < 0.05
                if hz(b0, b1) and vt(a0, a1):
                    pend[k_] = ch + [(b1[0], a0[1])]
                elif vt(b0, b1) and hz(a0, a1):
                    pend[k_] = ch + [(a0[0], b1[1])]
        pending = pend
    for ch in join_close(pending, 8.0):
        if len(ch) >= 3:
            closed.append(ch)             # cạnh còn thiếu trùng nét thanh (VD cạnh áp thanh cánh): tự khép
    return closed


def area_centroid(A):
    A = np.asarray(A, float)
    x, y = A[:, 0], A[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y1 - x1 * y
    a = cr.sum() / 2
    if abs(a) < 1e-9:
        return A.mean(axis=0)
    return np.array([((x + x1) * cr).sum() / (6 * a), ((y + y1) * cr).sum() / (6 * a)])


def dist_to_poly(p, A):
    best = 1e18
    n = len(A)
    for i in range(n):
        a, b = A[i], A[(i + 1) % n]
        ab = b - a
        t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1)
        best = min(best, float(np.linalg.norm(p - (a + t * ab))))
    return best


def fit_detail(P, E, f, holes=None, bolts=None):
    """Đặt hình chi tiết P (đơn vị chi tiết, hệ số f sang đơn vị mặt đứng) lên đường bao E trên mặt đứng: thử xoay
    theo từng cặp cạnh (P, E) và lật gương; dời trọng tâm trùng nhau. Trả (sai lệch tb, hàm biến đổi, mô tả)."""
    Pa, Ea = np.array(P, float) * f, np.array(E, float)
    cP, cE = area_centroid(Pa), area_centroid(Ea)
    best = None
    holes_fn = None
    if holes and bolts:
        Ha = np.array(holes, float) * f
        Ba = np.array(bolts, float)

        def holes_fn(X, tr):
            cP_, mir_, R_, cX_, cE_ = tr
            Hx = ((Ha - cP_) * np.array([mir_, 1.0])) @ R_.T - cX_ + cE_
            return float(np.mean([np.min(np.linalg.norm(Ba - h, axis=1)) for h in Hx]))

    def edges(A):
        return [(A[(i + 1) % len(A)] - A[i]) for i in range(len(A))]
    angs_E = [math.atan2(v[1], v[0]) for v in edges(Ea) if np.linalg.norm(v) > 0.4]
    for mir in (1, -1):
        Q = (Pa - cP) * np.array([mir, 1.0])
        angs_P = [math.atan2(v[1], v[0]) for v in edges(Q) if np.linalg.norm(v) > 0.4]
        for aE in angs_E:
            for aP in angs_P:
                th = aE - aP
                R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
                X = Q @ R.T
                cX = area_centroid(X)
                X = X - cX + cE
                d1 = np.mean([dist_to_poly(e, X) for e in Ea])
                d2 = np.mean([dist_to_poly(x, Ea) for x in X])
                err = (d1 + d2) / 2
                if holes_fn is not None:
                    err = (err + holes_fn(X, (cP, mir, R, cX, cE))) / 2
                if best is None or err < best[0] - 1e-9:
                    best = (err, th, mir, cX)
    if best is None:
        return None
    err, th, mir, cX = best
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])

    def T(q):
        v = ((np.array(q, float) * f - cP) * np.array([mir, 1.0])) @ R.T - cX + cE
        return (float(v[0]), float(v[1]))
    return err, T, {"xoay_do": round(math.degrees(th) % 360, 1), "lat_guong": mir < 0}


def read_dxf_cached(path):
    """Đọc DXF; lưu bản đã phân tích (pickle) cạnh thư mục out/.cache theo kích thước + thời điểm sửa file,
    lần sau nạp lại nhanh hơn ~4 lần. Xoá out/.cache nếu nghi bộ nhớ đệm hỏng."""
    import hashlib
    import pickle
    st = Path(path).stat()
    key = hashlib.sha1(f"{Path(path).resolve()}|{st.st_size}|{st.st_mtime_ns}|{ezdxf.__version__}".encode()).hexdigest()[:16]
    cdir = ROOT / "out" / ".cache"
    cfile = cdir / f"dxf_{key}.pkl"
    if cfile.exists():
        try:
            return pickle.loads(cfile.read_bytes())
        except Exception:
            pass
    doc = ezdxf.readfile(path)
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        cfile.write_bytes(pickle.dumps(doc))
    except Exception:
        pass
    return doc


# ---------------------------------------------------------------- mặt đứng
def read_elevation(doc, msp):
    ms = R.members(doc, msp, ST.BOX)
    segs = R.segments(doc, msp, ST.BOX)
    # thanh cánh: thanh rộng gần đứng; DN-01: đoạn trên là L100x7 (nét lưng chung với HL130x9) -> thanh cánh vẽ
    # gộp có bề rộng 100..130, nhận cả thanh dài suốt chiều cao khung (CFG "leg_section")
    hbox = (ST.BOX[3] - ST.BOX[1])
    wide = [m for m in ms if 60 < m["ang"] < 120 and (m["width"] >= 120 or (
        ST.CFG.get("leg_section") and m["width"] >= 95 and abs(m["p2"][1] - m["p1"][1]) > 0.8 * hbox))]
    braces = [m for m in ms if m["width"] < 120 and not any(m is w_ for w_ in wide)]
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
    xmid_ = sum((x[1]["c1"][0] + x[1]["c2"][0]) / 2 for x in scored) / len(scored)
    isleft = lambda m: m["ang"] < 89.9 or (m["ang"] <= 90.1 and (m["c1"][0] + m["c2"][0]) / 2 < xmid_)
    left = max((x for x in scored if isleft(x[1])), key=lambda x: x[0])
    right = max((x for x in scored if not isleft(x[1])), key=lambda x: x[0])
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
            # chỉ nét LIỀN: nét đứt thẳng hàng phía trên/dưới là thanh cánh đoạn kề vẽ tham chiếu (DT-02 đỉnh:
            # thanh cánh DT-01 vẽ nét đứt) - không thuộc đoạn này
            if sg["k"] != "S" and not ST.CFG.get("leg_hidden_ok"):
                continue
            if all(dist_line(p, c1, c2) <= 170 / SC for p in (sg["a"], sg["b"])):
                ss += [(p[0] - c1[0]) * ux + (p[1] - c1[1]) * uy for p in (sg["a"], sg["b"])]
        a = (c1[0] + ux * min(ss), c1[1] + uy * min(ss))
        b = (c1[0] + ux * max(ss), c1[1] + uy * max(ss))
        legs.append({"m": m, "w1": c1, "w2": c2, "a": a, "b": b, "g": g, "n_wp": n_on})
    return ms, segs, braces, legs, wps
import state as ST  # noqa: E402
