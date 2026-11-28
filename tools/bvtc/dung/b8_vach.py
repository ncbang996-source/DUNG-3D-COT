"""Mặt cắt vách ngang (đoạn thân: 1/4 rồi xoay), đầu thanh vách 55, gỡ chạm vách.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (B1, B2, L, ONTOP, P, P1, P2, P_, Rk, _, a1, a2, a_, area, b_, bb, best, bolts, c, c_, cur, d2, d_, dd, dmm, doc, e, e1, e2, ex, fl_, gl, h, halfw, hv, hv3, i, inb, inside, k, k_, keep, labs, lo, m, members, mid, ms, msp, mt, n, near, nf, o, p, p_, pl, plates, pm_, pname, poly, pts, q, rep, s1, s2, s_, slope, sp_, t, t_, th, tl, tu, tup, u, v, xc, y0, ymark, zf,) = (V.get(k_) for k_ in ("B1", "B2", "L", "ONTOP", "P", "P1", "P2", "P_", "Rk", "_", "a1", "a2", "a_", "area", "b_", "bb", "best", "bolts", "c", "c_", "cur", "d2", "d_", "dd", "dmm", "doc", "e", "e1", "e2", "ex", "fl_", "gl", "h", "halfw", "hv", "hv3", "i", "inb", "inside", "k", "k_", "keep", "labs", "lo", "m", "members", "mid", "ms", "msp", "mt", "n", "near", "nf", "o", "p", "p_", "pl", "plates", "pm_", "pname", "poly", "pts", "q", "rep", "s1", "s2", "s_", "slope", "sp_", "t", "t_", "th", "tl", "tu", "tup", "u", "v", "xc", "y0", "ymark", "zf",))
    # --- mặt cắt vách ngang
    plan_rep = {}
    plan_chk = {}
    plan_bolts, plan_plates = [], []
    plan_members = []
    for pname, (ymark, box) in ST.PLANS.items():
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
            if pname in ST.CFG.get("plan_gauge_center", []):
                # góp ý 20261127_1721: trục bu lông vách ở GIỮA cánh nằm thanh mặt cột (đường đinh vẽ sát lưng làm
                # thanh vách cấn cánh đứng thanh mặt cột)
                g_plan = sec(mh["section"])["b"] / 2
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
                           "bolt_max": 0, "d_max_mm": 0, "leg_bolts": 0, "reason": f"bản vẽ {ST.SHEET} (mặt cắt)"})

    if not ONTOP and not ST.CFG.get("no_base"):
        # --- chân cột: số liệu đọc từ DXF (chi tiết tỉ lệ 1/10, xem SHEETS)
        # Vị trí (DT-02 khớp lỗ sườn với bu lông chân thanh cánh trên mặt đứng, lệch <= 5 mm):
        #   sườn 1 nằm trên cánh thanh cánh ở mặt đang xét (thanh cánh trái): x = -(HEEL + 200) + u
        #   sườn 3 trên cánh thứ hai (thấy ở thanh cánh phải, đối xứng gương):  x = HEEL - u
        #   mặt bằng bản đế: lưng cách mép ngoài 200, bản 450x450x40, sườn 1 bắt đầu từ mép bản.
        BC = ST.CFG["base"]
        RIB1, RIB2, RIB3, RIB1_H, RIB3_H = BC["rib1"], BC["rib2"], BC["rib3"], BC["rib1_h"], BC["rib3_h"]
        RIB_H = max(v for _, v in RIB1)
        HEEL = BC["heel"]
        if HEEL is None:
            # vị trí lưng thanh cánh: chọn sao cho lỗ sườn 1 (thanh cánh trái) và sườn 3 (thanh cánh phải) trùng bu lông
            # chân cột vẽ trên mặt đứng (bước 0,5 mm)
            bb = [((e.dxf.insert[0] - xc) * SC, zf(e.dxf.insert[1])) for e in msp.query("INSERT")
                  if e.dxf.name in ("1", "2", "3") and inb(e.dxf.insert) and zf(e.dxf.insert[1]) < ST.BASE_ZONE]
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
                           "reason": f"bản đế 450x450x40 (chi tiết {ST.SHEET})"})
            for du in (0.1, 0.35):
                for dv in (0.1, 0.35):
                    p = Rk @ (corner + du * ex_ + dv * ey_)
                    bolts.append({"id": 0, "p": p.round(5).tolist(), "axis": [0, 0, 1.0], "nut": [0, 0, 1.0],
                                  "d_mm": 56, "t_mm": 40, "kind": "neo"})
        rep["base"] = "4 bản đế 450x450x40, 12 sườn d12 (đúng hình chi tiết), 16 bu lông neo Ø56"
        rep["base_heel_mm"] = float(HEEL)
    else:
        rep["base"] = "không có chân cột: đoạn đặt trên %s (người dùng chốt bỏ bản đế)" % (ONTOP or ST.CFG.get("bottom_stub") or {"sheet": "?"})["sheet"]

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
    _l = locals()
    return {k_: _l[k_] for k_ in ['P1', 'P2', 'P_', 'Pk', 'Q', 'a_', 'b_', 'bb', 'byid', 'c_', 'cur', 'dmm', 'e1', 'e2', 'fh', 'key', 'm', 'o', 'p0', 'plan_chk', 'pm_', 'q', 'th', 'top', 'touching', 'ub'] if k_ in _l}

