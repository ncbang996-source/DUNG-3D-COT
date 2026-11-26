"""Kiểm tra va chạm mô hình DT-02 (dữ liệu scene): bu lông xuyên dọc cánh thép, thép chồng thép.

Chạy: python3 tools/bvtc/check_dt02.py data/n122/dt02_scene.json
"""
import json
import sys

import numpy as np


def load(p):
    s = json.load(open(p))
    return s, s["sections"]


def frame(m):
    if m["rule"] == "leg":
        e1, e2 = np.array(m["e1"]), np.array(m["e2"])
    else:
        e1, e2 = (np.array(v) for v in m["frames"]["bv"])
    P1 = np.array(m["p1"]) + np.array(m.get("poff1", [0, 0, 0]))
    P2 = np.array(m["p2"]) + np.array(m.get("poff2", [0, 0, 0]))
    return P1, P2, e1, e2


def cut_removed(m, x, L, fl, w, b):
    """Điểm (x dọc thanh, w ngang cánh từ lưng) trên cánh fl có nằm trong phần vát không."""
    for key, x0 in (("cut1", x), ("cut2", L - x)):
        c = m.get(key)
        if not c or x0 >= c["b"] / 1000:
            continue
        if c["flange"] == fl and w > b - c["a"] / 1000 * (1 - x0 / (c["b"] / 1000)):
            return True
        if c["flange"] == "heel" and (fl == "out" or w < c["a"] / 1000 * (1 - x0 / (c["b"] / 1000))):
            return True
    return False


def where(m, S, q, eps=0.0015):
    """0 = ngoài, 1 = trong cánh liên kết (e1), 2 = trong cánh còn lại (e2)."""
    P1, P2, e1, e2 = frame(m)
    L = np.linalg.norm(P2 - P1)
    u = (P2 - P1) / L
    s = S[m["section"]]
    b, t = s["b"] / 1000, s["t"] / 1000
    g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
    x = np.dot(q - P1, u)
    if not (eps < x < L - eps):
        return 0
    base = P1 + u * x
    a = np.dot(q - base, e1) + g1
    c = np.dot(q - base, e2) + g2
    if eps < a < b - eps and eps < c < t - eps and not cut_removed(m, x, L, "conn", a, b):
        return 1
    if eps < a < t - eps and eps < c < b - eps and not cut_removed(m, x, L, "out", c, b):
        return 2
    return 0


def bolt_issues(s, S):
    out = []
    ms = s["members"]
    for i, b in enumerate(s["bolts"]):
        if b["kind"] in ("neo",):
            continue
        p = np.array(b["p"])
        ax = np.array(b["nut"])
        L = (b.get("grip_mm") or 20) / 1000
        pts = [p + ax * L * f for f in np.linspace(0.1, 0.9, 9)]
        for m in ms:
            if min(np.linalg.norm(np.array(m["p1"]) - p), np.linalg.norm(np.array(m["p2"]) - p)) > 3 and \
                    np.linalg.norm(np.cross(np.array(m["p2"]) - np.array(m["p1"]), np.array(m["p1"]) - p)) / \
                    np.linalg.norm(np.array(m["p2"]) - np.array(m["p1"])) > 0.3:
                continue
            P1, P2, e1, e2 = frame(m)
            hits = [where(m, S, q) for q in pts]
            for fl in (1, 2):
                n_ = e2 if fl == 1 else e1          # pháp tuyến cánh
                if hits.count(fl) and abs(np.dot(n_, ax)) < 0.5:
                    out.append((i, b["kind"], m["id"], m["section"], m.get("side"), fl))
    return out


if __name__ == "__main__":
    s, S = load(sys.argv[1])
    iss = bolt_issues(s, S)
    print("bu lông xuyên dọc cánh:", len(iss))
    for x in iss[:40]:
        b = s["bolts"][x[0]]
        print(x, np.round(b["p"], 3).tolist())


