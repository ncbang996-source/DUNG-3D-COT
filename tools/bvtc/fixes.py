"""Các bước gỡ chạm / chỉnh hình sau khi dựng 3D (dùng chung cho dt02.py, combine_faces.py, dn_plans.py).

- top_bend: thanh ngang đỉnh + bản mã + bu lông bẻ 2 đầu VÀO TRONG theo thanh biên xà X1 (DN-01 mặt cắt 1-1).
- corner_fix: vát góc mép cánh còn lại 2 thanh mặt kề đâm nhau ở góc cột (ĐỀ XUẤT).
- first_ok / EndWindow: tìm cỡ vát nhanh. Vát chỉ bớt thép ở vùng đầu thanh (b <= cửa sổ W), nên:
  (1) kiểm chạm chỉ cần lấy mẫu vùng cửa sổ đầu thanh, phần ngoài cửa sổ kiểm 1 lần lúc chưa vát (vát chỉ bớt thép
      -> phần ngoài không chạm lúc chưa vát thì không bao giờ chạm);
  (2) vát lớn hơn (cùng a, b tăng) cắt bỏ một tập lớn hơn -> chạm/không chạm đơn điệu theo b -> tìm b nhỏ nhất bằng
      chia đôi, cho đúng kết quả như thử lần lượt từ nhỏ đến lớn.
"""
import math
import re

import numpy as np

import check_dt02 as CK


def rot(k):
    c, s = math.cos(k * math.pi / 2), math.sin(k * math.pi / 2)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def first_ok(cands, ok):
    """Phần tử đầu tiên của cands (tăng dần) thỏa ok(c), biết ok đơn điệu (sai ... sai đúng ... đúng). None nếu không có."""
    if not cands or not ok(cands[-1]):
        return None
    lo, hi = 0, len(cands) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(cands[mid]):
            hi = mid
        else:
            lo = mid + 1
    return cands[lo]


def end_window(m, key, W):
    """Khoảng x (m, dọc thanh từ p1) của cửa sổ đầu thanh ứng với cut1 (đầu p1) / cut2 (đầu p2)."""
    P1, P2 = CK.frame(m)[:2]
    L = float(np.linalg.norm(P2 - P1))
    return (-1.0, W) if key == "cut1" else (L - W, L + 1.0)


class EndContact:
    """Kiểm chạm nhanh khi thử vát ở đầu thanh. pairs: [(x, kx, y, ky, eps)] - kiểm x với y (2 chiều); kx/ky = đầu
    đang thử vát (cut1/cut2) hoặc None (thanh không vát). Tạo đối tượng khi các đầu đang thử CHƯA vát thêm (nhiều thép
    nhất); vát về sau chỉ bớt thép nên:
    - điểm mẫu ngoài cửa sổ đầu thanh: kiểm 1 lần ở đây (chạm -> far_hit, dùng cách kiểm đầy đủ);
    - điểm mẫu của thanh không vát: chỉ giữ các điểm đang nằm trong thanh kia (về sau chỉ có thể ít đi)."""

    def __init__(self, S, pairs, W=0.6):
        self.S, self.W, self.pairs = S, W, pairs
        self.far_hit = False
        self.fixed = {}
        for i, (x, kx, y, ky, e) in enumerate(pairs):
            for j, (u, ku, v) in enumerate(((x, kx, y), (y, ky, x))):
                if ku is None:
                    pts = CK.samples(u, S)
                    self.fixed[(i, j)] = pts[CK.where_v(v, S, pts, e) > 0] if len(pts) else pts
                else:
                    far = CK.samples(u, S, xr=end_window(u, ku, W), outside=True)
                    if len(far) and np.any(CK.where_v(v, S, far, e) > 0):
                        self.far_hit = True

    def touching(self):
        S = self.S
        for i, (x, kx, y, ky, e) in enumerate(self.pairs):
            for j, (u, ku, v) in enumerate(((x, kx, y), (y, ky, x))):
                if ku is None:
                    sp = self.fixed[(i, j)]
                elif self.far_hit:
                    sp = CK.samples(u, S)
                else:
                    sp = CK.samples(u, S, xr=end_window(u, ku, self.W))
                if len(sp) and np.any(CK.where_v(v, S, sp, e) > 0):
                    return True
        return False


