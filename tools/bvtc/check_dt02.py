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
    for key, x0 in (("cut1", x), ("cut1b", x), ("cut2", L - x), ("cut2b", L - x)):
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
    A1 = np.array([m["p1"] for m in ms], float)
    A2 = np.array([m["p2"] for m in ms], float)
    for i, b in enumerate(s["bolts"]):
        if b["kind"] in ("neo",):
            continue
        p = np.array(b["p"])
        ax = np.array(b["nut"])
        L = (b.get("grip_mm") or 20) / 1000
        pts = [p + ax * L * f for f in np.linspace(0.1, 0.9, 9)]
        # lọc thanh xa (cùng điều kiện như trước, tính cho mọi thanh một lần)
        d_end = np.minimum(np.linalg.norm(A1 - p, axis=1), np.linalg.norm(A2 - p, axis=1))
        d_line = np.linalg.norm(np.cross(A2 - A1, A1 - p), axis=1) / np.linalg.norm(A2 - A1, axis=1)
        for mi in np.nonzero(~((d_end > 3) & (d_line > 0.3)))[0]:
            m = ms[mi]
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


def prof_extra(m, xmm, Lmm):
    """Phần lệch độ sâu (mm) so với nối thẳng 2 đầu, tại xmm (thanh bẻ lệch)."""
    pr = m.get("prof")
    xmm = np.atleast_1d(np.asarray(xmm, float))
    if not pr:
        return np.zeros_like(xmm)
    xs, ds = [p[0] for p in pr], [p[1] for p in pr]
    return np.interp(xmm, xs, ds) - (ds[0] + (ds[-1] - ds[0]) * xmm / Lmm)


def bend_theta(m, xmm):
    """Góc bẻ (rad) cánh còn lại tại vị trí xmm dọc thanh (0 ngoài vùng bẻ, tuyến tính trong đoạn chuyển tiếp)."""
    xmm = np.atleast_1d(np.asarray(xmm, float))
    th = np.zeros_like(xmm)
    for bd in m.get("bends", []):
        t0 = np.radians(bd["theta_deg"])
        r = bd["ramp"]
        f = np.clip(np.minimum((xmm - (bd["x0"] - r)) / r, ((bd["x1"] + r) - xmm) / r), 0, 1)
        th = np.where(np.abs(f * t0) > np.abs(th), f * t0, th)
    return th


def where_v(m, S, Q, eps=0.0015):
    """Bản véc-tơ của where(): Q (n,3) -> mảng 0/1/2. Lọc trước các điểm xa đoạn trục thanh hơn bán kính bao R
    (chắc chắn ngoài thanh) - kết quả không đổi, nhanh hơn nhiều khi Q lớn."""
    Q = np.asarray(Q, float)
    if len(Q) > 64:
        P1, P2 = frame(m)[:2]
        s_ = S[m["section"]]
        bb = s_["b"] / 1000
        R = 2 * bb + abs(m["g"][0]) / 1000 + abs(m["g"][1]) / 1000 + 0.02 + max(0.0, -eps)
        if m.get("prof"):
            R += max(abs(d) for _, d in m["prof"]) / 1000 * 2
        ab = P2 - P1
        t = np.clip((Q - P1) @ ab / (ab @ ab), 0.0, 1.0)
        near = np.linalg.norm(Q - (P1 + np.outer(t, ab)), axis=1) <= R
        out = np.zeros(len(Q), int)
        if np.any(near):
            out[near] = _where_v(m, S, Q[near], eps)
        return out
    return _where_v(m, S, Q, eps)


