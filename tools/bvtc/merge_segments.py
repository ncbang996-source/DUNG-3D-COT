"""Ghép 2 đoạn đã dựng thành 1 mô hình: đoạn trên (vd DT-01) đặt lên đoạn dưới (vd DT-02).

Chạy: python3 tools/bvtc/merge_segments.py <scene đoạn dưới> <scene đoạn trên> <scene ra>

Đoạn trên dựng với cấu hình "on_top_of" có bản mã nối + thép góc nối trong của đoạn dưới (đánh dấu "ext") đặt
theo lỗ bu lông. Cao độ ráp = độ chênh tâm bản mã nối "ext" (đoạn trên) với bản mã nối cùng vị trí của đoạn dưới.
Phần "ext" của đoạn trên bỏ (đoạn dưới đã có); bu lông mối nối của đoạn trên giữ (đoạn dưới không có bu lông ở lỗ
chờ phía trên).
"""
import json
import math
import sys

import numpy as np


def plate_center(pl):
    o, a1, a2 = (np.array(pl[k]) for k in ("origin", "a1", "a2"))
    P = np.array(pl["poly"])
    return o + a1 * P[:, 0].mean() + a2 * P[:, 1].mean()


def main(lo_path, up_path, out_path, lo_sheet=None):
    lo, up = json.load(open(lo_path)), json.load(open(up_path))
    lo_sheet = lo_sheet or lo["title"].split()[2]
    ext = [p for p in up["plates"] if p.get("ext") == lo_sheet]
    spl = [p for p in lo["plates"] if "mối nối với đoạn trên" in p.get("reason", "")
           or "phần trên (bẻ góc" in p.get("reason", "")]
    if not ext or not spl:
        raise SystemExit("không thấy bản mã nối để ráp (ext ở đoạn trên / mối nối ở đoạn dưới)")
    d = []
    for p in ext:
        c = plate_center(p)
        td = np.array(p["thick_dir"])
        cands = [q for q in spl if np.dot(np.array(q["thick_dir"]), td) > 0.99]
        q = min(cands, key=lambda q: np.linalg.norm((plate_center(q) - c)[:2]))
        d.append(plate_center(q) - c)
    d = np.array(d)
    dz = float(np.median(d[:, 2]))
    # tinh chỉnh theo bu lông chung 2 đoạn (cùng lỗ, cùng trục): chênh cao độ trung vị của các cặp gần nhau
    lb = [b for b in lo["bolts"] if b["kind"] == "drawing"]
    pairs = []
    for b in up["bolts"]:
        if b["kind"] != "drawing":
            continue
        q = np.array(b["p"]) + np.array([0, 0, dz])
        for o in lb:
            dv = np.array(o["p"]) - q
            if np.linalg.norm(dv[:2]) < 0.015 and abs(dv[2]) < 0.06 and abs(np.dot(o["axis"], b["axis"])) > 0.99:
                pairs.append(dv[2])
    if len(pairs) >= 3:
        dz += float(np.median(pairs))
    n_pairs = len(pairs)
    resid = d - np.array([0, 0, float(np.median(d[:, 2]))])
    shift = np.array([0, 0, dz])

    def sh(v):
        return (np.array(v) + shift).round(5).tolist()

    members = [m for m in lo["members"]]
    nid = max(m["id"] for m in members)
    for m in up["members"]:
        if m.get("ext") == lo_sheet:
            continue
        m = dict(m)
        for k in ("p1", "p2", "p1d", "p2d"):
            if k in m:
                m[k] = sh(m[k])
        nid += 1
        m["id"] = nid
        m["segment"] = "tren"
        members.append(m)
    plates = list(lo["plates"])
    for p in up["plates"]:
        if p.get("ext") == lo_sheet:
            continue
        p = dict(p)
        for k in ("origin", "node"):
            p[k] = sh(p[k])
        plates.append(p)
    bolts = list(lo["bolts"])
    P_lo = np.array([b["p"] for b in bolts]) if bolts else np.zeros((0, 3))
    n_dup = 0
    for b in up["bolts"]:
        b = dict(b)
        b["p"] = sh(b["p"])
        # cùng lỗ đã có bu lông ở đoạn dưới (VD 3 bu lông bản mã 228 vào phần đứng DT-01): giữ 1
        if len(P_lo) and np.min(np.linalg.norm(P_lo - np.array(b["p"]), axis=1)) < 0.02:
            dup = next((j for j, o in enumerate(bolts) if np.linalg.norm(np.array(o["p"]) - np.array(b["p"])) < 0.02 and
                        abs(np.dot(o["axis"], b["axis"])) > 0.99), None)
            if dup is not None:
                n_dup += 1
                # giữ bản kẹp nhiều lớp hơn (VD 3 bu lông M24 bản mã 228: DN-02 có cả đầu thanh xiên, DT-01 thì không)
                if b.get("grip_mm", 0) > bolts[dup].get("grip_mm", 0) + 0.5:
                    bolts[dup] = b
                continue
        bolts.append(b)
    secs = dict(lo["sections"])
    secs.update(up["sections"])
    zs = [c for m in members for c in (m["p1"][2], m["p2"][2])]
    rep = {"ghep": {"doan_duoi": lo["title"], "doan_tren": up["title"], "cao_do_rap_m": round(dz, 4),
                    "lech_ngang_ban_ma_mm": round(float(np.abs(resid[:, :2]).max()) * 1000, 1),
                    "lech_cao_ban_ma_mm": round(float(np.abs(resid[:, 2]).max()) * 1000, 1),
                    "bu_long_trung_bo": n_dup, "cap_bu_long_khop": n_pairs},
           "z_range_m": [round(min(zs), 3), round(max(zs), 3)],
           "doan_duoi": lo["report"]["build"], "doan_tren": up["report"]["build"]}
    nm = lambda t: t.split(":")[1].split("(")[0].strip() if t.startswith("Cột") else t.split()[2]
    title = "Cột N122: %s + %s (ghép)" % (nm(lo["title"]), nm(up["title"]))
    out = {"title": title, "members": members, "sections": secs, "nodes": [], "plates": plates, "bolts": bolts,
           "report": {"total_mass_kg": round(sum(m.get("mass_kg", 0) for m in members), 1),
                      "orientation": lo["report"]["orientation"], "build": rep}}
    json.dump(out, open(out_path, "w"), ensure_ascii=False)
    print(json.dumps(rep["ghep"], ensure_ascii=False), "z:", rep["z_range_m"])