def top_bend(members, plates, bolts, tb):
    """Mặt cắt 1-1 DN-01: thanh ngang đỉnh L70x6 2080 (mặt có xà) BẺ 2 đầu 300 mm VÀO TRONG (về phía trục
    xà, chụm theo 2 thanh biên xà X1 - mặt bằng 1-1 tờ xà), độ dốc 327/1000 (~18 độ),
    bản mã đỉnh bẻ theo (nét bản mã vẽ dọc phần bẻ). Phần ngoài |x| > x_b (đầu đoạn thẳng 2080/2) xoay quanh trục
    đứng tại x = +-x_b, mặt lưng cột; thanh giữ 1 thanh, phần bẻ thể hiện bằng độ sâu theo chiều dài (prof)."""
    th = math.atan(tb["slope"])
    xb = tb["x_mm"] / 1000
    out = {"x_bend_mm": tb["x_mm"], "goc_do": round(math.degrees(th), 2), "thanh": 0, "ban_ma": 0, "bu_long": 0}
    for k in range(4):
        Rk = rot(k)
        loc = lambda p: Rk.T @ np.array(p)
        glo = lambda v: Rk @ np.array(v)
        near = lambda z: abs(z - tb["z_m"]) < 0.35
        nrm = glo([0, -1.0, 0])                                    # pháp tuyến ngoài mặt k
        # trục bẻ (đứng) tại x = +-x_b, nằm trong mặt áp của bản mã đỉnh (chung cho thanh, bản mã, bu lông)
        ybs = [loc(pl["origin"])[1] for pl in plates if pl.get("face_k") == k and near(pl["origin"][2])
               and abs(np.dot(pl["thick_dir"], nrm)) > 0.99 and pl.get("kind") != "filler"]
        if not ybs:
            continue
        ybk = max(ybs)

        def bend_pt(q, yb):
            x, y, z = q
            if abs(x) <= xb:
                return np.array(q), 0.0
            sg = 1 if x > 0 else -1
            phi = th * sg
            dx, dy = x - sg * xb, y - yb
            return np.array([sg * xb + dx * math.cos(phi) - dy * math.sin(phi),
                             yb + dx * math.sin(phi) + dy * math.cos(phi), z]), phi

        for m in members:
            if m.get("face_k") != k or m["rule"] != "face" or not near(m["p1"][2]) or \
                    abs(m["p1"][2] - m["p2"][2]) > 0.01:
                continue
            a, b = loc(m["p1"]), loc(m["p2"])
            if max(abs(a[0]), abs(b[0])) <= xb + 0.01:
                continue
            L0 = abs(b[0] - a[0])
            pts, ends = [], []
            for q in (a, b):
                ex = max(0.0, abs(q[0]) - xb)
                sg = 1 if q[0] > 0 else -1
                ends.append((sg * (xb + ex * math.cos(th)), ex * math.sin(th)))
            Lp = abs(ends[1][0] - ends[0][0])
            sg1 = 1 if ends[1][0] > ends[0][0] else -1
            x_of = lambda xl: (xl - ends[0][0]) * sg1 * 1000                 # mm dọc thanh từ p1
            pts = [[0.0, round(ends[0][1] * 1000, 2)]]
            for xl in sorted((-xb, xb), key=lambda v: x_of(v)):
                if 0 < x_of(xl) < Lp * 1000:
                    pts.append([round(x_of(xl), 1), 0.0])
            pts.append([round(Lp * 1000, 1), round(ends[1][1] * 1000, 2)])
            for key, (xe, de) in zip(("p1", "p2"), ends):
                q = loc(m[key])
                q[0] = xe
                m[key] = (glo(q) - nrm * de).round(5).tolist()
            m["prof"], m["prof_n"] = pts, (-nrm).round(6).tolist()
            m["length"] = round(L0, 4)                                 # chiều dài thật không đổi khi bẻ
            m["bend_note"] = "bẻ 2 đầu vào trong theo mặt cắt %s (%s)" % (tb["plan"], tb["note"])
            out["thanh"] += 1
        for pl in list(plates):
            if pl.get("face_k") != k or not near(pl["origin"][2]) or abs(np.dot(pl["thick_dir"], nrm)) < 0.99:
                continue
            o, a1, a2 = (np.array(pl[x]) for x in ("origin", "a1", "a2"))
            P3 = [o + a1 * u + a2 * v for u, v in pl["poly"]]
            xs = [loc(q)[0] for q in P3]
            if max(abs(x) for x in xs) <= xb + 0.005:
                continue
            yb = ybk
            sg = 1 if np.mean(xs) > 0 else -1
            # cắt đa giác tại x = sg*xb: phần trong giữ, phần ngoài xoay
            inner, outer = [], []
            n_ = len(P3)
            for i in range(n_):
                qa, qb = loc(P3[i]), loc(P3[(i + 1) % n_])
                ia, ib = sg * qa[0] <= xb, sg * qb[0] <= xb
                (inner if ia else outer).append(qa)
                if ia != ib:
                    t_ = (sg * xb - qa[0]) / (qb[0] - qa[0])
                    qc = qa + (qb - qa) * t_
                    inner.append(qc)
                    outer.append(qc)
            if len(outer) < 3:
                continue
            outer = [bend_pt(q, yb)[0] for q in outer]
            phi = th * sg
            a1o = Rk @ np.array([math.cos(phi), math.sin(phi), 0.0]) * np.sign(np.dot(a1, glo([1.0, 0, 0])) or 1)
            tdo = Rk @ np.array([-math.sin(phi), math.cos(phi), 0.0]) * np.sign(np.dot(pl["thick_dir"], glo([0, 1.0, 0])))
            for part, a1_, td_, nm_ in ((inner, a1, np.array(pl["thick_dir"]), ""), (outer, a1o, tdo, " (phần bẻ)")):
                G = [glo(q) for q in part]
                o_ = G[0]
                poly = [[round(float(np.dot(q - o_, a1_)), 5), round(float(np.dot(q - o_, a2)), 5)] for q in G]
                area = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                               for i in range(len(poly)))) / 2
                q_ = dict(pl, origin=o_.round(5).tolist(), a1=np.array(a1_).round(6).tolist(),
                          thick_dir=np.array(td_).round(6).tolist(), poly=poly, area_m2=round(area, 5),
                          mass_kg=round(area * pl["t_mm"] / 1000 * 7850, 2), reason=pl["reason"] + nm_)
                if nm_:
                    plates.append(q_)
                else:
                    plates[plates.index(pl)] = q_
            out["ban_ma"] += 1
        for b in bolts:
            if b.get("face_k") != k or not near(b["p"][2]):
                continue
            q = loc(b["p"])
            if abs(q[0]) <= xb:
                continue
            qn, phi = bend_pt(q, ybk)
            R2 = np.array([[math.cos(phi), -math.sin(phi), 0], [math.sin(phi), math.cos(phi), 0], [0, 0, 1.0]])
            b["p"] = glo(qn).round(5).tolist()
            for key in ("axis", "nut"):
                b[key] = (Rk @ R2 @ Rk.T @ np.array(b[key])).round(6).tolist()
            out["bu_long"] += 1
    return out


