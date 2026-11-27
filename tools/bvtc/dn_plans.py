"""Vách ngang đoạn có 2 kiểu mặt (DN-02): dựng lại thanh giằng vách theo mặt cắt, không cắt 1/4 rồi xoay.

Chạy: python3 tools/bvtc/dn_plans.py <dxf> <tờ, VD DN-02> <scene vào (đã ghép mặt)> <scene ra>

Mỗi mặt cắt (1-1, 2-2, 3-3): 2 thanh chéo L60x5 chạy suốt góc - góc, chéo nhau ở tâm (1 bu lông + tấm đệm "1D").
- Thanh nét LIỀN: cánh còn lại chĩa LÊN, đặt TRÊN cánh nằm ngang của thanh ngang mặt cột; nét KHUẤT: chĩa XUỐNG,
  đặt DƯỚI cánh đó (quy tắc đã chốt). Thanh chủ ở mỗi đầu = thanh ngang mặt cột có cánh nằm ngang chứa tim bu lông
  (tìm theo hình 3D đã dựng). Ở tâm 2 thanh cách nhau = chiều dày cánh thanh chủ, lót tấm đệm theo ký hiệu.
- Đầu thanh = tim bu lông ngoài cùng + 25 mm (M16). Bu lông đứng xỏ từ dưới lên.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import check_dt02 as CK  # noqa: E402
import dt02 as T  # noqa: E402
import fixes as F  # noqa: E402

SC = 25.0
ED = {16: 25.0, 20: 30.0, 24: 40.0}


def flange_z(host, S, xy, r=0.012):
    """Khoảng z (m) của cánh nằm ngang thanh chủ tại vị trí xy (lấy theo điểm mẫu hình 3D)."""
    sp = CK.samples(host, S, step=0.004)
    near = sp[np.linalg.norm(sp[:, :2] - np.array(xy), axis=1) < r]
    if not len(near):
        return None
    return float(near[:, 2].min()) - 0.0015, float(near[:, 2].max()) + 0.0015     # mẫu cách mặt 1,5 mm


def main(dxf, sheet, scene_in, scene_out):
    T.use_sheet(sheet)
    doc = T.read_dxf_cached(dxf)
    msp = doc.modelspace()
    s = json.load(open(scene_in))
    S = s["sections"]
    rep = {}
    s["members"] = [m for m in s["members"] if m["rule"] != "plan"]
    s["bolts"] = [b for b in s["bolts"] if b["kind"] != "plan"]
    s["plates"] = [p for p in s["plates"] if "mặt cắt" not in p.get("reason", "") and "tâm vách" not in p.get("reason", "")]
    zlev = {k: v["z_mm"] for k, v in s["report"]["build"]["mat_A"]["plans"].items()}
    nid = max(m["id"] for m in s["members"])
    for pname, (_ym, box) in T.PLANS.items():
        z = zlev[pname] / 1000
        pm = T.R.members(doc, msp, box)
        T.R.assign_labels(pm, T.R.text_labels(msp, box), None)
        diags = [m for m in pm if m["width"] < 120 and 20 < m["ang"] % 180 < 160 and abs(m["ang"] % 180 - 90) > 20]
        ins = lambda p: box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
        # bu lông vách (khối 1/2/3 = M16/M20/M24; DN-01 vách 1-1 dùng M20)
        bins = [((e.dxf.insert[0], e.dxf.insert[1]), {"1": 16, "2": 20, "3": 24}[e.dxf.name]) for e in msp.query("INSERT")
                if e.dxf.name in ("1", "2", "3") and ins(e.dxf.insert)]
        dsym = [(e.dxf.insert[0], e.dxf.insert[1]) for e in msp.query("INSERT") if e.dxf.name == "D" and ins(e.dxf.insert)]
        dl = None
        for t_ in msp.query("TEXT"):
            mt = re.fullmatch(r"(\d*)D\.(\d+)_(\d+)", t_.dxf.text.strip())
            if mt and ins(t_.dxf.insert):
                dl = (int(mt.group(1) or 1), float(mt.group(3)))
        blab = {}
        for t_ in msp.query("TEXT"):
            mt = re.fullmatch(r"1\.(\d+)_(\d+)", t_.dxf.text.strip())
            if mt and ins(t_.dxf.insert):
                blab.setdefault(int(mt.group(1)), []).append(int(mt.group(2)))
        # tâm vách = giao 2 đường tâm thanh chéo
        a, b = diags[0], diags[1]
        cen = T.inter(a["c1"], a["c2"], b["c1"], b["c2"])
        loc = lambda p: np.array([(p[0] - cen[0]) * SC, (p[1] - cen[1]) * SC]) / 1000      # m, hệ mô hình
        hosts_all = [m for m in s["members"] if m["rule"] == "face" and m["type"] == "G" and
                     abs((m["p1"][2] + m["p2"][2]) / 2 - z) < 0.2]
        made = []
        for d in diags:
            c1, c2 = loc(d["c1"]), loc(d["c2"])
            u = (c2 - c1) / np.linalg.norm(c2 - c1)
            nrm = np.array([-u[1], u[0]])
            on = [(loc(q), d_) for q, d_ in bins if abs(np.dot(loc(q) - c1, nrm)) < 0.008]
            ends = sorted(on, key=lambda q: np.dot(q[0] - c1, u))
            (e1b, d1b), (e2b, d2b) = ends[0], ends[-1]
            up = d["vis"] == "S"
            zr = []
            hid = []
            for eb in (e1b, e2b):
                best = None
                for h in hosts_all:
                    fz = flange_z(h, S, eb)
                    if fz and (best is None or abs(fz[0] - z) < abs(best[1][0] - z)):
                        best = (h, fz)
                if best is None:
                    raise SystemExit(f"{pname}: không tìm được thanh chủ tại bu lông {np.round(eb, 3)}")
                hid.append(best[0]["id"])
                zr.append(best[1])
            secn = d.get("section") or "L60X5"
            sct = S.get(secn) or T.sec(secn)
            S[secn] = sct
            tt = sct["t"] / 1000
            g = d.get("heel_to_center") or sct["b"] / 2
            P1 = np.array([*(e1b - u * ED[d1b] / 1000), zr[0][1] if up else zr[0][0]])
            P2 = np.array([*(e2b + u * ED[d2b] / 1000), zr[1][1] if up else zr[1][0]])
            u3 = (P2 - P1) / np.linalg.norm(P2 - P1)
            e1 = np.array([nrm[0], nrm[1], 0.0])
            e2 = np.array([0, 0, 1.0 if up else -1.0])
            nid += 1
            m = {"id": nid, "p1": P1.round(5).tolist(), "p2": P2.round(5).tolist(),
                 "length": round(float(np.linalg.norm(P2 - P1)), 4), "section": secn, "A_cm2": sct["A_geom_cm2"],
                 "type": "G", "rule": "plan", "variant": "bv", "auto_variant": "bv",
                 "frames": {"bv": [e1.round(6).tolist(), e2.round(6).tolist()]}, "offs": {"bv": [0, 0, 0]},
                 "g": [g, 0.0], "group": 3, "bolts": {}, "bolt": None, "node1": None, "node2": None, "face_k": -1,
                 "x_pair": False, "default_up": up, "side": "LEN" if up else "XUONG", "plan": pname,
                 "host_ids": hid, "mass_kg": round(sct["A_geom_cm2"] * 1e-4 * float(np.linalg.norm(P2 - P1)) * 7850, 3)}
            s["members"].append(m)
            made.append(m)
            for eb, db_, (zb, zt) in zip((e1b, e2b), (d1b, d2b), zr):
                Lb = min(blab.get(db_, [40]))
                bot = zb - (0 if up else tt)
                top = zt + (tt if up else 0)
                s["bolts"].append({"id": 0, "p": [round(float(eb[0]), 5), round(float(eb[1]), 5), round(bot, 5)],
                                   "axis": [0, 0, 1.0], "nut": [0, 0, 1.0], "d_mm": db_,
                                   "grip_mm": round((top - bot) * 1000, 1), "L_mm": Lb, "L_from": "ký hiệu bản vẽ",
                                   "t_mm": 8, "kind": "plan"})
        # bu lông + tấm đệm ở tâm
        lo_m = min(made, key=lambda m: m["p1"][2])
        hi_m = max(made, key=lambda m: m["p1"][2])
        zc_lo = (lo_m["p1"][2] + lo_m["p2"][2]) / 2            # mặt trên thanh dưới (XUONG: mặt tựa = mặt trên)
        zc_hi = (hi_m["p1"][2] + hi_m["p2"][2]) / 2            # mặt dưới thanh trên
        gap = (zc_hi - zc_lo) * 1000
        tf = dl[1] if dl else 6.0
        nf = max(1, round(gap / tf)) if gap > tf / 2 else 0
        rr = 0.022
        for i in range(nf):
            z0 = zc_lo + i * tf / 1000
            poly = [[round(rr * math.cos(2 * math.pi * k / 20), 5), round(rr * math.sin(2 * math.pi * k / 20), 5)]
                    for k in range(20)]
            s["plates"].append({"kind": "filler", "node": [0, 0, round(z0, 5)], "members": [], "t_mm": tf,
                                "on_leg": False, "origin": [0.0, 0.0, round(z0, 5)], "a1": [1.0, 0, 0],
                                "a2": [0, 1.0, 0], "thick_dir": [0, 0, 1.0], "poly": poly,
                                "area_m2": round(math.pi * rr * rr, 5),
                                "mass_kg": round(math.pi * rr * rr * tf / 1000 * 7850, 2), "bolt_max": 1, "d_max_mm": 0,
                                "leg_bolts": 0, "reason": "tấm đệm Ø44 dày %g tâm vách %s (ký hiệu 1D)" % (tf, pname)})
        tlo = S[lo_m["section"]]["t"] / 1000
        thi = S[hi_m["section"]]["t"] / 1000
        bot, top = zc_lo - tlo, zc_hi + thi
        dc_ = min(bins, key=lambda b_: math.dist(b_[0], cen))[1]
        Lc = max(blab.get(dc_, [50]))
        s["bolts"].append({"id": 0, "p": [0.0, 0.0, round(bot, 5)], "axis": [0, 0, 1.0], "nut": [0, 0, 1.0],
                           "d_mm": dc_, "grip_mm": round((top - bot) * 1000, 1), "L_mm": Lc, "L_from": "ký hiệu bản vẽ",
                           "t_mm": 8, "kind": "plan"})
        rep[pname] = {"z_mm": zlev[pname], "khe_tam_mm": round(gap, 1), "tam_dem": f"{nf} x {tf:g}",
                      "ep_mm": round(gap - nf * tf, 1),
                      "thanh": [{"side": m["side"], "section": m["section"], "chu": m["host_ids"],
                                 "dai_mm": round(m["length"] * 1000)} for m in made]}
    # gỡ chạm: góc cánh còn lại ở đầu thanh vách lấn vào thanh mặt cột -> vát góc (bội 5 mm, diện tích cắt nhỏ nhất)
    faces = [m for m in s["members"] if m["rule"] in ("face", "leg")]
    fixes = []

    GAP = 0.010     # góp ý (người dùng chốt): khe tối thiểu 10 mm với thép khác (trừ thanh chủ thanh vách tựa lên)

    def hits(m, others, gap=GAP):
        sp = CK.samples(m, S)
        for o in others:
            e_ = 0.001 if o["id"] in m["host_ids"] else -gap
            if len(sp) and np.any(CK.where_v(o, S, sp, e_) > 0):
                return True
            so = CK.samples(o, S)
            if len(so) and np.any(CK.where_v(m, S, so, e_) > 0):
                return True
        return False
    pec = T.CFG.get("plan_end_cut", {})
    for m in [x for x in s["members"] if x["rule"] == "plan"]:
        for key, ck in (("p1", "cut1"), ("p2", "cut2")):
            P_ = np.array(m[key])
            near = [o for o in faces if CK.seg_dist(P_, P_ + 1e-6, *CK.frame(o)[:2]) < 0.3]
            n_ = pec.get(m["plan"])
            if n_:
                # vát ghi trên mặt cắt (VD DN-01 1-1 "vát cánh 20x20mm", 2-2 "60x60mm", mũi tên chỉ đầu thanh chéo ở
                # góc vách): chọn góc vát (mép cánh nằm / góc lưng / cánh đứng) gỡ được chạm, ưu tiên đạt khe 10 mm
                done = None
                for gap_ in (GAP, 0.0):
                    for fl_ in ("conn", "heel", "out"):
                        m[ck] = {"flange": fl_, "a": n_, "b": n_}
                        if not hits(m, near, gap_):
                            done = (fl_, gap_)
                            break
                    if done:
                        break
                if done:
                    m[ck]["note"] = "vát cánh %dx%dmm theo mặt cắt %s (%s)" % (
                        n_, n_, m["plan"], {"conn": "góc mép cánh nằm", "heel": "góc lưng",
                                            "out": "góc mép cánh đứng"}[done[0]])
                    fixes.append({"plan": m["plan"], "side": m["side"], "vat_mm": f"{n_}x{n_} (bản vẽ, {done[0]})",
                                  "khe_min_mm": round(done[1] * 1000)})
                    continue
                m.pop(ck, None)
            if not hits(m, near):
                continue
            best = None
            # khe mục tiêu 10 mm; không đạt (cánh nằm thanh vách cũng sát thép bên dưới) thì lấy khe lớn nhất đạt được.
            # Tìm nhanh (fixes.EndContact + first_ok): chỉ lấy mẫu vùng đầu thanh, b nhỏ nhất tìm bằng chia đôi -
            # cùng kết quả như thử lần lượt (vát lớn hơn chỉ bớt thép).
            for gap_ in (GAP, 0.008, 0.006, 0.005, 0.004, 0.003, 0.002, 0.0):
                m.pop(ck, None)
                ec = F.EndContact(S, [(m, ck, o, None, 0.001 if o["id"] in m["host_ids"] else -gap_) for o in near])
                for fl_ in ("out", "conn", "heel"):
                    amax = 25 if fl_ == "heel" else 55          # góc lưng: không cắt tới lỗ bu lông (đường đinh 35)
                    bmax = 150 if fl_ == "heel" else 395          # góc lưng: cánh còn lại lùi đúng b
                    m[ck] = {"flange": fl_, "a": amax, "b": bmax}
                    if ec.touching():
                        continue                   # vát tối đa cũng không đạt khe này
                    for A_ in range(10, amax + 5, 5):
                        cand = [B_ for B_ in range(10, bmax + 5, 5) if not (best and A_ * B_ >= best[0])]

                        def ok_b(B_, A_=A_, fl_=fl_):
                            m[ck] = {"flange": fl_, "a": A_, "b": B_}
                            return not ec.touching()
                        B_ = F.first_ok(cand, ok_b)
                        if B_ is not None:
                            best = (A_ * B_, A_, B_, gap_, fl_)
                if best:
                    break
            if best:
                m[ck] = {"flange": best[4], "a": best[1], "b": best[2],
                         "note": "vát góc %s %dx%dmm (ĐỀ XUẤT - khe >= %d mm với thép quanh góc vách)"
                                 % ({"out": "cánh còn lại", "conn": "mép cánh nằm", "heel": "lưng"}[best[4]],
                                    best[1], best[2],
                                    round(best[3] * 1000))}
                fixes.append({"plan": m["plan"], "side": m["side"], "vat_mm": f"{best[1]}x{best[2]} ({best[4]})",
                              "khe_min_mm": round(best[3] * 1000)})
            else:
                m.pop(ck, None)
                fixes.append({"plan": m["plan"], "side": m["side"], "loi": "không gỡ được"})
    rep["vat_goc"] = fixes
    s["report"]["build"]["vach_dn"] = rep
    json.dump(s, open(scene_out, "w"), ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:5])