def _where_v(m, S, Q, eps=0.0015):
    P1, P2, e1, e2 = frame(m)
    L = np.linalg.norm(P2 - P1)
    u = (P2 - P1) / L
    s = S[m["section"]]
    b, t = s["b"] / 1000, s["t"] / 1000
    g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
    # hình thanh trong app: P(f) = P1 + f (P2 - P1) + e1 (a - g1) + e2 (c - g2) (khung e1, e2 không nhất thiết
    # vuông góc trục khi 2 đầu có độ sâu khác nhau) -> giải hệ 3x3
    sol = np.linalg.solve(np.c_[P2 - P1, e1, e2], (Q - P1).T)
    if m.get("prof"):
        Q = Q - np.outer(prof_extra(m, sol[0] * L * 1000, L * 1000) / 1000, np.array(m["prof_n"]))
        sol = np.linalg.solve(np.c_[P2 - P1, e1, e2], (Q - P1).T)
    x = sol[0] * L
    a = sol[1] + g1
    c = sol[2] + g2
    ok = (x > eps) & (x < L - eps)
    # cánh còn lại bẻ cục bộ quanh mép lưng: tính lại (a, c) cho điểm trong vùng bẻ với khung đã xoay
    ab, cb = a.copy(), c.copy()
    th = bend_theta(m, x * 1000)
    if np.any(th != 0):
        H = P1[None, :] + np.outer(sol[0], P2 - P1) - e1 * g1 - e2 * g2
        v = Q - H
        uu = u
        co, si = np.cos(-th), np.sin(-th)
        # quay ngược v quanh u góc -th (Rodrigues)
        vr = v * co[:, None] + np.cross(uu, v) * si[:, None] + np.outer(v @ uu, uu) * (1 - co)[:, None]
        nb = th != 0
        ab[nb] = (vr @ e1)[nb]
        cb[nb] = (vr @ e2)[nb]
    in1 = ok & (a > eps) & (a < b - eps) & (c > eps) & (c < t - eps)
    in2 = ok & (ab > eps) & (ab < t - eps) & (cb > eps) & (cb < b - eps)

    def cutmask(fl, w):
        r = np.zeros(len(Q), bool)
        for key, x0 in (("cut1", x), ("cut1b", x), ("cut2", L - x), ("cut2b", L - x)):
            cc = m.get(key)
            if not cc:
                continue
            bb, aa = cc["b"] / 1000, cc["a"] / 1000
            near = x0 < bb
            # điểm ngoài đầu thanh (x0 < 0, khi kiểm khe có nới) lấy theo mép vát tại đầu thanh: vát lớn hơn luôn bớt
            # thép nhiều hơn (đơn điệu - cần cho tìm cỡ vát bằng chia đôi)
            x0c = np.maximum(x0, 0.0)
            if cc["flange"] == fl:
                r |= near & (w > b - aa * (1 - x0c / bb))
            if cc["flange"] == "heel":
                r |= near & ((fl == "out") | (w < aa * (1 - x0c / bb)))
        return r
    out = np.zeros(len(Q), int)
    out[in2 & ~cutmask("out", cb)] = 2
    out[in1 & ~cutmask("conn", a)] = 1
    return out


def cut_mask(m, x, L, fl, w, b):
    """Bản véc-tơ của cut_removed: x, w là mảng cùng kích thước."""
    r = np.zeros(np.broadcast(x, w).shape, bool)
    for key, x0 in (("cut1", x), ("cut1b", x), ("cut2", L - x), ("cut2b", L - x)):
        c = m.get(key)
        if not c:
            continue
        bb, aa = c["b"] / 1000, c["a"] / 1000
        near = x0 < bb
        f = aa * (1 - x0 / bb)
        if c["flange"] == fl:
            r |= near & (w > b - f)
        if c["flange"] == "heel":
            r |= near & ((fl == "out") | (w < f))
    return r


_SAMPLE_CACHE = {}
_GEOM_KEYS = ("p1", "p2", "poff1", "poff2", "e1", "e2", "frames", "g", "section", "cut1", "cut2", "cut1b", "cut2b",
              "bends", "prof",
              "prof_n", "rule")


