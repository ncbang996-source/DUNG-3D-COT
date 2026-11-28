"""Bước hoàn thiện sau khi dựng / ghép (góp ý gop_y 20261127_1721):
(a) đầu thanh vách thò ra ngoài mặt lưng thanh mặt cột (thanh chủ) -> vát tam giác phần thò;
(b) đầu bu lông / đai ốc / thân bu lông cấn thép (thanh không thuộc lớp kẹp) -> vát tam giác đầu thanh bị cấn,
    giữ khoảng cách bu lông tới mép (fixes.tri_search); cấn ở giữa thanh -> báo, không tự sửa.

Chạy: python3 tools/bvtc/hoan_thien.py <scene vào> <scene ra>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_dt02 as CK  # noqa: E402
import fixes as F  # noqa: E402

TOL = 0.0005


def end_key(m, q):
    P1, P2 = CK.frame(m)[:2]
    L = np.linalg.norm(P2 - P1)
    x = float(np.dot(np.array(q) - P1, (P2 - P1) / L))
    return ("cut1" if x < L / 2 else "cut2"), min(x, L - x)


def protrusion_fix(s, S, rep):
    """Thanh vách (rule plan) thò ra ngoài mặt lưng thanh chủ (cánh liên kết thanh mặt cột, phía ngoài cột)."""
    M = {m["id"]: m for m in s["members"]}
    for m in [x for x in s["members"] if x["rule"] == "plan"]:
        for hid in m.get("host_ids") or []:
            h = M.get(hid)
            if h is None or h["rule"] != "face":
                continue
            P1h, P2h, e1h, e2h = CK.frame(h)
            n = -e2h if h.get("side") == "TRONG" else e2h          # pháp tuyến ra ngoài cột của mặt lưng
            o = P1h - e1h * h["g"][0] / 1000 - e2h * h["g"][1] / 1000
            if h.get("side") != "TRONG":
                # thanh chủ NGOÀI: cánh còn lại (cánh nằm, nơi thanh vách bắt) chĩa ra ngoài cột -> giới hạn = mép cánh đó
                o = o + e2h * S[h["section"]]["b"] / 1000
            sp = CK.samples(m, S)
            out = (sp - o) @ n > TOL
            if not out.any():
                continue
            q = sp[out].mean(0)
            key, _ = end_key(m, q)
            if m.get(key):
                rep.append({"loai": "thò ra ngoài mặt lưng", "thanh": m["id"], "loi": "đầu thanh đã có vát"})
                continue
            spots = F.bolt_spots(m, S, s["bolts"])

            def touching(m=m, o=o, n=n):
                return bool(np.any((CK.samples(m, S) - o) @ n > TOL))
            best = F.tri_search([(m, key, spots, touching)], S, amax_frac=0.6)
            if best:
                cut = best[3]
                cut["note"] = "vát tam giác %s %dx%dmm (ĐỀ XUẤT - phần thò ra ngoài mặt lưng thanh mặt cột)" % (
                    "cánh còn lại" if cut["flange"] == "out" else "mép cánh liên kết", cut["a"], cut["b"])
                m[key] = cut
                rep.append({"loai": "thò ra ngoài mặt lưng", "thanh": m["id"], "vat": "%dx%d %s" % (cut["a"], cut["b"], cut["flange"])})
            else:
                rep.append({"loai": "thò ra ngoài mặt lưng", "thanh": m["id"], "loi": "không gỡ được"})


def restack(b, s, S):
    """Xếp lại lớp kẹp bu lông theo hình học thật (dọc trục, cụm lớp liền nhau quanh giữa lớp kẹp cũ)."""
    import xa
    ax = np.array(b.get("nut") or b["axis"], float)
    mid = np.array(b["p"]) + ax * (b.get("grip_mm") or 20) / 2000
    runs = xa.stack(mid, ax, s["members"], s["plates"], S, span=0.08)
    if not runs:
        return False
    runs.sort()
    groups = [[runs[0]]]
    for r_ in runs[1:]:
        if r_[0] - max(x[1] for x in groups[-1]) <= (0.025 if b.get("no_filler") else 0.010):   # khe <= 10 mm (lệch giữa 2 đoạn ghép): bu lông qua đủ lớp
            groups[-1].append(r_)
        else:
            groups.append([r_])
    g = min(groups, key=lambda G: 0 if G[0][0] <= 0 <= max(x[1] for x in G) else
            min(abs(G[0][0]), abs(max(x[1] for x in G))))
    s0, s1 = g[0][0], max(x[1] for x in g)
    gaps, e = [], g[0][1]
    for r_ in g[1:]:
        if r_[0] > e + 0.0012 and b.get("no_filler"):
            gaps.append(round((r_[0] - e) * 1000, 1))      # người dùng: không đặt vòng đệm (VD mặt cắt 2-2 xà X1)
        elif r_[0] > e + 0.0012:
            gaps.append(round((r_[0] - e) * 1000, 1))
            # tấm đệm dày vừa khe (quy tắc đã chốt), vuông 44 x 44 quanh bu lông
            c = mid + ax * e
            e1 = np.cross(ax, [0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.cross(ax, [1.0, 0, 0])
            e1 = e1 / np.linalg.norm(e1)
            e2 = np.cross(ax, e1)
            tt = (r_[0] - e) * 1000 - 0.4
            s["plates"].append({"kind": "filler", "node": np.round(c, 4).tolist(), "members": [], "t_mm": round(tt, 1),
                                "on_leg": False, "origin": np.round(c + ax * 0.0002, 5).tolist(),
                                "a1": np.round(e1, 6).tolist(), "a2": np.round(e2, 6).tolist(),
                                "thick_dir": np.round(ax, 6).tolist(),
                                "poly": [[round(0.0185 * np.cos(2 * np.pi * k / 16), 5), round(0.0185 * np.sin(2 * np.pi * k / 16), 5)]
                                         for k in range(16)],
                                "area_m2": 0.00194, "mass_kg": round(0.00194 * tt / 1000 * 7850, 2), "bolt_max": 1,
                                "d_max_mm": b.get("d_mm", 16), "leg_bolts": 0,
                                "reason": "tấm đệm dày %.1f vừa khe giữa các lớp (lệch 2 đoạn ghép)" % tt})
        e = max(e, r_[1])
    b["khe_lop_mm"] = gaps
    grip = (s1 - s0) * 1000
    d = b.get("d_mm", 16)
    b["p"] = np.round(mid + ax * s0, 5).tolist()
    b["grip_mm"] = round(grip, 1)
    need = grip + 0.8 * d + 7
    if (b.get("L_mm") or 0) < need:
        b["L_mm"] = int(np.ceil(need / 10) * 10)
        b["L_from"] = "tính (xếp lại lớp kẹp)"
    return True


def bolt_fix(s, S, rep):
    M = {m["id"]: m for m in s["members"]}
    # 1. bu lông có thanh nằm trên trục nhưng lớp kẹp chưa tính (đầu / đai ốc nằm trong thanh đó): xếp lại lớp kẹp
    n_re = 0
    for r in CK.bolt_steel(s, S):
        b = s["bolts"][r["bolt"]]
        m = M[r["m"]]
        ax = np.array(b.get("nut") or b["axis"], float)
        line = np.array(b["p"]) + np.outer(np.linspace(-0.05, (b.get("grip_mm") or 20) / 1000 + 0.05, 61), ax)
        if np.any(CK.where_v(m, S, line, 0.0005) > 0) and restack(b, s, S):
            n_re += 1
            if b.get("khe_lop_mm"):
                rep.append({"loai": "bu lông xếp lại lớp kẹp", "bu_long": r["bolt"], "khe_mm": b["khe_lop_mm"],
                            "at": np.round(b["p"], 3).tolist(), "ghi_chu": "khe giữa các lớp (lệch 2 đoạn ghép) - đã đặt tấm đệm vừa khe"})
    if n_re:
        rep.append({"loai": "bu lông xếp lại lớp kẹp", "so": n_re})
    for r in CK.bolt_steel(s, S):
        m = M[r["m"]]
        b = s["bolts"][r["bolt"]]
        Q = CK.bolt_body_points(b, shank=(r["loai"] == "thân"))
        hit = Q[CK.where_v(m, S, Q, TOL) > 0]
        if not len(hit):
            continue                                     # đã gỡ khi sửa chỗ khác
        key, dx = end_key(m, hit.mean(0))
        if dx > 0.25:
            rep.append({"loai": "bu lông cấn thép", "thanh": m["id"], "bu_long": r["bolt"], "loi": "cấn giữa thanh"})
            continue
        spots = F.bolt_spots(m, S, s["bolts"])
        if m.get(key) and m[key]["flange"] in ("out", "conn") and not m.get(key + "b"):
            # đầu thanh đã có vát tam giác ở 1 cánh: thêm vát tam giác ở cánh kia (giữ vát cũ)
            other = "conn" if m[key]["flange"] == "out" else "out"

            def touch2(m=m, Q=Q):
                return bool(np.any(CK.where_v(m, S, Q, TOL) > 0))
            best = F.tri_search([(m, key + "b", spots, touch2)], S, amax_frac=0.6, flanges=(other,))
            if best:
                cut = best[3]
                cut["note"] = "vát tam giác %s %dx%dmm (ĐỀ XUẤT - tránh cấn đầu / đai ốc bu lông M%d)" % (
                    "cánh còn lại" if other == "out" else "mép cánh liên kết", cut["a"], cut["b"], r["d"])
                m[key + "b"] = cut
                rep.append({"loai": "bu lông cấn thép", "thanh": m["id"], "vat_them": "%dx%d %s" % (cut["a"], cut["b"], other)})
                continue
        c0 = m.pop(key, None)
        # vát đang có ở đầu này (gỡ chạm trước đó): tìm vát mới thay thế, vẫn phải hết chạm với các thanh quanh đầu thanh
        P_ = np.array(m["p1"] if key == "cut1" else m["p2"])
        # mọi bu lông quanh đầu thanh (đầu / đai ốc; thân nếu thanh không phải lớp kẹp của bu lông đó)
        for b2 in s["bolts"]:
            if b2 is b or np.linalg.norm(np.array(b2["p"]) - P_) > 0.3:
                continue
            Q = np.r_[Q, CK.bolt_body_points(b2)]
        near = [o for o in s["members"] if o is not m and CK.seg_dist(P_, P_ + 1e-6, *CK.frame(o)[:2]) < 0.3]
        ec = F.EndContact(S, [(m, key, o, None, 0.001) for o in near]) if c0 else None
        pls = [pp for pp in (CK.plate_points(pl) for pl in s["plates"] if pl.get("kind") != "filler"
                             and np.linalg.norm(np.array(pl["node"]) - P_) < 0.6) if len(pp)] if c0 else []

        def touching(m=m, Q=Q, ec=ec, pls=pls):
            return bool(np.any(CK.where_v(m, S, Q, TOL) > 0)) or (ec is not None and ec.touching()) or \
                any(np.any(CK.where_v(m, S, pp, 0.001) > 0) for pp in pls)
        best = F.tri_search([(m, key, spots, touching)], S, amax_frac=0.6)
        if not best and not any(sp_[2] == "out" for sp_ in spots):
            # cánh còn lại không có lỗ ở thanh này: cho vát tam giác cánh còn lại tới 75% bề rộng
            best = F.tri_search([(m, key, spots, touching)], S, amax_frac=0.75, flanges=("out",))
        if not best and c0:
            m[key] = c0
        if best:
            cut = best[3]
            cut["note"] = "vát tam giác %s %dx%dmm (ĐỀ XUẤT - tránh cấn %s bu lông M%d)" % (
                "cánh còn lại" if cut["flange"] == "out" else "mép cánh liên kết", cut["a"], cut["b"],
                "thân" if r["loai"] == "thân" else "đầu / đai ốc", r["d"])
            m[key] = cut
            rep.append({"loai": "bu lông cấn thép", "thanh": m["id"], "vat": "%dx%d %s" % (cut["a"], cut["b"], cut["flange"])})
        else:
            rep.append({"loai": "bu lông cấn thép", "thanh": m["id"], "bu_long": r["bolt"], "loi": "không gỡ được"})


def plate_fix(s, S, rep):
    """Bản mã chạm thanh ở gần đầu thanh (VD tai bản mã bẻ theo mặt xà X1): vát tam giác đầu thanh."""
    M = {m["id"]: m for m in s["members"]}
    for r in CK.plate_clashes(s, S):
        m = M[r["m"]]
        pl = s["plates"][r["plate"]]
        if pl.get("kind") == "filler":
            rep.append({"loai": "tấm đệm chạm thép", "thanh": m["id"], "loi": "cần xem"})
            continue
        pts = CK.plate_points(pl)
        h = pts[CK.where_v(m, S, pts, 0.001) > 0]
        if not len(h):
            continue
        key, dx = end_key(m, h.mean(0))
        if dx > 0.3:
            rep.append({"loai": "bản mã chạm thép", "thanh": m["id"], "loi": "giữa thanh"})
            continue
        k2 = key if not m.get(key) else (key + "b" if not m.get(key + "b") else None)
        if k2 is None:
            rep.append({"loai": "bản mã chạm thép", "thanh": m["id"], "loi": "đầu thanh đã có 2 vát"})
            continue
        fls = ("out", "conn") if k2 == key else (("conn",) if m[key]["flange"] == "out" else ("out",))

        def touching(m=m, pts=pts):
            return bool(np.any(CK.where_v(m, S, pts, 0.001) > 0))
        best = F.tri_search([(m, k2, F.bolt_spots(m, S, s["bolts"]), touching)], S, amax_frac=0.6, flanges=fls)
        if best:
            cut = best[3]
            cut["note"] = "vát tam giác %s %dx%dmm (ĐỀ XUẤT - tránh chạm bản mã)" % (
                "cánh còn lại" if cut["flange"] == "out" else "mép cánh liên kết", cut["a"], cut["b"])
            m[k2] = cut
            rep.append({"loai": "bản mã chạm thép", "thanh": m["id"], "vat": "%dx%d %s" % (cut["a"], cut["b"], cut["flange"])})
        else:
            rep.append({"loai": "bản mã chạm thép", "thanh": m["id"], "loi": "không gỡ được"})


def main(src, dst):
    s = json.load(open(src))
    S = s["sections"]
    rep = []
    if "--ghep" not in sys.argv:
        protrusion_fix(s, S, rep)          # host_ids chỉ đúng trong scene từng đoạn (mô hình ghép đánh lại số thanh)
    plate_fix(s, S, rep)
    bolt_fix(s, S, rep)
    s["report"]["build"]["hoan_thien"] = rep
    json.dump(s, open(dst, "w"), ensure_ascii=False)
    import collections
    print(json.dumps(collections.Counter((r["loai"], "lỗi: " + r["loi"] if "loi" in r else "đã sửa") for r in rep)
                     .most_common(), ensure_ascii=False))
    for r in rep:
        if "loi" in r:
            print("  ", r)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])  # thêm --ghep cho mô hình đã ghép
