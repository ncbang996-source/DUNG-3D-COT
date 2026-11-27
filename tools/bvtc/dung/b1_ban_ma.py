"""Bản mã mặt đứng (lớp Banma, nét khuất, bản hàn vuông góc), khớp hình chi tiết theo số hiệu, lỗ chờ.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (Lg, _, a_, b_, best, d_, doc, keep, legs, m, msp, rep, segs, t, xline,) = (V.get(k_) for k_ in ("Lg", "_", "a_", "b_", "best", "d_", "doc", "keep", "legs", "m", "msp", "rep", "segs", "t", "xline",))
    # --- bản mã (lớp Banma) có nút liên kết bên trong, độ dày theo nhãn "d N"
    x0, ya, x1, yb = ST.BOX
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
    hip = ST.CFG.get("hidden_inner_plates")
    if hip:
        ents = [e for e in msp.query('LWPOLYLINE[layer=="COT"]') if R.linetype(doc, e) == "H"
                and all(inb((q[0], q[1])) for q in e.get_points())]
        for pts in banma_loops(msp, ents=ents):
            xs_, ys_ = [q[0] for q in pts], [q[1] for q in pts]
            if (max(xs_) - min(xs_)) * SC < 150 or (max(ys_) - min(ys_)) * SC < 150:
                continue
            if not any(dist_line(q, L_["w1"], L_["w2"]) < 6 for q in pts for L_ in legs):
                continue
            if min(ys_) < min(Lg["a"][1], Lg["b"][1]) + ST.BASE_ZONE / SC:
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
                   for nm_, c_ in SHEETS.items() for b_ in [c_["box"]] if nm_ != ST.SHEET)

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
            hm_ = ST.CFG.get("detail_hole_max")
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
    if ST.CFG.get("top_kink"):
        xb_ = xline(Lg, KY) - Lg["g"] / SC
        tops_ = [max(sg["a"][1], sg["b"][1]) for sg in segs if sg["k"] == "S"
                 and abs(math.degrees(sg["ang"]) - 90) < 0.5 and min(sg["a"][1], sg["b"][1]) >= KY - 0.3
                 and abs((sg["a"][0] + sg["b"][0]) / 2 - xb_) < 0.3]
        KTOP = max(tops_) if tops_ else None
    _l = locals()
    return {k_: _l[k_] for k_ in ['A_', 'KTOP', 'KY', 'P', 'P2', '_', 'a1', 'a2', 'b2', 'banma', 'bolt_ins', 'c', 'c_', 'cxy_', 'd2', 'db', 'i', 'idx', 'inb', 'near', 'ok_', 'p', 'pl', 'plates2d', 'pts', 'res_', 'x0', 'x1', 'xs_', 'y0_', 'y1_', 'ys_'] if k_ in _l}