EDGE = {16: 21, 20: 29, 24: 32}      # mép tối thiểu (ghi chú chung bản vẽ)
ENDD = {16: 25, 20: 30, 24: 40}


def bolt_edges(s, S):
    """Mỗi bu lông: cánh thép nó xuyên (vuông góc), khoảng cách tới mép cánh / đầu thanh."""
    rep = []
    for i, b in enumerate(s["bolts"]):
        if b["kind"] == "neo":
            continue
        p = np.array(b["p"])
        ax = np.array(b["nut"])
        L = (b.get("grip_mm") or 20) / 1000
        through = []
        for m in s["members"]:
            P1, P2, e1, e2 = frame(m)
            Lm = np.linalg.norm(P2 - P1)
            u = (P2 - P1) / Lm
            sct = S[m["section"]]
            bb, t = sct["b"] / 1000, sct["t"] / 1000
            g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
            for fl, n_, ea in ((1, e2, e1), (2, e1, e2)):
                if abs(np.dot(n_, ax)) < 0.9:
                    continue
                # giao trục bu lông với mặt giữa cánh
                c0 = (t / 2 - (g2 if fl == 1 else g1))
                base_n = np.dot(P1, n_) + c0
                den = np.dot(ax, n_)
                tt = (base_n - np.dot(p, n_)) / den
                if not (-0.002 <= tt <= L + 0.002):
                    continue
                q = p + ax * tt
                x = np.dot(q - P1, u)
                if not (-0.06 < x < Lm + 0.06):
                    continue
                w = np.dot(q - P1 - u * x, ea) + (g1 if fl == 1 else g2)
                if -0.04 < w < bb + 0.04 and -0.06 < x < Lm + 0.06:
                    through.append({"id": m["id"], "sec": m["section"], "fl": fl, "w_mm": round(w * 1000, 1),
                                    "toe_mm": round((bb - w) * 1000, 1), "end_mm": round(min(x, Lm - x) * 1000, 1),
                                    "in": 0 < w < bb and 0 < x < Lm})
        rep.append((i, b, through))
    return rep


def where_v(m, S, Q, eps=0.0015):
    """Bản véc-tơ của where(): Q (n,3) -> mảng 0/1/2."""
    P1, P2, e1, e2 = frame(m)
    L = np.linalg.norm(P2 - P1)
    u = (P2 - P1) / L
    s = S[m["section"]]
    b, t = s["b"] / 1000, s["t"] / 1000
    g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
    # hình thanh trong app: P(f) = P1 + f (P2 - P1) + e1 (a - g1) + e2 (c - g2) (khung e1, e2 không nhất thiết
    # vuông góc trục khi 2 đầu có độ sâu khác nhau) -> giải hệ 3x3
    sol = np.linalg.solve(np.c_[P2 - P1, e1, e2], (Q - P1).T)
    x = sol[0] * L
    a = sol[1] + g1
    c = sol[2] + g2
    ok = (x > eps) & (x < L - eps)
    in1 = ok & (a > eps) & (a < b - eps) & (c > eps) & (c < t - eps)
    in2 = ok & (a > eps) & (a < t - eps) & (c > eps) & (c < b - eps)

    def cutmask(fl, w):
        r = np.zeros(len(Q), bool)
        for key, x0 in (("cut1", x), ("cut2", L - x)):
            cc = m.get(key)
            if not cc:
                continue
            bb, aa = cc["b"] / 1000, cc["a"] / 1000
            near = x0 < bb
            if cc["flange"] == fl:
                r |= near & (w > b - aa * (1 - x0 / bb))
            if cc["flange"] == "heel":
                r |= near & ((fl == "out") | (w < aa * (1 - x0 / bb)))
        return r
    out = np.zeros(len(Q), int)
    out[in2 & ~cutmask("out", c)] = 2
    out[in1 & ~cutmask("conn", a)] = 1
    return out


