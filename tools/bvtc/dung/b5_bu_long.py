"""Bu lông vẽ, đầu thanh theo bu lông, chồng lớp thép tại bu lông.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (BSTUB, KTOP, KY, L, L_, Lg, ONTOP, P, SPL, TS, _, a_, b_, back_extra, banma, bolt_ins, bpos_d, c1, c2, d_, delta_s, gl, hs, i, inb, jb, keep, leg_sec_at, legs, m, msp, n_, p_, pl, plates2d, rep, s1, s2, sgn, sof, sp_, t_, tl, toe, u_, xline, zf,) = (V.get(k_) for k_ in ("BSTUB", "KTOP", "KY", "L", "L_", "Lg", "ONTOP", "P", "SPL", "TS", "_", "a_", "b_", "back_extra", "banma", "bolt_ins", "bpos_d", "c1", "c2", "d_", "delta_s", "gl", "hs", "i", "inb", "jb", "keep", "leg_sec_at", "legs", "m", "msp", "n_", "p_", "pl", "plates2d", "rep", "s1", "s2", "sgn", "sof", "sp_", "t_", "tl", "toe", "u_", "xline", "zf",))
    # --- bu lông vẽ (khối 1/2/3): độ sâu = mặt tiếp xúc của thanh dưới nó
    bolts2d = []
    # ký hiệu bu lông "S.F_D": S con, M F, dài D (mm)
    blabs = []
    for t_ in msp.query("TEXT"):
        mt = re.fullmatch(r"(\d+)\.(\d+)_(\d+)", t_.dxf.text.strip())
        if mt and inb(t_.dxf.insert):
            blabs.append((int(mt.group(1)), int(mt.group(2)), int(mt.group(3)), (t_.dxf.insert[0], t_.dxf.insert[1])))

    def bolt_len(q, dmm, grip):
        """Chiều dài theo ký hiệu bản vẽ gần nhất cùng đường kính: chọn L ngắn nhất >= kẹp + đai ốc + vòng đệm."""
        need = grip + 0.8 * dmm + 4 + 3
        cand = sorted({L for (n_, d_, L, pp) in blabs if d_ == dmm and math.dist(pp, q) < 40})
        if not cand:
            return None, need
        ok = [L for L in cand if L >= need]
        return (ok[0] if ok else cand[-1]), need

    base_y = min(Lg["a"][1], Lg["b"][1])
    for e in msp.query("INSERT"):
        if e.dxf.name not in ("1", "2", "3") or not inb(e.dxf.insert):
            continue
        q = (e.dxf.insert[0], e.dxf.insert[1])
        if TS and q[1] > max(Lg["a"][1], Lg["b"][1]) + 0.2:
            continue                                   # lỗ chờ trên thanh cánh đoạn trên: bu lông thuộc lúc ráp
        if not ONTOP and (q[1] - base_y) * SC < ST.BASE_ZONE and \
                any(dist_line(q, L_["w1"], L_["w2"]) < 16 for L_ in legs):
            continue                                   # chân cột: lấy đúng theo lỗ trên chi tiết sườn
        pl_in = [pl for pl in plates2d if "holes" in pl and point_in_poly(q, pl["pts"])]
        if pl_in:
            # bản mã có hình chi tiết: lấy lỗ theo chi tiết. Bu lông vẽ không có lỗ chi tiết nào trong 15 mm (lỗ chi
            # tiết lệch mặt đứng > ngưỡng, bị coi là lỗ chờ - VD đầu thanh xiên DN-02, góp ý "thanh xiên thiếu bu lông")
            # -> giữ bu lông vẽ (nằm đúng đường đinh thanh)
            if any(math.dist(h_, q) * SC < 15 for pl in pl_in for h_, _ in pl["holes"]):
                continue
            rep.setdefault("bolts_drawn_no_detail_hole", []).append(
                {"ban_ma": pl_in[0].get("mark"), "p": [round(q[0], 2), round(q[1], 2)], "d": {"1": 16, "2": 20, "3": 24}[e.dxf.name]})
            bolts2d.append({"p": q, "d": {"1": 16, "2": 20, "3": 24}[e.dxf.name], "src": "mặt đứng (lỗ chi tiết lệch)"})
            continue
        if not any(point_in_poly(q, pl["pts"]) for pl in plates2d) and \
                any(point_in_poly(q, P) for P in banma if P not in [pl["pts"] for pl in plates2d]):
            continue                                   # lỗ trên hình chi tiết vẽ riêng
        bolts2d.append({"p": q, "d": {"1": 16, "2": 20, "3": 24}[e.dxf.name], "src": "mặt đứng"})
    for pl in plates2d:
        for q, d_ in pl.get("holes", []):
            if ST.CFG.get("detail_hole_max"):
                # tim bu lông lấy đúng vị trí vẽ trên mặt đứng (trên đường đinh thanh) khi lỗ chi tiết lệch ít
                nb_ = min(bolt_ins, key=lambda b_: math.dist(b_[0], q), default=None)
                if nb_ and math.dist(nb_[0], q) * SC < 20:
                    q = nb_[0]
            bolts2d.append({"p": q, "d": d_, "src": "chi tiết bản mã " + pl.get("mark", "")})
    # khối bu lông vẽ chồng nhau (cùng tim, khác ký hiệu M20/M24): giữ 1, lấy đường kính lớn hơn
    ded_ = []
    for bb in bolts2d:                                   # giữ thứ tự; trùng tim thì giữ con đường kính lớn
        j_ = next((i for i, o in enumerate(ded_) if math.dist(bb["p"], o["p"]) * SC < 3), None)
        if j_ is None:
            ded_.append(bb)
        elif bb["d"] > ded_[j_]["d"]:
            ded_[j_] = bb
    rep["bolts_duplicate_removed"] = len(bolts2d) - len(ded_)
    bolts2d[:] = ded_

    # --- đầu thanh: tối thiểu = tim bu lông ngoài cùng + khoảng cách tới đầu thanh (thanh giằng 25/30/40 mm cho
    #     M16/M20/M24 - ghi chú chung). Cần khi phần đầu thanh nằm sau thanh cánh, nét vẽ bị khuất/không vẽ.
    ED = {16: 25.0, 20: 30.0, 24: 40.0}
    rep["ends_extended"] = 0
    rep["ends_drawn_kept"] = 0
    # nét đầu thanh vẽ rõ (đoạn ngắn vuông góc trục thanh tại đầu thanh): đầu thanh đã xác định, KHÔNG kéo dài
    short_lines = []
    for e in msp.query("LINE"):
        a_, b_ = (e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])
        if inb(a_) and inb(b_) and 30 <= math.dist(a_, b_) * SC <= 160:
            short_lines.append((a_, b_))

    def end_drawn(m, pe):
        L = math.dist(m["c1"], m["c2"])
        u_ = ((m["c2"][0] - m["c1"][0]) / L, (m["c2"][1] - m["c1"][1]) / L)
        for a_, b_ in short_lines:
            d_ = ((b_[0] - a_[0]) / math.dist(a_, b_), (b_[1] - a_[1]) / math.dist(a_, b_))
            if abs(d_[0] * u_[0] + d_[1] * u_[1]) < 0.1 and \
                    min(dist_seg(pe, a_, b_)[0], math.dist(pe, a_), math.dist(pe, b_)) < 0.3:
                return True
        return False

    def in_flange(m, q, margin=5.0):
        """Bu lông q (2D) có xuyên cánh liên kết thanh m: nằm trong đoạn đường tim (c1..c2, dư 10 mm) và trong
        bề rộng cánh (từ lưng tới mép, cách mép >= margin mm)."""
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        sq = (q[0] - c1[0]) * u_[0] + (q[1] - c1[1]) * u_[1]
        if not (-0.4 <= sq <= L + 0.4):
            return False
        o = ((q[0] - c1[0]) * m["nvec"][0] + (q[1] - c1[1]) * m["nvec"][1]) * SC
        b_ = sec(m["section"])["b"]
        hs = m["heel_signed"] if m["heel_signed"] is not None else b_ / 2
        toe = hs - math.copysign(b_, hs)
        return min(hs, toe) + margin <= o <= max(hs, toe) - margin
    for m in keep:
        c1, c2 = m["c1"], m["c2"]
        L = math.dist(c1, c2)
        u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
        sof = lambda p_: (p_[0] - c1[0]) * u_[0] + (p_[1] - c1[1]) * u_[1]
        # bu lông của thanh: nằm trên đường đinh (đường tâm) của thanh (lệch <= 8 mm) và trong cánh; bu lông nối
        # thanh cánh nằm trong vùng đầu thanh nhưng không trên đường đinh thanh giằng -> không tính
        offs_ = m.get("centers_rel") or [0.0]

        def crossing_bolt_at_end(q):
            # bu lông tại đầu thanh (nút) mà thanh khác chạy QUA -> bu lông giao chữ X, không thuộc thanh này
            # (bu lông giao của >= 2 thanh khác cùng chạy qua; nút chỉ 1 thanh chạy qua thì bu lông vẫn của thanh này)
            if min(math.dist(q, c1), math.dist(q, c2)) > 1.0:
                return False
            n_ = 0
            for o in keep:
                if o is m:
                    continue
                d_, t_ = dist_seg(q, o["c1"], o["c2"])
                if d_ * SC < 8 and 0.05 < t_ < 0.95:
                    n_ += 1
            return n_ >= 2
        # vị trí bu lông vẽ trên mặt đứng (lỗ theo chi tiết bản mã có thể lệch vài mm so với đường đinh)
        bl_ = [(b["p"], b["d"]) for b in bolts2d] + bpos_d
        on = [(sof(bp_), bd_) for bp_, bd_ in bl_ if in_flange(m, bp_) and not crossing_bolt_at_end(bp_) and
              min(abs(((bp_[0] - c1[0]) * m["nvec"][0] + (bp_[1] - c1[1]) * m["nvec"][1]) * SC - o_)
                  for o_ in offs_) <= 8]
        s1, s2 = sof(m["b1"]), sof(m["b2"])
        lo_side = [x for x in on if x[0] < (s1 + s2) / 2]
        hi_side = [x for x in on if x[0] >= (s1 + s2) / 2]
        if lo_side and end_drawn(m, m["b1"]):
            rep["ends_drawn_kept"] += 1
            lo_side = []
        if hi_side and end_drawn(m, m["b2"]):
            rep["ends_drawn_kept"] += 1
            hi_side = []
        if lo_side:
            sb, dd = min(lo_side)
            need = sb - ED[dd] / SC
            if need < s1 - 0.04:
                m["b1"] = (c1[0] + u_[0] * need, c1[1] + u_[1] * need)
                rep["ends_extended"] += 1
        if hi_side:
            sb, dd = max(hi_side)
            need = sb + ED[dd] / SC
            if need > s2 + 0.04:
                m["b2"] = (c1[0] + u_[0] * need, c1[1] + u_[1] * need)
                rep["ends_extended"] += 1

    # --- chồng lớp thép tại mỗi bu lông (theo hình học đã dựng, không đoán theo thanh gần nhất):
    #     mọi cánh liên kết của thanh / bản mã / cánh thanh cánh có lỗ trùng tim bu lông -> bu lông kẹp từ lớp
    #     trong cùng tới lớp ngoài cùng; kiểm tra các lớp phải liền nhau (không hở).
    def layers_at(q):
        lay = []
        for m in keep:
            c1, c2 = m["c1"], m["c2"]
            L = math.dist(c1, c2)
            u_ = ((c2[0] - c1[0]) / L, (c2[1] - c1[1]) / L)
            sq = (q[0] - c1[0]) * u_[0] + (q[1] - c1[1]) * u_[1]
            sb = sorted(((m["b1"][0] - c1[0]) * u_[0] + (m["b1"][1] - c1[1]) * u_[1],
                         (m["b2"][0] - c1[0]) * u_[0] + (m["b2"][1] - c1[1]) * u_[1]))
            if not (sb[0] + 0.2 <= sq <= sb[1] - 0.2):          # cách đầu thanh >= 5 mm
                continue
            o = ((q[0] - c1[0]) * m["nvec"][0] + (q[1] - c1[1]) * m["nvec"][1]) * SC
            b_ = sec(m["section"])["b"]
            hs = m["heel_signed"] if m["heel_signed"] is not None else b_ / 2
            toe = hs - math.copysign(b_, hs)
            if not (min(hs, toe) + 5 <= o <= max(hs, toe) - 5):
                continue
            # độ sâu nội suy theo 2 đầu thanh THẬT (b1 <-> δ đầu 1, b2 <-> δ đầu 2), giống hình 3D
            d_ = delta_s(m, sq * SC)
            rng = (d_, d_ + m["t_mm"]) if m["out"] else (d_ - m["t_mm"], d_)
            lay.append((rng[0], rng[1], m["section"] + (" NGOAI" if m["out"] else " TRONG")))
        for pl in plates2d:
            # bu lông sát mép bản mã (nét bao vẽ qua tim lỗ / lệch vài mm): vẫn xuyên bản mã
            if point_in_poly(q, pl["pts"]) or (BSTUB and dist_to_poly(q, np.array(pl["pts"])) * SC < 8):
                lay.append((pl["delta0"], pl["delta0"] + pl["t"], "bản mã d%d" % pl["t"]))
        if BSTUB:
            # thanh cánh theo cao độ: phần đứng DT-01 (HL150x12) dưới khe B-B, HL130x9 trên; mối nối B-B / A-A
            on_flange = False
            zq = zf(q[1])
            for L_ in legs:
                sgn = 1 if L_ is Lg else -1
                off = (q[0] - xline(L_, q[1])) * SC * sgn
                if -L_["g"] + 5 <= off <= sec(leg_sec_at(zq))["b"] - L_["g"] - 5:
                    on_flange = True
            if on_flange and zq >= 0:
                jb, gb = BSTUB["joint_mm"], BSTUB["gap"] / 2
                in_gap_ = any(abs(zq - sp_["z"]) <= sp_["gap"] / 2 for sp_ in SPL)
                if zq < jb - gb:
                    lay.append((gl - tl, gl - tl + sec(BSTUB["section"])["t"], BSTUB["section"] + " (" + BSTUB["sheet"] + ")"))
                elif zq > jb + gb and not in_gap_:
                    lay.append((gl - tl, gl + back_extra(zq), leg_sec_at(zq)))
                bi_ = BSTUB.get("inner", "HL130X9")
                if abs(zq - jb) < BSTUB.get("inner_L", 670.0) / 2:
                    lay.append((gl - tl - sec(bi_)["t"], gl - tl, bi_ + " nối trong " + BSTUB.get("joint_name", "B-B")))
                for sp_ in ST.CFG.get("leg_splices", []):
                    ti_ = sec(sp_["inner"])["t"]
                    if abs(zq - sp_["z"]) < sp_["inner_L"] / 2:
                        lay.append((gl - tl - ti_, gl - tl, sp_["inner"] + " nối trong"))
            return lay
        for L_ in legs:
            ylo, yhi = sorted((L_["a"][1], L_["b"][1]))
            yhi = max(yhi, KTOP or yhi)
            if not (ylo <= q[1] <= yhi):
                continue
            # cánh thanh cánh trên mặt: từ lưng (cách đường tim g, phía ngoài) tới mép (150 - g, phía trong)
            sgn = 1 if L_ is Lg else -1                      # phía trong mặt = +x với thanh cánh trái
            off = (q[0] - xline(L_, min(q[1], KY) if KTOP else q[1])) * SC * sgn
            if -L_["g"] + 5 <= off <= sec(L_["section"])["b"] - L_["g"] - 5:
                lay.append((gl - tl, gl, L_["section"]))
        if any(n_.startswith(Lg["section"]) for _, _, n_ in lay) and \
                any(pl.get("splice") and point_in_poly(q, pl["pts"]) for pl in plates2d):
            lay.append((gl - tl - 9, gl - tl, "HL130X9 nối trong"))
        elif ST.CFG.get("top_kink") and q[1] > max(Lg["a"][1], Lg["b"][1]) + 1e-6:
            pass                                       # phần uốn thẳng đứng: lỗ chờ nối thanh cánh đoạn trên
        elif lay and all(n_.startswith(Lg["section"]) for _, _, n_ in lay):
            # mối nối thanh cánh: thép góc nối trong HL130x9 + bản nối ngoài d10 (hình cắt A-A)
            lay += [(gl - tl - 9, gl - tl, "HL130X9 nối trong"), (gl, gl + 10, "bản nối ngoài d10")]
        return lay
    _l = locals()
    return {k_: _l[k_] for k_ in ['ED', 'L', 'a_', 'b_', 'bb', 'bolt_len', 'bolts2d', 'c1', 'c2', 'd_', 'dd', 'e', 'layers_at', 'm', 'mt', 'nb_', 'need', 'pl', 'q', 's1', 's2', 'sb', 't_', 'u_'] if k_ in _l}

