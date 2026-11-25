"""Dựng 3D cột N122 từ bản vẽ chế tạo (BVTC, 2D) - giai đoạn 1: thân DT-02 + DT-01, 4 mặt.

Giả thiết (người dùng xác nhận): 4 mặt thân giống nhau khi nhìn từ ngoài vào (đối xứng xoay 90°).
Mặt đứng nhìn từ NGOÀI vào. Mặt trước: y = -h(z), trục ngang của bản vẽ = +x.

Hướng thanh lấy TỪ BẢN VẼ:
- nét chiều dày cánh còn lại KHUẤT -> cánh còn lại chĩa vào trong; LIỀN -> chĩa ra ngoài;
- phía nét chiều dày = phía góc lưng;
- đường tâm (CENTER) = đường đinh, khoảng cách tới lưng đo trên bản vẽ.
Độ sâu (lệch khỏi mặt phẳng mặt cột) CHƯA đọc được từ mặt đứng: tạm theo quy tắc hiện hành
(thanh trong áp mặt trong cánh thanh cánh, thanh ngoài áp mặt ngoài).

Chạy:  python3 tools/bvtc/build_n122.py <BVTC.dxf> <out_dir>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import ezdxf  # noqa: E402
import bvtc_read as R  # noqa: E402
import section_library as SL  # noqa: E402

SC = R.SC
# Bổ sung kích thước JIS G3192 cho các cỡ có trong N122 (b, t, r1, r2 - mm).
EXTRA_JIS = {"L75X6": (75, 6, 8.5, 4), "L130X9": (130, 9, 12, 6), "L150X15": (150, 15, 14, 10),
             "L200X20": (200, 20, 18, 12), "L250X25": (250, 25, 24, 12)}
SL.JIS_G3192.update(EXTRA_JIS)

ELEV = {  # tên: hộp vùng mặt đứng trên bản vẽ
    "DT-02": (-2376, -122104, -1990, -121674),
    "DT-01": (-2347, -121499, -2116, -121087),
    "DN-02a": (-2372, -120821, -2220, -120473),   # mặt có đầu xà -> mặt trước, sau
    "DN-02b": (-2210, -120821, -2059, -120473),   # mặt bên
    "DN-01a": (-2372, -120251, -2199, -119861),
    "DN-01b": (-2193, -120251, -2042, -119861),
}
FACES = {"DT-02": (0, 1, 2, 3), "DT-01": (0, 1, 2, 3), "DN-02a": (0, 2), "DN-02b": (1, 3),
         "DN-01a": (0, 2), "DN-01b": (1, 3)}
# Mặt cắt vách ngang: tên -> (đoạn mặt đứng chứa vạch cắt, y vạch cắt, (x,y) tên mặt cắt)
PLANS = {
    "DT-01 1-1": ("DT-01", -121416.7, (-1912.8, -121368.1)),
    # DT-02: tam giác giằng góc / 1/4 vách, góc cột ở dưới-trái; khung đọc đặt tay (tránh hình bên cạnh)
    "DT-02 1-1": ("DT-02", -121780.0, (-1930.5, -121772.6), (-1980, -121766, -1880, -121680)),
    "DT-02 2-2": ("DT-02", -121852.3, (-1896.8, -122076.3), (-1980, -122063, -1812, -121905)),
    "DT-02 3-3": ("DT-02", -121935.3, (-1918.9, -121898.8), (-1980, -121880, -1867, -121785)),
    "DT-02 4-4": ("DT-02", -122015.4, (-1836.7, -122184.8), (-1875, -122170, -1805, -122092)),
    "DN-02 1-1": ("DN-02a", -120563.2, (-1938.9, -120574.4)),
    "DN-02 2-2": ("DN-02a", -120722.9, (-1938.2, -120699.1)),
    "DN-02 3-3": ("DN-02a", -120783.1, (-1939.0, -120825.2)),
    "DN-01 1-1": ("DN-01a", -119874.8, (-1935.3, -119982.8)),
    "DN-01 2-2": ("DN-01a", -119997.0, (-1800.7, -119971.4)),
    "DN-01 3-3": ("DN-01a", -120054.8, (-1919.2, -120119.6)),
}
BASE_WIDTH = 7500.0       # mm, bề rộng chân cột giữa đường tim thanh cánh (sơ đồ toàn thể)


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def legs_of(ms):
    """Hai thanh cánh của mặt đứng: thanh rộng gần đứng có NHIỀU đầu thanh xiên/ngang chạm vào nhất
    (loại bỏ hình khai triển thanh cánh vẽ bên cạnh)."""
    def touches(leg):
        (x1, y1), (x2, y2) = leg["c1"], leg["c2"]
        L = math.dist(leg["c1"], leg["c2"])
        n = 0
        for m in ms:
            if m is leg or m["width"] >= 120:
                continue
            for p in (m["c1"], m["c2"]):
                d = abs((x2 - x1) * (y1 - p[1]) - (x1 - p[0]) * (y2 - y1)) / L
                if d < 1.0:
                    n += 1
        return n
    cand = [m for m in ms if m["width"] >= 120 and 60 < m["ang"] < 120]
    lefts = [m for m in cand if m["ang"] <= 90]
    rights = [m for m in cand if m["ang"] > 90]
    if not rights:   # thanh cánh thẳng đứng
        cand.sort(key=lambda m: (m["c1"][0] + m["c2"][0]))
        lefts, rights = cand[:len(cand) // 2], cand[len(cand) // 2:]
    left = max(lefts, key=touches)
    right = max(rights, key=touches)

    def inter(a, b):
        (x1, y1), (x2, y2) = a["c1"], a["c2"]
        (x3, y3), (x4, y4) = b["c1"], b["c2"]
        dd = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(dd) < 1e-9:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / dd
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    braces = [m for m in ms if m["width"] < 120]
    wps = [p for i, a in enumerate(braces) for b in braces[i + 1:]
           if abs(a["ang"] - b["ang"]) > 3 and (p := inter(a, b)) is not None]

    def misfit(leg):
        """Giao điểm các cặp thanh xiên/ngang (điểm làm việc) gần thanh cánh phải nằm trên đường tim:
        điểm = -tổng khoảng cách (giới hạn 3 đơn vị) từ các giao điểm gần tới đường thử."""
        (x1, y1), (x2, y2) = leg["c1"], leg["c2"]
        L = math.dist(leg["c1"], leg["c2"])
        ylo, yhi = sorted((leg["p1"][1], leg["p2"][1]))
        tot = 0.0
        for p in wps:
            if not (ylo - 2 <= p[1] <= yhi + 2):
                continue
            d = abs((x2 - x1) * (y1 - p[1]) - (x1 - p[0]) * (y2 - y1)) / L
            if d < 3.0:
                tot += min(d, 3.0)
        return -tot
    for leg in (left, right):
        pick_working_line(leg, ms, misfit)
    return left, right


def pick_working_line(leg, ms, touches):
    """Thanh cánh có nhiều đường tâm (đường tim làm việc + đường đinh mối nối): chọn đường có nhiều
    đầu thanh xiên/ngang chạm vào nhất làm đường tim; cập nhật khoảng cách tới lưng."""
    if leg.get("_wl"):
        return
    nx = leg["nvec"]
    best = (touches(leg), 0.0)   # touches = hàm điểm (lớn hơn = tốt hơn)
    base = (leg["c1"], leg["c2"], leg["p1"], leg["p2"])
    for off in leg["centers_rel"]:
        if abs(off) < 1e-6:
            continue
        o = off / SC
        sh = lambda p: (p[0] + nx[0] * o, p[1] + nx[1] * o)
        leg["c1"], leg["c2"] = sh(base[0]), sh(base[1])
        t = touches(leg)
        if t > best[0]:
            best = (t, off)
        leg["c1"], leg["c2"] = base[0], base[1]
    o = best[1] / SC
    sh = lambda p: (p[0] + nx[0] * o, p[1] + nx[1] * o)
    leg["c1"], leg["c2"], leg["p1"], leg["p2"] = (sh(q) for q in base)
    if leg.get("heel_signed") is not None:
        leg["heel_to_center"] = abs(leg["heel_signed"] - best[1])
    leg["_wl"] = best[1]


def leg_pieces(ms, leg):
    """Mọi đoạn thanh cánh nằm trên cùng đường tim với thanh cánh đã chọn (mối nối thanh cánh)."""
    (x1, y1), (x2, y2) = leg["c1"], leg["c2"]
    L = math.dist(leg["c1"], leg["c2"])
    dist = lambda p: abs((x2 - x1) * (y1 - p[1]) - (x1 - p[0]) * (y2 - y1)) / L
    out = []
    for m in ms:
        if m is leg:
            out.append(m)
            continue
        if m["width"] >= 120 and abs(m["ang"] - leg["ang"]) < 1.0 and \
                min(abs(dist(m["c1"]) - abs(leg.get("_wl", 0)) / SC), dist(m["c1"])) < 1.0:
            # đặt đoạn lên đúng đường tim đã chọn, giữ khoảng cách lưng thực đo của đoạn
            s_ = lambda p: ((p[0] - x1) * (x2 - x1) + (p[1] - y1) * (y2 - y1)) / L ** 2
            proj = lambda p: (x1 + s_(p) * (x2 - x1), y1 + s_(p) * (y2 - y1))
            if m.get("heel_signed") is not None:
                nx = m["nvec"]
                heel_pt = (m["c1"][0] + nx[0] * m["heel_signed"] / SC, m["c1"][1] + nx[1] * m["heel_signed"] / SC)
                m["heel_to_center"] = round(dist(heel_pt) * SC, 1)
            m["c1"], m["c2"], m["p1"], m["p2"] = proj(m["c1"]), proj(m["c2"]), proj(m["p1"]), proj(m["p2"])
            if not m.get("section"):
                m["section"] = leg.get("section")
            out.append(m)
    return out


def line_x_at(m, y):
    (x1, y1), (x2, y2) = m["c1"], m["c2"]
    return x1 + (y - y1) * (x2 - x1) / (y2 - y1)


def section_props(name, lib_cache):
    if name not in lib_cache:
        base = SL.base_name(name)
        b, t, r1, r2 = SL.JIS_G3192[base]
        pts = SL.profile(b, t, r1, r2)
        A, cx, cy = SL.poly_props(pts)
        lib_cache[name] = {"name": name, "base": base, "standard": "JIS G3192", "b": b, "t": t, "r1": r1,
                           "r2": r2, "A_geom_cm2": round(A / 100, 3), "A_pdf_cm2": round(A / 100, 3),
                           "cx": round(cx, 2), "cy": round(cy, 2), "gauge": b / 2,
                           "profile": [[round(x, 3), round(y, 3)] for x, y in pts]}
    return lib_cache[name]


def rot(theta):
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def main(dxf, out):
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    data = {}
    for name, box in ELEV.items():
        ms = R.members(doc, msp, box)
        L, Rr = legs_of(ms)
        y_mid = (L["c1"][1] + L["c2"][1]) / 2
        xc = (line_x_at(L, y_mid) + line_x_at(Rr, y_mid)) / 2
        R.assign_labels(ms, R.text_labels(msp, box), xc)
        data[name] = {"ms": ms, "L": L, "R": Rr, "xc": xc}

    # --- trục z: DT-02 gốc tại bề rộng 7500; DT-01 nối tiếp theo cùng đường thanh cánh
    def halfw(d, y):
        return (line_x_at(d["R"], y) - line_x_at(d["L"], y)) / 2 * SC     # mm
    d2 = data["DT-02"]
    ya, yb = sorted([d2["L"]["c1"][1], d2["L"]["c2"][1]])
    slope = (halfw(d2, yb) - halfw(d2, ya)) / ((yb - ya) * SC)               # dh/dz (<0)
    y0 = ya + (BASE_WIDTH / 2 - halfw(d2, ya)) / slope / SC                  # y tại z = 0
    d2["zmap"] = (y0, 0.0)
    d1 = data["DT-01"]
    ya1 = min(d1["L"]["c1"][1], d1["L"]["c2"][1])
    z_at = (halfw(d1, ya1) - BASE_WIDTH / 2) / slope
    d1["zmap"] = (ya1, z_at)
    slope1 = (halfw(d1, ya1 + 100) - halfw(d1, ya1)) / (100 * SC)
    report = {"slope_DT02": slope, "slope_DT01": slope1, "z_DT01_bottom_leg_line": z_at}

    def hor_levels(d):
        """Cao độ y (bản vẽ) các thanh ngang nối 2 thanh cánh (kể cả thanh khuất)."""
        ys = []
        for m in d["ms"]:
            a = m["ang"] % 180
            if (a < 1 or a > 179) and abs(m["c2"][0] - m["c1"][0]) * SC > 0.4 * 2 * halfw(d, m["c1"][1]):
                ys.append(m["c1"][1])
        return sorted(ys)
    # điểm gãy dốc = thanh ngang cao nhất của DT-01
    y_bend = hor_levels(d1)[-1]
    z_bend = d1["zmap"][1] + (y_bend - d1["zmap"][0]) * SC
    report["z_bend"] = z_bend
    report["h_bend_DT"] = BASE_WIDTH / 2 + slope * z_bend
    zlow = z_bend
    for seg in ("DN-02", "DN-01"):
        tops = []
        for f in "ab":
            d = data[seg + f]
            lv = hor_levels(d)
            d["zmap"] = (lv[0], zlow)                 # thanh ngang thấp nhất = nối với đoạn dưới
            d["vertical_legs"] = True
            report[f"h_{seg}{f}"] = halfw(d, lv[0])
            tops.append(zlow + (lv[-1] - lv[0]) * SC)
        report[f"z_top_{seg}"] = tops
        zlow = min(tops)

    h_head = report["h_DN-02a"]
    report["h_head_used"] = h_head
    lib_cache = {}
    members, bars = [], []
    for name in ELEV:
        d = data[name]
        yref, zref = d["zmap"]
        zf = lambda y, yref=yref, zref=zref: zref + (y - yref) * SC          # mm
        if d.get("vertical_legs"):
            hconst = h_head                                  # mọi mặt đoạn ngọn: cùng đường tim thanh cánh
            d["xscale"] = h_head / halfw(d, yref)            # chuẩn hóa sai số đo của từng mặt
            hf = lambda z, hconst=hconst: hconst
            slope_d = 0.0
        else:
            hf = lambda z: BASE_WIDTH / 2 + slope * z                         # mm (đường tim thanh cánh)
            slope_d = slope

        def to3(p, d=d, zf=zf, hf=hf):
            z = zf(p[1])
            return np.array([(p[0] - d["xc"]) * SC * d.get("xscale", 1.0), -hf(z), z]) / 1000.0   # m, mặt trước

        tup = unit([0, -slope_d, 1])                                            # hướng lên dọc mặt trước
        nface = unit(np.cross([1, 0, 0], tup))                                # pháp tuyến mặt trước
        if nface[1] > 0:
            nface = -nface                                                    # ra ngoài (-y)
        legL, legR = d["L"], d["R"]
        piecesL, piecesR = leg_pieces(d["ms"], legL), leg_pieces(d["ms"], legR)
        for m in d["ms"]:
            if m["all_hidden"] and not any(m is q for q in piecesL + piecesR):
                continue                                                      # thanh phía sau, lấy ở mặt cắt
            is_leg = any(m is q for q in piecesL + piecesR)
            if not is_leg and m["width"] >= 120:
                continue                                                      # đoạn thanh cánh đoạn khác vẽ chồng
            if not m.get("section"):
                continue
            if not is_leg:
                hx = [abs(p[0] - d["xc"]) * SC - halfw(d, p[1]) for p in (m["c1"], m["c2"])]
                if max(hx) > 60:
                    d.setdefault("skipped_outside", []).append(m)              # đầu xà: dựng ở phần xà
                    continue
            # thanh cánh: lấy hết chiều dài thanh (đường tâm vẽ ngắn hơn); thanh khác: đường tâm vẽ tới nút
            P1, P2 = (to3(m["p1"]), to3(m["p2"])) if is_leg else (to3(m["c1"]), to3(m["c2"]))
            bars.append({"seg": name, "leg": is_leg,
                         "leg_side": ("L" if any(m is q for q in piecesL) else "R") if is_leg else None,
                         "P1": P1, "P2": P2, "m": m})
        d["tup"], d["nface"] = tup, nface

    # --- 4 mặt bằng xoay 90°; thanh cánh chỉ lấy thanh trái của mặt trước rồi xoay (4 góc)
    out_members = []
    mid = 0
    for k in range(4):
        Rk = rot(k * math.pi / 2)
        for b in bars:
            m = b["m"]
            if k not in FACES[b["seg"]]:
                # thanh cánh: lấy từ mặt "a" (hoặc mặt duy nhất) và xoay đủ 4 góc
                if not (b["leg"] and b["leg_side"] == "L" and b["seg"] in ("DN-02a", "DN-01a")):
                    continue
            elif b["leg"] and (b["leg_side"] == "R" or b["seg"].endswith("b")):
                continue
            d = data[b["seg"]]
            s = section_props(m["section"], lib_cache)
            P1, P2 = Rk @ b["P1"], Rk @ b["P2"]
            u = unit(P2 - P1)
            n = Rk @ d["nface"]
            n = unit(n - np.dot(n, u) * u)
            tup = Rk @ d["tup"]
            ex = Rk @ np.array([1.0, 0, 0])
            mid += 1
            rec = {"id": mid, "p1": P1.round(5).tolist(), "p2": P2.round(5).tolist(),
                   "length": round(float(np.linalg.norm(P2 - P1)), 4), "section": m["section"],
                   "A_cm2": s["A_geom_cm2"], "group": 0, "node1": None, "node2": None,
                   "bolts": {}, "bolt": None, "seg": b["seg"], "face_k": k,
                   "drawing": {"vis": m["vis"], "edges": m["edges"], "heel_to_center": m["heel_to_center"],
                               "width": m["width"], "ang2d": round(m["ang"], 2)}}
            if b["leg"]:
                # thanh cánh góc (-h,-h) xoay k: lưng ra ngoài góc, 2 cánh trên 2 mặt kề
                corner = unit(np.array([P1[0], P1[1], 0]))
                fa = Rk @ np.array([0, -1.0, 0])                      # mặt trước (đã xoay)
                fb = Rk @ np.array([-1.0, 0, 0])                      # mặt trái (đã xoay)
                e1 = unit(-fb - np.dot(-fb, u) * u)                   # cánh nằm trên mặt trước, chạy vào trong
                e2 = unit(-fa - np.dot(-fa, u) * u - np.dot(-fa, e1) * e1)
                g = m["heel_to_center"] or s["b"] / 2
                rec.update({"type": "C", "rule": "leg", "e1": e1.round(6).tolist(), "e2": e2.round(6).tolist(),
                            "g": [g, g], "variant": "leg", "auto_variant": "leg", "frames": {}, "offs": {}})
                _ = corner
            else:
                hv = m["heel_dir"]
                hv3 = unit(hv[0] * ex + hv[1] * tup) if hv else unit(tup)
                hv3 = unit(hv3 - np.dot(hv3, u) * u - np.dot(hv3, n) * n)
                e1 = -hv3                                             # từ lưng ra mép cánh liên kết
                outside = m["vis"] == "S"
                e2 = n if outside else -n
                zmid = (P1[2] + P2[2]) / 2 * 1000
                # chuẩn thanh cánh tại cao độ: dùng tiết diện thanh cánh của đoạn
                legsec = section_props(d["L"]["section"], lib_cache)
                gl = (d["L"]["heel_to_center"] or legsec["b"] / 2) / 1000
                tl = legsec["t"] / 1000
                off = n * (gl if outside else gl - tl)
                g = m["heel_to_center"] or s["b"] / 2
                ang = m["ang"] % 180
                typ = "G" if (ang < 3 or ang > 177) else "X"
                rec.update({"type": typ, "rule": "face", "face": "+-xy"[0], "variant": "bv", "auto_variant": "bv",
                            "frames": {"bv": [e1.round(6).tolist(), e2.round(6).tolist()]},
                            "offs": {"bv": off.round(6).tolist()}, "g": [g, 0.0],
                            "x_pair": False, "default_up": False, "side": "NGOAI" if outside else "TRONG",
                            "zmid_mm": round(zmid)})
            rec["mass_kg"] = round(rec["A_cm2"] * 1e-4 * rec["length"] * 7850, 3)
            out_members.append(rec)

    # --- vách ngang từ các mặt cắt (nhìn từ trên xuống; nét chiều dày LIỀN = cánh còn lại chĩa LÊN)
    plan_rep = {}
    for pname, spec in PLANS.items():
        seg, ymark, (tx, ty) = spec[:3]
        d = data[seg]
        lv = hor_levels(d) or [ymark]
        ycut = min(lv, key=lambda y: abs(y - ymark))
        if abs(ycut - ymark) > 12:
            ycut = ymark
        z = d["zmap"][1] + (ycut - d["zmap"][0]) * SC
        h = h_head if d.get("vertical_legs") else BASE_WIDTH / 2 + slope * z
        sz = (h + 500) / SC
        box = spec[3] if len(spec) > 3 else (tx - sz - 12, ty + 2, tx + sz + 12, ty + 2 * sz + 30)
        pm = R.members(doc, msp, box)
        # khung vách: cặp thanh dọc (và cặp thanh ngang) cách nhau gần 2h nhất (bỏ phần xà vẽ kèm)
        vx = sorted({round((m["c1"][0] + m["c2"][0]) / 2, 2) for m in pm if 88 < m["ang"] < 92})
        hy = sorted({round((m["c1"][1] + m["c2"][1]) / 2, 2) for m in pm if m["ang"] < 2 or m["ang"] > 178})

        def best_pair(vals):
            best = None
            for i, a_ in enumerate(vals):
                for b_ in vals[i + 1:]:
                    err = abs((b_ - a_) * SC - 2 * h) / (2 * h)
                    if best is None or err < best[0]:
                        best = (err, a_, b_)
            return best
        px, py = best_pair(vx), best_pair(hy)
        # vách vẽ đủ (phủ cả hai phía tâm) thì không xoay nhân bản
        allx = [p[0] for m in pm for p in (m["c1"], m["c2"])]
        ally = [p[1] for m in pm for p in (m["c1"], m["c2"])]
        full = (max(allx) - min(allx)) * SC > 1.4 * h and (max(ally) - min(ally)) * SC > 1.4 * h
        corner_plan = not full and not (px and py and px[0] < 0.12 and py[0] < 0.12)
        if corner_plan:
            # mặt cắt chỉ vẽ tam giác giằng góc: góc vuông dưới-trái = góc cột (-h, -h), xoay đủ 4 góc
            if not vx or not hy:
                plan_rep[pname] = {"error": "không tìm được góc", "n": len(pm)}
                continue
            cx = min(vx) + h / SC
            cy = min(hy) + h / SC
            hx_meas = hy_meas = None
        else:
            cx, cy = (px[1] + px[2]) / 2, (py[1] + py[2]) / 2
            hx_meas, hy_meas = (px[2] - px[1]) / 2 * SC, (py[2] - py[1]) / 2 * SC
        R.assign_labels(pm, R.text_labels(msp, box), cx)
        kept = 0
        for m in pm:
            if m["width"] >= 120 or not m.get("section") or m["all_hidden"] and m["vis"] is None:
                continue
            P1 = np.array([(m["c1"][0] - cx) * SC, (m["c1"][1] - cy) * SC, z]) / 1000
            P2 = np.array([(m["c2"][0] - cx) * SC, (m["c2"][1] - cy) * SC, z]) / 1000
            m["_P"] = (P1, P2)
            on_per = lambda P: max(abs(P[0]), abs(P[1])) * 1000 > h - 80
            ax_ = unit(P2 - P1)
            if on_per(P1) and on_per(P2) and (abs(ax_[0]) > 0.999 or abs(ax_[1]) > 0.999) and \
                    abs(abs(P1[0 if abs(ax_[1]) > 0.999 else 1]) * 1000 - h) < 120:
                continue                                       # thanh ngang mặt cột: đã có từ mặt đứng
            if max(abs(P1[0]), abs(P1[1]), abs(P2[0]), abs(P2[1])) * 1000 > h + 150:
                continue                                       # thuộc xà
            sct = section_props(m["section"], lib_cache)
            u = unit(P2 - P1)
            hv = m["heel_dir"]
            hv3 = unit(np.array([hv[0], hv[1], 0.0])) if hv else unit(np.cross([0, 0, 1.0], u))
            hv3 = unit(hv3 - np.dot(hv3, u) * u)
            up = m["vis"] == "S"
            e2 = np.array([0, 0, 1.0 if up else -1.0])
            e1 = unit(-hv3 - np.dot(-hv3, e2) * e2)
            g = m["heel_to_center"] or sct["b"] / 2
            for k in (range(4) if corner_plan else [0]):
                Rk = rot(k * math.pi / 2)
                Q1, Q2, f1, f2 = Rk @ P1, Rk @ P2, Rk @ e1, Rk @ e2
                mid += 1
                rec = {"id": mid, "p1": Q1.round(5).tolist(), "p2": Q2.round(5).tolist(),
                       "length": round(float(np.linalg.norm(Q2 - Q1)), 4), "section": m["section"],
                       "A_cm2": sct["A_geom_cm2"], "group": 0, "node1": None, "node2": None, "bolts": {},
                       "bolt": None, "seg": pname, "face_k": -1, "type": "G", "rule": "plan", "variant": "bv",
                       "auto_variant": "bv", "frames": {"bv": [f1.round(6).tolist(), f2.round(6).tolist()]},
                       "offs": {"bv": [0, 0, 0]}, "g": [g, 0.0], "x_pair": False, "default_up": up,
                       "side": "LEN" if up else "XUONG",
                       "drawing": {"vis": m["vis"], "edges": m["edges"], "heel_to_center": m["heel_to_center"],
                                   "width": m["width"], "ang2d": round(m["ang"], 2)}}
                rec["mass_kg"] = round(rec["A_cm2"] * 1e-4 * rec["length"] * 7850, 3)
                out_members.append(rec)
                kept += 1
        plan_rep[pname] = {**plan_rep.get(pname, {}), "z_mm": round(z), "h_mm": round(h),
                           "h_meas": [round(hx_meas), round(hy_meas)] if hx_meas else "góc", "n_read": len(pm),
                           "n_kept": kept, "corner_plan": corner_plan}
    report["plans"] = plan_rep
    # loại thanh vách trùng (mặt cắt đầy đủ bị nhân 4 khi xoay)
    seen, uniq = set(), []
    for m in out_members:
        key = tuple(sorted([tuple(np.round(m["p1"], 2)), tuple(np.round(m["p2"], 2))]))
        if m["rule"] == "plan" and key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    report["plan_duplicates_removed"] = len(out_members) - len(uniq)
    out_members = uniq

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    scene = {"members": out_members, "sections": lib_cache, "nodes": [], "plates": [], "bolts": [],
             "report": {"total_mass_kg": round(sum(m["mass_kg"] for m in out_members), 1),
                        "orientation": {"x_members": {"outside": [], "inside": []}, "clash_other": [],
                                        "clash_coplanar_overlap": [], "overridden": []},
                        "build": report}}
    (out / "n122_scene.json").write_text(json.dumps(scene, ensure_ascii=False))
    print(f"Thanh: {len(out_members)} | tiết diện: {sorted(lib_cache)}")
    print("Độ dốc DT-02 / DT-01:", round(slope, 5), round(slope1, 5), "| z đáy đường thanh cánh DT-01:", round(z_at))
    zs = [c for m in out_members for c in (m["p1"][2], m["p2"][2])]
    print("z:", round(min(zs), 3), "->", round(max(zs), 3), "m")
    return scene


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
