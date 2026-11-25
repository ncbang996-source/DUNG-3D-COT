"""Giai đoạn 4: thư viện tiết diện thép góc đều cạnh theo JIS G3192.

Kích thước danh định b, t, r1 (bán kính góc trong), r2 (bán kính mép cánh) lấy theo bảng
JIS G3192. Diện tích và trọng tâm được TÍNH từ hình học (đa giác có bo cung) rồi so với A
trong PDF. HL = thép góc đều cạnh cùng kích thước (người dùng đã xác nhận).

Chạy:  python3 src/section_library.py out/
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

# name: (b, t, r1, r2) mm, theo JIS G3192 (Equal-leg angle).
JIS_G3192 = {
    "L50X4": (50, 4, 6.5, 3),
    "L60X5": (60, 5, 6.5, 3),
    "L65X5": (65, 5, 8.5, 3),
    "L70X6": (70, 6, 8.5, 4),
    "L80X6": (80, 6, 8.5, 4),
    "L90X7": (90, 7, 10, 5),
    "L100X7": (100, 7, 10, 5),
    "L120X8": (120, 8, 12, 5),
    "L130X12": (130, 12, 12, 8.5),
    "L150X12": (150, 12, 14, 7),
    "L175X12": (175, 12, 15, 11),
}

ARC_SEG = 6


def base_name(section: str) -> str:
    """HL175X12 -> L175X12."""
    return re.sub(r"^H", "", section.upper())


def _arc(cx, cy, r, a0, a1, n=ARC_SEG):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(n + 1)]


def profile(b: float, t: float, r1: float, r2: float, rounded: bool = True) -> list[tuple[float, float]]:
    """Đa giác tiết diện L (mm), góc lưng (heel) tại gốc tọa độ.
    Cánh 1 dọc trục s1 (dày theo s2), cánh 2 dọc trục s2 (dày theo s1). Ngược chiều kim đồng hồ."""
    if not rounded:
        return [(0, 0), (b, 0), (b, t), (t, t), (t, b), (0, b)]
    pts = [(0.0, 0.0), (b, 0.0)]
    # Mép cánh 1: bo r2 ở góc trong (b, t)
    pts += _arc(b - r2, t - r2, r2, 0.0, math.pi / 2)[:]
    # Góc trong giữa hai cánh: bo r1, tâm (t + r1, t + r1), từ (t+r1, t) tới (t, t+r1)
    pts += _arc(t + r1, t + r1, r1, -math.pi / 2, -math.pi)
    # Mép cánh 2: bo r2 tại (t, b)
    pts += _arc(t - r2, b - r2, r2, 0.0, math.pi / 2)
    pts.append((0.0, b))
    # Bỏ điểm trùng liên tiếp
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 1e-9:
            out.append(p)
    return out


def poly_props(pts):
    a = cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a /= 2
    return a, cx / (6 * a), cy / (6 * a)


def area_exact(b, t, r1, r2):
    return 2 * b * t - t * t + (1 - math.pi / 4) * (r1 * r1 - 2 * r2 * r2)


def build(sections_pdf: dict) -> tuple[dict, list[str]]:
    lib, problems = {}, []
    for name, info in sections_pdf.items():
        base = base_name(name)
        if base not in JIS_G3192:
            problems.append(f"{name}: không có trong bảng JIS G3192")
            continue
        b, t, r1, r2 = JIS_G3192[base]
        pts = profile(b, t, r1, r2)
        A_poly, cx, cy = poly_props(pts)
        A_ex = area_exact(b, t, r1, r2)
        A_pdf = info["A_cm2"] * 100
        dev = (A_ex - A_pdf) / A_pdf * 100
        if abs(dev) >= 1:
            problems.append(f"{name}: A hình học {A_ex/100:.2f} cm2 lệch {dev:+.2f}% so với PDF {info['A_cm2']}")
        lib[name] = {
            "name": name, "base": base, "standard": "JIS G3192",
            "b": b, "t": t, "r1": r1, "r2": r2,
            "A_geom_cm2": round(A_ex / 100, 3), "A_poly_cm2": round(A_poly / 100, 3),
            "A_pdf_cm2": info["A_cm2"], "A_dev_pct": round(dev, 3),
            "cx": round(cx, 2), "cy": round(cy, 2),   # trọng tâm từ góc lưng (mm)
            "gauge": b / 2,                             # đường đinh: giữa bề rộng cánh
            "profile": [[round(x, 3), round(y, 3)] for x, y in pts],
        }
    return lib, problems


def print_report(lib, problems):
    print("=== THƯ VIỆN TIẾT DIỆN (JIS G3192) ===")
    print(f"{'Tên':<10}{'b':>5}{'t':>4}{'r1':>6}{'r2':>6}{'A hh':>8}{'A pdf':>8}{'lệch%':>8}{'cx=cy':>8}")
    for k, v in sorted(lib.items(), key=lambda kv: (kv[1]["b"], kv[1]["t"])):
        print(f"{k:<10}{v['b']:>5}{v['t']:>4}{v['r1']:>6}{v['r2']:>6}{v['A_geom_cm2']:>8.2f}"
              f"{v['A_pdf_cm2']:>8.2f}{v['A_dev_pct']:>8.2f}{v['cx']:>8.2f}")
    print("Vấn đề:", problems or "không (mọi tiết diện lệch < 1%)")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    secs = json.loads((out / "sections.json").read_text())
    lib, problems = build(secs)
    (out / "section_library.json").write_text(json.dumps(lib, indent=1))
    print_report(lib, problems)
