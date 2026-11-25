"""Đọc hình chiếu đứng của bản vẽ chế tạo cột (2D, tỉ lệ 1/25) thành danh sách thanh thép góc.

Mỗi thanh thép góc trên mặt đứng (nhìn từ NGOÀI vào) gồm: 2 nét mép, 1 hay nhiều đường tâm (CENTER),
1 nét chiều dày cánh còn lại sát mép LƯNG. Nét chiều dày KHUẤT -> cánh còn lại chĩa vào trong (thanh
TRONG); nét LIỀN -> chĩa ra ngoài (thanh NGOÀI).
"""
from __future__ import annotations

import math
import re

SC = 25.0          # 1 đơn vị bản vẽ = 25 mm
SECTION_RE = re.compile(r"^H?L\d+x\d+$", re.I)


def linetype(doc, e):
    l = e.dxf.get("linetype", "BYLAYER")
    if l.upper() == "BYLAYER":
        l = doc.layers.get(e.dxf.layer).dxf.linetype
    l = l.upper()
    return "A" if l.startswith("CENTER") else ("H" if l.startswith(("HIDDEN", "DASH")) else "S")


def segments(doc, msp, box, layers=("0", "COT")):
    x0, y0, x1, y1 = box
    ins = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    out = []
    for e in msp:
        if e.dxf.layer not in layers:
            continue
        t = e.dxftype()
        if t == "LINE":
            pairs = [((e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1]))]
        elif t == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
            pairs = list(zip(pts, pts[1:]))
        else:
            continue
        k = linetype(doc, e)
        for a, b in pairs:
            if ins(a) and ins(b):
                ln = math.dist(a, b)
                if ln * SC >= 150:
                    out.append({"a": a, "b": b, "k": k, "ang": math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi,
                                "len": ln})
    return out


def _rel(l, o):
    ax = (math.cos(l["ang"]), math.sin(l["ang"]))
    nx = (-ax[1], ax[0])
    f = lambda p: ((p[0] - l["a"][0]) * nx[0] + (p[1] - l["a"][1]) * nx[1],
                   (p[0] - l["a"][0]) * ax[0] + (p[1] - l["a"][1]) * ax[1])
    (oa, sa), (ob, sb) = f(o["a"]), f(o["b"])
    return (oa + ob) / 2, sorted((sa, sb))


