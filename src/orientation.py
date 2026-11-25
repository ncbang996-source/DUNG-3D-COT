"""Giai đoạn 5: hệ trục địa phương, hướng cánh, dịch tim theo đường đinh.

Quy ước tiết diện (xem section_library.profile): góc lưng (heel) ở gốc (s1, s2) = (0, 0),
cánh 1 dọc s1 (dày theo s2), cánh 2 dọc s2 (dày theo s1).
Điểm thế giới:  P = p + (s1 - g1)·e1 + (s2 - g2)·e2 + x·u,  với (g1, g2) là vị trí đường tim DXF
trong tọa độ tiết diện (mm -> m).

Quy tắc (người dùng đã duyệt):
- Thanh cánh C, CĐ: lưng quay ra ngoài góc thân cột, hai cánh nằm trên hai mặt kề nhau,
  ôm vào trong. Đường tim = giao 2 đường đinh: (g1, g2) = (b/2, b/2).
- Thanh nằm trên mặt ngoài thân cột: cánh liên kết nằm trong mặt phẳng mặt cột, lưng áp mặt
  phẳng, đường đinh ở giữa cánh: (g1, g2) = (b/2, 0). Cánh còn lại hướng VÀO trong.
  Nếu bị cấn thép (ngoài vùng nút) thì thử đổi phía góc lưng trong mặt phẳng, rồi lật RA ngoài.
- Thanh không nằm trên mặt ngoài (vách ngang, xà): cánh liên kết nằm ngang (mặt phẳng chứa
  trục thanh và phương ngang vuông góc), lưng ở trên, cánh còn lại chĩa XUỐNG. Bị cấn thì
  thử đổi phía góc lưng, rồi lật lên.
- File orientation_override.csv (cột: id,variant) ghi đè phương án của từng thanh.
  variant: "in+", "in-", "out+", "out-"  (in = cánh chĩa vào trong/xuống, +/- = phía góc lưng).

Chạy:  python3 src/orientation.py out/ [data/orientation_override.csv]
Đầu ra: out/scene.json, out/orientation_report.json
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

FACE_TOL = 2e-3            # m, sai số điểm nằm trên mặt cột
NODE_EXCL = 1.0            # vùng loại trừ quanh nút chung = NODE_EXCL*max(b) + NODE_EXCL_ADD
NODE_EXCL_ADD = 0.03       # m
SAMPLE_STEP = 0.02         # m, bước lấy mẫu dọc thanh khi kiểm tra cấn
CLASH_EPS = 0.5e-3         # m, điểm phải vào sâu hơn mức này mới tính là cấn
VARIANTS = ["in+", "in-", "out+", "out-"]
LEG_TYPES = {"C", "CĐ"}


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


# ---------------------------------------------------------------- thân cột
class Body:
    """Thân cột vuông đối xứng quanh trục z, nửa bề rộng h(z) tuyến tính từng đoạn theo thanh cánh."""

    def __init__(self, members):
        pts = {}
        for m in members:
            if m["type"] in LEG_TYPES:
                for p in (m["p1"], m["p2"]):
                    pts[round(p[2], 4)] = abs(p[0])
        self.z = np.array(sorted(pts))
        self.h = np.array([pts[z] for z in self.z])

    def half(self, z):
        return float(np.interp(z, self.z, self.h))

    def slope(self, z0, z1):
        return (self.half(z1) - self.half(z0)) / (z1 - z0) if abs(z1 - z0) > 1e-9 else \
            float(np.gradient(self.h, self.z)[np.searchsorted(self.z, z0).clip(0, len(self.z) - 1)])

    def faces_of(self, p):
        """Các mặt (+x, -x, +y, -y) chứa điểm p."""
        x, y, z = p
        if z < self.z[0] - FACE_TOL or z > self.z[-1] + FACE_TOL:
            return set()
        h = self.half(z)
        f = set()
        if abs(x - h) < FACE_TOL and abs(y) <= h + FACE_TOL: f.add("+x")
        if abs(x + h) < FACE_TOL and abs(y) <= h + FACE_TOL: f.add("-x")
        if abs(y - h) < FACE_TOL and abs(x) <= h + FACE_TOL: f.add("+y")
        if abs(y + h) < FACE_TOL and abs(x) <= h + FACE_TOL: f.add("-y")
        return f

    def normal(self, face, z0, z1):
        """Pháp tuyến hướng ra ngoài của mặt cột trong đoạn z0..z1."""
        za, zb = sorted((z0, z1))
        if zb - za < 1e-6:
            za, zb = za - 0.05, zb + 0.05
        s = (self.half(zb) - self.half(za)) / (zb - za)
        ax = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[face]
        return unit([ax[0], ax[1], -s])


# ---------------------------------------------------------------- khung địa phương
def frame_leg(m, body):
    p1, p2 = np.array(m["p1"]), np.array(m["p2"])
    u = unit(p2 - p1)
    mid = (p1 + p2) / 2
    sx, sy = np.sign(mid[0]), np.sign(mid[1])
    fx, fy = ("+x" if sx > 0 else "-x"), ("+y" if sy > 0 else "-y")
    nA = body.normal(fx, p1[2], p2[2])
    nB = body.normal(fy, p1[2], p2[2])
    dA = unit(np.cross(u, nA))                 # nằm trong mặt A, vuông góc trục
    if dA[1] * sy > 0: dA = -dA                # hướng vào trong (về phía -sy)
    e1 = dA
    dB = unit(np.cross(u, nB))
    if dB[0] * sx > 0: dB = -dB
    e2 = unit(dB - np.dot(dB, e1) * e1 - np.dot(dB, u) * u)
    return u, e1, e2, {"rule": "leg", "faces": [fx, fy]}


def frames_member(m, body):
    """Trả về (u, rule_info, dict variant -> (e1, e2)) cho thanh không phải cánh cột."""
    p1, p2 = np.array(m["p1"]), np.array(m["p2"])
    u = unit(p2 - p1)
    common = body.faces_of(p1) & body.faces_of(p2)
    if len(common) == 1:
        face = next(iter(common))
        n = body.normal(face, p1[2], p2[2])
        n = unit(n - np.dot(n, u) * u)          # khử sai số làm tròn 4 số lẻ của DXF
        w = unit(np.cross(n, u))
        if w[2] < -1e-9 or (abs(w[2]) <= 1e-9 and np.dot(w, [1, 1, 0]) < 0):
            w = -w                              # +w: hướng lên (hoặc +x/+y khi thanh đứng)
        inward = -n
        info = {"rule": "face", "face": face}
    else:
        h = np.cross([0, 0, 1], u)
        mid = (p1 + p2) / 2
        if np.linalg.norm(h) < 1e-6:
            # Thanh đứng ngoài mặt thân (thanh đứng của xà): cánh liên kết nằm trong mặt đứng
            # song song trục X, cánh còn lại chĩa về phía trục giữa xà (y = 0).
            h = np.array([1.0, 0, 0])
            n = np.array([0, 1.0 if mid[1] >= 0 else -1.0, 0])
            n = unit(n - np.dot(n, u) * u)
            w = h if np.dot(h, [mid[0], mid[1], 0]) >= 0 else -h
            out = {}
            for v in VARIANTS:
                out[v] = ((-w if v.endswith("+") else w), (-n if v.startswith("in") else n))
            return u, {"rule": "plan", "faces": sorted(common), "vertical": True}, out
        h = unit(h)
        n = unit(np.cross(u, h))
        if n[2] < 0: n = -n                     # n hướng lên
        radial = np.array([mid[0], mid[1], 0.0])
        w = h if np.dot(h, radial) >= 0 else -h  # +w: hướng ra xa trục cột
        inward = -n                              # "in" = chĩa xuống
        info = {"rule": "plan", "faces": sorted(common)}
    out = {}
    for v in VARIANTS:
        e2 = inward if v.startswith("in") else -inward
        # "+": góc lưng về phía +w  => cánh liên kết chạy từ lưng theo -w
        e1 = -w if v.endswith("+") else w
        out[v] = (e1, e2)
    return u, info, out


# ---------------------------------------------------------------- hình khối để kiểm tra cấn
class Solid:
    """Thép góc = 2 hộp. Dùng để lấy mẫu điểm và kiểm tra điểm nằm trong."""

    def __init__(self, p1, p2, u, e1, e2, g, b, t):
        self.p1, self.p2 = np.asarray(p1, float), np.asarray(p2, float)
        self.L = np.linalg.norm(self.p2 - self.p1)
        self.u, self.e1, self.e2 = u, e1, e2
        self.g, self.b, self.t = g, b, t
        self.R = np.stack([u, e1, e2])           # hàng = trục
        self.boxes = [((0, b), (0, t)), ((0, t), (0, b))]   # (s1 range, s2 range), m
        c = [self.world(x, s1, s2) for x in (0, self.L) for s1 in (0, b) for s2 in (0, b)]
        self.lo, self.hi = np.min(c, 0), np.max(c, 0)

    def world(self, x, s1, s2):
        return self.p1 + x * self.u + (s1 - self.g[0]) * self.e1 + (s2 - self.g[1]) * self.e2

    def local(self, P):
        d = P - self.p1
        return np.stack([d @ self.u, d @ self.e1 + self.g[0], d @ self.e2 + self.g[1]], axis=-1)

    def contains(self, P, eps=CLASH_EPS):
        q = self.local(P)
        x, s1, s2 = q[:, 0], q[:, 1], q[:, 2]
        inx = (x > eps) & (x < self.L - eps)
        r = np.zeros(len(P), bool)
        for (a0, a1), (b0, b1) in self.boxes:
            r |= inx & (s1 > a0 + eps) & (s1 < a1 - eps) & (s2 > b0 + eps) & (s2 < b1 - eps)
        return r

    def samples(self):
        n = max(2, int(self.L / SAMPLE_STEP) + 1)
        xs = np.linspace(0, self.L, n)
        b, t = self.b, self.t
        cross = [(s1, s2) for s1 in np.linspace(0, b, 6) for s2 in (0, t)] + \
                [(s1, s2) for s2 in np.linspace(t, b, 5) for s1 in (0, t)]
        pts = np.array([self.world(x, s1, s2) for x in xs for s1, s2 in cross])
        return pts

    def overlaps_bbox(self, o, pad=0.0):
        return np.all(self.lo - pad <= o.hi) and np.all(o.lo - pad <= self.hi)


def clash(a: Solid, b: Solid, shared_nodes, excl):
    """True nếu a và b giao nhau ngoài vùng nút chung."""
    if not a.overlaps_bbox(b):
        return False
    for s, o in ((a, b), (b, a)):
        P = s.samples()
        if shared_nodes:
            d = np.min([np.linalg.norm(P - np.asarray(n), axis=1) for n in shared_nodes], axis=0)
            P = P[d > excl]
        if len(P) and o.contains(P).any():
            return True
    return False


# ---------------------------------------------------------------- chạy
def read_overrides(path):
    ov = {}
    if path and Path(path).exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                v = row["variant"].strip()
                if v not in VARIANTS:
                    raise ValueError(f"orientation_override: thanh {row['id']} variant '{v}' không hợp lệ")
                ov[int(row["id"])] = v
    return ov


def solve(model, lib, overrides=None, check_clash=True):
    overrides = overrides or {}
    body = Body(model)
    placed: dict[int, Solid] = {}
    result = {}
    log = {"flipped_out": [], "heel_swapped": [], "unresolved": [], "overridden": []}

    def key_nodes(m):
        return {tuple(m["p1"]), tuple(m["p2"])}

    sec = lambda m: lib[m["section"]]
    legs = [m for m in model if m["type"] in LEG_TYPES]
    others = sorted((m for m in model if m["type"] not in LEG_TYPES),
                    key=lambda m: (-sec(m)["b"], -sec(m)["t"], m["id"]))

    for m in legs:
        s = sec(m)
        b, t = s["b"] / 1000, s["t"] / 1000
        u, e1, e2, info = frame_leg(m, body)
        g = (b / 2, b / 2)
        placed[m["id"]] = Solid(m["p1"], m["p2"], u, e1, e2, g, b, t)
        result[m["id"]] = {"u": u, "e1": e1, "e2": e2, "g": g, "variant": "leg", **info}

    # chỉ số không gian thô để giới hạn cặp kiểm tra
    def neighbours(sol):
        return [(i, o) for i, o in placed.items() if sol.overlaps_bbox(o)]

    # Chọn phương án theo NHÓM (nhóm = các thanh đối xứng) để giữ đối xứng 4 mặt.
    groups: dict[int, list[dict]] = {}
    for m in others:
        groups.setdefault(m["group"], []).append(m)
    gorder = sorted(groups, key=lambda g: (-sec(groups[g][0])["b"], -sec(groups[g][0])["t"], g))

    def build_solid(m, fr, v):
        s = sec(m)
        b, t = s["b"] / 1000, s["t"] / 1000
        e1, e2 = fr[v]
        return Solid(m["p1"], m["p2"], fr["_u"], e1, e2, (b / 2, 0.0), b, t)

    def hits_of(m, sol, pool):
        hits = []
        for i, o in pool.items():
            if i == m["id"] or not sol.overlaps_bbox(o):
                continue
            om = by_id[i]
            shared = [np.array(p) for p in key_nodes(m) & key_nodes(om)]
            excl = NODE_EXCL * max(sol.b, o.b) + NODE_EXCL_ADD
            if clash(sol, o, shared, excl):
                hits.append(i)
        return hits

    for gid in gorder:
        mems = groups[gid]
        frs, infos = {}, {}
        for m in mems:
            u, info, fr = frames_member(m, body)
            fr["_u"] = u
            frs[m["id"]], infos[m["id"]] = fr, info
        chosen_v: dict[int, str] = {m["id"]: overrides[m["id"]] for m in mems if m["id"] in overrides}
        free = [m for m in mems if m["id"] not in chosen_v]
        tries = []
        if free:
            best = None
            for v in (VARIANTS if check_clash else VARIANTS[:1]):
                sols = {m["id"]: build_solid(m, frs[m["id"]], v) for m in free}
                if not check_clash:
                    best = (0, v, {})
                    break
                pool = dict(placed)
                pool.update({i: build_solid(by_id[i], frs[i], chosen_v[i]) for i in chosen_v})
                pool.update(sols)
                hits = {m["id"]: hits_of(m, sols[m["id"]], pool) for m in free}
                n_bad = sum(1 for h in hits.values() if h)
                tries.append({"variant": v, "clash": {k: h for k, h in hits.items() if h}})
                if best is None or n_bad < best[0]:
                    best = (n_bad, v, hits)
                if n_bad == 0:
                    break
            n_bad, v, hits = best
            for m in free:
                chosen_v[m["id"]] = v
            entry = {"group": gid, "members": [m["id"] for m in free], "variant": v, "tries": tries}
            if n_bad:
                log["unresolved"].append({**entry, "still_clash": {k: h for k, h in hits.items() if h}})
            if v.startswith("out"):
                log["flipped_out"].append(entry)
            elif v != "in+":
                log["heel_swapped"].append(entry)
        for m in mems:
            v = chosen_v[m["id"]]
            if m["id"] in overrides:
                log["overridden"].append(m["id"])
            placed[m["id"]] = build_solid(m, frs[m["id"]], v)
            e1, e2 = frs[m["id"]][v]
            result[m["id"]] = {"u": frs[m["id"]]["_u"], "e1": e1, "e2": e2, "g": (sec(m)["b"] / 2000, 0.0),
                               "variant": v, "frames": {k: frs[m["id"]][k] for k in VARIANTS}, **infos[m["id"]]}
    return result, log


by_id: dict[int, dict] = {}


def main(out: Path, override_path=None):
    global by_id
    model = json.loads((out / "model.json").read_text())
    lib = json.loads((out / "section_library.json").read_text())
    by_id = {m["id"]: m for m in model}
    ov = read_overrides(override_path)
    res, log = solve(model, lib, ov)
    scene = []
    for m in model:
        r = res[m["id"]]
        scene.append({**m,
                      "e1": [round(float(v), 6) for v in r["e1"]],
                      "e2": [round(float(v), 6) for v in r["e2"]],
                      "g": [round(r["g"][0] * 1000, 3), round(r["g"][1] * 1000, 3)],   # mm
                      "variant": r["variant"], "auto_variant": r["variant"], "rule": r["rule"],
                      "frames": {k: [[round(float(x), 6) for x in e] for e in fe]
                                 for k, fe in r.get("frames", {}).items()},
                      "face": r.get("face") or ",".join(r.get("faces", []))})
    rules = {}
    for s in scene:
        rules[s["rule"]] = rules.get(s["rule"], 0) + 1
    rep = {"n": len(scene), "rules": rules,
           "variants": {v: sum(1 for s in scene if s["variant"] == v) for v in VARIANTS + ["leg"]},
           **log}
    (out / "scene.json").write_text(json.dumps({"members": scene, "sections": lib}, ensure_ascii=False))
    (out / "orientation_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print("=== HƯỚNG CÁNH ===")
    print(f"Số thanh            : {rep['n']}")
    print(f"Theo quy tắc        : {rules}  (leg = thanh cánh, face = trên mặt cột, plan = vách ngang/xà)")
    print(f"Phương án           : {rep['variants']}")
    fmt = lambda L: "; ".join(f"Gr{x['group']}({x['variant']}): {x['members']}" for x in L) or "không"
    print(f"Đổi phía góc lưng   : {fmt(log['heel_swapped'])}")
    print(f"Lật ra ngoài / lên  : {fmt(log['flipped_out'])}")
    print(f"Ghi đè từ CSV       : {log['overridden'] or 'không'}")
    print("Vẫn cấn mọi phương án:")
    for x in log["unresolved"] or []:
        print(f"   Gr{x['group']} chọn {x['variant']}: " + ", ".join(f"{k} cấn {v}" for k, v in x["still_clash"].items()))
    if not log["unresolved"]:
        print("   không")
    return scene, rep


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    ovp = sys.argv[2] if len(sys.argv) > 2 else "data/orientation_override.csv"
    main(out, ovp)