def samples(m, S, step=0.01, xr=None, outside=False):
    """Điểm mẫu trên 2 cánh (mặt ngoài + giữa chiều dày), bỏ phần vát; có bẻ cánh, bẻ lệch.
    Tính bằng mảng numpy và nhớ theo hình học thanh (gọi lại khi thanh không đổi thì lấy ngay).
    xr = (x0, x1) m dọc thanh: chỉ lấy điểm có x trong khoảng (outside=True: ngoài khoảng) - đúng tập con của bộ
    điểm đầy đủ, dùng khi tìm cỡ vát ở đầu thanh (phần còn lại của thanh không đổi)."""
    key = (json.dumps({k: m.get(k) for k in _GEOM_KEYS}, sort_keys=True, default=str), step,
           tuple(round(v, 6) for v in xr) if xr else None, outside)
    hit = _SAMPLE_CACHE.get(key)
    if hit is not None:
        return hit
    P1, P2, e1, e2 = frame(m)
    L = np.linalg.norm(P2 - P1)
    u = (P2 - P1) / L
    s = S[m["section"]]
    b, t = s["b"] / 1000, s["t"] / 1000
    g1, g2 = m["g"][0] / 1000, m["g"][1] / 1000
    # dọc thanh: bước step ở thân, dày 3 mm trong 300 mm hai đầu (chỗ lấn nhỏ ở nút, góc cột hay nằm ở đầu thanh)
    fine = min(step, 0.003)
    e_ = min(0.3, L / 2)
    xs = np.unique(np.concatenate([np.arange(0.002, e_, fine), np.arange(e_, L - e_, step),
                                   np.arange(max(e_, L - e_), L - 0.001, fine)]))
    ws = np.linspace(0.002, b - 0.002, max(3, int(b / fine) + 1))
    cs = np.array([0.0015, t / 2, t - 0.0015])
    if xr is not None:
        inw = (xs >= xr[0]) & (xs <= xr[1])
        xs = xs[~inw] if outside else xs[inw]
    X, W, C = np.meshgrid(xs, ws, cs, indexing="ij")
    X, W, C = X.ravel(), W.ravel(), C.ravel()
    base = P1[None, :] + np.outer(X, u)
    if m.get("prof"):
        base = base + np.outer(prof_extra(m, X * 1000, L * 1000) / 1000, np.array(m["prof_n"]))
    H = base - e1 * g1 - e2 * g2
    # cánh liên kết
    keep1 = ~cut_mask(m, X, L, "conn", W, b)
    P_conn = (H + np.outer(W, e1) + np.outer(C, e2))[keep1]
    # cánh còn lại (có thể bẻ quanh mép lưng)
    keep2 = ~cut_mask(m, X, L, "out", W, b)
    V = np.outer(C, e1) + np.outer(W, e2)
    if m.get("bends"):
        th = bend_theta(m, X * 1000)
        co, si = np.cos(th)[:, None], np.sin(th)[:, None]
        V = V * co + np.cross(u, V) * si + np.outer(V @ u, u) * (1 - co)
    P_out = (H + V)[keep2]
    res = np.concatenate([P_conn, P_out]) if len(P_conn) + len(P_out) else np.zeros((0, 3))
    if len(_SAMPLE_CACHE) > 600:          # mỗi mục vài MB: giới hạn để chạy nhiều tờ song song không hết bộ nhớ
        _SAMPLE_CACHE.clear()
    _SAMPLE_CACHE[key] = res
    return res


_F21 = np.linspace(0, 1, 21)


def seg_dist(a1, a2, b1, b2):
    """Khoảng cách gần đúng 2 đoạn (21 điểm trên đoạn a tới đoạn b)."""
    a1, a2, b1, b2 = (np.asarray(v, float) for v in (a1, a2, b1, b2))
    P = a1 + np.outer(_F21, a2 - a1)
    ab = b2 - b1
    den = ab @ ab
    t = np.clip((P - b1) @ ab / den, 0, 1) if den > 0 else np.zeros(len(P))
    return float(np.min(np.linalg.norm(P - (b1 + np.outer(t, ab)), axis=1)))


def clashes(s, S, eps=0.001, only=None):
    ms = s["members"]
    res = []
    fr = {m["id"]: frame(m) for m in ms}
    lo = np.array([np.minimum(*fr[m["id"]][:2]) for m in ms])
    hi = np.array([np.maximum(*fr[m["id"]][:2]) for m in ms])
    for i, a in enumerate(ms):
        if only and a["id"] not in only:
            continue
        A1, A2 = fr[a["id"]][:2]
        # khoảng cách 2 hộp bao đầu-mút >= 0.2 thì chắc chắn seg_dist >= 0.2: bỏ qua sớm
        gap_ = np.linalg.norm(np.maximum(0, np.maximum(lo - hi[i], lo[i] - hi)), axis=1)
        cand = [ms[j] for j in np.nonzero(gap_ < 0.2)[0] if ms[j] is not a
                and seg_dist(A1, A2, *fr[ms[j]["id"]][:2]) < 0.2]
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


