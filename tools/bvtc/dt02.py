"""Dựng 3D đầy đủ đoạn thân cột N122 (DT-02, DT-01) từ bản vẽ chế tạo (BVTC) để người dùng soát.

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
# Cấu hình từng tờ bản vẽ (toạ độ DXF). Chân cột: sườn d12 (mm, gốc = góc dưới-trái hình chi tiết 1/10, đọc từ DXF)
SHEETS = {
    "DT-02": {
        "box": (-2380, -122110, -2040, -121674),       # mặt đứng (không lấy hình khai triển thanh cánh)
        "plans": {   # tên: (y vạch cắt trên mặt đứng, khung đọc mặt cắt)
            "1-1": (-121780.0, (-1980, -121766, -1880, -121680)),
            "2-2": (-121852.3, (-1980, -122063, -1812, -121905)),
            "3-3": (-121935.3, (-1980, -121880, -1867, -121785)),
            "4-4": (-122015.4, (-1875, -122170, -1805, -122092)),
        },
        "level_cut": {"1-1": 30, "2-2": 45, "3-3": 30, "4-4": 30},
        "foot_diag_cut": True,                         # ghi chú vát 40x60 đầu dưới thanh xiên chính (tờ DT-02)
        "top_splice": {"plate_t": 10},                 # bản mã nối d10 ở đỉnh (chi tiết + hình cắt A-A)
        "base": {
            "rib1": [(0, 100), (0, 0), (545, 0), (545, 350), (435, 490), (220, 490)],
            "rib2": [(0, 100), (0, 0), (157, 0), (192, 30), (260, 490), (220, 490)],
            "rib3": [(0, 30), (30, 0), (345, 0), (345, 350), (235, 490), (73, 490)],
            "rib1_h": [(265, 98), (277, 177), (289, 256), (300, 335), (312, 415), (315, 131), (327, 210), (339, 289),
                       (351, 368), (362, 448), (430, 213), (468, 272), (505, 331)],
            "rib3_h": [(71, 138), (83, 217), (95, 296), (106, 375), (110, 91), (118, 454), (122, 171), (133, 250),
                       (145, 329), (157, 408), (230, 213), (268, 272), (305, 331)],
            "diag_u": (430, 230), "heel": 3771.0, "L": {"leg": 70, "diag": 60},
            "labels": {"leg": "12.20_70", "diag": "3.20_60"},
        },
    },
    "DT-01": {
        "box": (-2357, -121515, -2133, -121060),
        "plans": {"1-1": (-121420.53, (-2020, -121345, -1828, -121170))},
        "level_cut": {"1-1": 25},
        # mặt cắt 1-1 ghi "trục uốn" cách góc 300, lệch 15: 2 nửa thanh ngang mặt cột bẻ lệch ra ngoài 15 mm để áp vừa
        # mặt trong bản mã giữa 312 (người dùng xác nhận); thứ tự: thanh xiên ngoài - bản mã - thanh xiên trong
        "center_joggle": {"offset": 15.0, "from_leg": 300.0, "ramp": 45.0, "straight": True},
        # người dùng chốt: bỏ bản đế, đoạn đặt lên DT-02 (bản mã chờ d10 + thép góc nối trong HL130x9 của DT-02)
        "on_top_of": {"sheet": "DT-02", "plate_t": 10},
        # bản mã nét khuất ở đỉnh = bản mã 301/302 d10 của đoạn ngọn DN-02 (DN-02 vẽ nét liền, ngoài cánh thanh
        # cánh, ghi d10), bẻ góc theo đường gãy thanh cánh
        "hidden_inner_plates": {"t": 10, "note": "bản mã 228/228a của DN-02 (DN-02 ghi d10), bẻ góc theo thanh cánh"},
        "top_kink": True,
        "base": {
            "rib1": [(0, 100), (0, 0), (515, 0), (515, 220), (435, 420), (200, 420)],
            "rib2": [(0, 100), (0, 0), (158, 0), (192, 30), (250, 420), (200, 420)],
            "rib3": [(0, 30), (26, 0), (311, 0), (311, 220), (231, 420), (58, 420)],
            "rib1_h": [(265, 98), (277, 177), (288, 256), (300, 335), (315, 131), (327, 210), (339, 289), (350, 368),
                       (428, 120), (476, 156)],
            "rib3_h": [(66, 137), (78, 217), (90, 296), (101, 375), (105, 91), (117, 170), (128, 250), (140, 329),
                       (224, 120), (272, 156)],
            "diag_u": (400, 200), "heel": None, "L": {"leg": 70, "diag": 60},
            "labels": {"leg": "8.20_70", "diag": "3.20_60"},
        },
    },
    # ĐOẠN NGỌN DN-02 (người dùng chốt 4 đề xuất): thẳng đứng, 2 kiểu mặt -> dựng 2 lần rồi ghép theo mặt
    #   DN-02  = mặt có xà (trước/sau, k = 0, 2): L90x7 dài 2840 + L60x5 chống; bỏ L70x6 nghiêng của xà (vẽ cụt)
    #   DN-02s = mặt bên (k = 1, 3)
    # z = 0 tại đường gãy thanh cánh (đầu dưới phần đứng DT-01). Thanh cánh DN-02 HL130x9 (232) từ khe B-B
    # (860 trên đường gãy) tới khe A-A (6240), HL130x9 (203) từ A-A tới đỉnh; dưới B-B là phần đứng DT-01
    # (HL150x12 - 301, chữ "HL130x12" ở hình B-B ghi nhầm), lưng thẳng hàng, đường tim cách lưng 80.
    "DN-02": {
        "box": (-2395, -120835, -2195, -120480),
        "plans": {"1-1": (-120567.9, (-1998, -120564, -1880, -120458)),
                  "2-2": (-120727.9, (-1998, -120694, -1880, -120588)),
                  "3-3": (-120787.9, (-1985, -120808, -1893, -120718))},
        "level_cut": {"3-3": 50},
        "no_base": True,
        "faces": [0, 2],
        "drop_rules": [{"sections": ["L70X6", None], "non_horizontal": True}],
        "bottom_stub": {"sheet": "DT-01", "joint_mm": 860.0, "gap": 10.0, "section": "HL150X12"},
        "leg_splices": [{"z": 6240.0, "gap": 10.0, "inner": "HL120X8", "inner_L": 730.0}],
        "waiting_holes": True,
        "detail_hole_max": 15.0,
        "banma_join_gap": 20.0,
        "trim_to_end_lines": True,
    },
}
SHEETS["DN-02s"] = dict(SHEETS["DN-02"], box=(-2190, -120835, -2045, -120480), faces=[1, 3])
SHEET = "DT-02"
CFG = SHEETS[SHEET]
BOX = CFG["box"]
PLANS = CFG["plans"]
TOL = 0.6                                        # đơn vị bản vẽ (15 mm) để coi là chạm
BASE_ZONE = 560.0                                # vùng chân cột (mm từ đáy thanh cánh) = chiều cao sườn + 70


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


def banma_loops(msp, tol=0.05, ents=None):
    """Đường bao bản mã (lớp Banma): polyline kín giữ nguyên; các polyline hở nối đầu-cuối thành vòng kín."""
    closed, opens, pending = [], [], []
    src_ = list(ents if ents is not None else msp.query('LWPOLYLINE[layer=="Banma"]'))
    if ents is None and CFG.get("banma_join_gap"):
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
    if CFG.get("banma_join_gap"):
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
                        if d_ < CFG["banma_join_gap"] and (best_ is None or d_ < best_[0]):
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
            # chỉ nét LIỀN: nét đứt thẳng hàng phía trên/dưới là thanh cánh đoạn kề vẽ tham chiếu (DT-02 đỉnh:
            # thanh cánh DT-01 vẽ nét đứt) - không thuộc đoạn này
            if sg["k"] != "S":
                continue
            if all(dist_line(p, c1, c2) <= 170 / SC for p in (sg["a"], sg["b"])):
                ss += [(p[0] - c1[0]) * ux + (p[1] - c1[1]) * uy for p in (sg["a"], sg["b"])]
        a = (c1[0] + ux * min(ss), c1[1] + uy * min(ss))
        b = (c1[0] + ux * max(ss), c1[1] + uy * max(ss))
        legs.append({"m": m, "w1": c1, "w2": c2, "a": a, "b": b, "g": g, "n_wp": n_on})
    return ms, segs, braces, legs, wps


def main(dxf, outdir):
    doc = read_dxf_cached(dxf)
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
        ytop_leg = max(Lg["a"][1], Lg["b"][1], Rg["a"][1], Rg["b"][1])
        above = (m["c1"][1] + m["c2"][1]) / 2 > ytop_leg - 0.5        # thanh của đoạn phía trên vẽ tham chiếu
        drop_ = any((m.get("section") in r_["sections"]) and (not r_.get("non_horizontal") or 3 < m["ang"] % 180 < 177)
                    for r_ in CFG.get("drop_rules", []))
        if CFG.get("bottom_stub") and max(m["c1"][1], m["c2"][1]) < min(Lg["a"][1], Lg["b"][1]) - 0.5:
            drop_ = True                                 # thanh của đoạn dưới vẽ tham chiếu
        if CFG.get("drop_rules") and not m["all_hidden"] and not drop_ and not inside:
            inside = m.get("section") is not None           # thanh chìa ra ngoài thân (xà): giữ nếu có nhãn
        if m["all_hidden"] or not inside or above or drop_:
            dropped.append(m)
            continue
        if not m.get("section"):
            freq = {}
            for t, _ in labs:
                freq[t] = freq.get(t, 0) + 1
            best = min(freq, key=lambda t: (abs(int(re.match(r"H?L(\d+)", t).group(1)) - m["width"]), -freq[t]))
            m["section"], m["section_from"] = best, "đoán theo bề rộng"
        keep.append(m)
    if CFG.get("trim_to_end_lines"):
        # nét đầu thanh (đoạn ngắn lớp COT vuông góc trục, dài ~ bề rộng thanh) nằm trong khoảng thanh: thanh dừng ở đó
        # (nét kích thước lớp 0 thẳng hàng mép thanh làm thanh bị đọc dài ra - VD L90x7 xà DN-02)
        x0b, y0b, x1b, y1b = BOX
        ends_ = [((e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])) for e in msp.query('LINE[layer=="COT"]')
                 if x0b <= e.dxf.start[0] <= x1b and y0b <= e.dxf.start[1] <= y1b]
        rep["ends_trimmed"] = []
        for m in keep:
            L = math.dist(m["c1"], m["c2"])
            u_ = ((m["c2"][0] - m["c1"][0]) / L, (m["c2"][1] - m["c1"][1]) / L)
            sof = lambda q: (q[0] - m["c1"][0]) * u_[0] + (q[1] - m["c1"][1]) * u_[1]
            s1, s2 = sorted((sof(m["b1"]), sof(m["b2"])))
            for a_, b_ in ends_:
                ln = math.dist(a_, b_)
                if not (0.6 * m["width"] / SC <= ln <= 1.4 * m["width"] / SC):
                    continue
                d_ = ((b_[0] - a_[0]) / ln, (b_[1] - a_[1]) / ln)
                if abs(d_[0] * u_[0] + d_[1] * u_[1]) > 0.05:
                    continue
                mid_ = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
                if dist_line(mid_, m["c1"], m["c2"]) * SC > 0.7 * m["width"]:
                    continue
                sm = sof(mid_)
                if s1 + 1.0 < sm < s1 + 0.45 * (s2 - s1) and (sm - s1) * SC > 100:
                    rep["ends_trimmed"].append({"section": m.get("section"), "mm": round((sm - s1) * SC)})
                    s1 = sm
                elif s2 - 0.45 * (s2 - s1) < sm < s2 - 1.0 and (s2 - sm) * SC > 100:
                    rep["ends_trimmed"].append({"section": m.get("section"), "mm": round((s2 - sm) * SC)})
                    s2 = sm
            P_ = lambda t: (m["c1"][0] + u_[0] * t, m["c1"][1] + u_[1] * t)
            if sof(m["b1"]) <= sof(m["b2"]):
                m["b1"], m["b2"] = P_(s1), P_(s2)
            else:
                m["b1"], m["b2"] = P_(s2), P_(s1)
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
    for pts in banma_loops(msp):
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
        plates2d.append({"pts": pts, "pts0": pts, "t": t_mm, "nodes": inside_nodes})

    # --- bản mã vẽ NÉT KHUẤT (lớp COT) tại nút thanh cánh đầu trên DT-01 (nối đoạn trên): dựng như bản mã nút
    #     thanh cánh (áp mặt ngoài cánh). Dày không ghi: suy từ tấm đệm (khe giao chữ X = 2 x 10; đệm D ở thanh
    #     trong khớp với bản mã ngoài), xem CFG.
    hip = CFG.get("hidden_inner_plates")
    if hip:
        ents = [e for e in msp.query('LWPOLYLINE[layer=="COT"]') if R.linetype(doc, e) == "H"
                and all(inb((q[0], q[1])) for q in e.get_points())]
        for pts in banma_loops(msp, ents=ents):
            xs_, ys_ = [q[0] for q in pts], [q[1] for q in pts]
            if (max(xs_) - min(xs_)) * SC < 150 or (max(ys_) - min(ys_)) * SC < 150:
                continue
            if not any(dist_line(q, L_["w1"], L_["w2"]) < 6 for q in pts for L_ in legs):
                continue
            if min(ys_) < min(Lg["a"][1], Lg["b"][1]) + BASE_ZONE / SC:
                continue                          # sườn chân cột vẽ nét khuất: đã dựng theo chi tiết sườn
            inside_nodes = [n for n in nodes if point_in_poly(n, pts)]
            cxy_ = (sum(xs_) / len(xs_), sum(ys_) / len(ys_))
            plates2d.append({"pts": pts, "pts0": pts, "t": hip["t"], "nodes": inside_nodes or [cxy_],
                             "hidden": True, "note": hip.get("note", "")})
            rep.setdefault("inner_plates", []).append({"size_mm": [round((max(xs_) - min(xs_)) * SC),
                                                                   round((max(ys_) - min(ys_)) * SC)], "t": hip["t"]})

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
            if re.fullmatch(r"\d{3}a?", t.dxf.text.strip())]
    thk_all = [(int(t.dxf.text.split()[-1]), (t.dxf.insert[0], t.dxf.insert[1])) for t in msp.query("TEXT")
               if re.fullmatch(r"d\s*\d+", t.dxf.text.strip())]
    banma = banma_loops(msp)
    bolt_ins = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name])
                for e in msp.query("INSERT") if e.dxf.name in ("1", "2", "3")]

    def in_any_elev(P):
        # hình nằm trong khung mặt đứng của một tờ khác (VD mặt bên DN-02s): không phải hình chi tiết
        return any(all(b_[0] <= q[0] <= b_[2] and b_[1] <= q[1] <= b_[3] for q in P)
                   for nm_, c_ in SHEETS.items() for b_ in [c_["box"]] if nm_ != SHEET)

    def detail_of(label, exclude):
        best = None
        for tx, p in nums:
            if tx != label:
                continue
            for P in banma:
                if in_any_elev(P):
                    continue
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
        # chọn chi tiết + phép đặt (xoay, lật) khớp đường bao bản mã trên mặt đứng nhất
        fits = []
        bolts_here = [q for q, _ in bolt_ins if point_in_poly(q, pl["pts"])]
        for c_ in cands:
            hs_ = [q for q, _ in bolt_ins if point_in_poly(q, c_[2])]
            fit_ = fit_detail(c_[2], pl["pts"], 10.0 / SC, hs_, bolts_here)
            if fit_:
                fits.append((fit_[0], c_, fit_))
        if not fits:
            continue
        err, main_, (err, Tf, desc) = min(fits, key=lambda z: z[0])
        if err * SC > 30:
            rep["warnings"].append(f"bản mã {main_[0]}: chi tiết không khớp đường bao mặt đứng (lệch {err * SC:.0f} mm)")
            continue
        tx, p, P, _ = main_
        db = bbox(P)
        # tinh chỉnh: lỗ chi tiết phải trùng bu lông vẽ trên mặt đứng (bu lông nằm đúng đường đinh thanh) ->
        # khớp cứng (xoay + dời, giữ lật) các cặp lỗ - bu lông gần nhau, lặp vài lần
        hs0 = [q for q, _ in bolt_ins if point_in_poly(q, P)]
        if hs0 and bolts_here:
            Tc = Tf
            for _ in range(4):
                A_ = np.array([Tc(q) for q in hs0])
                Bh = np.array(bolts_here)
                idx = [int(np.argmin(np.linalg.norm(Bh - a_, axis=1))) for a_ in A_]
                ok_ = [i for i, j in enumerate(idx) if np.linalg.norm(Bh[j] - A_[i]) * SC < 60]
                if len(ok_) < 2:
                    break
                Aa, Bb = A_[ok_], Bh[[idx[i] for i in ok_]]
                ca, cb = Aa.mean(0), Bb.mean(0)
                Hm = (Aa - ca).T @ (Bb - cb)
                th_ = math.atan2(Hm[0, 1] - Hm[1, 0], Hm[0, 0] + Hm[1, 1])
                Rr = np.array([[math.cos(th_), -math.sin(th_)], [math.sin(th_), math.cos(th_)]])
                Tc = (lambda T0, Rr, ca, cb: (lambda q: tuple(Rr @ (np.array(T0(q)) - ca) + cb)))(Tc, Rr, ca, cb)
            A_ = np.array([Tc(q) for q in hs0])
            res_ = [float(np.min(np.linalg.norm(np.array(bolts_here) - a_, axis=1))) * SC for a_ in A_]
            pl["hole_fit_mm"] = round(max(res_), 1)
            hm_ = CFG.get("detail_hole_max")
            if hm_:
                # lỗ chi tiết không có bu lông vẽ trên mặt đứng (lỗ chờ / lỗ thừa): giữ hình, không đặt bu lông
                pl["holes_skip"] = [q for q, r_ in zip(hs0, res_) if r_ > hm_]
                pl["hole_fit_mm"] = round(max([r_ for r_ in res_ if r_ <= hm_] or [0.0]), 1)
            if hm_ and sum(r_ <= hm_ for r_ in res_) < 0.75 * len(res_):
                rep["warnings"].append(f"bản mã {tx}: lỗ chi tiết lệch bu lông vẽ {max(res_):.0f} mm -> dùng hình mặt đứng")
                continue
            Tf = Tc
        pl["pts"] = [Tf(q) for q in P]
        pl["holes"] = [(Tf(q), d_) for q, d_ in bolt_ins if point_in_poly(q, P) and q not in pl.get("holes_skip", [])]
        pl["fit"] = {"lech_mm": round(err * SC, 1), "dat": desc}
        pl["t"] = min(thk_all, key=lambda t_: math.dist(t_[1], p))[0]
        pl["mark"] = tx
        info = {"mark": tx, "size_mm": [round((db[2] - db[0]) * 10), round((db[3] - db[1]) * 10)], "t": pl["t"],
                "holes": len(pl["holes"]), **pl["fit"], "lo_lech_bu_long_ve_max_mm": pl.get("hole_fit_mm")}
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

    # đỉnh đoạn uốn thẳng đứng: đường gãy KY (đầu trên phần nghiêng), đầu trên phần đứng KTOP (nét liền thẳng đứng
    # ở lưng thanh cánh); phía trên KY đường tim thanh cánh thẳng đứng
    KY = max(Lg["a"][1], Lg["b"][1])
    KTOP = None
    if CFG.get("top_kink"):
        xb_ = xline(Lg, KY) - Lg["g"] / SC
        tops_ = [max(sg["a"][1], sg["b"][1]) for sg in segs if sg["k"] == "S"
                 and abs(math.degrees(sg["ang"]) - 90) < 0.5 and min(sg["a"][1], sg["b"][1]) >= KY - 0.3
                 and abs((sg["a"][0] + sg["b"][0]) / 2 - xb_) < 0.3]
        KTOP = max(tops_) if tops_ else None

    # --- đoạn đặt trên đoạn khác (DT-01 trên DT-02, người dùng chốt: bỏ bản đế, ráp vào bản mã chờ của DT-02):
    #     lấy bản mã nối d10 vẽ ở đỉnh tờ đoạn dưới, dời sang tờ này sao cho lỗ chờ trùng bu lông chân thanh cánh +
    #     đầu dưới thanh xiên vẽ trên tờ này (khớp theo lỗ, mỗi bên một phép dời)
    ONTOP = CFG.get("on_top_of")
    if ONTOP:
        bx2 = SHEETS[ONTOP["sheet"]]["box"]
        inb2 = lambda p: bx2[0] <= p[0] <= bx2[2] and bx2[1] <= p[1] <= bx2[3]
        ytop2 = bx2[3]
        y_leg0 = min(Lg["a"][1], Lg["b"][1])
        B1 = [q for q, _ in bolt_ins if inb(q) and (q[1] - y_leg0) * SC < 900]
        rep["joint"] = []
        for P in banma:
            if not all(inb2(q) for q in P) or max(q[1] for q in P) < ytop2 - 80:
                continue
            ysz = (max(q[1] for q in P) - min(q[1] for q in P)) * SC
            if ysz < 500:
                continue
            B2 = [q for q, _ in bolt_ins if point_in_poly(q, P)]
            ymid2 = (max(q[1] for q in P) + min(q[1] for q in P)) / 2
            up2 = [q for q in B2 if q[1] > ymid2]
            if not up2 or not B1:
                continue
            # dời ban đầu: tâm nhóm lỗ trên (thuộc đoạn này) -> tâm bu lông cùng phía thanh cánh trên tờ này
            sideL = np.mean([q[0] for q in up2]) < (bx2[0] + bx2[2]) / 2
            B1s = np.array([q for q in B1 if (q[0] < xc) == sideL])
            if not len(B1s):
                continue
            U2 = np.array(up2)
            # phép dời khớp nhiều lỗ nhất (thử mọi cặp lỗ chờ - bu lông), rồi tinh chỉnh trung bình
            best_ = None
            for a_ in U2:
                for b_ in B1s:
                    t_ = b_ - a_
                    nmatch = sum(1 for q in U2 + t_ if np.min(np.linalg.norm(B1s - q, axis=1)) * SC < 12)
                    if best_ is None or nmatch > best_[0]:
                        best_ = (nmatch, t_)
            tr = best_[1]
            for _ in range(6):
                A_ = U2 + tr
                idx = [int(np.argmin(np.linalg.norm(B1s - a_, axis=1))) for a_ in A_]
                ok_ = [i for i, j in enumerate(idx) if np.linalg.norm(B1s[j] - A_[i]) * SC < 15]
                if not ok_:
                    break
                tr = tr + np.mean([B1s[idx[i]] - A_[i] for i in ok_], axis=0)
            A_ = U2 + tr
            res_ = [float(np.min(np.linalg.norm(B1s - a_, axis=1))) * SC for a_ in A_]
            pts_ = [(q[0] + tr[0], q[1] + tr[1]) for q in P]
            cxy_ = (sum(q[0] for q in pts_) / len(pts_), sum(q[1] for q in pts_) / len(pts_))
            plates2d.append({"pts": pts_, "pts0": pts_, "t": ONTOP["plate_t"], "nodes": [cxy_], "ext": ONTOP["sheet"],
                             "splice": True})
            rep["joint"].append({"ben": "trái" if sideL else "phải", "doi_mm": [round(tr[0] * SC, 1), round(tr[1] * SC, 1)],
                                 "lo_khop": len(ok_), "lech_lo_max_mm": round(max(res_), 1)})
    # đoạn dưới cùng có bản mã nối thanh cánh ở đỉnh (bản mã chờ đoạn trên): dày theo chi tiết, đánh dấu mối nối
    TS = CFG.get("top_splice")
    if TS:
        ytop_leg_ = max(Lg["a"][1], Lg["b"][1])
        for pl in plates2d:
            ys_ = [q[1] for q in pl["pts"]]
            if min(ys_) < ytop_leg_ < max(ys_):
                pl["t"], pl["splice"] = TS["plate_t"], True

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
            # chỉ tách khi bản mã có bản hàn vuông góc chắn giữa (DT-02: 419); thanh TRONG chạy sau bản mã ngoài
            # cũng bị ngắt nét nhưng vẫn liền (DT-01 nút giữa 1-1)
            if not any(point_in_poly(pm_, pl["pts"]) and "strip" in pl for pl in plates2d):
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
            if point_in_poly(p, pl["pts"]) or point_in_poly(p, pl["pts0"]) or \
                    any(math.dist(p, n) < TOL for n in pl["nodes"]):
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
    # đoạn đặt trên phần đứng của đoạn dưới (DN-02 trên DT-01): dưới khe B-B là HL150x12 của DT-01, mặt trong
    # thẳng mặt trong HL130x9 -> lưng lồi ra STUB_OUT = 12 - 9 = 3 mm (bù bằng tấm d3 dưới bản nối ngoài)
    BSTUB = CFG.get("bottom_stub")
    STUB_OUT = (sec(BSTUB["section"])["t"] - tl) if BSTUB else 0.0
    for pl in plates2d:                       # bản mã áp mặt ngoài cánh thanh cánh (A-A) nếu nằm trên thanh cánh
        on_leg_ = any(dist_line(n, L_["w1"], L_["w2"]) < 3.0 for n in pl["nodes"] for L_ in legs)
        pl["delta0"] = gl if on_leg_ else None
        pl["on_leg_fixed"] = on_leg_
        if pl.get("hidden"):
            pl["delta0"], pl["on_leg_fixed"] = gl, True       # như bản mã nút thanh cánh: áp mặt ngoài cánh
        if BSTUB and on_leg_:
            zc_ = zf(sum(q[1] for q in pl["pts"]) / len(pl["pts"]))
            zlo_ = min(zf(q[1]) for q in pl["pts"])
            if zlo_ < BSTUB["joint_mm"]:
                # bản mã trên phần đứng DT-01 / bản nối B-B: áp lưng HL150x12 (lưng lồi ra 3 mm so với HL130x9 vì
                # 2 thanh cánh thẳng mặt trong) hoặc tấm d3
                pl["delta0"] = gl + STUB_OUT
            for sp_ in [dict(z=BSTUB["joint_mm"], L=670.0, t=10)] + [dict(z=x_["z"], L=x_.get("plate_L", 690.0), t=10)
                                                                     for x_ in CFG.get("leg_splices", [])]:
                if abs(zc_ - sp_["z"]) < 120 and (max(zf(q[1]) for q in pl["pts"]) - zlo_) > sp_["L"] - 60:
                    pl["t"], pl["leg_splice"] = sp_["t"], sp_["z"]
            if zlo_ < -1.0:
                # bản mã qua đường gãy (228/228a): phần dưới nằm trong mặt nghiêng DT-01 -> đoạn dưới dựng cả tấm bẻ góc;
                # ở đây chỉ giữ phần đứng (đánh dấu "ext" để mô hình ghép bỏ, dùng tấm của đoạn dưới)
                yk_ = min(Lg["a"][1], Lg["b"][1])
                P_, out_ = pl["pts"], []
                for i_ in range(len(P_)):
                    a_, b_ = P_[i_], P_[(i_ + 1) % len(P_)]
                    if a_[1] >= yk_:
                        out_.append(a_)
                    if (a_[1] >= yk_) != (b_[1] >= yk_):
                        t_ = (yk_ - a_[1]) / (b_[1] - a_[1])
                        out_.append((a_[0] + t_ * (b_[0] - a_[0]), yk_))
                pl["pts"], pl["ext"] = out_, BSTUB["sheet"]
    if BSTUB:
        # tấm d3 (231, 145x330, chi tiết DN-02) dưới bản nối ngoài B-B, trên lưng HL130x9 (bù 3 mm), từ lưng ra
        jb = BSTUB["joint_mm"]
        yz = lambda zmm: min(Lg["a"][1], Lg["b"][1]) + zmm / SC
        for L_ in legs:
            sgn = 1 if L_ is Lg else -1
            xb0 = lambda y_: xline(L_, y_) - sgn * L_["g"] / SC
            y0_, y1_ = yz(jb + BSTUB["gap"] / 2), yz(jb + BSTUB["gap"] / 2 + 330.0)
            pts_ = [(xb0(y0_), y0_), (xb0(y0_) + sgn * 145 / SC, y0_), (xb0(y1_) + sgn * 145 / SC, y1_), (xb0(y1_), y1_)]
            plates2d.append({"pts": pts_, "pts0": pts_, "t": STUB_OUT, "nodes": [], "delta0": gl, "on_leg_fixed": True,
                             "note": "tấm d3 (231) bù chiều dày, dưới bản nối ngoài B-B", "hidden": True, "d3": True})
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

    # bu lông vẽ (vị trí) để biết đầu thanh có bắt qua cánh thanh cánh không
    bpos_d = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name]) for e in msp.query("INSERT")
              if e.dxf.name in ("1", "2", "3") and inb(e.dxf.insert)]
    bpos = [q for q, _ in bpos_d]

    def on_leg_fp(q):
        for L_ in legs:
            ylo, yhi = sorted((L_["a"][1], L_["b"][1]))
            yhi = max(yhi, KTOP or yhi)
            if ylo <= q[1] <= yhi:
                sgn = 1 if L_ is Lg else -1
                off = (q[0] - xline(L_, min(q[1], KY) if KTOP else q[1])) * SC * sgn
                if -L_["g"] + 5 <= off <= sec(L_["section"])["b"] - L_["g"] - 5:
                    return True
        return False

    def bolt_on_leg_at_end(m, k):
        """Đầu k của thanh có bu lông (trên đường đinh thanh) xuyên qua cánh thanh cánh."""
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        for q in bpos:
            sq = (q[0] - c1[0]) * u_[0] + (q[1] - c1[1]) * u_[1]
            o = ((q[0] - c1[0]) * m["nvec"][0] + (q[1] - c1[1]) * m["nvec"][1]) * SC
            if abs(o) > 8 or not (-0.4 <= sq <= L + 0.4):
                continue
            if (sq < L / 2) == (k == 0) and on_leg_fp(q):
                return True
        return False

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
                in_base = (pk[1] - min(Lg["a"][1], Lg["b"][1])) * SC < BASE_ZONE and \
                    any(dist_line(pk, L_["w1"], L_["w2"]) < 12 for L_ in legs)
                if in_base and not ONTOP:
                    # chân cột: đầu thanh ép sát sườn d12 (sườn nằm ngoài lưng cánh thanh cánh, mặt trong δ = g)
                    lo, hi = gl, gl + 12
                elif pl is not None and pl.get("inner"):
                    # bản mã nằm sau cánh thanh cánh: thanh TRONG áp mặt trong bản mã, thanh NGOÀI áp mặt ngoài cánh
                    lo, hi = (pl["delta0"], pl["delta0"] + pl["t"]) if not m["out"] else (gl - tl, gl)
                elif pl is not None and pl["delta0"] is not None and pl.get("on_leg_fixed") and not m["out"] \
                        and bolt_on_leg_at_end(m, k):
                    # thanh TRONG có bu lông bắt qua cánh thanh cánh: ốp mặt trong thanh cánh; phần ngoài mép thanh
                    # cánh cách bản mã = dày cánh thanh cánh -> chèn tấm đệm (ký hiệu D)
                    lo, hi = gl - tl, gl
                elif pl is not None and pl["delta0"] is not None:
                    lo, hi = pl["delta0"], pl["delta0"] + pl["t"]
                elif kind == "leg":
                    lo, hi = gl - tl, gl + (STUB_OUT if BSTUB and zf(pk[1]) < BSTUB["joint_mm"] else 0)
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

    # --- nút giữa có thanh ngang bẻ lệch (DT-01): bản mã giữa áp lưng thanh ngang đã bẻ; thanh xiên trong ép sát
    #     mặt trong bản mã, thanh xiên ngoài ép sát mặt ngoài bản mã (thêm 1 điểm độ sâu giữa thanh)
    cj = CFG.get("center_joggle")
    rep["center_joggle"] = []
    for pl in [p_ for p_ in plates2d if not p_.get("on_leg_fixed")] if cj else []:
        halves = [m for m in keep if (m["ang"] % 180 < 3 or m["ang"] % 180 > 177) and pl in m["plate"]]
        if not halves:
            continue
        leg_d = min(m["delta"][1 - m["plate"].index(pl)] for m in halves)
        d_in = leg_d + cj["offset"]
        pl["delta0"] = d_in
        cen = pl["nodes"][0]
        for m in halves:
            kp = m["plate"].index(pl)
            m["delta"][kp] = d_in
            c1, c2 = m["c1"], m["c2"]
            L = math.dist(c1, c2)
            s_leg = 0.0 if kp == 1 else L * SC                    # đầu thanh cánh (mm theo trục từ c1)
            sgn = 1 if kp == 1 else -1
            s_k = s_leg + sgn * cj["from_leg"]
            if cj.get("straight"):
                # người dùng chốt: không nhấn cục bộ; thanh thẳng nối 2 đầu (đầu thanh cánh áp mặt trong cánh,
                # đầu giữa áp mặt trong bản mã) = uốn/ép đều theo chiều dài
                m["dprof"] = []
                L_mm = L * SC
                rep["center_joggle"].append({"section": m["section"], "leg_mm": leg_d, "giua_mm": d_in,
                                             "cach": "thanh thẳng, lệch %g mm trải đều trên %d mm (%.2f độ)" % (
                                                 cj["offset"], round(L_mm), math.degrees(math.atan2(cj["offset"], L_mm)))})
            else:
                m["dprof"] = sorted([(s_k, leg_d), (s_k + sgn * cj["ramp"], d_in)])
                rep["center_joggle"].append({"section": m["section"], "leg_mm": leg_d, "giua_mm": d_in,
                                             "truc_uon_cach_tim_thanh_canh_mm": cj["from_leg"]})
        for m in keep:
            if m in halves or pl in m["plate"]:
                continue
            d_, t = dist_seg(cen, m["c1"], m["c2"])
            if d_ < 1.0 and 0.05 < t < 0.95:
                sc_ = t * math.dist(m["c1"], m["c2"]) * SC
                m["dprof"] = [(sc_, d_in + pl["t"] if m["out"] else d_in)]
                rep["center_joggle"].append({"section": m["section"], "side": "NGOAI" if m["out"] else "TRONG",
                                             "ep_sat_ban_ma_mm": m["dprof"][0][1]})

    def delta_s(m, smm):
        """Độ sâu lưng thanh tại vị trí smm (mm dọc trục từ c1): nội suy theo 2 đầu thanh thật + điểm bẻ."""
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        s1_ = ((m["b1"][0] - c1[0]) * u_[0] + (m["b1"][1] - c1[1]) * u_[1]) * SC
        s2_ = ((m["b2"][0] - c1[0]) * u_[0] + (m["b2"][1] - c1[1]) * u_[1]) * SC
        pts_ = sorted([(s1_, m["delta"][0]), (s2_, m["delta"][1])] + list(m.get("dprof", [])))
        xs_, ds_ = [p_[0] for p_ in pts_], [p_[1] for p_ in pts_]
        return float(np.interp(smm, xs_, ds_))

    # --- vát cánh theo ghi chú bản vẽ (mặt đứng: 40x60 đầu dưới thanh xiên chính bắt sườn chân cột;
    #     45x45 đầu 4 thanh xiên tại bản mã giữa). Vát trên cánh liên kết (thấy trên mặt đứng).
    base_y0 = min(Lg["a"][1], Lg["b"][1])
    for m in keep:
        for k in (0, 1):
            p_ = pt_k(m, k)
            kind_, _h = m["host"][k]
            near_leg = any(dist_line(p_, L_["w1"], L_["w2"]) < 12 for L_ in legs)
            if CFG.get("foot_diag_cut") and near_leg and (p_[1] - base_y0) * SC < BASE_ZONE:
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
    level_cut = CFG["level_cut"]
    for pname, (ymark, _box) in PLANS.items():
        for m in keep:
            ang = m["ang"] % 180
            if (ang < 3 or ang > 177) and abs(m["c1"][1] - ymark) < 12 and level_cut.get(pname):
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
        if TS and q[1] > max(Lg["a"][1], Lg["b"][1]) + 0.2:
            continue                                   # lỗ chờ trên thanh cánh đoạn trên: bu lông thuộc lúc ráp
        if not ONTOP and (q[1] - base_y) * SC < BASE_ZONE and \
                any(dist_line(q, L_["w1"], L_["w2"]) < 16 for L_ in legs):
            continue                                   # chân cột: lấy đúng theo lỗ trên chi tiết sườn
        if any("holes" in pl and point_in_poly(q, pl["pts"]) for pl in plates2d):
            continue                                   # bản mã có hình chi tiết: lấy lỗ theo chi tiết
        if not any(point_in_poly(q, pl["pts"]) for pl in plates2d) and \
                any(point_in_poly(q, P) for P in banma if P not in [pl["pts"] for pl in plates2d]):
            continue                                   # lỗ trên hình chi tiết vẽ riêng
        bolts2d.append({"p": q, "d": {"1": 16, "2": 20, "3": 24}[e.dxf.name], "src": "mặt đứng"})
    for pl in plates2d:
        for q, d_ in pl.get("holes", []):
            if CFG.get("detail_hole_max"):
                # tim bu lông lấy đúng vị trí vẽ trên mặt đứng (trên đường đinh thanh) khi lỗ chi tiết lệch ít
                nb_ = min(bolt_ins, key=lambda b_: math.dist(b_[0], q), default=None)
                if nb_ and math.dist(nb_[0], q) * SC < 20:
                    q = nb_[0]
            bolts2d.append({"p": q, "d": d_, "src": "chi tiết bản mã " + pl.get("mark", "")})
    # khối bu lông vẽ chồng nhau (cùng tim, khác ký hiệu M20/M24): giữ 1, lấy đường kính lớn hơn
    ded_ = []
    for bb in bolts2d:                                   # giữ thứ tự; trùng tim thì giữ con đường kính lớn
        j_ = next((i for i, o in enumerate(ded_) if math.dist(bb["p"], o["p"]) * SC < 3), None)
        if j_ is None:
            ded_.append(bb)
        elif bb["d"] > ded_[j_]["d"]:
            ded_[j_] = bb
    rep["bolts_duplicate_removed"] = len(bolts2d) - len(ded_)
    bolts2d[:] = ded_

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

        def crossing_bolt_at_end(q):
            # bu lông tại đầu thanh (nút) mà thanh khác chạy QUA -> bu lông giao chữ X, không thuộc thanh này
            # (bu lông giao của >= 2 thanh khác cùng chạy qua; nút chỉ 1 thanh chạy qua thì bu lông vẫn của thanh này)
            if min(math.dist(q, c1), math.dist(q, c2)) > 1.0:
                return False
            n_ = 0
            for o in keep:
                if o is m:
                    continue
                d_, t_ = dist_seg(q, o["c1"], o["c2"])
                if d_ * SC < 8 and 0.05 < t_ < 0.95:
                    n_ += 1
            return n_ >= 2
        # vị trí bu lông vẽ trên mặt đứng (lỗ theo chi tiết bản mã có thể lệch vài mm so với đường đinh)
        bl_ = [(b["p"], b["d"]) for b in bolts2d] + bpos_d
        on = [(sof(bp_), bd_) for bp_, bd_ in bl_ if in_flange(m, bp_) and not crossing_bolt_at_end(bp_) and
              min(abs(((bp_[0] - c1[0]) * m["nvec"][0] + (bp_[1] - c1[1]) * m["nvec"][1]) * SC - o_)
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
            d_ = delta_s(m, sq * SC)
            rng = (d_, d_ + m["t_mm"]) if m["out"] else (d_ - m["t_mm"], d_)
            lay.append((rng[0], rng[1], m["section"] + (" NGOAI" if m["out"] else " TRONG")))
        for pl in plates2d:
            # bu lông sát mép bản mã (nét bao vẽ qua tim lỗ / lệch vài mm): vẫn xuyên bản mã
            if point_in_poly(q, pl["pts"]) or (BSTUB and dist_to_poly(q, np.array(pl["pts"])) * SC < 8):
                lay.append((pl["delta0"], pl["delta0"] + pl["t"], "bản mã d%d" % pl["t"]))
        if BSTUB:
            # thanh cánh theo cao độ: phần đứng DT-01 (HL150x12) dưới khe B-B, HL130x9 trên; mối nối B-B / A-A
            on_flange = False
            for L_ in legs:
                sgn = 1 if L_ is Lg else -1
                off = (q[0] - xline(L_, q[1])) * SC * sgn
                if -L_["g"] + 5 <= off <= sec(L_["section"])["b"] - L_["g"] - 5:
                    on_flange = True
            zq = zf(q[1])
            if on_flange and zq >= 0:
                jb, gb = BSTUB["joint_mm"], BSTUB["gap"] / 2
                if zq < jb - gb:
                    lay.append((gl - tl, gl - tl + sec(BSTUB["section"])["t"], BSTUB["section"] + " (" + BSTUB["sheet"] + ")"))
                elif zq > jb + gb:
                    lay.append((gl - tl, gl, Lg["section"]))
                if abs(zq - jb) < 335:
                    lay.append((gl - tl - 9, gl - tl, "HL130X9 nối trong B-B"))
                for sp_ in CFG.get("leg_splices", []):
                    ti_ = sec(sp_["inner"])["t"]
                    if abs(zq - sp_["z"]) < sp_["inner_L"] / 2:
                        lay.append((gl - tl - ti_, gl - tl, sp_["inner"] + " nối trong"))
            return lay
        for L_ in legs:
            ylo, yhi = sorted((L_["a"][1], L_["b"][1]))
            yhi = max(yhi, KTOP or yhi)
            if not (ylo <= q[1] <= yhi):
                continue
            # cánh thanh cánh trên mặt: từ lưng (cách đường tim g, phía ngoài) tới mép (150 - g, phía trong)
            sgn = 1 if L_ is Lg else -1                      # phía trong mặt = +x với thanh cánh trái
            off = (q[0] - xline(L_, min(q[1], KY) if KTOP else q[1])) * SC * sgn
            if -L_["g"] + 5 <= off <= sec(L_["section"])["b"] - L_["g"] - 5:
                lay.append((gl - tl, gl, L_["section"]))
        if any(n_.startswith(Lg["section"]) for _, _, n_ in lay) and \
                any(pl.get("splice") and point_in_poly(q, pl["pts"]) for pl in plates2d):
            lay.append((gl - tl - 9, gl - tl, "HL130X9 nối trong"))
        elif CFG.get("top_kink") and q[1] > max(Lg["a"][1], Lg["b"][1]) + 1e-6:
            pass                                       # phần uốn thẳng đứng: lỗ chờ nối thanh cánh đoạn trên
        elif lay and all(n_.startswith(Lg["section"]) for _, _, n_ in lay):
            # mối nối thanh cánh: thép góc nối trong HL130x9 + bản nối ngoài d10 (hình cắt A-A)
            lay += [(gl - tl - 9, gl - tl, "HL130X9 nối trong"), (gl, gl + 10, "bản nối ngoài d10")]
        return lay

    # --- tấm đệm (khối "D" = vòng nét đứt quanh bu lông; ký hiệu "nD.F_T" = n tấm, bu lông F, dày T):
    #     số tấm mỗi vị trí = n / số khối D cùng ký hiệu (nút thanh cánh: 2 vị trí x 1 tấm; giao chữ X: 1 vị trí
    #     x 2 tấm chồng nhau - người dùng xác nhận). Tấm đệm đặt áp lớp thép phía ngoài của khe.
    dlabs = []
    for t_ in msp.query("TEXT"):
        mt = re.fullmatch(r"(\d*)D\.(\d+)_(\d+)", t_.dxf.text.strip())
        if mt and inb(t_.dxf.insert):
            dlabs.append({"n": int(mt.group(1) or 1), "d": int(mt.group(2)), "t": float(mt.group(3)),
                          "p": (t_.dxf.insert[0], t_.dxf.insert[1]), "syms": []})
    dsyms = []
    for e in msp.query('INSERT[name=="D"]'):
        if inb(e.dxf.insert):
            r_ = next((c.dxf.radius for c in doc.blocks.get("D") if c.dxftype() == "CIRCLE"), 0.88) * e.dxf.xscale
            sym = {"p": (e.dxf.insert[0], e.dxf.insert[1]), "r_mm": r_ * SC}
            if dlabs:
                lab = min(dlabs, key=lambda L_: math.dist(L_["p"], sym["p"]))
                if math.dist(lab["p"], sym["p"]) < 25:
                    lab["syms"].append(sym)
                    sym["lab"] = lab
            dsyms.append(sym)
    # khối D không có ký hiệu số lượng/chiều dày gần đó: lấy 1 tấm dày 10 (như nút thanh cánh) - báo lại
    for sym in dsyms:
        if "lab" not in sym:
            sym["lab"] = {"n": 1, "d": 20, "t": float(CFG.get("filler_default_t", 10)), "p": sym["p"],
                          "syms": [sym], "assumed": True}
    fillers2d = []
    rep["fillers"] = []

    rep["bolt_gaps"] = []
    rep["bolts_dropped"] = 0
    keepb2 = []
    rep["holes_waiting"] = []
    for bb in bolts2d:
        lay = layers_at(bb["p"])
        # lỗ chờ cho đoạn phía trên (đỉnh đoạn có phần uốn thẳng đứng): chỉ xuyên thanh cánh (nối thanh cánh đoạn
        # trên) hoặc chỉ xuyên bản mã của đoạn trên (thanh của đoạn trên bắt vào) -> bu lông lắp khi ráp đoạn trên
        if CFG.get("waiting_holes") and lay:
            # lỗ chờ: chỉ xuyên 1 chi tiết (thanh / bản mã) - thanh kia thuộc xà hoặc đoạn kề, lắp khi ráp
            nm_ = [n_ for _, _, n_ in lay]
            outside_ = abs(bb["p"][0] - xc) * SC > halfw(bb["p"][1]) + 120
            if all(n_.startswith("bản mã") for n_ in nm_) or (len(lay) == 1 and outside_) or \
                    (len(lay) == 1 and nm_[0].startswith(Lg["section"]) and
                     zf(bb["p"][1]) > zf(max(Lg["a"][1], Lg["b"][1])) - 400):
                rep["holes_waiting"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                             "M": bb["d"], "qua": nm_})
                continue
        if CFG.get("top_kink") and lay and bb["p"][1] > max(Lg["a"][1], Lg["b"][1]) - 2.0:
            nm_ = [n_ for _, _, n_ in lay]
            if all(n_.startswith(Lg["section"]) for n_ in nm_) or all(n_.startswith("bản mã") for n_ in nm_):
                rep["holes_waiting"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                             "M": bb["d"], "qua": nm_})
                continue
        if not lay:
            rep["bolts_dropped"] += 1
            rep.setdefault("bolts_dropped_pts", []).append(bb["p"])
            continue
        lay.sort()
        # khối D đặt đúng tim bu lông vẽ; bu lông lấy theo hình chi tiết bản mã có thể lệch vài mm
        sym = next((sy for sy in dsyms if "lab" in sy and math.dist(sy["p"], bb["p"]) < 1.2 and
                    min(bolts2d, key=lambda b2: math.dist(b2["p"], sy["p"])) is bb), None)
        if sym:
            lab = sym["lab"]
            nper = max(1, round(lab["n"] / len(lab["syms"])))
            if lab.get("assumed") and CFG.get("waiting_holes"):
                # không có ký hiệu: chọn 1-2 tấm dày 8/10 vừa khe nhất (không dày hơn khe) - giả định, báo lại
                cur0 = lay[0][1]
                gmax = 0.0
                for a0_, b0_, _n in lay[1:]:
                    gmax = max(gmax, a0_ - cur0)
                    cur0 = max(cur0, b0_)
                opts = [(n_ * t_, n_, t_) for n_ in (1, 2) for t_ in (8.0, 10.0) if n_ * t_ <= gmax + 0.01]
                if opts:
                    _, nper, tt_ = max(opts)
                    lab = dict(lab, t=tt_, n=nper * len(lab["syms"]))
            # khe lớn nhất giữa các lớp
            gaps = []
            cur = lay[0][1]
            for a_, b_, n_ in lay[1:]:
                if a_ > cur + 0.5:
                    gaps.append((a_ - cur, cur, a_))
                cur = max(cur, b_)
            if gaps:
                g_, glo, ghi = max(gaps)
                th = nper * lab["t"]
                if abs(g_ - th) > 2.5:
                    # số tấm theo khe (giữ chiều dày ghi): VD 4D.20_8 tại nút thanh cánh HL130x9 (khe 9) -> 1 tấm 8
                    k_ = min(range(1, max(nper, lab["n"], 1) + 1), key=lambda k: abs(g_ - k * lab["t"]))
                    if abs(g_ - k_ * lab["t"]) <= 2.5:
                        nper, th = k_, k_ * lab["t"]
                if (abs(g_ - th) > 2.5 or (CFG.get("waiting_holes") and th > g_ + 0.5)) and g_ / nper >= 3:
                    # người dùng chốt: chiều dày tấm đệm sửa cho vừa khe (VD 2D.20_8 ở khe 20 -> 2 tấm 10)
                    t_fit = float(math.floor(g_ / nper))
                    rep.setdefault("fillers_resized", []).append({"z_mm": round(zf(bb["p"][1])), "ky_hieu": f"{nper} x {lab['t']:g}",
                                                                  "khe_mm": round(g_, 1), "sua": f"{nper} x {t_fit:g}"})
                    lab = dict(lab, t=t_fit)
                    th = nper * t_fit
                for i in range(nper):
                    f_hi = ghi - i * lab["t"]
                    lay.append((f_hi - lab["t"], f_hi, "tấm đệm d%d" % lab["t"]))
                    # tấm đệm sát mép cánh thanh cánh (tâm cách mép < bán kính): cắt phẳng theo mép, chừa 1 mm
                    clip_ = None
                    # mô hình 3D dùng thanh cánh trái xoay 4 góc -> bên phải lấy đối xứng gương của thanh cánh trái
                    ul = np.array(Lg["w2"]) - np.array(Lg["w1"])
                    ul = ul / np.linalg.norm(ul)
                    for sgn_ in (1, -1):
                        qx = bb["p"][0] if sgn_ == 1 else 2 * xc - bb["p"][0]
                        toe_ = (qx - xline(Lg, bb["p"][1])) * SC - (sec(Lg["section"])["b"] - Lg["g"])
                        if 0 < toe_ < sym["r_mm"] + 1 and abs(qx - xline(Lg, bb["p"][1])) * SC < 300:
                            nl = np.array([ul[1], -ul[0]]) * (1 if ul[1] > 0 else -1)      # hướng vào trong mặt
                            nl = nl * np.array([sgn_, 1.0])
                            clip_ = (nl.tolist(), toe_ - 4.0)     # chừa 1 mm + sai số nét vẽ ~3 mm
                    fillers2d.append({"p": bb["p"], "lo": f_hi - lab["t"], "t": lab["t"], "r": sym["r_mm"],
                                      "clip": clip_})
                lay.sort()
                rep["fillers"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                       "khe_mm": round(g_, 1), "dem": f"{nper} x {lab['t']:g}",
                                       "con_ep_mm": round(g_ - th, 1),
                                       **({"gia_dinh": "không có ký hiệu, lấy %d x %g" % (nper, lab["t"])} if lab.get("assumed") else {})})
            else:
                rep["fillers"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                       "khe_mm": 0, "loi": "không có khe để đặt tấm đệm"})
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

    # đoạn đặt trên đoạn khác: đầu dưới thanh cánh = bu lông thấp nhất trên cánh thanh cánh - 50 mm (như đầu trên
    # thanh cánh đoạn dưới; chi tiết HL130x9: 2 nhóm lỗ cách 110 = 50 + khe 10 + 50). Nét thanh cánh tờ này vẽ
    # kéo tới mặt bản đế (dùng khi đoạn đứng trên móng).
    if ONTOP:
        for L_ in legs:
            la_, lb_ = np.array(L_["a"]), np.array(L_["b"])
            lo_e, hi_e = (la_, lb_) if la_[1] < lb_[1] else (lb_, la_)
            u2 = (hi_e - lo_e) / np.linalg.norm(hi_e - lo_e)
            sgn = 1 if L_ is Lg else -1
            sb = [float(np.dot(np.array(b["p"]) - lo_e, u2)) for b in bolts2d
                  if -L_["g"] + 5 <= (b["p"][0] - xline(L_, b["p"][1])) * SC * sgn <= sec(L_["section"])["b"] - L_["g"] - 5
                  and dist_line(b["p"], L_["w1"], L_["w2"]) * SC < 120 and (b["p"][1] - lo_e[1]) * SC < 900]
            if sb:
                new_lo = lo_e + u2 * (min(sb) - ONTOP.get("leg_end", 50.0) / SC)
                rep.setdefault("leg_bottom_trim_mm", []).append(round(float(np.dot(new_lo - lo_e, u2)) * SC, 1))
                if la_[1] < lb_[1]:
                    L_["a"] = tuple(new_lo)
                else:
                    L_["b"] = tuple(new_lo)

    def prof3d(m, nn):
        """Độ sâu theo chiều dài (thanh bẻ lệch / ép sát giữa thanh): [[x mm từ p1, δ mm], ...]."""
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        s1_ = ((m["b1"][0] - c1[0]) * u_[0] + (m["b1"][1] - c1[1]) * u_[1]) * SC
        s2_ = ((m["b2"][0] - c1[0]) * u_[0] + (m["b2"][1] - c1[1]) * u_[1]) * SC
        sg = 1 if s2_ >= s1_ else -1
        pts_ = [[0.0, m["delta"][0]]] + [[round((sp - s1_) * sg, 1), round(dv, 2)] for sp, dv in m["dprof"]] + \
            [[round(abs(s2_ - s1_), 1), m["delta"][1]]]
        return {"prof": sorted(pts_), "prof_n": nn.round(6).tolist()}

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
    ez = np.array([0, 0, 1.0])
    nv0 = np.array([0, -1.0, 0])                   # pháp tuyến ngoài mặt trước phần thẳng đứng
    # --- ĐỈNH ĐOẠN UỐN THẲNG ĐỨNG (người dùng chốt, xem DN-02): thanh cánh gãy tại đường ngang y_k (đầu trên nét
    #     liền phần nghiêng), phía trên thẳng đứng tới đầu thanh; bản mã qua đường gãy bẻ góc theo đó
    KINK = None
    if CFG.get("top_kink"):
        y_k = max(Lg["a"][1], Lg["b"][1])
        xb_k = xline(Lg, y_k) - Lg["g"] / SC                       # lưng thanh cánh trái tại đường gãy
        tops = [max(sg["a"][1], sg["b"][1]) for sg in segs if sg["k"] == "S"
                and abs(math.degrees(sg["ang"]) - 90) < 0.5 and min(sg["a"][1], sg["b"][1]) >= y_k - 0.3
                and abs((sg["a"][0] + sg["b"][0]) / 2 - xb_k) < 0.3]
        if tops:
            KINK = {"y": y_k, "h": halfw(y_k), "ytop": max(tops)}
            rep["top_kink"] = {"z_gay_mm": round(zf(y_k)), "z_dinh_mm": round(zf(max(tops))),
                               "dai_doan_dung_mm": round((max(tops) - y_k) * SC),
                               "goc_uon_do": round(math.degrees(math.atan(abs(slope))), 2)}

    def up_(q):
        return KINK is not None and q[1] > KINK["y"] + 1e-6

    def place(q, d_mm):
        """Điểm 3D (chưa xoay mặt) của điểm bản vẽ q, lệch d_mm theo pháp tuyến mặt; kèm pháp tuyến, hướng lên."""
        if up_(q):
            return np.array([(q[0] - xc) * SC, -KINK["h"], zf(q[1])]) / 1000 + nv0 * d_mm / 1000, nv0, ez
        return to3(q)[0] + nf * d_mm / 1000, nf, tup

    def clip_y(P, y, keep_above):
        out_ = []
        for i in range(len(P)):
            a_, b_ = P[i], P[(i + 1) % len(P)]
            ia, ib = (a_[1] >= y) == keep_above, (b_[1] >= y) == keep_above
            if ia:
                out_.append(a_)
            if ia != ib:
                t_ = (y - a_[1]) / (b_[1] - a_[1])
                out_.append((a_[0] + t_ * (b_[0] - a_[0]), y))
        return out_
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
        # khung cánh nằm ngang: mặt cắt ngang thanh cánh nằm ngang -> đầu thanh cắt ngang (mặt bản đế, mối nối 2
        # đoạn khe 10 mm, đường gãy phần uốn thẳng đứng gặp nhau khít); mỗi cánh vẫn nằm đúng mặt cột
        e1, e2 = -fb, -fa
        s_ = sec(L_["section"])
        legs_parts = [(P1, P2, "thanh cánh")]
        if KINK:
            Pt = Rk @ (np.array([-KINK["h"], -KINK["h"], zf(KINK["ytop"])]) / 1000)
            legs_parts = [(P1, P2, "thanh cánh (phần nghiêng)"),
                          (P2, Pt, "thanh cánh (phần uốn thẳng đứng, gãy %.1f độ)" % rep["top_kink"]["goc_uon_do"])]
        legs_parts = [(P1_, P2_, side_, L_["section"], L_["g"], None) for P1_, P2_, side_ in legs_parts]
        if BSTUB:
            # DN-02: phần đứng DT-01 (HL150x12, lưng lồi 3 mm, vẽ để ráp) | khe B-B | HL130x9 203/204 | khe A-A |
            # HL130x9 201/202 (chi tiết theo số hiệu tờ DN-02)
            Pz = lambda zmm: P1 + (P2 - P1) * (zmm - zf(L_["a"][1])) / (zf(L_["b"][1]) - zf(L_["a"][1]))
            jb, gb = BSTUB["joint_mm"], BSTUB["gap"] / 2
            cuts_ = [jb] + [sp_["z"] for sp_ in CFG.get("leg_splices", [])]
            gaps_ = [gb] + [sp_["gap"] / 2 for sp_ in CFG.get("leg_splices", [])]
            ztop = zf(max(L_["a"][1], L_["b"][1]))
            legs_parts = [(Pz(0.0), Pz(jb - gb), "phần đứng thanh cánh %s (301/302, vẽ để ráp)" % BSTUB["sheet"],
                           BSTUB["section"], L_["g"] + STUB_OUT, BSTUB["sheet"])]
            names_ = ["thanh cánh 203/204", "thanh cánh 201/202"]
            for i_ in range(len(cuts_)):
                z0_ = cuts_[i_] + gaps_[i_]
                z1_ = (cuts_[i_ + 1] - gaps_[i_ + 1]) if i_ + 1 < len(cuts_) else ztop
                legs_parts.append((Pz(z0_), Pz(z1_), names_[min(i_, 1)], L_["section"], L_["g"], None))
            # thép góc nối trong (vát góc lưng 12x12 theo chi tiết)
            for zc_, Li_, sec_, nm_ in [(jb, 670.0, "HL130X9", "thép góc nối trong B-B (232)")] + \
                    [(sp_["z"], sp_["inner_L"], sp_["inner"], "thép góc nối trong A-A (229)") for sp_ in CFG.get("leg_splices", [])]:
                si = sec(sec_)
                if si["profile"][0] == [0.0, 0.0]:
                    si["profile"] = [[12.0, 0.0]] + si["profile"][1:] + [[0.0, 12.0]]
                    si["note"] = "vát góc lưng 12x12"
                legs_parts.append((Pz(zc_ - Li_ / 2), Pz(zc_ + Li_ / 2), nm_, sec_, gl - tl, None))
        for P1_, P2_, side_, secn_, g_, ext_ in legs_parts:
            s2_ = sec(secn_)
            mid += 1
            members.append({"id": mid, "p1": P1_.round(5).tolist(), "p2": P2_.round(5).tolist(),
                            "length": round(float(np.linalg.norm(P2_ - P1_)), 4), "section": secn_,
                            "A_cm2": s2_["A_geom_cm2"], "type": "C", "rule": "leg", "e1": e1.round(6).tolist(),
                            "e2": e2.round(6).tolist(), "g": [g_, g_], "variant": "leg",
                            "auto_variant": "leg", "frames": {}, "offs": {}, "group": 1, "bolts": {}, "bolt": None,
                            "node1": None, "node2": None, "face_k": k, "side": side_,
                            **({"leg_piece": True} if KINK or BSTUB else {}), **({"ext": ext_} if ext_ else {})})
        # thép góc nối trong HL130x9 (hình cắt A-A + chi tiết DT-02: dài 750, vát góc lưng 12x12 tránh góc lượn
        # thanh cánh): lồng trong góc thanh cánh, dài bằng bản mã nối, cùng đường tim
        for pl in plates2d:
            if not pl.get("splice") or np.mean([q[0] for q in pl["pts"]]) > xc:
                continue
            la_, lb_ = np.array(L_["a"]), np.array(L_["b"])
            u2 = (lb_ - la_) / np.linalg.norm(lb_ - la_)
            ss_ = [float(np.dot(np.array(q) - la_, u2)) for q in pl["pts"]]
            Q1, Q2 = la_ + u2 * min(ss_), la_ + u2 * max(ss_)
            P1, P2 = Rk @ to3(tuple(Q1))[0], Rk @ to3(tuple(Q2))[0]
            si = sec("HL130X9")
            if si["profile"][0] == [0.0, 0.0]:
                si["profile"] = [[12.0, 0.0]] + si["profile"][1:] + [[0.0, 12.0]]
                si["note"] = "vát góc lưng 12x12 (chi tiết DT-02)"
            gi = L_["g"] - tl
            mid += 1
            members.append({"id": mid, "p1": P1.round(5).tolist(), "p2": P2.round(5).tolist(),
                            "length": round(float(np.linalg.norm(P2 - P1)), 4), "section": "HL130X9",
                            "A_cm2": si["A_geom_cm2"], "type": "C", "rule": "leg", "e1": e1.round(6).tolist(),
                            "e2": e2.round(6).tolist(), "g": [gi, gi], "variant": "leg", "auto_variant": "leg",
                            "frames": {}, "offs": {}, "group": 1, "bolts": {}, "bolt": None, "node1": None,
                            "node2": None, "face_k": k, "side": "thép góc nối trong (mối nối thanh cánh)",
                            **({"ext": pl["ext"]} if pl.get("ext") else {})})
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
                **(prof3d(m, nn) if m.get("dprof") else {}),
                "g": [m["heel_to_center"] or s_["b"] / 2, 0.0], "group": 2, "bolts": {}, "bolt": None,
                "node1": None, "node2": None, "face_k": k, "x_pair": False, "default_up": False,
                "side": "NGOAI" if m["out"] else "TRONG",
                "plate_end": [bool(m["plate"][kk] is not None and not m["plate"][kk].get("on_leg_fixed")) for kk in (0, 1)],
                **({f"cut{kk + 1}": v for kk, v in m.get("cuts", {}).items()}),
                "drawing": {"edges": m["edges"], "width": m["width"], "section_from": m.get("section_from", "nhãn"),
                            "delta_mm": [round(v, 1) for v in m["delta"]]}})
        for pl in plates2d:
          parts_ = [(pl["pts"], "")]
          if KINK and any(q[1] > KINK["y"] + 1e-6 for q in pl["pts"]) and any(q[1] < KINK["y"] - 1e-6 for q in pl["pts"]):
              # bản mã qua đường gãy: bẻ góc theo thanh cánh (phần dưới trong mặt nghiêng, phần trên thẳng đứng)
              parts_ = [(clip_y(pl["pts"], KINK["y"], False), " - phần dưới (nghiêng)"),
                        (clip_y(pl["pts"], KINK["y"], True), " - phần trên (bẻ góc, thẳng đứng)")]
          for pts_, tag_ in parts_:
            upper_ = KINK is not None and np.mean([q[1] for q in pts_]) > KINK["y"]
            nrm_ = Rk @ (nv0 if upper_ else nf)
            P = [Rk @ (np.array([(q[0] - xc) * SC, -KINK["h"], zf(q[1])]) / 1000 + nv0 * pl["delta0"] / 1000)
                 if upper_ else Rk @ to3(q)[0] + n * pl["delta0"] / 1000 for q in pts_]
            o, a1, a2 = P[0], Rk @ ex, Rk @ (ez if upper_ else tup)
            poly = [[round(float(np.dot(q - o, a1)), 5), round(float(np.dot(q - o, a2)), 5)] for q in P]
            area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                           for i in range(len(poly)))) / 2
            plates.append({"kind": "gusset", "node": o.round(4).tolist(), "members": [], "t_mm": pl["t"],
                           "on_leg": True, "face_k": k, "origin": o.round(5).tolist(), "a1": a1.round(6).tolist(),
                           "a2": a2.round(6).tolist(), "thick_dir": nrm_.round(6).tolist(), "poly": poly,
                           "area_m2": round(area, 5), "mass_kg": round(area * pl["t"] / 1000 * 7850, 2),
                           "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0,
                           **({"ext": pl["ext"]} if pl.get("ext") else {}),
                           "reason": pl["note"] if pl.get("d3") else
                           ("bản mã %s d%g - phần đứng (tấm bẻ góc đủ dựng ở %s, phần này vẽ để ráp)" % (
                               pl.get("mark", "228/228a"), pl["t"], pl["ext"])) if pl.get("ext") and BSTUB else
                           ("bản mã nối thanh cánh d%g của %s (bản mã chờ, vẽ để ráp)" % (pl["t"], pl["ext"]))
                           if pl.get("ext") else
                           ("bản nối ngoài thanh cánh %s d%g" % ("B-B (233)" if pl["leg_splice"] == BSTUB["joint_mm"]
                                                                 else "A-A (230)", pl["t"])) if pl.get("leg_splice") else
                           ("bản mã nối thanh cánh d%g (mối nối với đoạn trên)" % pl["t"]) if pl.get("splice") else
                           ("bản mã nút đầu trên d%g (%s)%s" % (pl["t"], pl["note"], tag_))
                           if pl.get("hidden") else
                           ("bản mã %s theo hình chi tiết (%s)" % (pl["mark"], SHEET)) if pl.get("mark")
                           else f"bản vẽ {SHEET} (mặt đứng)"})
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
        for f_ in fillers2d:
            # tấm đệm tròn (vòng nét đứt trên bản vẽ), nằm trong mặt cột tại tim bu lông
            c0_, nr0_, up0_ = place(f_["p"], f_["lo"])
            cen, nfl_ = Rk @ c0_, Rk @ nr0_
            a1f, a2f = Rk @ ex, Rk @ up0_
            rr = f_["r"] / 1000
            poly = [[rr * math.cos(2 * math.pi * i / 20), rr * math.sin(2 * math.pi * i / 20)] for i in range(20)]
            if f_.get("clip"):
                # bỏ phần tròn vượt qua mép cánh thanh cánh: chiếu điểm vượt về đường cắt
                nl, dmm = np.array(f_["clip"][0]), f_["clip"][1] / 1000
                poly = [(np.array(q) - nl * (np.dot(q, nl) + dmm)).tolist() if np.dot(q, nl) < -dmm else q for q in poly]
            poly = [[round(q[0], 5), round(q[1], 5)] for q in poly]
            area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                           for i in range(len(poly)))) / 2
            plates.append({"kind": "filler", "node": cen.round(4).tolist(), "members": [], "t_mm": f_["t"],
                           "on_leg": False, "face_k": k, "origin": cen.round(5).tolist(), "a1": a1f.round(6).tolist(),
                           "a2": a2f.round(6).tolist(), "thick_dir": nfl_.round(6).tolist(), "poly": poly,
                           "area_m2": round(area, 5), "mass_kg": round(area * f_["t"] / 1000 * 7850, 2),
                           "bolt_max": 1, "d_max_mm": 0, "leg_bolts": 0,
                           "reason": "tấm đệm Ø%d dày %g (ký hiệu D)" % (round(2 * f_["r"]), f_["t"])})
        for b in bolts2d:
            p0_, nb0_, _ = place(b["p"], b["lo"])                 # mặt tựa đầu bu lông (phía trong)
            p, nb_ = Rk @ p0_, Rk @ nb0_
            bolts.append({"id": 0, "p": p.round(5).tolist(), "axis": nb_.round(6).tolist(), "grip_mm": round(b["hi"] - b["lo"], 1),
                          "L_mm": b["L"], "L_from": b["L_from"],
                          "nut": nb_.round(6).tolist(), "d_mm": b["d"], "t_mm": 10, "kind": "drawing", "face_k": k})

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
            # đường tâm chạy qua trục đối xứng mà nét mép bị ngắt (vòng nhãn tiết diện đè lên): thanh liền qua trục
            qc1 = ((m["c1"][0] - cxp) * SC - hp, (m["c1"][1] - cyp) * SC - hp)
            qc2 = ((m["c2"][0] - cxp) * SC - hp, (m["c2"][1] - cyp) * SC - hp)
            # thanh song song trục, đầu cách trục đối xứng < 250 mm: kéo tới trục (thanh liền qua trục, nét mép bị vòng
            # nhãn tiết diện che); phần đối xứng sẽ ghép lại thành 1 thanh
            dq = (q2[0] - q1[0], q2[1] - q1[1])
            Lq_ = math.hypot(*dq)
            for ii in (0, 1):
                if Lq_ > 0 and abs(dq[ii]) / Lq_ > 0.999:
                    if -250 < q2[ii] < 0 and q2[ii] > q1[ii]:
                        q2 = tuple(0.0 if jj == ii else q2[jj] for jj in (0, 1))
                    elif -250 < q1[ii] < 0 and q1[ii] > q2[ii]:
                        q1 = tuple(0.0 if jj == ii else q1[jj] for jj in (0, 1))
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
                           "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0, "reason": f"bản vẽ {SHEET} (mặt cắt)"})

    if not ONTOP and not CFG.get("no_base"):
        # --- chân cột: số liệu đọc từ DXF (chi tiết tỉ lệ 1/10, xem SHEETS)
        # Vị trí (DT-02 khớp lỗ sườn với bu lông chân thanh cánh trên mặt đứng, lệch <= 5 mm):
        #   sườn 1 nằm trên cánh thanh cánh ở mặt đang xét (thanh cánh trái): x = -(HEEL + 200) + u
        #   sườn 3 trên cánh thứ hai (thấy ở thanh cánh phải, đối xứng gương):  x = HEEL - u
        #   mặt bằng bản đế: lưng cách mép ngoài 200, bản 450x450x40, sườn 1 bắt đầu từ mép bản.
        BC = CFG["base"]
        RIB1, RIB2, RIB3, RIB1_H, RIB3_H = BC["rib1"], BC["rib2"], BC["rib3"], BC["rib1_h"], BC["rib3_h"]
        RIB_H = max(v for _, v in RIB1)
        HEEL = BC["heel"]
        if HEEL is None:
            # vị trí lưng thanh cánh: chọn sao cho lỗ sườn 1 (thanh cánh trái) và sườn 3 (thanh cánh phải) trùng bu lông
            # chân cột vẽ trên mặt đứng (bước 0,5 mm)
            bb = [((e.dxf.insert[0] - xc) * SC, zf(e.dxf.insert[1])) for e in msp.query("INSERT")
                  if e.dxf.name in ("1", "2", "3") and inb(e.dxf.insert) and zf(e.dxf.insert[1]) < BASE_ZONE]
            tz = tup[2]

            BB = np.array(bb, float).reshape(-1, 2)
            U1, V1 = np.array(RIB1_H, float).T
            U3, V3 = np.array(RIB3_H, float).T

            def cost(H, dz):
                # tổng khoảng cách từ mỗi lỗ sườn tới bu lông mặt đứng gần nhất (tính mảng)
                if not len(BB):
                    return 0.0
                hx = np.concatenate([-(H + 200) + U1, H - U3])
                hz = np.concatenate([V1, V3]) * tz + dz
                d = np.hypot(hx[:, None] - BB[None, :, 0], hz[:, None] - BB[None, :, 1])
                return float(d.min(axis=1).sum())
            h0 = halfw(y0)
            HEEL, DZ = min(((H, dz) for H in np.arange(h0 - 20, h0 + 120, 0.5) for dz in np.arange(-20, 31, 1.0)),
                           key=lambda z_: cost(*z_))
            nh = len(RIB1_H) + len(RIB3_H)
            rep["base_heel_fit_mm"] = {"heel": float(HEEL), "lech_tb_mm": round(cost(HEEL, DZ) / nh, 1),
                                       "lo_tren_bu_long_mat_dung_cao_hon_mm": float(DZ),
                                       "ghi_chu": "sườn đặt đáy trên mặt bản đế (cao độ 0) như DT-02"}
        slope_abs = abs(slope)
        Z0 = 11.0
        T_RIB = 12.0
        W1, W2, W3 = (max(u for u, _ in r) for r in (RIB1, RIB2, RIB3))
        rib_specs = [(RIB1, lambda u: -(HEEL + 200) + u, f"sườn 1 ({W1}x{RIB_H}, {len(RIB1_H)} lỗ)"),
                     (RIB3, lambda u: HEEL - u, f"sườn 3 ({W3}x{RIB_H}, {len(RIB3_H)} lỗ)"),
                     # cạnh xiên của sườn 2 có độ dốc = độ nghiêng thanh cánh -> áp dọc mặt ngoài sườn 1
                     (RIB2, lambda u: HEEL + T_RIB - slope_abs * RIB_H * tup[2] + (W2 - u), f"sườn 2 ({W2}x{RIB_H}, không lỗ)")]
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
            for holes, xf, ndiag in ((RIB1_H, lambda u: -(HEEL + 200) + u, BC["diag_u"][0]),
                                     (RIB3_H, lambda u: HEEL - u, BC["diag_u"][1])):
                for u, v in holes:
                    p0 = np.array([xf(u), -h_base, 0.0]) / 1000 + nf * gl / 1000
                    p0 = p0 - tup * (p0[2] / tup[2]) + tup * v / 1000
                    diag = u >= ndiag
                    lo = gl - 7 if diag else gl - tl
                    p_head = Rk @ (p0 + nf * (lo - gl) / 1000)
                    bolts.append({"id": 0, "p": p_head.round(5).tolist(), "axis": n.round(6).tolist(),
                                  "nut": n.round(6).tolist(), "d_mm": 20, "grip_mm": (gl + T_RIB) - lo,
                                  "L_mm": BC["L"]["diag"] if diag else BC["L"]["leg"],
                                  "L_from": "ký hiệu bản vẽ " + (BC["labels"]["diag"] if diag else BC["labels"]["leg"]),
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
                           "reason": f"bản đế 450x450x40 (chi tiết {SHEET})"})
            for du in (0.1, 0.35):
                for dv in (0.1, 0.35):
                    p = Rk @ (corner + du * ex_ + dv * ey_)
                    bolts.append({"id": 0, "p": p.round(5).tolist(), "axis": [0, 0, 1.0], "nut": [0, 0, 1.0],
                                  "d_mm": 56, "t_mm": 40, "kind": "neo"})
        rep["base"] = "4 bản đế 450x450x40, 12 sườn d12 (đúng hình chi tiết), 16 bu lông neo Ø56"
        rep["base_heel_mm"] = float(HEEL)
    else:
        rep["base"] = "không có chân cột: đoạn đặt trên %s (người dùng chốt bỏ bản đế)" % (ONTOP or CFG.get("bottom_stub") or {"sheet": "?"})["sheet"]

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
        # người dùng chốt: bu lông đứng xỏ TỪ DƯỚI LÊN (đầu bu lông dưới, đai ốc trên); bu lông ngang từ trong ra ngoài
        b_["p"] = [round(float(p0[0]), 5), round(float(p0[1]), 5), round(float(bot), 5)]
        b_["axis"], b_["nut"] = [0, 0, 1.0], [0, 0, 1.0]
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
                orig_ = np.array(m[key])
                lg_ = [o for o in members if o["rule"] == "leg" and
                       CK.seg_dist(orig_, orig_ + 1e-6, *CK.frame(o)[:2]) < 0.4]

                def hits_leg():
                    sp = CK.samples(m, LIB)
                    sp = sp[np.linalg.norm(sp - np.array(m[key]), axis=1) < 0.25]
                    if any(np.any(CK.where_v(o, LIB, sp, 0.001) > 0) for o in lg_):
                        return True
                    for o in lg_:
                        so = CK.samples(o, LIB)
                        so = so[np.linalg.norm(so - np.array(m[key]), axis=1) < 0.25]
                        if len(so) and np.any(CK.where_v(m, LIB, so, 0.001) > 0):
                            return True
                    return False
                got = need
                while got > 0:
                    m[key] = (orig_ + sign * u_ * got / 1000).round(5).tolist()
                    if not hits_leg():
                        break
                    got -= 1.0
                if got <= 0:
                    m[key] = orig_.round(5).tolist()
                    got = 0.0
                m["length"] = round(float(np.linalg.norm(np.array(m["p2"]) - np.array(m["p1"]))), 4)
                rep["base_end_extended"].append({"section": m["section"], "mm": round(got, 1),
                                                 **({"thieu_mm": round(need - got, 1),
                                                     "ly_do": "kéo đủ thì chạm cánh thanh cánh"} if got < need - 0.5 else {})})

    # đầu thanh vách đặt trên/dưới thanh vách khác còn chạm cánh đứng thanh chủ: lùi đầu thanh từng 5 mm
    for pm_ in [m for m in members if m["rule"] == "plan" and m.get("on_plan")]:
        for key in pm_["on_plan"]:
            hosts = [o for o in members if o is not pm_ and o["rule"] == "plan"
                     and CK.seg_dist(np.array(pm_[key]), np.array(pm_[key]) + 1e-6, *CK.frame(o)[:2]) < 0.12]
            if not any(touching(pm_, o) for o in hosts):
                continue
            P_ = np.array(pm_[key])
            other = np.array(pm_["p2" if key == "p1" else "p1"])
            u_ = (other - P_) / np.linalg.norm(other - P_)
            for dmm in range(5, 35, 5):
                pm_[key] = (P_ + u_ * dmm / 1000).round(5).tolist()
                if not any(touching(pm_, o) for o in hosts):
                    break
            pm_["length"] = round(float(np.linalg.norm(np.array(pm_["p2"]) - np.array(pm_["p1"]))), 4)
            rep["clash_fix"].append({"loai": "lùi đầu thanh vách khỏi cánh đứng thanh vách chủ", "plan": pm_["plan"],
                                     "section": pm_["section"], "mm": dmm})

    face_m = [m for m in members if m["rule"] == "face"]
    for i, a_ in enumerate(face_m):
        for b_ in face_m[i + 1:]:
            if a_["face_k"] == b_["face_k"] or (a_["face_k"] - b_["face_k"]) % 2 == 0:
                continue
            if CK.seg_dist(*CK.frame(a_)[:2], *CK.frame(b_)[:2]) > 0.15 or not touching(a_, b_):
                continue
            # đầu thanh gần chỗ chạm (cả 2 đầu thanh chéo đều ở thanh cánh nên lấy theo vị trí chạm)
            spa = CK.samples(a_, LIB)
            hit_ = spa[CK.where_v(b_, LIB, spa, 0.001) > 0]
            if not len(hit_):
                spb = CK.samples(b_, LIB)
                hit_ = spb[CK.where_v(a_, LIB, spb, 0.001) > 0]
            cp_ = hit_.mean(axis=0)
            keys = ["cut1" if np.linalg.norm(np.array(m_["p1"]) - cp_) < np.linalg.norm(np.array(m_["p2"]) - cp_)
                    else "cut2" for m_ in (a_, b_)]
            if a_.get(keys[0]) or b_.get(keys[1]):
                # đã vát ở cặp khác: tăng dần vát đang có (bội 5 mm) tới khi hết chạm
                ok_ = False
                for inc in range(5, 120, 5):
                    for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                        c0 = m_.get(k_)
                        if c0 and c0["flange"] == "out":
                            c0["b"] = c0.setdefault("_b0", c0["b"]) + inc
                    if not touching(a_, b_):
                        ok_ = True
                        break
                for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                    c0 = m_.get(k_)
                    if c0 and "_b0" in c0:
                        c0.pop("_b0")
                        c0["note"] = re.sub(r"\d+x\d+mm", f"{c0['a']}x{c0['b']}mm", c0.get("note", ""))
                if not ok_:
                    rep["warnings"].append(f"chạm tại góc cột chưa gỡ được: {a_['section']}/{b_['section']}")
                continue
            # vát cả 2 thanh như nhau, chọn (ngang cánh a, dọc thanh b) bội 5 mm có diện tích cắt nhỏ nhất
            best = None
            for A_ in range(15, 75, 5):
                for B_ in range(15, 170, 5):
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
    rep["faces"] = CFG.get("faces")
    rep["leg"] = {"section": Lg["section"], "g_mm": Lg["g"], "n_brace_ends_on_leg": Lg["n_wp"]}
    scene = {"title": f"Đoạn thân {SHEET} cột N122 (dựng từ BVTC)", "members": members, "sections": LIB,
             "nodes": [], "plates": plates, "bolts": bolts,
             "report": {"total_mass_kg": round(sum(m["mass_kg"] for m in members), 1),
                        "orientation": {"x_members": {"outside": [], "inside": []}, "clash_other": [],
                                        "clash_coplanar_overlap": [], "overridden": []}, "build": rep}}
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    tag = SHEET.lower().replace("-", "")
    (out / f"{tag}_scene.json").write_text(json.dumps(scene, ensure_ascii=False))
    # dữ liệu kiểm tra chồng hình (mặt trước, hệ x-z mm)
    chk = {"cad": [[[(sg["a"][0] - xc) * SC, zf(sg["a"][1])], [(sg["b"][0] - xc) * SC, zf(sg["b"][1])], sg["k"]]
                   for sg in segs],
           "plates": [[[(q[0] - xc) * SC, zf(q[1])] for q in pl["pts"]] for pl in plates2d],
           "bolts": [[(b["p"][0] - xc) * SC, zf(b["p"][1])] for b in bolts2d], "plans": plan_chk,
           "dropped_bolts": [[(q[0] - xc) * SC, zf(q[1])] for q in rep.pop("bolts_dropped_pts", [])],
           "no_host": [{"section": m["section"], "p1": [(m["c1"][0] - xc) * SC, zf(m["c1"][1])],
                        "p2": [(m["c2"][0] - xc) * SC, zf(m["c2"][1])], "side": "NGOAI" if m["out"] else "TRONG"}
                       for m in rep.pop("no_host", [])]}
    (out / f"{tag}_check.json").write_text(json.dumps(chk))
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:3000])
    return scene


def use_sheet(name):
    global SHEET, CFG, BOX, PLANS, BASE_ZONE
    SHEET, CFG = name, SHEETS[name]
    BOX, PLANS = CFG["box"], CFG["plans"]
    BASE_ZONE = max(v for _, v in CFG["base"]["rib1"]) + 70.0 if "base" in CFG else 0.0


if __name__ == "__main__":
    use_sheet(sys.argv[3] if len(sys.argv) > 3 else "DT-02")
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
