"""Đọc mặt đứng, lọc thanh giằng (trong thân / khuất / xà / tờ kề), cắt theo nét đầu thanh, gốc cao độ.

Một bước của dt02.main (tách tự động - xem docs/BO_DUNG.md). Vào: biến các bước trước (V); ra: biến bước sau dùng.
"""
from dt02_base import *  # noqa: F401,F403
import state as ST  # noqa: F401


def run(V):  # noqa: C901
    (dxf,) = (V.get(k_) for k_ in ("dxf",))
    doc = read_dxf_cached(dxf)
    msp = doc.modelspace()
    rep = {"warnings": []}
    ms, segs, braces, legs, wps = read_elevation(doc, msp)
    Lg, Rg = legs
    xline = lambda leg, y: leg["w1"][0] + (y - leg["w1"][1]) * (leg["w2"][0] - leg["w1"][0]) / (leg["w2"][1] - leg["w1"][1])
    ymid = (Lg["w1"][1] + Lg["w2"][1]) / 2
    xc = (xline(Lg, ymid) + xline(Rg, ymid)) / 2
    halfw = lambda y: (xline(Rg, y) - xline(Lg, y)) / 2 * SC           # mm
    labs = R.text_labels(msp, ST.BOX)
    R.assign_labels(ms, labs, xc)
    for leg in legs:
        leg["section"] = ST.CFG.get("leg_section") or leg["m"].get("section") or "HL150X12"

    # chỉ giữ thanh giằng trong thân, có nét thấy (không phải toàn khuất), có tiết diện
    keep, dropped = [], []
    for m in braces:
        inside = all(abs(p[0] - xc) * SC <= halfw(p[1]) + 60 for p in (m["c1"], m["c2"]))
        ytop_leg = max(Lg["a"][1], Lg["b"][1], Rg["a"][1], Rg["b"][1])
        above = (m["c1"][1] + m["c2"][1]) / 2 > ytop_leg - 0.5        # thanh của đoạn phía trên vẽ tham chiếu
        if ST.CFG.get("leg_hidden_ok"):
            above = False                    # DN-01 là đoạn trên cùng: thanh ngang đỉnh nằm ngang đầu thanh cánh
        drop_ = any((m.get("section") in r_["sections"]) and (not r_.get("non_horizontal") or 3 < m["ang"] % 180 < 177)
                    for r_ in ST.CFG.get("drop_rules", []))
        if ST.CFG.get("bottom_stub") and max(m["c1"][1], m["c2"][1]) < min(Lg["a"][1], Lg["b"][1]) - 0.5:
            drop_ = True                                 # thanh của đoạn dưới vẽ tham chiếu
        if (ST.CFG.get("drop_rules") or ST.CFG.get("xa_keep_horizontal")) and not m["all_hidden"] and not drop_ \
                and not inside:
            # thanh chìa ra ngoài thân (xà): giữ nếu có nhãn; "xa_keep_horizontal" (người dùng chốt: phần xà dựng
            # sau) chỉ giữ thanh ngang mặt cột (L90x7 2840...), bỏ thanh xiên/chống của xà (L60x5, L70x6)
            horiz_ = m["ang"] % 180 < 3 or m["ang"] % 180 > 177
            inside = m.get("section") is not None and (horiz_ or not ST.CFG.get("xa_keep_horizontal"))
        if m["all_hidden"] or not inside or above or drop_:
            dropped.append(m)
            continue
        if not m.get("section"):
            freq = {}
            for t, _ in labs:
                freq[t] = freq.get(t, 0) + 1
            best = min(freq, key=lambda t: (abs(int(re.match(r"H?L(\d+)", t).group(1)) - m["width"]), -freq[t]))
            m["section"], m["section_from"] = best, "đoán theo bề rộng"
        keep.append(m)
    if ST.CFG.get("trim_to_end_lines"):
        # nét đầu thanh (đoạn ngắn lớp COT vuông góc trục, dài ~ bề rộng thanh) nằm trong khoảng thanh: thanh dừng ở đó
        # (nét kích thước lớp 0 thẳng hàng mép thanh làm thanh bị đọc dài ra - VD L90x7 xà DN-02)
        x0b, y0b, x1b, y1b = ST.BOX
        ends_ = [((e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])) for e in msp.query('LINE[layer=="COT"]')
                 if x0b <= e.dxf.start[0] <= x1b and y0b <= e.dxf.start[1] <= y1b]
        rep["ends_trimmed"] = []
        for m in keep:
            L = math.dist(m["c1"], m["c2"])
            u_ = ((m["c2"][0] - m["c1"][0]) / L, (m["c2"][1] - m["c1"][1]) / L)
            sof = lambda q: (q[0] - m["c1"][0]) * u_[0] + (q[1] - m["c1"][1]) * u_[1]
            s1, s2 = sorted((sof(m["b1"]), sof(m["b2"])))
            for a_, b_ in ends_:
                ln = math.dist(a_, b_)
                if not (0.6 * m["width"] / SC <= ln <= 1.4 * m["width"] / SC):
                    continue
                d_ = ((b_[0] - a_[0]) / ln, (b_[1] - a_[1]) / ln)
                if abs(d_[0] * u_[0] + d_[1] * u_[1]) > 0.05:
                    continue
                mid_ = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
                if dist_line(mid_, m["c1"], m["c2"]) * SC > 0.7 * m["width"]:
                    continue
                sm = sof(mid_)
                if s1 + 1.0 < sm < s1 + 0.45 * (s2 - s1) and (sm - s1) * SC > 100:
                    rep["ends_trimmed"].append({"section": m.get("section"), "mm": round((sm - s1) * SC)})
                    s1 = sm
                elif s2 - 0.45 * (s2 - s1) < sm < s2 - 1.0 and (s2 - sm) * SC > 100:
                    rep["ends_trimmed"].append({"section": m.get("section"), "mm": round((s2 - sm) * SC)})
                    s2 = sm
            P_ = lambda t: (m["c1"][0] + u_[0] * t, m["c1"][1] + u_[1] * t)
            if sof(m["b1"]) <= sof(m["b2"]):
                m["b1"], m["b2"] = P_(s1), P_(s2)
            else:
                m["b1"], m["b2"] = P_(s2), P_(s1)
    rep["n_brace_drawing"] = len(braces)
    rep["n_brace_kept"] = len(keep)
    rep["dropped"] = [{"ang": round(m["ang"], 1), "w": m["width"], "edges": m["edges"]} for m in dropped]

    # --- gốc cao độ: đầu dưới thanh cánh
    y0 = min(Lg["a"][1], Lg["b"][1])
    zf = lambda y: (y - y0) * SC                                          # mm
    _l = locals()
    return {k_: _l[k_] for k_ in ['L', 'Lg', 'P_', '_', 'a_', 'b_', 'best', 'd_', 'doc', 'halfw', 'inside', 'keep', 'labs', 'legs', 'm', 'ms', 'msp', 'rep', 's1', 's2', 'segs', 'sof', 't', 'u_', 'xc', 'xline', 'y0', 'zf'] if k_ in _l}

