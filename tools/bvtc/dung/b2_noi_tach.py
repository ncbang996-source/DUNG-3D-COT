"""Đoạn đặt trên đoạn khác (bản mã chờ), bản mã nối đỉnh, tách thanh tại bản mã.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (A_, Lg, P, _, a_, b_, banma, bolt_ins, cxy_, i, idx, inb, keep, m, ok_, p, pl, plates2d, rep, res_, sof, xc, ys_,) = (V.get(k_) for k_ in ("A_", "Lg", "P", "_", "a_", "b_", "banma", "bolt_ins", "cxy_", "i", "idx", "inb", "keep", "m", "ok_", "p", "pl", "plates2d", "rep", "res_", "sof", "xc", "ys_",))
    # --- đoạn đặt trên đoạn khác (DT-01 trên DT-02, người dùng chốt: bỏ bản đế, ráp vào bản mã chờ của DT-02):
    #     lấy bản mã nối d10 vẽ ở đỉnh tờ đoạn dưới, dời sang tờ này sao cho lỗ chờ trùng bu lông chân thanh cánh +
    #     đầu dưới thanh xiên vẽ trên tờ này (khớp theo lỗ, mỗi bên một phép dời)
    ONTOP = ST.CFG.get("on_top_of")
    if ONTOP:
        bx2 = SHEETS[ONTOP["sheet"]]["box"]
        inb2 = lambda p: bx2[0] <= p[0] <= bx2[2] and bx2[1] <= p[1] <= bx2[3]
        ytop2 = bx2[3]
        y_leg0 = min(Lg["a"][1], Lg["b"][1])
        B1 = [q for q, _ in bolt_ins if inb(q) and (q[1] - y_leg0) * SC < 900]
        rep["joint"] = []
        for P in banma:
            if not all(inb2(q) for q in P) or max(q[1] for q in P) < ytop2 - 80:
                continue
            ysz = (max(q[1] for q in P) - min(q[1] for q in P)) * SC
            if ysz < 500:
                continue
            B2 = [q for q, _ in bolt_ins if point_in_poly(q, P)]
            ymid2 = (max(q[1] for q in P) + min(q[1] for q in P)) / 2
            up2 = [q for q in B2 if q[1] > ymid2]
            if not up2 or not B1:
                continue
            # dời ban đầu: tâm nhóm lỗ trên (thuộc đoạn này) -> tâm bu lông cùng phía thanh cánh trên tờ này
            sideL = np.mean([q[0] for q in up2]) < (bx2[0] + bx2[2]) / 2
            B1s = np.array([q for q in B1 if (q[0] < xc) == sideL])
            if not len(B1s):
                continue
            U2 = np.array(up2)
            # phép dời khớp nhiều lỗ nhất (thử mọi cặp lỗ chờ - bu lông), rồi tinh chỉnh trung bình
            best_ = None
            for a_ in U2:
                for b_ in B1s:
                    t_ = b_ - a_
                    nmatch = sum(1 for q in U2 + t_ if np.min(np.linalg.norm(B1s - q, axis=1)) * SC < 12)
                    if best_ is None or nmatch > best_[0]:
                        best_ = (nmatch, t_)
            tr = best_[1]
            for _ in range(6):
                A_ = U2 + tr
                idx = [int(np.argmin(np.linalg.norm(B1s - a_, axis=1))) for a_ in A_]
                ok_ = [i for i, j in enumerate(idx) if np.linalg.norm(B1s[j] - A_[i]) * SC < 15]
                if not ok_:
                    break
                tr = tr + np.mean([B1s[idx[i]] - A_[i] for i in ok_], axis=0)
            A_ = U2 + tr
            res_ = [float(np.min(np.linalg.norm(B1s - a_, axis=1))) * SC for a_ in A_]
            pts_ = [(q[0] + tr[0], q[1] + tr[1]) for q in P]
            cxy_ = (sum(q[0] for q in pts_) / len(pts_), sum(q[1] for q in pts_) / len(pts_))
            plates2d.append({"pts": pts_, "pts0": pts_, "t": ONTOP["plate_t"], "nodes": [cxy_], "ext": ONTOP["sheet"],
                             "splice": True})
            rep["joint"].append({"ben": "trái" if sideL else "phải", "doi_mm": [round(tr[0] * SC, 1), round(tr[1] * SC, 1)],
                                 "lo_khop": len(ok_), "lech_lo_max_mm": round(max(res_), 1)})
    # đoạn dưới cùng có bản mã nối thanh cánh ở đỉnh (bản mã chờ đoạn trên): dày theo chi tiết, đánh dấu mối nối
    TS = ST.CFG.get("top_splice")
    if TS:
        ytop_leg_ = max(Lg["a"][1], Lg["b"][1])
        for pl in plates2d:
            ys_ = [q[1] for q in pl["pts"]]
            if min(ys_) < ytop_leg_ < max(ys_):
                pl["t"], pl["splice"] = TS["plate_t"], True

    # --- thanh vẽ liền một đường tâm nhưng nét mép bị ngắt tại bản mã (VD thanh ngang L80x6 qua bản mã giữa):
    #     thực tế là 2 thanh, mỗi thanh dừng ở bản mã. Tách tại giữa chỗ ngắt.
    rep["split_at_plate"] = []
    for m in list(keep):
        iv = sorted(m["edge_iv"])
        if not iv:
            continue
        merged = [list(iv[0])]
        for a_, b_ in iv[1:]:
            if a_ > merged[-1][1] + 1e-6:
                merged.append([a_, b_])
            else:
                merged[-1][1] = max(merged[-1][1], b_)
        for (a0, a1_), (b0, b1_) in zip(merged, merged[1:]):
            if b0 - a1_ < 4.0:
                continue
            smid = (a1_ + b0) / 2
            pm_ = (m["ref_a"][0] + m["ref_u"][0] * smid, m["ref_a"][1] + m["ref_u"][1] * smid)
            # chỉ tách khi bản mã có bản hàn vuông góc chắn giữa (DT-02: 419); thanh TRONG chạy sau bản mã ngoài
            # cũng bị ngắt nét nhưng vẫn liền (DT-01 nút giữa 1-1)
            plk_ = next((pl for pl in plates2d if point_in_poly(pm_, pl["pts"]) and "strip" in pl), None)
            if plk_ is None:
                continue
            # góp ý (người dùng chốt): 3 thanh giao nhau thì ít nhất 1 thanh chạy thẳng. Các thanh xiên đã dừng ở
            # bản mã này (đầu thanh nằm trong bản mã) -> thanh ngang chạy liên tục, không tách (DT-02 nút giữa)
            ends_in_ = sum(1 for o in keep if o is not m for q in (o["c1"], o["c2"]) if point_in_poly(q, plk_["pts"]))
            if ends_in_ >= 2:
                rep["split_at_plate"].append({"section": m["section"], "khong_tach": "thanh xiên đã dừng ở bản mã "
                                              "(%d đầu thanh) -> thanh này chạy liên tục" % ends_in_})
                continue
            P = lambda s_: (m["ref_a"][0] + m["ref_u"][0] * s_, m["ref_a"][1] + m["ref_u"][1] * s_)
            sof = lambda q: (q[0] - m["ref_a"][0]) * m["ref_u"][0] + (q[1] - m["ref_a"][1]) * m["ref_u"][1]
            sc1, sc2 = sorted((sof(m["c1"]), sof(m["c2"])))
            sb1, sb2 = merged[0][0], merged[-1][1]
            parts = []
            for (cs, ce, bs, be) in ((sc1, smid, sb1, a1_), (smid, sc2, b0, sb2)):
                n_ = dict(m)
                n_["c1"], n_["c2"], n_["b1"], n_["b2"] = P(cs), P(ce), P(bs), P(be)
                n_["p1"], n_["p2"] = P(min(cs, bs)), P(max(ce, be))
                n_["edge_iv"] = [x for x in iv if bs - 1e-6 <= x[0] <= be + 1e-6]
                n_["split_from"] = True
                parts.append(n_)
            keep.remove(m)
            keep.extend(parts)
            rep["split_at_plate"].append({"section": m["section"], "ang": round(m["ang"], 1),
                                          "gap_mm": round((b0 - a1_) * SC)})
            break
    _l = locals()
    return {k_: _l[k_] for k_ in ['B1', 'B2', 'ONTOP', 'P', 'TS', '_', 'a_', 'b1_', 'b_', 'be', 'cxy_', 'idx', 'm', 'n_', 'pl', 'pm_', 'pts_', 'sof', 't_'] if k_ in _l}