def leg_side_z(sc, key):
    zs = [(m["p1"][2] + m["p2"][2]) / 2 for m in sc["members"] if m["rule"] == "leg" and key in m.get("side", "")]
    return float(np.median(zs)) if zs else None


# Thanh của đoạn dưới nằm trên mối nối nhưng người dùng chốt giữ theo đoạn dưới (đã thống kê khối lượng ở đó):
# DN-02: thanh xiên L80x6 (214) và thanh ngang L70x6 (234) phía trên mối nối A-A
KEEP_LO_ABOVE = {"L80X6": "214", "L70X6": "234"}


def replace_above(lo_path, up_path, out_path):
    """Đoạn trên vẽ lặp phần đỉnh đoạn dưới (DN-01 vẽ lại DN-02 từ L90x7 1570 tới L70x6 1710). Người dùng chốt: lấy
    đoạn trên thay phần trùng phía trên mối nối A-A của đoạn dưới, trừ các thanh KEEP_LO_ABOVE.
    Cao độ ráp: tâm thép góc nối trong A-A (2 đoạn cùng vẽ), tinh chỉnh theo bu lông chung (cùng lỗ, cùng trục)."""
    lo, up = json.load(open(lo_path)), json.load(open(up_path))
    z_lo = leg_side_z(lo, "thép góc nối trong A-A (229)")
    z_up = leg_side_z(up, "thép góc nối trong A-A (229, DN-02)")
    if z_lo is None or z_up is None:
        raise SystemExit("không thấy thép góc nối trong A-A ở 2 đoạn")
    dz = z_lo - z_up
    pairs = []
    for b in up["bolts"]:
        q = np.array(b["p"]) + np.array([0, 0, dz])
        for o in lo["bolts"]:
            dv = np.array(o["p"]) - q
            if np.linalg.norm(dv[:2]) < 0.015 and abs(dv[2]) < 0.03 and abs(np.dot(o["axis"], b["axis"])) > 0.99:
                pairs.append(dv)
    pairs = np.array(pairs)
    if len(pairs) >= 3:
        dz += float(np.median(pairs[:, 2]))
    zc = z_lo + 0.02                      # trên mặt cắt này lấy theo đoạn trên
    shift = np.array([0, 0, dz])
    sh = lambda v: (np.array(v) + shift).round(5).tolist()
    zmid = lambda m: (m["p1"][2] + m["p2"][2]) / 2
    members, kept_lo = [], []
    for m in lo["members"]:
        above_ = max(m["p1"][2], m["p2"][2]) > zc
        if zmid(m) <= zc and not (above_ and m["rule"] == "face" and m["section"] in KEEP_LO_ABOVE):
            members.append(m)
        elif m["rule"] == "face" and m["section"] in KEEP_LO_ABOVE:
            m = dict(m, mark=KEEP_LO_ABOVE[m["section"]], note_segment="lấy theo đoạn dưới (đã thống kê ở đó)")
            members.append(m)
            kept_lo.append(m)
    nid = max(m["id"] for m in members)
    n_dup = 0
    for m in up["members"]:
        if m.get("ext"):
            continue
        m = dict(m)
        for k in ("p1", "p2"):
            m[k] = sh(m[k])
        if zmid(m) <= zc:
            continue
        P = np.array([m["p1"], m["p2"]])
        # trùng thanh giữ theo đoạn dưới: cùng tiết diện, cùng mặt; p1/p2 là đường tim (đường tim 2 tờ cách lưng khác
        # nhau: DN-02 80, DN-01 50 -> lệch 30 mm theo pháp tuyến mặt) -> sai khác <= 45 mm
        if any(o["section"] == m["section"] and o.get("face_k") == m.get("face_k") and
               min(np.abs(P - np.array([o["p1"], o["p2"]])).max(),
                   np.abs(P[::-1] - np.array([o["p1"], o["p2"]])).max()) < 0.045
               for o in kept_lo):
            n_dup += 1
            continue
        nid += 1
        m["id"] = nid
        m["segment"] = "tren"
        members.append(m)
    pc = lambda p: np.array(p["origin"]) + np.array(p["a1"]) * np.mean([q[0] for q in p["poly"]]) + \
        np.array(p["a2"]) * np.mean([q[1] for q in p["poly"]])
    plates = [p for p in lo["plates"] if pc(p)[2] <= zc]
    up_pl = []
    for p in up["plates"]:
        if p.get("ext"):
            continue
        p = dict(p)
        for k in ("origin", "node"):
            p[k] = sh(p[k])
        if pc(p)[2] > zc:
            up_pl.append(p)
    plates += up_pl
    # bản mã đoạn dưới phía trên mặt cắt mà đoạn trên không vẽ (DN-01 vẽ nét đứt bản 219/220 của DN-02 ở cao độ
    # L70x6 1710 -> không đọc): giữ bản của đoạn dưới (góp ý: thiếu bản mã cả 4 mặt)
    n_keep = 0
    for p in lo["plates"]:
        if pc(p)[2] <= zc or p.get("kind") == "filler":
            continue
        if not any(q.get("kind") != "filler" and np.linalg.norm(pc(q) - pc(p)) < 0.12 and
                   abs(np.dot(q["thick_dir"], p["thick_dir"])) > 0.9 for q in up_pl):
            plates.append(p)
            n_keep += 1
    bolts = [b for b in lo["bolts"] if b["p"][2] <= zc]
    kept = [p for p in plates if p in lo["plates"] and pc(p)[2] > zc]

    def on_plate(b, p):
        o, a1, a2 = (np.array(p[k]) for k in ("origin", "a1", "a2"))
        q = np.array(b["p"]) - o
        u, v = q @ a1, q @ a2
        P = np.array(p["poly"])
        return abs(np.dot(b["axis"], p["thick_dir"])) > 0.9 and P[:, 0].min() - 0.01 <= u <= P[:, 0].max() + 0.01 \
            and P[:, 1].min() - 0.01 <= v <= P[:, 1].max() + 0.01 and abs(q @ np.array(p["thick_dir"])) < 0.08
    lo_kb = [b for b in lo["bolts"] if b["p"][2] > zc and any(on_plate(b, p) for p in kept)]
    for b in up["bolts"]:
        b = dict(b)
        b["p"] = sh(b["p"])
        if b["p"][2] > zc:
            # cùng lỗ với bu lông đoạn dưới ở bản mã giữ lại: dùng bu lông đoạn dưới (lớp kẹp có bản mã)
            if any(np.linalg.norm(np.cross(np.array(o["p"]) - np.array(b["p"]), o["axis"])) < 0.015 and
                   abs(np.dot(o["axis"], b["axis"])) > 0.99 for o in lo_kb):
                continue
            bolts.append(b)
    bolts += lo_kb
    secs = dict(lo["sections"])
    secs.update(up["sections"])
    # thanh đoạn trên áp mặt ngoài thanh cánh ở chỗ có bản mã giữ lại của đoạn dưới (đoạn trên không vẽ bản mã đó):
    # đẩy đầu thanh ra ngoài đúng chiều dày bản mã; bu lông qua bản mã cộng thêm lớp kẹp
    import check_dt02 as CK
    n_push = 0
    up_ids = {m["id"] for m in members if m.get("segment") == "tren"}
    for p in kept:
        pts = CK.plate_points(p)
        td = np.array(p["thick_dir"]) * p["t_mm"] / 1000
        for m in members:
            if m["id"] not in up_ids or m["rule"] != "face":
                continue
            if CK.seg_dist(*CK.frame(m)[:2], pc(p), pc(p) + 1e-6) > 0.6:
                continue
            if not np.any(CK.where_v(m, secs, pts, 0.001) > 0):
                continue
            k = 1 if np.linalg.norm(np.array(m["p1"]) - pc(p)) < np.linalg.norm(np.array(m["p2"]) - pc(p)) else 2
            old_ = m.get("poff%d" % k, [0, 0, 0])
            m["poff%d" % k] = (np.array(old_) + td).round(6).tolist()
            if np.any(CK.where_v(m, secs, pts, 0.001) > 0):
                m["poff%d" % k] = old_
            else:
                n_push += 1
        for b in bolts:
            if b in lo_kb or not on_plate(b, p):
                continue
            b["grip_mm"] = round(b.get("grip_mm", 0) + p["t_mm"], 1)
            need = b["grip_mm"] + 0.8 * b["d_mm"] + 7
            if b.get("L_mm", 0) < need:
                b["L_mm"] = int(math.ceil(need / 10) * 10)
    zs = [c for m in members for c in (m["p1"][2], m["p2"][2])]
    rep = {"ghep": {"doan_duoi": lo["title"], "doan_tren": up["title"], "cao_do_rap_m": round(dz, 4),
                    "cat_tai_z_m": round(zc, 4), "day_dau_thanh_qua_ban_ma_giu": n_push, "cap_bu_long_khop": len(pairs),
                    "lech_bu_long_chung_mm": round(float(np.abs(pairs).max()) * 1000, 1) if len(pairs) else None,
                    "giu_doan_duoi": {v: sum(1 for m in kept_lo if m["mark"] == v) for v in KEEP_LO_ABOVE.values()},
                    "bo_trung_doan_tren": n_dup, "giu_ban_ma_doan_duoi": n_keep},
           "z_range_m": [round(min(zs), 3), round(max(zs), 3)],
           "doan_duoi": lo["report"]["build"], "doan_tren": up["report"]["build"]}
    nm = lambda t: t.split(":")[1].split("(")[0].strip() if t.startswith("Cột") else t.split()[2]
    title = "Cột N122: %s + %s (ghép)" % (nm(lo["title"]), nm(up["title"]))
    out = {"title": title, "members": members, "sections": secs, "nodes": [], "plates": plates, "bolts": bolts,
           "report": {"total_mass_kg": round(sum(m.get("mass_kg", 0) for m in members), 1),
                      "orientation": lo["report"]["orientation"], "build": rep}}
    json.dump(out, open(out_path, "w"), ensure_ascii=False)
    print(json.dumps(rep["ghep"], ensure_ascii=False), "z:", rep["z_range_m"])


if __name__ == "__main__":
    if len(sys.argv) > 4 and sys.argv[4] == "--replace-above":
        replace_above(*sys.argv[1:4])
    else:
        main(*sys.argv[1:5])