def corner_fix(members, LIB, rep):
    """2 thanh mặt kề nhau cùng bắt vào thanh cánh tại một cao độ: cánh còn lại (chĩa vào trong) đâm nhau ở góc
    cột -> vát góc mép cánh còn lại ở đầu thanh (bội 5 mm, nhỏ nhất) - ĐỀ XUẤT. Gọi lại sau khi ghép 2 kiểu mặt
    (combine_faces.py) để chỉ vát chỗ thật sự chạm với thanh mặt kề thật (góp ý: mặt không cấn thì không vát)."""

    def touching(a_, b_):
        sp = CK.samples(a_, LIB)
        if len(sp) and np.any(CK.where_v(b_, LIB, sp, 0.001) > 0):
            return True
        sp = CK.samples(b_, LIB)
        return bool(len(sp) and np.any(CK.where_v(a_, LIB, sp, 0.001) > 0))
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
            ec = EndContact(LIB, [(a_, keys[0], b_, keys[1], 0.001)])
            if a_.get(keys[0]) or b_.get(keys[1]):
                # đã vát ở cặp khác: tăng dần vát đang có (bội 5 mm) tới khi hết chạm
                def set_inc(inc):
                    for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                        c0 = m_.get(k_)
                        if c0 and c0["flange"] == "out":
                            c0["b"] = c0.setdefault("_b0", c0["b"]) + inc

                def ok_inc(inc):
                    set_inc(inc)
                    return not ec.touching()
                inc_ = first_ok(list(range(5, 120, 5)), ok_inc)
                set_inc(inc_ if inc_ is not None else 115)
                ok_ = inc_ is not None
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
                cand = [B_ for B_ in range(15, 170, 5) if not (best and A_ * B_ >= best[0])]

                def ok_b(B_, A_=A_):
                    for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                        m_[k_] = {"flange": "out", "a": A_, "b": B_}
                    return not ec.touching()
                B_ = first_ok(cand, ok_b)
                if B_ is not None:
                    best = (A_ * B_, A_, B_)
            for m_, k_ in ((a_, keys[0]), (b_, keys[1])):
                m_.pop(k_, None)
                if best:
                    m_[k_] = {"flange": "out", "a": best[1], "b": best[2],
                              "note": f"vát góc mép cánh còn lại {best[1]}x{best[2]}mm (ĐỀ XUẤT - bản vẽ không ghi; "
                                      "tránh chạm thanh mặt kề tại góc cột)"}
            rep["clash_fix"].append({"loai": "vát góc mép cánh còn lại đầu thanh tại góc cột (đề xuất)",
                                     "section": a_["section"] + "/" + b_["section"],
                                     "mm": f"{best[1]}x{best[2]}" if best else "không gỡ được"})


