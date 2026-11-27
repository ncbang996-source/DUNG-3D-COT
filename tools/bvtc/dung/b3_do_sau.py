"""Thanh chủ từng đầu thanh, thanh cánh nhiều đoạn (back_extra, leg_sec_at), lan truyền độ sâu.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (KTOP, KY, L, Lg, ONTOP, P_, _, a_, b_, best, cxy_, d_, db, inb, keep, legs, m, msp, p, pl, plates2d, pts_, rep, t, t_, u_, xline, y0_, y1_, zf,) = (V.get(k_) for k_ in ("KTOP", "KY", "L", "Lg", "ONTOP", "P_", "_", "a_", "b_", "best", "cxy_", "d_", "db", "inb", "keep", "legs", "m", "msp", "p", "pl", "plates2d", "pts_", "rep", "t", "t_", "u_", "xline", "y0_", "y1_", "zf",))
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
    BSTUB = ST.CFG.get("bottom_stub")
    STUB_OUT = (sec(BSTUB["section"])["t"] - tl) if BSTUB else 0.0
    SPL = ST.CFG.get("leg_splices", [])

    def back_extra(zmm):
        """Lưng thanh cánh lệch (mm, + ra ngoài) so với lưng thanh cánh chính tại cao độ zmm: các đoạn thanh cánh
        khác chiều dày ghép THẲNG MẶT TRONG (DN-02 B-B: HL150x12 lồi 3; DN-01 A-A: L100x7 lùi 2, bù tấm d2)."""
        if BSTUB and zmm < BSTUB["joint_mm"]:
            return STUB_OUT
        e_ = 0.0
        for sp_ in SPL:
            if sp_.get("above") and zmm > sp_["z"]:
                e_ = sec(sp_["above"])["t"] - tl
        return e_

    def leg_sec_at(zmm):
        if BSTUB and zmm < BSTUB["joint_mm"]:
            return BSTUB["section"]
        s_ = Lg["section"]
        for sp_ in SPL:
            if sp_.get("above") and zmm > sp_["z"]:
                s_ = sp_["above"]
        return s_
    for pl in plates2d:                       # bản mã áp mặt ngoài cánh thanh cánh (A-A) nếu nằm trên thanh cánh
        on_leg_ = any(dist_line(n, L_["w1"], L_["w2"]) < 3.0 for n in pl["nodes"] for L_ in legs)
        pl["delta0"] = gl if on_leg_ else None
        pl["on_leg_fixed"] = on_leg_
        if pl.get("hidden"):
            pl["delta0"], pl["on_leg_fixed"] = gl, True       # như bản mã nút thanh cánh: áp mặt ngoài cánh
        if BSTUB and on_leg_:
            zc_ = zf(sum(q[1] for q in pl["pts"]) / len(pl["pts"]))
            zlo_ = min(zf(q[1]) for q in pl["pts"])
            zhi_ = max(zf(q[1]) for q in pl["pts"])
            # bản mã trên phần đứng DT-01 / bản nối B-B: áp lưng HL150x12 (lưng lồi ra 3 mm so với HL130x9 vì
            # 2 thanh cánh thẳng mặt trong) hoặc tấm d3; bản qua mối nối áp lưng thanh lồi hơn; trên L100x7: lùi 2
            pl["delta0"] = gl + max(back_extra(zlo_), back_extra(zhi_))
            for sp_ in [dict(z=BSTUB["joint_mm"], L=BSTUB.get("plate_L", 670.0), t=BSTUB.get("plate_t", 10))] + \
                    [dict(z=x_["z"], L=x_.get("plate_L", 690.0), t=x_.get("plate_t", 10)) for x_ in SPL]:
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
    shims_ = []
    if BSTUB and STUB_OUT > 0:
        # tấm d3 (231, 145x330, chi tiết DN-02) dưới bản nối ngoài B-B, trên lưng HL130x9 (bù 3 mm), từ lưng ra
        shims_.append((BSTUB["joint_mm"], BSTUB["gap"], 145.0, 330.0, STUB_OUT,
                       "tấm d3 (231) bù chiều dày, dưới bản nối ngoài B-B"))
    for sp_ in SPL:
        if sp_.get("shim"):
            sh_ = sp_["shim"]
            shims_.append((sp_["z"], sp_["gap"], sh_["w"], sh_["L"], sh_["t"], sh_["note"]))
    yz = lambda zmm: min(Lg["a"][1], Lg["b"][1]) + zmm / SC
    for jb, gap_, w_, Ls_, t_, note_ in shims_:
        for L_ in legs:
            sgn = 1 if L_ is Lg else -1
            xb0 = lambda y_: xline(L_, y_) - sgn * L_["g"] / SC
            y0_, y1_ = yz(jb + gap_ / 2), yz(jb + gap_ / 2 + Ls_)
            pts_ = [(xb0(y0_), y0_), (xb0(y0_) + sgn * w_ / SC, y0_), (xb0(y1_) + sgn * w_ / SC, y1_), (xb0(y1_), y1_)]
            plates2d.append({"pts": pts_, "pts0": pts_, "t": t_, "nodes": [], "on_leg_fixed": True,
                             "delta0": gl + back_extra(jb + gap_ / 2 + 1), "note": note_, "hidden": True, "d3": True})
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
            # thanh TRONG chạy liên tục qua bản mã (góp ý: thanh ngang DT-02 không cắt ở nút giữa): bản mã áp lưng nó
            if not m["out"] and m["plate"][0] is not pl and m["plate"][1] is not pl and None not in m["delta"]:
                cxy_ = (sum(q[0] for q in pl["pts"]) / len(pl["pts"]), sum(q[1] for q in pl["pts"]) / len(pl["pts"]))
                d_, t_ = dist_seg(cxy_, m["c1"], m["c2"])
                if d_ * SC < 60 and 0.05 < t_ < 0.95:
                    ds.append(m["delta"][0] + (m["delta"][1] - m["delta"][0]) * t_)
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
                in_base = (pk[1] - min(Lg["a"][1], Lg["b"][1])) * SC < ST.BASE_ZONE and \
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
                    lo, hi = gl - tl, gl + back_extra(zf(pk[1]))
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
            # thanh chìa qua 2 thanh cánh (thanh ngang xà L90x7 2840, DN-01 3-3): đầu thanh không nằm trên thanh chủ ->
            # độ sâu theo chỗ cắt thanh cánh: có bản mã trên thanh cánh thì NGOÀI áp mặt ngoài bản mã
            dd_ = []
            for L_ in legs:
                pc_ = inter(m["c1"], m["c2"], L_["w1"], L_["w2"])
                if pc_ and dist_seg(pc_, m["c1"], m["c2"])[0] < TOL:
                    pl_ = next((pl for pl in plates2d if pl.get("on_leg_fixed") and point_in_poly(pc_, pl["pts"])), None)
                    if pl_ is not None and m["out"]:
                        dd_.append(pl_["delta0"] + pl_["t"])
                    else:
                        dd_.append(gl + back_extra(zf(pc_[1])) if m["out"] else gl - tl)
            if dd_:
                m["delta"] = [max(dd_) if m["out"] else min(dd_)] * 2
                rep.setdefault("host_from_leg_crossing", []).append({"section": m["section"], "delta_mm": m["delta"][0]})
                continue
            m["delta"] = [gl if m["out"] else gl - tl] * 2
            rep["warnings"].append(f"thanh {m['section']} góc {m['ang']:.1f}: không tìm được thanh chủ")
            rep.setdefault("no_host", []).append(m)
    for pl in plates2d:
        if pl["delta0"] is None:
            pl["delta0"] = gl
    _l = locals()
    return {k_: _l[k_] for k_ in ['BSTUB', 'L_', 'P_', 'SPL', 'STUB_OUT', 'a_', 'b_', 'back_extra', 'bpos_d', 'gl', 'h', 'hi', 'i_', 'jb', 'k', 'leg_sec_at', 'lo', 'm', 'out_', 'pk', 'pl', 'pt_k', 'pts_', 'sgn', 'sp_', 't_', 'tl', 'v', 'w_', 'zc_'] if k_ in _l}