def bolt_body_points(b, shank=False):
    """Điểm mẫu phần đầu bu lông (+ vòng đệm) và đai ốc (+ vòng đệm, đuôi ren) - phần nằm NGOÀI các lớp thép kẹp.
    Bán kính 0,9 d (lục giác / vòng đệm), đầu cao 0,7 d + 3, đai ốc 0,8 d + 3 + đuôi ren."""
    d = b.get("d_mm", 16) / 1000
    p = np.array(b["p"], float)
    ax = np.array(b.get("nut") or b["axis"], float)
    ax = ax / np.linalg.norm(ax)
    g = (b.get("grip_mm") or 20) / 1000
    L = max((b.get("L_mm") or 0) / 1000, g + 0.8 * d + 0.003)
    t1 = np.cross(ax, [0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.cross(ax, [1.0, 0, 0])
    t1 = t1 / np.linalg.norm(t1)
    t2 = np.cross(ax, t1)
    pts = []
    parts = ((-(0.7 * d + 0.003), -0.001, 0.9 * d), (g + 0.001, g + 0.8 * d + 0.003, 0.9 * d), (g + 0.001, L, 0.5 * d))
    if shank:
        parts = ((0.001, g - 0.001, 0.5 * d),)
    for s0, s1, r in parts:
        for sv in np.linspace(s0, s1, 4):
            for rr in (r * 0.5, r):
                for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
                    pts.append(p + ax * sv + t1 * rr * np.cos(a) + t2 * rr * np.sin(a))
    return np.array(pts)


def bolt_steel(s, S):
    """Đầu / đai ốc bu lông cấn thép (thanh hoặc bản mã)."""
    res = []
    ms = s["members"]
    A1 = np.array([frame(m)[0] for m in ms])
    A2 = np.array([frame(m)[1] for m in ms])
    for i, b in enumerate(s["bolts"]):
        if b["kind"] in ("neo",):
            continue
        Q = bolt_body_points(b)
        c = Q.mean(0)
        ab = A2 - A1
        t = np.clip(np.einsum("ij,ij->i", c - A1, ab) / np.einsum("ij,ij->i", ab, ab), 0, 1)
        dn = np.linalg.norm(c - (A1 + ab * t[:, None]), axis=1)
        Qs = bolt_body_points(b, shank=True)
        p0 = np.array(b["p"], float)
        axv = np.array(b.get("nut") or b["axis"], float)
        Qa = p0 + np.outer(np.linspace(0.0005, (b.get("grip_mm") or 20) / 1000 - 0.0005, 9), axv)
        for j in np.nonzero(dn < 0.25)[0]:
            n = int(np.sum(where_v(ms[j], S, Q, 0.0005) > 0))
            if n:
                res.append({"bolt": i, "d": b.get("d_mm"), "m": ms[j]["id"], "sec": ms[j]["section"], "loai": "đầu/đai ốc",
                            "side": ms[j].get("side"), "n": n, "at": np.round(b["p"], 3).tolist()})
            # thân bu lông: thanh không phải lớp kẹp (trục bu lông không qua cánh) mà mép thanh lấn vào thân bu lông
            if not np.any(where_v(ms[j], S, Qa, 0.0) > 0):
                n2 = int(np.sum(where_v(ms[j], S, Qs, 0.0005) > 0))
                if n2:
                    res.append({"bolt": i, "d": b.get("d_mm"), "m": ms[j]["id"], "sec": ms[j]["section"],
                                "loai": "thân", "side": ms[j].get("side"), "n": n2, "at": np.round(b["p"], 3).tolist()})
    return res


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "bolts":
    s, S = load(sys.argv[1])
    res = bolt_steel(s, S)
    print("bu lông cấn thép:", len(res))
    for r in res[:30]:
        print(r)


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "all":
    # 1 lần nạp: bu lông xuyên dọc cánh (đã in ở trên) + thép-thép + bản mã-thép, chỉ in số lượng + 10 dòng đầu
    s, S = load(sys.argv[1])
    res = clashes(s, S)
    print("cặp chạm:", len(res))
    for r in res[:10]:
        print(r)
    res = plate_clashes(s, S)
    print("bản mã chạm thép:", len(res))
    for r in res[:10]:
        print(r)
    res = bolt_steel(s, S)
    print("bu lông cấn thép:", len(res))
    for r in res[:10]:
        print(r)
