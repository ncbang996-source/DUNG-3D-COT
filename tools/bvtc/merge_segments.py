"""Ghép 2 đoạn đã dựng thành 1 mô hình: đoạn trên (vd DT-01) đặt lên đoạn dưới (vd DT-02).

Chạy: python3 tools/bvtc/merge_segments.py <scene đoạn dưới> <scene đoạn trên> <scene ra>

Đoạn trên dựng với cấu hình "on_top_of" có bản mã nối + thép góc nối trong của đoạn dưới (đánh dấu "ext") đặt
theo lỗ bu lông. Cao độ ráp = độ chênh tâm bản mã nối "ext" (đoạn trên) với bản mã nối cùng vị trí của đoạn dưới.
Phần "ext" của đoạn trên bỏ (đoạn dưới đã có); bu lông mối nối của đoạn trên giữ (đoạn dưới không có bu lông ở lỗ
chờ phía trên).
"""
import json
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
        if len(P_lo) and np.min(np.linalg.norm(P_lo - np.array(b["p"]), axis=1)) < 0.02 and \
                any(np.linalg.norm(np.array(o["p"]) - np.array(b["p"])) < 0.02 and
                    abs(np.dot(o["axis"], b["axis"])) > 0.99 for o in lo["bolts"]):
            n_dup += 1
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
    for p in up["plates"]:
        if p.get("ext"):
            continue
        p = dict(p)
        for k in ("origin", "node"):
            p[k] = sh(p[k])
        if pc(p)[2] > zc:
            plates.append(p)
    bolts = [b for b in lo["bolts"] if b["p"][2] <= zc]
    for b in up["bolts"]:
        b = dict(b)
        b["p"] = sh(b["p"])
        if b["p"][2] > zc:
            bolts.append(b)
    secs = dict(lo["sections"])
    secs.update(up["sections"])
    zs = [c for m in members for c in (m["p1"][2], m["p2"][2])]
    rep = {"ghep": {"doan_duoi": lo["title"], "doan_tren": up["title"], "cao_do_rap_m": round(dz, 4),
                    "cat_tai_z_m": round(zc, 4), "cap_bu_long_khop": len(pairs),
                    "lech_bu_long_chung_mm": round(float(np.abs(pairs).max()) * 1000, 1) if len(pairs) else None,
                    "giu_doan_duoi": {v: sum(1 for m in kept_lo if m["mark"] == v) for v in KEEP_LO_ABOVE.values()},
                    "bo_trung_doan_tren": n_dup},
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
