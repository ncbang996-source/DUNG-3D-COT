"""Ghép 2 lần dựng của một đoạn có 2 kiểu mặt (VD DN-02: mặt có xà / mặt bên) thành 1 mô hình.

Chạy: python3 tools/bvtc/combine_faces.py <scene A> <scene B> <scene ra>

Mỗi lần dựng xoay 1 mặt đứng ra 4 mặt (face_k = 0..3). Lấy từ A các mặt trong cấu hình "faces" của A (VD 0, 2),
từ B các mặt của B (1, 3). Thanh cánh, thép góc nối, mặt cắt vách (không thuộc riêng mặt nào) lấy từ A.
"""
import json
import sys


def main(a_path, b_path, out_path):
    A, B = json.load(open(a_path)), json.load(open(b_path))
    fa = set(A["report"]["build"].get("faces") or [0, 2])
    fb = set(B["report"]["build"].get("faces") or [1, 3])

    def pick(items, faces, shared):
        out = []
        for it in items:
            fk = it.get("face_k")
            if it.get("rule") in ("leg", "plan") or fk is None:
                if shared:
                    out.append(it)
            elif fk in faces:
                out.append(it)
        return out
    members = pick(A["members"], fa, True) + pick(B["members"], fb, False)
    for i, m in enumerate(members, 1):
        m["id"] = i
    plates = pick(A["plates"], fa, True) + pick(B["plates"], fb, False)
    bolts = pick(A["bolts"], fa, True) + pick(B["bolts"], fb, False)
    secs = dict(A["sections"])
    secs.update(B["sections"])
    for k, v in A["sections"].items():
        secs[k] = v
    rep = {"mat_A": A["report"]["build"], "mat_B": B["report"]["build"], "faces_A": sorted(fa), "faces_B": sorted(fb),
           "z_range_m": A["report"]["build"].get("z_range_m")}
    title = A["title"].replace("Đoạn thân", "Đoạn ngọn")
    out = {"title": title, "members": members, "sections": secs, "nodes": [], "plates": plates, "bolts": bolts,
           "report": {"total_mass_kg": round(sum(m.get("mass_kg", 0) for m in members if not m.get("ext")), 1),
                      "orientation": A["report"]["orientation"], "build": rep}}
    json.dump(out, open(out_path, "w"), ensure_ascii=False)
    print("thanh", len(members), "bản mã/tấm", len(plates), "bu lông", len(bolts))


if __name__ == "__main__":
    main(*sys.argv[1:4])
