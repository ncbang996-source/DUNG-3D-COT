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


def main(lo_path, up_path, out_path):
    lo, up = json.load(open(lo_path)), json.load(open(up_path))
    lo_sheet = lo["title"].split()[2]
    ext = [p for p in up["plates"] if p.get("ext") == lo_sheet]
    spl = [p for p in lo["plates"] if "mối nối với đoạn trên" in p.get("reason", "")]
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
    resid = d - np.array([0, 0, dz])
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
    for b in up["bolts"]:
        b = dict(b)
        b["p"] = sh(b["p"])
        bolts.append(b)
    secs = dict(lo["sections"])
    secs.update(up["sections"])
    zs = [c for m in members for c in (m["p1"][2], m["p2"][2])]
    rep = {"ghep": {"doan_duoi": lo["title"], "doan_tren": up["title"], "cao_do_rap_m": round(dz, 4),
                    "lech_ngang_ban_ma_mm": round(float(np.abs(resid[:, :2]).max()) * 1000, 1),
                    "lech_cao_ban_ma_mm": round(float(np.abs(resid[:, 2]).max()) * 1000, 1)},
           "z_range_m": [round(min(zs), 3), round(max(zs), 3)],
           "doan_duoi": lo["report"]["build"], "doan_tren": up["report"]["build"]}
    title = "Cột N122: %s + %s (ghép)" % (lo["title"].split()[2], up["title"].split()[2])
    out = {"title": title, "members": members, "sections": secs, "nodes": [], "plates": plates, "bolts": bolts,
           "report": {"total_mass_kg": round(sum(m.get("mass_kg", 0) for m in members), 1),
                      "orientation": lo["report"]["orientation"], "build": rep}}
    json.dump(out, open(out_path, "w"), ensure_ascii=False)
    print(json.dumps(rep["ghep"], ensure_ascii=False), "z:", rep["z_range_m"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
