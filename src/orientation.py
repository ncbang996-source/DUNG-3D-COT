"""Giai đoạn 5: hệ trục địa phương, hướng cánh, dịch tim theo đường đinh.

Quy ước tiết diện (xem section_library.profile): góc lưng (heel) ở gốc (s1, s2) = (0, 0),
cánh 1 dọc s1 (dày theo s2), cánh 2 dọc s2 (dày theo s1).
Điểm thế giới:  P = p + (s1 - g1)·e1 + (s2 - g2)·e2 + x·u,  với (g1, g2) là vị trí đường tim DXF
trong tọa độ tiết diện (mm -> m).

Quy tắc (người dùng đã duyệt):
- Thanh cánh C, CĐ: lưng quay ra ngoài góc thân cột, hai cánh nằm trên hai mặt kề nhau,
  ôm vào trong. Đường tim = giao 2 đường đinh: (g1, g2) = (b/2, b/2).
- Thanh nằm trên mặt ngoài thân cột: cánh liên kết song song mặt cột, đường đinh ở giữa cánh:
  (g1, g2) = (b/2, 0) trên mặt lưng. Lưng ÉP SÁT cánh thanh cánh (người dùng chốt):
    * Cặp thanh xiên chéo nhau chữ X: nhìn từ ngoài vào mặt cột, thanh đi lên về bên PHẢI nằm
      NGOÀI (lưng áp mặt ngoài cánh thanh cánh, cánh chĩa ra ngoài); thanh kia nằm TRONG (lưng áp
      mặt trong cánh thanh cánh, cánh chĩa vào trong). Hai thanh hở nhau đúng bằng chiều dày
      cánh thanh cánh.
    * Mọi thanh khác trên mặt cột: nằm TRONG.
  Mặt cột (DXF) đi qua đường tim thanh cánh = giao 2 đường đinh, nên mặt ngoài cánh thanh cánh
  cách mặt cột b_c/2, mặt trong cách b_c/2 - t_c (b_c, t_c: tiết diện thanh cánh cùng cao độ).
  Không tự lật trong/ngoài; chỉ tự đổi phía góc lưng (+/-) nếu bị cấn.
- Thanh không nằm trên mặt ngoài (vách ngang, xà): cánh liên kết nằm ngang (mặt phẳng chứa
  trục thanh và phương ngang vuông góc), cánh còn lại chĩa XUỐNG (riêng XAD: chĩa LÊN). Bị cấn
  thì thử đổi phía góc lưng, rồi lật. Nếu vẫn cấn: dời điểm bắt đầu thanh ở nút chung dọc theo
  thanh bị cấn, ra xa nút một đoạn 3d (d = đường kính bu lông), làm tròn LÊN bội số 5 mm.
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


def ceil5(mm: float) -> float:
    return float(np.ceil(mm / 5.0 - 1e-9) * 5.0)


def leg_section_at(model, lib, z):
    """Tiết diện thanh cánh (b, t theo m) tại cao độ z (các thanh cánh đối xứng nên lấy 1 góc)."""
    best = None
    for m in model:
        if m["type"] not in LEG_TYPES or m["p1"][0] <= 0 or m["p1"][1] <= 0:
            continue
        z0, z1 = sorted((m["p1"][2], m["p2"][2]))
        # biên giữa hai đoạn: lấy đoạn PHÍA TRÊN (z0 <= z < z1) cho nhất quán
        d = 0 if z0 - 1e-6 <= z < z1 - 1e-6 else min(abs(z - z0), abs(z - z1)) + 1e-9
        if best is None or d < best[0]:
            best = (d, lib[m["section"]])
    s = best[1]
    return s["b"] / 1000, s["t"] / 1000


def x_members(model, body):
    """Các thanh trên mặt cột thuộc cặp chéo chữ X: tại một nút không phải nút thanh cánh có
    2 cặp thanh xiên thẳng hàng cùng mặt. Trả về {id: (True nếu nằm NGOÀI, cao độ nút giao)}."""
    leg_nodes = {tuple(p) for m in model if m["type"] in LEG_TYPES for p in (m["p1"], m["p2"])}
    face_of = {}
    for m in model:
        if m["type"] in LEG_TYPES:
            continue
        c = body.faces_of(m["p1"]) & body.faces_of(m["p2"])
        if len(c) == 1:
            face_of[m["id"]] = next(iter(c))
    by_node: dict[tuple, list] = {}
    for m in model:
        if m["id"] in face_of:
            for k in ("p1", "p2"):
                by_node.setdefault(tuple(m[k]), []).append(m)
    ax = lambda m: unit(np.subtract(m["p2"], m["p1"]))
    res = {}
    for nd, ms in by_node.items():
        if nd in leg_nodes:
            continue
        diag = [m for m in ms if 1e-3 < abs(ax(m)[2]) < 1 - 1e-3]
        pairs = [(a, b) for i, a in enumerate(diag) for b in diag[i + 1:]
                 if face_of[a["id"]] == face_of[b["id"]] and abs(abs(np.dot(ax(a), ax(b))) - 1) < 1e-4]
        if len(pairs) < 2:
            continue
        for a, b in pairs:
            for m in (a, b):
                face = face_of[m["id"]]
                n = body.normal(face, m["p1"][2], m["p2"][2])
                right = np.cross(-n, [0, 0, 1])          # bên phải khi đứng ngoài nhìn vào
                u = ax(m)
                if u[2] < 0:
                    u = -u
                outside = bool(np.dot(u, right) > 0)       # đi lên về bên phải -> NGOÀI
                if m["id"] in res and abs(res[m["id"]][1] - nd[2]) > 1e-6:
                    res[m["id"]] = (outside, min(res[m["id"]][1], nd[2]))
                else:
                    res[m["id"]] = (outside, nd[2])
    return res


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
        info = {"rule": "face", "face": face, "n": n}
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
        up = m.get("type") == "XAD"              # người dùng: thanh XAD cánh hướng LÊN
        inward = n if up else -n                 # "in" = hướng mặc định (xuống; XAD: lên)
        info = {"rule": "plan", "faces": sorted(common), "default_up": up}
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
    xout = x_members(model, body)
    log["x_members"] = {"outside": sorted(i for i, o in xout.items() if o[0]),
                        "inside": sorted(i for i, o in xout.items() if not o[0])}
    # Thanh liền: các đoạn cùng tiết diện, thẳng hàng, nối qua nút (DXF chỉ chia đoạn) -> MỘT thanh,
    # dùng chung hướng (nếu có đoạn nằm NGOÀI thì cả thanh nằm ngoài) và chung chuẩn thanh cánh.
    parent = {m["id"]: m["id"] for m in others}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    ax = lambda m: unit(np.subtract(m["p2"], m["p1"]))
    nodes_of: dict[tuple, list] = {}
    for m in others:
        for k in ("p1", "p2"):
            nodes_of.setdefault(tuple(m[k]), []).append(m)
    for ms in nodes_of.values():
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                if a["section"] == b["section"] and abs(abs(np.dot(ax(a), ax(b))) - 1) < 1e-4:
                    parent[find(a["id"])] = find(b["id"])
    chains: dict[int, list] = {}
    for m in others:
        chains.setdefault(find(m["id"]), []).append(m["id"])
    chain_of = {i: c for c in chains.values() for i in c}
    chain_out = {i: any(xout.get(j, (False, 0))[0] for j in chain_of[i]) for i in chain_of}
    chain_zref = {}
    for c in chains.values():
        zx = [xout[j][1] for j in c if j in xout]
        if zx:
            for j in c:
                chain_zref[j] = min(zx)
    log["chains"] = [sorted(c) for c in chains.values() if len(c) > 1]
    leg_nodes = {round(p[2], 4): None for m in legs for p in (m["p1"], m["p2"])}
    leg_pts = {tuple(p) for m in legs for p in (m["p1"], m["p2"])}
    log["endpoint_shift"] = []

    def setup(m):
        """Khung, các phương án được phép, độ dịch tim theo phương án."""
        u, info, fr = frames_member(m, body)
        fr["_u"] = u
        fr["_p1"], fr["_p2"] = np.array(m["p1"], float), np.array(m["p2"], float)
        offs = {v: np.zeros(3) for v in VARIANTS}
        allowed = list(VARIANTS)
        if info["rule"] == "face":
            n = info["n"]
            # Tiết diện thanh cánh làm chuẩn ép sát:
            #  - cụm chữ X: thanh cánh tại cao độ nút giao (cả 4 nửa thanh cùng một chuẩn);
            #  - thanh khác: thanh cánh tại đầu thanh bắt vào thanh cánh (nếu có), không thì trung điểm.
            if m["id"] in chain_zref:
                zref = chain_zref[m["id"]]
            else:
                on_leg = [p[2] for p in (m["p1"], m["p2"]) if tuple(p) in leg_pts]
                zref = min(on_leg) if on_leg else (m["p1"][2] + m["p2"][2]) / 2
            bc, tc = leg_section_at(model, lib, zref)
            offs = {v: n * ((bc / 2 - tc) if v.startswith("in") else bc / 2) for v in VARIANTS}
            outside = chain_out.get(m["id"], False)
            side = "out" if outside else "in"
            allowed = [side + "+", side + "-"]
            info = {**info, "x_pair": m["id"] in xout, "leg_b": bc, "leg_t": tc, "leg_ref_z": zref}
        fr["_offs"] = offs
        return info, fr, allowed

    def build_solid(m, fr, v):
        s = sec(m)
        b, t = s["b"] / 1000, s["t"] / 1000
        e1, e2 = fr[v]
        o = fr["_offs"][v]
        return Solid(fr["_p1"] + o, fr["_p2"] + o, fr["_u"], e1, e2, (b / 2, 0.0), b, t)

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

    frs_all, infos_all = {}, {}
    for gid in gorder:
        mems = groups[gid]
        frs, infos, allowed = {}, {}, {}
        for m in mems:
            infos[m["id"]], frs[m["id"]], allowed[m["id"]] = setup(m)
        chosen_v: dict[int, str] = {m["id"]: overrides[m["id"]] for m in mems if m["id"] in overrides}
        free = [m for m in mems if m["id"] not in chosen_v]
        tries = []
        if free:
            # phương án dùng chung cho nhóm theo dạng (phía góc lưng); phía trong/ngoài theo từng thanh
            def var_for(m, heel, flip):
                al = allowed[m["id"]]
                if len(al) == 2:                    # thanh mặt cột: không lật trong/ngoài
                    return al[0] if heel == "+" else al[1]
                return ("out" if flip else "in") + heel
            options = [("+", False), ("-", False), ("+", True), ("-", True)]
            if all(len(allowed[m["id"]]) == 2 for m in free):
                options = options[:2]
            if not check_clash:
                options = options[:1]
            best = None
            for heel, flip in options:
                vs = {m["id"]: var_for(m, heel, flip) for m in free}
                sols = {m["id"]: build_solid(m, frs[m["id"]], vs[m["id"]]) for m in free}
                if not check_clash:
                    best = (0, vs, {})
                    break
                pool = dict(placed)
                pool.update({i: build_solid(by_id[i], frs[i], chosen_v[i]) for i in chosen_v})
                pool.update(sols)
                hits = {m["id"]: hits_of(m, sols[m["id"]], pool) for m in free}
                n_bad = sum(1 for h in hits.values() if h)
                tries.append({"heel": heel, "flip": flip, "clash": {k: h for k, h in hits.items() if h}})
                if best is None or n_bad < best[0]:
                    best = (n_bad, vs, hits)
                if n_bad == 0:
                    break
            n_bad, vs, hits = best
            chosen_v.update(vs)
            v0 = vs[free[0]["id"]]
            entry = {"group": gid, "members": [m["id"] for m in free], "variant": v0, "tries": tries}
            if n_bad:
                entry["still_clash"] = {k: h for k, h in hits.items() if h}
                log["unresolved"].append(entry)
            if infos[free[0]["id"]]["rule"] != "face" and v0.startswith("out"):
                log["flipped_out"].append(entry)
            elif v0[-1] == "-":
                log["heel_swapped"].append(entry)
        for m in mems:
            v = chosen_v[m["id"]]
            if m["id"] in overrides:
                log["overridden"].append(m["id"])
            placed[m["id"]] = build_solid(m, frs[m["id"]], v)
            frs_all[m["id"]], infos_all[m["id"]] = frs[m["id"]], infos[m["id"]]
            result[m["id"]] = {"variant": v}

    # Thanh liền: thống nhất phía góc lưng theo đoạn dẫn (đoạn thuộc cặp chữ X, không thì id nhỏ nhất)
    log["chain_unified"] = []
    for c in chains.values():
        if len(c) < 2:
            continue
        lead = min(c, key=lambda j: (j not in xout, infos_all[j]["rule"] != "face", j))
        v = result[lead]["variant"]
        for j in c:
            if j in overrides or j == lead:
                continue
            if infos_all[j]["rule"] != infos_all[lead]["rule"]:
                # đoạn nối dài ra ngoài mặt cột (vd vào xà): theo khung và độ dịch của đoạn dẫn
                for vv in VARIANTS:
                    e1, e2 = frs_all[lead][vv]
                    frs_all[j][vv] = (e1, e2)
                frs_all[j]["_offs"] = dict(frs_all[lead]["_offs"])
                infos_all[j] = {**infos_all[j], "follows": lead}
            elif result[j]["variant"] == v:
                continue
            log["chain_unified"].append({"id": j, "from": result[j]["variant"], "to": v, "lead": lead})
            result[j]["variant"] = v
            placed[j] = build_solid(by_id[j], frs_all[j], v)

    # Thanh vẫn cấn (không phải thanh mặt cột): dời điểm bắt dọc thanh bị cấn, 3d làm tròn lên 5 mm.
    if check_clash:
        for entry in log["unresolved"]:
            fixed = {}
            for mid, hit_ids in entry["still_clash"].items():
                m, fr = by_id[mid], frs_all[mid]
                if infos_all[mid]["rule"] == "face":
                    continue
                d = (m.get("bolt") or {}).get("d_mm", 16)
                dist = ceil5(3 * d)
                for cid in hit_ids:
                    c = by_id[cid]
                    shared = key_nodes(m) & key_nodes(c)
                    if not shared:
                        continue
                    nd = np.array(next(iter(shared)))
                    other = np.array(c["p2"] if tuple(c["p1"]) == tuple(nd) else c["p1"], float)
                    dvec = unit(other - nd)
                    k = "_p1" if np.allclose(fr["_p1"], nd) else "_p2"
                    backup = {kk: (fr[kk].copy() if isinstance(fr[kk], np.ndarray) else fr[kk])
                              for kk in ("_p1", "_p2", "_u", *VARIANTS)}
                    fr[k] = fr[k] + dvec * dist / 1000
                    fr["_u"] = unit(fr["_p2"] - fr["_p1"])
                    # dựng lại khung theo trục mới (thanh vách ngang)
                    mm = {**m, "p1": fr["_p1"].tolist(), "p2": fr["_p2"].tolist()}
                    _, _, fr2 = frames_member(mm, body)
                    for vv in VARIANTS:
                        fr[vv] = fr2[vv]
                    fixed[mid] = {"end": "p1" if k == "_p1" else "p2", "along": cid,
                                  "dist_mm": dist, "new": [round(x, 4) for x in fr[k]]}
                    break
                v = result[mid]["variant"]
                sol = build_solid(m, fr, v)
                placed[mid] = sol
                left = hits_of(m, sol, placed)
                if mid in fixed:
                    fixed[mid]["clash_after"] = left
                    if left:                          # không gỡ được cấn -> trả về vị trí cũ
                        fr.update(backup)
                        placed[mid] = build_solid(m, fr, v)
                        fixed[mid]["reverted"] = True
                    else:
                        entry["still_clash"].pop(mid, None)
            if fixed:
                log["endpoint_shift"].append({"group": entry["group"], "members": fixed})
        log["unresolved"] = [e for e in log["unresolved"] if e["still_clash"]]

    for mid, fr in frs_all.items():
        v = result[mid]["variant"]
        e1, e2 = fr[v]
        m = by_id[mid]
        info = {k: v2 for k, v2 in infos_all[mid].items() if k != "n"}
        result[mid] = {"u": fr["_u"], "e1": e1, "e2": e2, "g": (sec(m)["b"] / 2000, 0.0), "variant": v,
                       "frames": {k: fr[k] for k in VARIANTS},
                       "offs": {k: fr["_offs"][k] for k in VARIANTS},
                       "p1d": fr["_p1"], "p2d": fr["_p2"], **info}
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
                      "face": r.get("face") or ",".join(r.get("faces", [])),
                      "default_up": bool(r.get("default_up", False)),
                      "x_pair": bool(r.get("x_pair", False)),
                      "offs": {k: [round(float(x), 6) for x in o] for k, o in r.get("offs", {}).items()},
                      **({"p1d": [round(float(x), 5) for x in r["p1d"]], "p2d": [round(float(x), 5) for x in r["p2d"]]}
                         if "p1d" in r and (not np.allclose(r["p1d"], m["p1"]) or not np.allclose(r["p2d"], m["p2"]))
                         else {})})
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
    print(f"Lật (vách ngang/xà) : {fmt(log['flipped_out'])}")
    print(f"Cặp chữ X           : {len(log['x_members']['outside'])} thanh ngoài, {len(log['x_members']['inside'])} thanh trong")
    print(f"Thanh liền (nhiều đoạn): {len(log['chains'])}, đoạn đổi hướng cho thống nhất: {len(log['chain_unified'])}")
    print(f"Ghi đè từ CSV       : {log['overridden'] or 'không'}")
    sc = {s["id"]: s for s in scene}

    def coplanar(a, b):
        A, B = sc[int(a)], sc[int(b)]
        return (A["rule"] == B["rule"] == "face" and A["face"] == B["face"]
                and A["variant"][:2] == B["variant"][:2])
    lap, real = [], []
    for x in log["unresolved"]:
        for k, hs in x["still_clash"].items():
            for h in hs:
                (lap if coplanar(k, h) else real).append((x["group"], int(k), h))
    rep["clash_coplanar_overlap"] = lap
    rep["clash_other"] = real
    (out / "orientation_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(f"Chồng mép cùng mặt phẳng gần nút (do ép sát cánh, xử lý khi chi tiết hóa): {len(lap)} cặp")
    print(f"Cấn khác: {len(real)} cặp")
    for g, k, h in real:
        print(f"   Gr{g}: thanh {k} cấn thanh {h} ({sc[k]['rule']}/{sc[h]['rule']})")
    print("Dời điểm bắt (3d, làm tròn lên 5 mm):")
    for e in log["endpoint_shift"]:
        for k, v in e["members"].items():
            st = "KHÔNG gỡ được, giữ vị trí cũ" if v.get("reverted") else "đã gỡ cấn"
            print(f"   Gr{e['group']} thanh {k}: đầu {v['end']} dời {v['dist_mm']:.0f} mm dọc thanh {v['along']}: {st}")
    if not log["endpoint_shift"]:
        print("   không")
    return scene, rep


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    ovp = sys.argv[2] if len(sys.argv) > 2 else "data/orientation_override.csv"
    main(out, ovp)
