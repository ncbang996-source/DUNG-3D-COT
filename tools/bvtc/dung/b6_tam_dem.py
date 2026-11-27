"""Tấm đệm (khối D, ký hiệu nD.F_T).

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (L, L_, Lg, ONTOP, _, a_, b2, b_, bb, bolt_len, bolts2d, c, c1, c2, doc, e, halfw, hi, i, inb, k, layers_at, legs, lo, m, msp, mt, n_, need, pts_, rep, sb, sgn, t_, u_, xc, xline, zf,) = (V.get(k_) for k_ in ("L", "L_", "Lg", "ONTOP", "_", "a_", "b2", "b_", "bb", "bolt_len", "bolts2d", "c", "c1", "c2", "doc", "e", "halfw", "hi", "i", "inb", "k", "layers_at", "legs", "lo", "m", "msp", "mt", "n_", "need", "pts_", "rep", "sb", "sgn", "t_", "u_", "xc", "xline", "zf",))
    # --- tấm đệm (khối "D" = vòng nét đứt quanh bu lông; ký hiệu "nD.F_T" = n tấm, bu lông F, dày T):
    #     số tấm mỗi vị trí = n / số khối D cùng ký hiệu (nút thanh cánh: 2 vị trí x 1 tấm; giao chữ X: 1 vị trí
    #     x 2 tấm chồng nhau - người dùng xác nhận). Tấm đệm đặt áp lớp thép phía ngoài của khe.
    dlabs = []
    for t_ in msp.query("TEXT"):
        mt = re.fullmatch(r"(\d*)D\.(\d+)_(\d+)", t_.dxf.text.strip())
        if mt and inb(t_.dxf.insert):
            dlabs.append({"n": int(mt.group(1) or 1), "d": int(mt.group(2)), "t": float(mt.group(3)),
                          "p": (t_.dxf.insert[0], t_.dxf.insert[1]), "syms": []})
    dsyms = []
    for e in msp.query('INSERT[name=="D"]'):
        if inb(e.dxf.insert):
            r_ = next((c.dxf.radius for c in doc.blocks.get("D") if c.dxftype() == "CIRCLE"), 0.88) * e.dxf.xscale
            sym = {"p": (e.dxf.insert[0], e.dxf.insert[1]), "r_mm": r_ * SC}
            if dlabs:
                lab = min(dlabs, key=lambda L_: math.dist(L_["p"], sym["p"]))
                if math.dist(lab["p"], sym["p"]) < 25:
                    lab["syms"].append(sym)
                    sym["lab"] = lab
            dsyms.append(sym)
    # khối D không có ký hiệu số lượng/chiều dày gần đó: lấy 1 tấm dày 10 (như nút thanh cánh) - báo lại
    for sym in dsyms:
        if "lab" not in sym:
            sym["lab"] = {"n": 1, "d": 20, "t": float(ST.CFG.get("filler_default_t", 10)), "p": sym["p"],
                          "syms": [sym], "assumed": True}
    fillers2d = []
    rep["fillers"] = []

    rep["bolt_gaps"] = []
    rep["bolts_dropped"] = 0
    keepb2 = []
    rep["holes_waiting"] = []
    for bb in bolts2d:
        lay = layers_at(bb["p"])
        # lỗ chờ cho đoạn phía trên (đỉnh đoạn có phần uốn thẳng đứng): chỉ xuyên thanh cánh (nối thanh cánh đoạn
        # trên) hoặc chỉ xuyên bản mã của đoạn trên (thanh của đoạn trên bắt vào) -> bu lông lắp khi ráp đoạn trên
        if ST.CFG.get("waiting_holes") and lay:
            # lỗ chờ: chỉ xuyên 1 chi tiết (thanh / bản mã) - thanh kia thuộc xà hoặc đoạn kề, lắp khi ráp
            nm_ = [n_ for _, _, n_ in lay]
            outside_ = abs(bb["p"][0] - xc) * SC > halfw(bb["p"][1]) + 120
            if all(n_.startswith("bản mã") for n_ in nm_) or (len(lay) == 1 and outside_) or \
                    (len(lay) == 1 and nm_[0].startswith(Lg["section"]) and
                     zf(bb["p"][1]) > zf(max(Lg["a"][1], Lg["b"][1])) - 400):
                rep["holes_waiting"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                             "M": bb["d"], "qua": nm_})
                continue
        if ST.CFG.get("top_kink") and lay and bb["p"][1] > max(Lg["a"][1], Lg["b"][1]) - 2.0:
            nm_ = [n_ for _, _, n_ in lay]
            if all(n_.startswith(Lg["section"]) for n_ in nm_) or all(n_.startswith("bản mã") for n_ in nm_):
                rep["holes_waiting"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                             "M": bb["d"], "qua": nm_})
                continue
        if not lay:
            rep["bolts_dropped"] += 1
            rep.setdefault("bolts_dropped_pts", []).append(bb["p"])
            continue
        lay.sort()
        # khối D đặt đúng tim bu lông vẽ; bu lông lấy theo hình chi tiết bản mã có thể lệch vài mm
        sym = next((sy for sy in dsyms if "lab" in sy and math.dist(sy["p"], bb["p"]) < 1.2 and
                    min(bolts2d, key=lambda b2: math.dist(b2["p"], sy["p"])) is bb), None)
        if sym:
            lab = sym["lab"]
            nper = max(1, round(lab["n"] / len(lab["syms"])))
            if lab.get("assumed") and ST.CFG.get("waiting_holes"):
                # không có ký hiệu: chọn 1-2 tấm dày 8/10 vừa khe nhất (không dày hơn khe) - giả định, báo lại
                cur0 = lay[0][1]
                gmax = 0.0
                for a0_, b0_, _n in lay[1:]:
                    gmax = max(gmax, a0_ - cur0)
                    cur0 = max(cur0, b0_)
                opts = [(n_ * t_, n_, t_) for n_ in (1, 2) for t_ in (8.0, 10.0) if n_ * t_ <= gmax + 0.01]
                if opts:
                    _, nper, tt_ = max(opts)
                    lab = dict(lab, t=tt_, n=nper * len(lab["syms"]))
            # khe lớn nhất giữa các lớp
            gaps = []
            cur = lay[0][1]
            for a_, b_, n_ in lay[1:]:
                if a_ > cur + 0.5:
                    gaps.append((a_ - cur, cur, a_))
                cur = max(cur, b_)
            if gaps:
                g_, glo, ghi = max(gaps)
                th = nper * lab["t"]
                if abs(g_ - th) > 2.5:
                    # số tấm theo khe (giữ chiều dày ghi): VD 4D.20_8 tại nút thanh cánh HL130x9 (khe 9) -> 1 tấm 8
                    k_ = min(range(1, max(nper, lab["n"], 1) + 1), key=lambda k: abs(g_ - k * lab["t"]))
                    if abs(g_ - k_ * lab["t"]) <= 2.5:
                        nper, th = k_, k_ * lab["t"]
                if (abs(g_ - th) > 2.5 or (ST.CFG.get("waiting_holes") and th > g_ + 0.5)) and g_ / nper >= 3:
                    # người dùng chốt: chiều dày tấm đệm sửa cho vừa khe (VD 2D.20_8 ở khe 20 -> 2 tấm 10)
                    t_fit = float(math.floor(g_ / nper))
                    rep.setdefault("fillers_resized", []).append({"z_mm": round(zf(bb["p"][1])), "ky_hieu": f"{nper} x {lab['t']:g}",
                                                                  "khe_mm": round(g_, 1), "sua": f"{nper} x {t_fit:g}"})
                    lab = dict(lab, t=t_fit)
                    th = nper * t_fit
                for i in range(nper):
                    f_hi = ghi - i * lab["t"]
                    lay.append((f_hi - lab["t"], f_hi, "tấm đệm d%d" % lab["t"]))
                    # tấm đệm sát mép cánh thanh cánh (tâm cách mép < bán kính): cắt phẳng theo mép, chừa 1 mm
                    clip_ = None
                    # mô hình 3D dùng thanh cánh trái xoay 4 góc -> bên phải lấy đối xứng gương của thanh cánh trái
                    ul = np.array(Lg["w2"]) - np.array(Lg["w1"])
                    ul = ul / np.linalg.norm(ul)
                    for sgn_ in (1, -1):
                        qx = bb["p"][0] if sgn_ == 1 else 2 * xc - bb["p"][0]
                        toe_ = (qx - xline(Lg, bb["p"][1])) * SC - (sec(Lg["section"])["b"] - Lg["g"])
                        if 0 < toe_ < sym["r_mm"] + 1 and abs(qx - xline(Lg, bb["p"][1])) * SC < 300:
                            nl = np.array([ul[1], -ul[0]]) * (1 if ul[1] > 0 else -1)      # hướng vào trong mặt
                            nl = nl * np.array([sgn_, 1.0])
                            clip_ = (nl.tolist(), toe_ - 4.0)     # chừa 1 mm + sai số nét vẽ ~3 mm
                    fillers2d.append({"p": bb["p"], "lo": f_hi - lab["t"], "t": lab["t"], "r": sym["r_mm"],
                                      "clip": clip_})
                lay.sort()
                rep["fillers"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                       "khe_mm": round(g_, 1), "dem": f"{nper} x {lab['t']:g}",
                                       "con_ep_mm": round(g_ - th, 1),
                                       **({"gia_dinh": "không có ký hiệu, lấy %d x %g" % (nper, lab["t"])} if lab.get("assumed") else {})})
            else:
                rep["fillers"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                       "khe_mm": 0, "loi": "không có khe để đặt tấm đệm"})
        lo, hi = lay[0][0], max(x[1] for x in lay)
        cur = lay[0][1]
        for a_, b_, n_ in lay[1:]:
            if a_ > cur + 0.5:
                rep["bolt_gaps"].append({"z_mm": round(zf(bb["p"][1])), "x_mm": round((bb["p"][0] - xc) * SC),
                                         "gap_mm": round(a_ - cur, 1), "layers": [x[2] for x in lay]})
            cur = max(cur, b_)
        L_b, need = bolt_len(bb["p"], bb["d"], hi - lo)
        bb.update({"lo": lo, "hi": hi, "layers": [x[2] for x in lay], "L": L_b or math.ceil(need / 10) * 10,
                   "L_from": "ký hiệu bản vẽ" if L_b else "tính (không thấy ký hiệu)"})
        keepb2.append(bb)
    bolts2d[:] = keepb2

    # đoạn đặt trên đoạn khác: đầu dưới thanh cánh = bu lông thấp nhất trên cánh thanh cánh - 50 mm (như đầu trên
    # thanh cánh đoạn dưới; chi tiết HL130x9: 2 nhóm lỗ cách 110 = 50 + khe 10 + 50). Nét thanh cánh tờ này vẽ
    # kéo tới mặt bản đế (dùng khi đoạn đứng trên móng).
    if ONTOP:
        for L_ in legs:
            la_, lb_ = np.array(L_["a"]), np.array(L_["b"])
            lo_e, hi_e = (la_, lb_) if la_[1] < lb_[1] else (lb_, la_)
            u2 = (hi_e - lo_e) / np.linalg.norm(hi_e - lo_e)
            sgn = 1 if L_ is Lg else -1
            sb = [float(np.dot(np.array(b["p"]) - lo_e, u2)) for b in bolts2d
                  if -L_["g"] + 5 <= (b["p"][0] - xline(L_, b["p"][1])) * SC * sgn <= sec(L_["section"])["b"] - L_["g"] - 5
                  and dist_line(b["p"], L_["w1"], L_["w2"]) * SC < 120 and (b["p"][1] - lo_e[1]) * SC < 900]
            if sb:
                new_lo = lo_e + u2 * (min(sb) - ONTOP.get("leg_end", 50.0) / SC)
                rep.setdefault("leg_bottom_trim_mm", []).append(round(float(np.dot(new_lo - lo_e, u2)) * SC, 1))
                if la_[1] < lb_[1]:
                    L_["a"] = tuple(new_lo)
                else:
                    L_["b"] = tuple(new_lo)

    def prof3d(m, nn):
        """Độ sâu theo chiều dài (thanh bẻ lệch / ép sát giữa thanh): [[x mm từ p1, δ mm], ...]."""
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        s1_ = ((m["b1"][0] - c1[0]) * u_[0] + (m["b1"][1] - c1[1]) * u_[1]) * SC
        s2_ = ((m["b2"][0] - c1[0]) * u_[0] + (m["b2"][1] - c1[1]) * u_[1]) * SC
        sg = 1 if s2_ >= s1_ else -1
        pts_ = [[0.0, m["delta"][0]]] + [[round((sp - s1_) * sg, 1), round(dv, 2)] for sp, dv in m["dprof"]] + \
            [[round(abs(s2_ - s1_), 1), m["delta"][1]]]
        return {"prof": sorted(pts_), "prof_n": nn.round(6).tolist()}
    _l = locals()
    return {k_: _l[k_] for k_ in ['L_', '_', 'a_', 'b_', 'bb', 'cur', 'e', 'fillers2d', 'g_', 'i', 'k_', 'la_', 'lb_', 'lo', 'mt', 'need', 'nl', 'nm_', 'prof3d', 't_', 'th', 'u2'] if k_ in _l}

