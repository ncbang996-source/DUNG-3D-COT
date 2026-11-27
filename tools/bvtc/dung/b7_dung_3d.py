"""Chiếu sang 3D, xoay 4 mặt: thanh cánh (nhiều đoạn, mối nối), thanh giằng, bản mã, bu lông.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (BSTUB, L_, Lg, P, P2, SPL, STUB_OUT, _, a1, a2, a_, ang, b_, back_extra, bolts2d, cen, fillers2d, g_, gl, h, halfw, i, i_, jb, k, keep, la_, lb_, leg_sec_at, m, nb_, nl, nm_, out_, p, pl, plates2d, prof3d, pts_, q, rep, segs, sp_, t_, tl, u2, v, xc, xline, zc_, zf,) = (V.get(k_) for k_ in ("BSTUB", "L_", "Lg", "P", "P2", "SPL", "STUB_OUT", "_", "a1", "a2", "a_", "ang", "b_", "back_extra", "bolts2d", "cen", "fillers2d", "g_", "gl", "h", "halfw", "i", "i_", "jb", "k", "keep", "la_", "lb_", "leg_sec_at", "m", "nb_", "nl", "nm_", "out_", "p", "pl", "plates2d", "prof3d", "pts_", "q", "rep", "segs", "sp_", "t_", "tl", "u2", "v", "xc", "xline", "zc_", "zf",))
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
    if ST.CFG.get("top_kink"):
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
            cuts_ = [jb] + [sp_["z"] for sp_ in ST.CFG.get("leg_splices", [])]
            gaps_ = [gb] + [sp_["gap"] / 2 for sp_ in ST.CFG.get("leg_splices", [])]
            ztop = zf(max(L_["a"][1], L_["b"][1]))
            legs_parts = [(Pz(0.0), Pz(jb - gb), BSTUB.get("stub_name", "phần đứng thanh cánh %s (301/302, vẽ để ráp)"
                                                           % BSTUB["sheet"]),
                           BSTUB["section"], L_["g"] + STUB_OUT, BSTUB["sheet"])]
            names_ = BSTUB.get("names", ["thanh cánh 203/204", "thanh cánh 201/202"])
            for i_ in range(len(cuts_)):
                z0_ = cuts_[i_] + gaps_[i_]
                z1_ = (cuts_[i_ + 1] - gaps_[i_ + 1]) if i_ + 1 < len(cuts_) else ztop
                zm_ = (z0_ + z1_) / 2
                legs_parts.append((Pz(z0_), Pz(z1_), names_[min(i_, len(names_) - 1)], leg_sec_at(zm_),
                                   L_["g"] + back_extra(zm_), None))
            # thép góc nối trong (vát góc lưng 12x12 theo chi tiết)
            for zc_, Li_, sec_, nm_, cut_ in [(jb, BSTUB.get("inner_L", 670.0), BSTUB.get("inner", "HL130X9"),
                                               BSTUB.get("inner_name", "thép góc nối trong B-B (232)"), 12.0)] + \
                    [(sp_["z"], sp_["inner_L"], sp_.get("inner_sec", sp_["inner"]),
                      sp_.get("inner_name", "thép góc nối trong A-A (229)"), sp_.get("inner_cut", 12.0))
                     for sp_ in ST.CFG.get("leg_splices", [])]:
                si = sec(sec_)
                if si["profile"][0] == [0.0, 0.0]:
                    si["profile"] = [[cut_, 0.0]] + si["profile"][1:] + [[0.0, cut_]]
                    si["note"] = "vát góc lưng %gx%g" % (cut_, cut_)
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
                           ("bản nối ngoài thanh cánh %s d%g" % (BSTUB.get("joint_name", "B-B") + " (233)"
                                                                 if pl["leg_splice"] == BSTUB["joint_mm"] else
                                                                 next((x_.get("name", "A-A (230)") for x_ in SPL
                                                                       if x_["z"] == pl["leg_splice"]), "A-A (230)"),
                                                                 pl["t"])) if pl.get("leg_splice") else
                           ("bản mã nối thanh cánh d%g (mối nối với đoạn trên)" % pl["t"]) if pl.get("splice") else
                           ("bản mã nút đầu trên d%g (%s)%s" % (pl["t"], pl["note"], tag_))
                           if pl.get("hidden") else
                           ("bản mã %s theo hình chi tiết (%s)" % (pl["mark"], ST.SHEET)) if pl.get("mark")
                           else f"bản vẽ {ST.SHEET} (mặt đứng)"})
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
    _l = locals()
    return {k_: _l[k_] for k_ in ['P', 'P1', 'P2', 'Rk', '_', 'a1', 'a2', 'area', 'b', 'bolts', 'cen', 'dmm', 'e1', 'e2', 'ex', 'hv', 'hv3', 'i_', 'k', 'm', 'members', 'mid', 'n', 'nf', 'o', 'p', 'pl', 'plates', 'poly', 's_', 'slope', 'tu', 'tup', 'u'] if k_ in _l}