def members(doc, msp, box, labels=None):
    S = segments(doc, msp, box)
    n = len(S)
    par = list(range(n))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(n):
        _, si = _rel(S[i], S[i])
        for j in range(i + 1, n):
            da = abs((S[i]["ang"] - S[j]["ang"] + math.pi / 2) % math.pi - math.pi / 2)
            if da > math.radians(0.8):
                continue
            off, s = _rel(S[i], S[j])
            ov = min(s[1], si[1]) - max(s[0], si[0])
            if abs(off) * SC < 160 and ov > 0.3 * min(S[i]["len"], S[j]["len"]):
                par[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    out = []
    for g in groups.values():
        cen = [S[i] for i in g if S[i]["k"] == "A"]
        if not cen:
            continue
        ref = max(cen, key=lambda l: l["len"])
        items = [(_rel(ref, S[i]), S[i]["k"]) for i in g]
        _, sr = _rel(ref, ref)
        Lr = sr[1] - sr[0]
        # nét mép/nét chiều dày phải chạy dọc phần đáng kể của thanh (loại nét ngắn của thanh khác song song)
        ed = sorted((round(o * SC, 1), k) for (o, sp), k in items
                    if k != "A" and min(sp[1], sr[1]) - max(sp[0], sr[0]) >= 0.3 * Lr)
        if len(ed) < 2:
            ed = sorted((round(o * SC, 1), k) for (o, _), k in items if k != "A")
        if len(ed) < 2:
            continue
        lo, hi = ed[0][0], ed[-1][0]
        heel = vis = tline = None
        for o, k in ed:
            if lo < o < hi:
                if o - lo <= 25:
                    heel, tline, vis = "lo", o - lo, k
                elif hi - o <= 25:
                    heel, tline, vis = "hi", hi - o, k
        ax = (math.cos(ref["ang"]), math.sin(ref["ang"]))
        nx = (-ax[1], ax[0])
        # đoạn trên đường tâm chuẩn, phủ hết các nét của thanh
        ss = [s for (_, s), _ in items]
        smin, smax = min(s[0] for s in ss), max(s[1] for s in ss)
        p1 = (ref["a"][0] + ax[0] * smin, ref["a"][1] + ax[1] * smin)
        p2 = (ref["a"][0] + ax[0] * smax, ref["a"][1] + ax[1] * smax)
        # chính đường tâm chuẩn (đường tim làm việc)
        _, sref = _rel(ref, ref)
        c1 = (ref["a"][0] + ax[0] * sref[0], ref["a"][1] + ax[1] * sref[0])
        c2 = (ref["a"][0] + ax[0] * sref[1], ref["a"][1] + ax[1] * sref[1])
        # đầu thanh THẬT: phạm vi các nét mép (không tính đường tâm, đường tâm vẽ kéo tới nút)
        se = [sp for (o, sp), k in items if k != "A" and min(sp[1], sr[1]) - max(sp[0], sr[0]) >= 0.3 * Lr]
        if se:
            e0, e1_ = min(x[0] for x in se), max(x[1] for x in se)
        else:
            e0, e1_ = smin, smax
        b1 = (ref["a"][0] + ax[0] * e0, ref["a"][1] + ax[1] * e0)
        b2 = (ref["a"][0] + ax[0] * e1_, ref["a"][1] + ax[1] * e1_)
        # đặt b1 cùng phía c1
        if math.dist(b1, c1) > math.dist(b1, c2):
            b1, b2 = b2, b1
        hv = None
        if heel:
            hv = nx if heel == "hi" else (-nx[0], -nx[1])
        heel_off = (hi if heel == "hi" else lo) if heel else None   # vị trí lưng so với đường tâm chuẩn (mm)
        cofs = sorted({round(o * SC, 1) for (o, _), k in items if k == "A"})
        out.append({
            "nvec": nx, "heel_signed": heel_off,
            "ang": math.degrees(ref["ang"]), "p1": p1, "p2": p2, "c1": c1, "c2": c2, "b1": b1, "b2": b2,
            "width": round(hi - lo), "heel_dir": hv, "heel_to_center": (abs(heel_off) if heel else None),
            "vis": vis, "tline": tline, "centers_rel": cofs, "edges": "".join(k for _, k in ed),
            "all_hidden": all(k == "H" for _, k in ed),
        })
    if labels is not None:
        assign_labels(out, labels)
    return out


def text_labels(msp, box):
    x0, y0, x1, y1 = box
    res = []
    for e in msp.query("TEXT"):
        p = e.dxf.insert
        t = e.dxf.text.strip()
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and SECTION_RE.match(t):
            res.append((t.upper(), (p[0], p[1])))
    return res


def assign_labels(ms, labels, xc=None):
    """Gán tiết diện: nhãn gần thanh nhất (ưu tiên bề rộng b khớp +-12 mm); thanh chưa có nhãn lấy
    nhãn của thanh đối xứng gương qua trục giữa mặt (xc) nếu có."""
    def cand(m, tol_b):
        best = None
        ax = (m["p2"][0] - m["p1"][0], m["p2"][1] - m["p1"][1])
        L = math.hypot(*ax)
        u = (ax[0] / L, ax[1] / L)
        for t, p in labels:
            b = int(re.match(r"H?L(\d+)", t).group(1))
            if tol_b is not None and abs(b - m["width"]) > tol_b:
                continue
            if m["width"] >= 120 and b < 120:
                continue                                  # thanh cánh chỉ nhận nhãn cánh >= 120
            q = (p[0] - m["p1"][0], p[1] - m["p1"][1])
            s = q[0] * u[0] + q[1] * u[1]
            d = abs(q[0] * u[1] - q[1] * u[0])
            if -0.05 * L <= s <= 1.05 * L and (best is None or d < best[0]):
                best = (d, t)
        return best
    for m in ms:
        best = cand(m, 12)
        if not best or best[0] * SC > 400:
            best2 = cand(m, None)
            best = best2 if best2 and best2[0] * SC <= 250 else best
        m["section"] = best[1] if best and best[0] * SC <= 400 else None
    if xc is not None:
        for m in ms:
            if m["section"]:
                continue
            mx = lambda p: (2 * xc - p[0], p[1])
            for o in ms:
                if o["section"] and abs(o["width"] - m["width"]) <= 12 and \
                        min(math.dist(mx(m["p1"]), o["p1"]) + math.dist(mx(m["p2"]), o["p2"]),
                            math.dist(mx(m["p1"]), o["p2"]) + math.dist(mx(m["p2"]), o["p1"])) < 2:
                    m["section"] = o["section"]
                    m["section_from"] = "mirror"
                    break
