"""Nút giữa bẻ lệch (DT-01), vát cánh theo ghi chú bản vẽ / mặt cắt.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (L, L_, Lg, b_, be, d_, k, keep, legs, m, pl, plates2d, pt_k, pts_, rep, sgn, t, u_, xs_,) = (V.get(k_) for k_ in ("L", "L_", "Lg", "b_", "be", "d_", "k", "keep", "legs", "m", "pl", "plates2d", "pt_k", "pts_", "rep", "sgn", "t", "u_", "xs_",))
    # --- nút giữa có thanh ngang bẻ lệch (DT-01): bản mã giữa áp lưng thanh ngang đã bẻ; thanh xiên trong ép sát
    #     mặt trong bản mã, thanh xiên ngoài ép sát mặt ngoài bản mã (thêm 1 điểm độ sâu giữa thanh)
    cj = ST.CFG.get("center_joggle")
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
            if ST.CFG.get("foot_diag_cut") and near_leg and (p_[1] - base_y0) * SC < ST.BASE_ZONE:
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
    level_cut = ST.CFG["level_cut"]
    for pname, (ymark, _box) in ST.PLANS.items():
        for m in keep:
            ang = m["ang"] % 180
            if (ang < 3 or ang > 177) and abs(m["c1"][1] - ymark) < 12 and level_cut.get(pname):
                for k in (0, 1):
                    if m["host"][k][0] == "leg":
                        m.setdefault("cuts", {})[k] = {"flange": "out", "a": level_cut[pname], "b": level_cut[pname],
                                                      "note": f"vát cánh {level_cut[pname]}x{level_cut[pname]}mm (mặt cắt {pname})"}
    _l = locals()
    return {k_: _l[k_] for k_ in ['L', 'ang', 'b_', 'c1', 'c2', 'cen', 'd_', 'delta_s', 'fl_', 'hs', 'k', 'm', 'p_', 'pl', 'pname', 'sgn', 't', 'toe', 'ymark'] if k_ in _l}

