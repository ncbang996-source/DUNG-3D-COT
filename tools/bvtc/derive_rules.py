"""Rút quy tắc hướng cánh từ bản vẽ chế tạo: phân loại vai trò hình học của từng thanh trên mặt đứng
(nhìn từ ngoài) rồi thống kê bản vẽ đặt thanh TRONG/NGOÀI và góc lưng phía nào."""
import collections
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ezdxf  # noqa: E402
import bvtc_read as R  # noqa: E402
import build_n122 as B  # noqa: E402


def seg_inter(a, b):
    (x1, y1), (x2, y2) = a["c1"], a["c2"]
    (x3, y3), (x4, y4) = b["c1"], b["c2"]
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(d) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / d
    return t, u


def classify(ms, legs):
    """Vai trò: leg / X-upL / X-upR / phu (đầu bắt vào giữa thanh khác) / ngang / xien."""
    braces = [m for m in ms if m["width"] < 120 and not m["all_hidden"]]
    out = []
    for m in braces:
        ang = m["ang"] % 180
        hor = ang < 3 or ang > 177
        crosses = False
        for o in braces:
            if o is m or abs(((o["ang"] - m["ang"] + 90) % 180) - 90) < 5:
                continue
            r = seg_inter(m, o)
            if r and 0.08 < r[0] < 0.92 and 0.08 < r[1] < 0.92:
                crosses = True
        on_mid = False
        for p in (m["c1"], m["c2"]):
            for o in braces:
                if o is m:
                    continue
                (x1, y1), (x2, y2) = o["c1"], o["c2"]
                L = math.dist(o["c1"], o["c2"])
                tt = ((p[0] - x1) * (x2 - x1) + (p[1] - y1) * (y2 - y1)) / L ** 2
                dd = abs((x2 - x1) * (y1 - p[1]) - (x1 - p[0]) * (y2 - y1)) / L
                if 0.1 < tt < 0.9 and dd < 0.6:
                    on_mid = True
        if hor:
            role = "ngang"
        elif crosses:
            role = "X-lenTrai" if ang > 90 else "X-lenPhai"
        elif on_mid:
            role = "phu(bat giua thanh khac)"
        else:
            role = "xien don"
        hv = m["heel_dir"]
        heel = "?" if not hv else ("tren" if hv[1] > 0.05 else ("duoi" if hv[1] < -0.05 else ("phai" if hv[0] > 0 else "trai")))
        side = {"H": "TRONG", "S": "NGOAI"}.get(m["vis"], "?")
        out.append({"role": role, "side": side, "heel": heel, "section": m.get("section"), "w": m["width"],
                    "ang": round(ang, 1), "len": round(math.dist(m["c1"], m["c2"]) * R.SC)})
    return out


def main(dxf):
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    rows = []
    for name, box in B.ELEV.items():
        ms = R.members(doc, msp, box)
        L, Rr = B.legs_of(ms)
        y_mid = (L["c1"][1] + L["c2"][1]) / 2
        xc = (B.line_x_at(L, y_mid) + B.line_x_at(Rr, y_mid)) / 2
        R.assign_labels(ms, R.text_labels(msp, box), xc)
        # bỏ thanh ngoài thân (đầu xà)
        def inside(m):
            return all(abs(p[0] - xc) * R.SC <= (B.line_x_at(Rr, p[1]) - B.line_x_at(L, p[1])) / 2 * R.SC + 60
                       for p in (m["c1"], m["c2"]))
        ms2 = [m for m in ms if inside(m)]
        for r in classify(ms2, (L, Rr)):
            r["seg"] = name
            rows.append(r)
    c = collections.Counter((r["role"], r["side"], r["heel"]) for r in rows)
    print(f"{'Vai trò':28s} {'Trong/ngoài':10s} {'Lưng':6s} Số thanh")
    for (role, side, heel), n in sorted(c.items()):
        print(f"{role:28s} {side:10s} {heel:6s} {n}")
    return rows


if __name__ == "__main__":
    rows = main(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