def samples(m, S, step=0.01):
    """Điểm mẫu trên 2 cánh (mặt ngoài + giữa chiều dày), bỏ phần vát."""
    P1, P2, e1, e2 = frame(m)
    L = np.linalg.norm(P2 - P1)
    u = (P2 - P1) / L
    s = S[m["section"]]
    b, t = s["b"] / 1000, s["t"] / 1000
    g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
    pts = []
    for x in np.arange(0.002, L - 0.001, step):
        base = P1 + u * x
        for w in np.linspace(0.002, b - 0.002, max(3, int(b / step) + 1)):
            for c in (0.0015, t / 2, t - 0.0015):
                if not cut_removed(m, x, L, "conn", w, b):
                    pts.append(base + e1 * (w - g1) + e2 * (c - g2))
                if not cut_removed(m, x, L, "out", w, b):
                    pts.append(base + e1 * (c - g1) + e2 * (w - g2))
    return np.array(pts)


def seg_dist(a1, a2, b1, b2):
    best = 1e9
    for f in np.linspace(0, 1, 21):
        p = a1 + (a2 - a1) * f
        ab = b2 - b1
        t = np.clip(np.dot(p - b1, ab) / np.dot(ab, ab), 0, 1)
        best = min(best, np.linalg.norm(p - (b1 + ab * t)))
    return best


def clashes(s, S, eps=0.001, only=None):
    ms = s["members"]
    res = []
    fr = {m["id"]: frame(m) for m in ms}
    for i, a in enumerate(ms):
        if only and a["id"] not in only:
            continue
        A1, A2 = fr[a["id"]][:2]
        cand = [b for b in ms if b is not a and seg_dist(A1, A2, *fr[b["id"]][:2]) < 0.2]
        if not cand:
            continue
        pts = samples(a, S)
        for b in cand:
            hit = pts[where_v(b, S, pts, eps) > 0]
            if len(hit):
                res.append({"a": a["id"], "a_sec": a["section"], "a_rule": a["rule"], "b": b["id"],
                            "b_sec": b["section"], "b_rule": b["rule"], "n": len(hit),
                            "at": (hit.mean(axis=0)).round(3).tolist()})
    return res


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "clash":
    s, S = load(sys.argv[1])
    face0 = None
    res = clashes(s, S)
    print("cặp chạm:", len(res))
    for r in res:
        print(r)


def plate_points(pl, step=0.008):
    o, a1, a2 = (np.array(pl[k]) for k in ("origin", "a1", "a2"))
    td = np.array(pl["thick_dir"]) * pl["t_mm"] / 1000
    poly = pl["poly"]
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    pts = []

    def inside2(x, y):
        c = False
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                c = not c
        return c
    for x in np.arange(min(xs) + 0.002, max(xs) - 0.001, step):
        for y in np.arange(min(ys) + 0.002, max(ys) - 0.001, step):
            if inside2(x, y):
                for f in (0.15, 0.5, 0.85):
                    pts.append(o + a1 * x + a2 * y + td * f)
    return np.array(pts)


def plate_clashes(s, S):
    res = []
    for k, pl in enumerate(s["plates"]):
        pts = plate_points(pl)
        if not len(pts):
            continue
        c = pts.mean(axis=0)
        for m in s["members"]:
            P1, P2 = frame(m)[:2]
            if seg_dist(P1, P2, c, c + 1e-6) > 0.8:
                continue
            h = pts[where_v(m, S, pts, 0.001) > 0]
            if len(h):
                res.append({"plate": k, "reason": pl["reason"], "m": m["id"], "sec": m["section"],
                            "side": m.get("side"), "n": len(h), "at": h.mean(axis=0).round(3).tolist()})
    return res


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "plates":
    s, S = load(sys.argv[1])
    res = plate_clashes(s, S)
    print("bản mã chạm thép:", len(res))
    for r in res:
        print(r)
