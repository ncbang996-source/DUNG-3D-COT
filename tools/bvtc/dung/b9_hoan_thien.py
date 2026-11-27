"""Bu lông vách theo lớp thép thật, bẻ cánh cục bộ, chân cột, bẻ đầu thanh đỉnh, vát góc cột, ghi scene.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (ED, L, Lg, P1, P2, P_, Pk, Q, a_, b, b1_, b_, bb, bolts, bolts2d, byid, c, c_, cen, cur, dmm, e1, e2, fh, i_, idx, key, m, members, need, o, outdir, p0, pk, pl, plan_chk, plates, plates2d, pm_, q, rep, segs, th, top, touching, u_, ub, w_, x0, x1, xc, zf,) = (V.get(k_) for k_ in ("ED", "L", "Lg", "P1", "P2", "P_", "Pk", "Q", "a_", "b", "b1_", "b_", "bb", "bolts", "bolts2d", "byid", "c", "c_", "cen", "cur", "dmm", "e1", "e2", "fh", "i_", "idx", "key", "m", "members", "need", "o", "outdir", "p0", "pk", "pl", "plan_chk", "plates", "plates2d", "pm_", "q", "rep", "segs", "th", "top", "touching", "u_", "ub", "w_", "x0", "x1", "xc", "zf",))
    # --- BẺ CÁNH CỤC BỘ (người dùng chốt, theo ảnh cột mẫu): cánh nằm ngang của thanh ngang mặt cột vuông góc mặt
    #     cột nên nghiêng theo độ xiên mặt cột; tại chỗ thanh giằng vách bắt vào, cánh được bẻ cục bộ quanh mép lưng
    #     thành mặt phẳng song song mặt đất -> thanh giằng tựa phẳng, hết hở. Vùng phẳng = vết thanh giằng trên cánh
    #     + 10 mm mỗi bên, đoạn chuyển tiếp 40 mm.
    rep["flange_bends"] = []
    RAMP = 40.0
    for pm_ in [m for m in members if m["rule"] == "plan" and "contact" in m]:
        for key, c_ in pm_["contact"].items():
            fh = byid.get(c_["host_id"])
            if fh is None:
                continue
            P1, P2, e1, e2 = CK.frame(fh)
            L = np.linalg.norm(P2 - P1)
            u_ = (P2 - P1) / L
            # bu lông vách của đầu thanh giằng này
            Pk = np.array(pm_[key])
            bb = [b_ for b_ in bolts if b_["kind"] == "plan" and np.linalg.norm(np.array(b_["p"])[:2] - Pk[:2]) < 0.2]
            cen = np.array(min(bb, key=lambda b_: np.linalg.norm(np.array(b_["p"])[:2] - Pk[:2]))["p"]) if bb else Pk
            xb = float(np.linalg.solve(np.c_[P2 - P1, e1, e2], cen - P1)[0] * L * 1000)
            ub = unit(np.array(pm_["p2"]) - np.array(pm_["p1"]))
            sphi = max(abs(float(np.linalg.norm(np.cross(ub, u_)))), 0.2)
            cphi = abs(float(np.dot(ub, u_)))
            half = 0.5 * (sec(pm_["section"])["b"] / sphi + sec(fh["section"])["b"] * cphi / sphi) + 10
            # góc xoay quanh trục thanh để cánh còn lại (theo e2) nằm ngang
            w_ = np.cross(u_, e2)
            th = math.atan2(-e2[2], w_[2])
            if abs(th) > math.pi / 2:
                th -= math.copysign(math.pi, th)
            x0, x1 = max(0.0, xb - half), min(L * 1000, xb + half)
            fh.setdefault("bends", []).append({"x0": round(x0, 1), "x1": round(x1, 1), "ramp": RAMP,
                                               "theta_deg": round(math.degrees(th), 3), "plan": pm_["plan"]})
            rep["flange_bends"].append({"plan": pm_["plan"], "host": fh["section"], "brace": pm_["section"],
                                        "len_mm": round(x1 - x0), "deg": round(math.degrees(th), 2)})

    rep["plan_bolt_layers"] = []
    zs_ = np.arange(-0.12, 0.12, 0.0005)
    for b_ in bolts:
        if b_["kind"] != "plan":
            continue
        p0 = np.array(b_["p"])
        Q = np.c_[np.full(len(zs_), p0[0]), np.full(len(zs_), p0[1]), p0[2] + zs_]
        inside_any = np.zeros(len(zs_), bool)
        names = []
        for o in members:
            if o["rule"] == "leg":
                continue
            if CK.seg_dist(p0, p0 + 1e-6, *CK.frame(o)[:2]) > 0.2:
                continue
            w = CK.where_v(o, LIB, Q, 0.0002) > 0
            if w.any():
                inside_any |= w
                names.append(o["section"] + " " + o.get("side", ""))
        if not inside_any.any():
            rep["warnings"].append(f"bu lông vách tại {np.round(p0, 3).tolist()}: không xuyên thép")
            b_["_drop"] = True
            continue
        # các đoạn thép liên tục dọc trục; giữ chuỗi đoạn quanh cao độ vách (hở giữa các đoạn <= 8 mm)
        idx = np.where(inside_any)[0]
        runs = []
        for i_ in idx:
            if runs and i_ == runs[-1][1] + 1:
                runs[-1][1] = i_
            else:
                runs.append([i_, i_])
        i0 = int(np.argmin(np.abs(zs_)))
        cur = min(runs, key=lambda r: 0 if r[0] <= i0 <= r[1] else min(abs(r[0] - i0), abs(r[1] - i0)))
        grp = [cur]
        for r in sorted(runs):
            if r is cur:
                continue
            if r[0] > grp[-1][1] and (r[0] - max(g[1] for g in grp)) * 0.5 <= 8:
                grp.append(r)
        for r in sorted(runs, reverse=True):
            if r[1] < min(g[0] for g in grp) and (min(g[0] for g in grp) - r[1]) * 0.5 <= 8:
                grp.append(r)
        lo_i, hi_i = min(g[0] for g in grp), max(g[1] for g in grp)
        names = [o["section"] + " " + o.get("side", "") for o in members if o["rule"] != "leg"
                 and CK.seg_dist(p0, p0 + 1e-6, *CK.frame(o)[:2]) <= 0.2
                 and np.any(CK.where_v(o, LIB, Q[lo_i:hi_i + 1], 0.0002) > 0)]
        top, bot = p0[2] + zs_[hi_i] + 0.00025, p0[2] + zs_[lo_i] - 0.00025
        gap = float(sum((b2_[0] - b1_[1] - 1) * 0.5 for b1_, b2_ in zip(sorted(grp), sorted(grp)[1:])))
        # người dùng chốt: bu lông đứng xỏ TỪ DƯỚI LÊN (đầu bu lông dưới, đai ốc trên); bu lông ngang từ trong ra ngoài
        b_["p"] = [round(float(p0[0]), 5), round(float(p0[1]), 5), round(float(bot), 5)]
        b_["axis"], b_["nut"] = [0, 0, 1.0], [0, 0, 1.0]
        b_["grip_mm"] = round((top - bot) * 1000, 1)
        b_["layers"] = names
        rep["plan_bolt_layers"].append({"xy": np.round(p0[:2], 3).tolist(), "layers": names,
                                        "grip_mm": b_["grip_mm"], "gap_mm": gap})
        if len(names) < 2:
            # lỗ chỉ xuyên 1 thanh (bản vẽ vẽ lỗ đối xứng; ký hiệu bu lông ghi 1 con): không có bu lông
            b_["_drop"] = True
            rep.setdefault("plan_holes_no_bolt", []).append({"xy": np.round(p0[:2], 3).tolist(), "layers": names})
    bolts[:] = [b_ for b_ in bolts if not b_.pop("_drop", False)]

    # --- đầu dưới thanh xiên chính tại sườn chân cột: lỗ lấy theo chi tiết sườn -> đầu thanh phải cách lỗ thấp
    #     nhất >= 30 mm (M20, ghi chú chung); kéo dài đầu thanh nếu thiếu
    rep["base_end_extended"] = []
    for m in [o for o in members if o["rule"] == "face"]:
        for key, pk in (("p1", "poff1"), ("p2", "poff2")):
            if m[key][2] > 0.6:
                continue
            P1, P2, e1, e2 = CK.frame(m)
            L = np.linalg.norm(P2 - P1)
            u_ = (P2 - P1) / L
            xs = []
            for b_ in bolts:
                if b_["kind"] != "chân cột" or "3.20_60" not in b_.get("L_from", ""):
                    continue                           # chỉ 3 lỗ thanh xiên trên sườn (3.20_60)
                q = np.array(b_["p"]) + np.array(b_["nut"]) * (b_.get("grip_mm", 20) / 2000)
                sol = np.linalg.solve(np.c_[P2 - P1, e1, e2], q - P1)
                a_ = sol[1] * 1000 + m["g"][0]
                if 15 < a_ < sec(m["section"])["b"] - 15 and abs(sol[2]) < 0.03:
                    xs.append(sol[0] * L * 1000 if key == "p1" else (1 - sol[0]) * L * 1000)
            if not xs:
                continue
            need = ED[20] - min(xs)
            if need > 0.5:
                sign = -1 if key == "p1" else 1
                orig_ = np.array(m[key])
                lg_ = [o for o in members if o["rule"] == "leg" and
                       CK.seg_dist(orig_, orig_ + 1e-6, *CK.frame(o)[:2]) < 0.4]

                def hits_leg():
                    sp = CK.samples(m, LIB)
                    sp = sp[np.linalg.norm(sp - np.array(m[key]), axis=1) < 0.25]
                    if any(np.any(CK.where_v(o, LIB, sp, 0.001) > 0) for o in lg_):
                        return True
                    for o in lg_:
                        so = CK.samples(o, LIB)
                        so = so[np.linalg.norm(so - np.array(m[key]), axis=1) < 0.25]
                        if len(so) and np.any(CK.where_v(m, LIB, so, 0.001) > 0):
                            return True
                    return False
                got = need
                while got > 0:
                    m[key] = (orig_ + sign * u_ * got / 1000).round(5).tolist()
                    if not hits_leg():
                        break
                    got -= 1.0
                if got <= 0:
                    m[key] = orig_.round(5).tolist()
                    got = 0.0
                m["length"] = round(float(np.linalg.norm(np.array(m["p2"]) - np.array(m["p1"]))), 4)
                rep["base_end_extended"].append({"section": m["section"], "mm": round(got, 1),
                                                 **({"thieu_mm": round(need - got, 1),
                                                     "ly_do": "kéo đủ thì chạm cánh thanh cánh"} if got < need - 0.5 else {})})

    # đầu thanh vách đặt trên/dưới thanh vách khác còn chạm cánh đứng thanh chủ: lùi đầu thanh từng 5 mm
    for pm_ in [m for m in members if m["rule"] == "plan" and m.get("on_plan")]:
        for key in pm_["on_plan"]:
            hosts = [o for o in members if o is not pm_ and o["rule"] == "plan"
                     and CK.seg_dist(np.array(pm_[key]), np.array(pm_[key]) + 1e-6, *CK.frame(o)[:2]) < 0.12]
            if not any(touching(pm_, o) for o in hosts):
                continue
            P_ = np.array(pm_[key])
            other = np.array(pm_["p2" if key == "p1" else "p1"])
            u_ = (other - P_) / np.linalg.norm(other - P_)
            for dmm in range(5, 35, 5):
                pm_[key] = (P_ + u_ * dmm / 1000).round(5).tolist()
                if not any(touching(pm_, o) for o in hosts):
                    break
            pm_["length"] = round(float(np.linalg.norm(np.array(pm_["p2"]) - np.array(pm_["p1"]))), 4)
            rep["clash_fix"].append({"loai": "lùi đầu thanh vách khỏi cánh đứng thanh vách chủ", "plan": pm_["plan"],
                                     "section": pm_["section"], "mm": dmm})

    if ST.CFG.get("top_bend"):
        rep["top_bend"] = top_bend(members, plates, bolts, ST.CFG["top_bend"])
    corner_fix(members, LIB, rep)

    for m in members:
        m["mass_kg"] = round(m["A_cm2"] * 1e-4 * m["length"] * 7850, 3)
    zs = [c for m in members for c in (m["p1"][2], m["p2"][2])]
    rep["z_range_m"] = [round(min(zs), 3), round(max(zs), 3)]
    rep["faces"] = ST.CFG.get("faces")
    rep["leg"] = {"section": Lg["section"], "g_mm": Lg["g"], "n_brace_ends_on_leg": Lg["n_wp"]}
    scene = {"title": f"Đoạn thân {ST.SHEET} cột N122 (dựng từ BVTC)", "members": members, "sections": LIB,
             "nodes": [], "plates": plates, "bolts": bolts,
             "report": {"total_mass_kg": round(sum(m["mass_kg"] for m in members), 1),
                        "orientation": {"x_members": {"outside": [], "inside": []}, "clash_other": [],
                                        "clash_coplanar_overlap": [], "overridden": []}, "build": rep}}
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    tag = ST.SHEET.lower().replace("-", "")
    (out / f"{tag}_scene.json").write_text(json.dumps(scene, ensure_ascii=False))
    # dữ liệu kiểm tra chồng hình (mặt trước, hệ x-z mm)
    chk = {"cad": [[[(sg["a"][0] - xc) * SC, zf(sg["a"][1])], [(sg["b"][0] - xc) * SC, zf(sg["b"][1])], sg["k"]]
                   for sg in segs],
           "plates": [[[(q[0] - xc) * SC, zf(q[1])] for q in pl["pts"]] for pl in plates2d],
           "bolts": [[(b["p"][0] - xc) * SC, zf(b["p"][1])] for b in bolts2d], "plans": plan_chk,
           "dropped_bolts": [[(q[0] - xc) * SC, zf(q[1])] for q in rep.pop("bolts_dropped_pts", [])],
           "no_host": [{"section": m["section"], "p1": [(m["c1"][0] - xc) * SC, zf(m["c1"][1])],
                        "p2": [(m["c2"][0] - xc) * SC, zf(m["c2"][1])], "side": "NGOAI" if m["out"] else "TRONG"}
                       for m in rep.pop("no_host", [])]}
    (out / f"{tag}_check.json").write_text(json.dumps(chk))
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:3000])
    return scene