# ---------------------------------------------------------------- vát TAM GIÁC giữ khoảng cách bu lông tới mép
# Góp ý người dùng (gop_y 20261127_1721): chỉ vát tam giác ở góc mép cánh (không vát vuông / chữ nhật / cắt lùi cả cánh),
# vát vừa đủ, bu lông phải còn đủ khoảng cách tới mép cắt; có thể vát cánh thanh kia thay vì cắt nhiều thanh này.
EDGE = {16: 21.0, 20: 29.0, 24: 32.0}         # tim bu lông tới mép thanh giằng, min (ghi chú chung bản vẽ)


def local(m, Q):
    """Toạ độ địa phương của điểm Q (n,3) trên thanh: x dọc thanh từ p1 (mm), a ngang cánh liên kết từ lưng, c ngang
    cánh còn lại từ lưng (mm)."""
    P1, P2, e1, e2 = CK.frame(m)
    L = float(np.linalg.norm(P2 - P1))
    sol = np.linalg.solve(np.c_[P2 - P1, e1, e2], (np.atleast_2d(Q) - P1).T)
    return np.c_[sol[0] * L * 1000, sol[1] * 1000 + m["g"][0], sol[2] * 1000 + m["g"][1]], L * 1000


def bolt_spots(m, S, bolts):
    """Bu lông xuyên qua thanh m: [(x mm dọc thanh, w mm ngang cánh từ lưng, cánh 'conn'/'out', d)]."""
    out = []
    P1, P2 = CK.frame(m)[:2]
    for b in bolts:
        p = np.array(b["p"])
        ab = P2 - P1
        t = np.clip((p - P1) @ ab / (ab @ ab), 0, 1)
        if np.linalg.norm(p - (P1 + ab * t)) > 0.25:
            continue
        ax = np.array(b["axis"])
        Q = p + np.outer(np.linspace(0.0, (b.get("grip_mm") or 20) / 1000, 7), ax)
        w = CK.where_v(m, S, Q, -0.001)
        if not np.any(w > 0):
            continue
        fl = 1 if np.sum(w == 1) >= np.sum(w == 2) else 2
        lc, L = local(m, Q[w == fl].mean(0))
        x, a, c = lc[0]
        out.append((x, a if fl == 1 else c, "conn" if fl == 1 else "out", b.get("d_mm", 16)))
    return out


def tri_ok(m, key, cut, spots, S):
    """Vát tam giác (cut = {flange, a, b}) ở đầu key có giữ đủ khoảng cách mọi bu lông tới mép cắt không."""
    bw = S[m["section"]]["b"]
    L = float(np.linalg.norm(np.array(CK.frame(m)[1]) - np.array(CK.frame(m)[0]))) * 1000
    A, B = cut["a"], cut["b"]
    for x, w, fl, d in spots:
        if fl != cut["flange"]:
            continue
        x0 = x if key.startswith("cut1") else L - x
        if x0 >= B + EDGE.get(d, 21):
            continue
        # đường cắt: từ (x0 = 0, w = bw - A) tới (x0 = B, w = bw)
        if x0 < B and w > bw - A * (1 - x0 / B):
            return False
        dist = abs(x0 * A - (w - (bw - A)) * B) / math.hypot(A, B)
        # không làm khoảng cách tới mép kém hơn hiện trạng (VD đường đinh 35 trên L60: mép còn 25 < 29 của M20)
        if dist < min(EDGE.get(d, 21), bw - w):
            return False
    return True


def tri_search(cands, S, amax_frac=0.5, bmax=200, flanges=("out", "conn")):
    """cands: [(thanh, key, spots, touching)] - touching(): còn chạm không (sau khi đặt vát thử lên thanh đó). Thử vát tam giác (cánh còn lại / cánh liên kết, a <= amax_frac*b cánh, bội 5 mm)
    trên từng thanh ứng viên, chọn diện tích cắt nhỏ nhất làm touching() = False. Trả (diện tích, thanh, key, cut) hoặc
    None. Thanh đã có vát ở đầu đó thì bỏ qua (không chồng 2 vát)."""
    best = None
    for m, key, spots, touching in cands:
        if m.get(key):
            continue
        bw = S[m["section"]]["b"]
        for fl in flanges:
            amax = int(bw * amax_frac) if fl != "heel" else int(m["g"][0]) - 10
            for A in range(5, amax + 1, 5):
                cand = [B for B in range(5, bmax + 1, 5) if not (best and A * B / 2 >= best[0])
                        and tri_ok(m, key, {"flange": fl, "a": A, "b": B}, spots, S)]

                def ok(B, A=A, fl=fl, m=m, key=key, touching=touching):
                    m[key] = {"flange": fl, "a": A, "b": B}
                    r = not touching()
                    m.pop(key, None)
                    return r
                B = first_ok(cand, ok)
                if B is not None:
                    best = (A * B / 2, m, key, {"flange": fl, "a": A, "b": B})
    return best
