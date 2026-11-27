"""Cắt vùng bản vẽ DXF ra PNG để xem.

Chạy: python3 tools/bvtc/render_regions.py <dxf> <thư mục ra> ten,x0,y0,rong,cao [ten2,...]  (toạ độ DXF)
Dùng DXF đã phân tích lưu ở out/.cache (như dt02.py) và chỉ vẽ các nét nằm trong vùng cần cắt -> vài giây thay vì
~40 s. Ảnh rộng 14 in x 110 dpi (~1540 px); vùng nhỏ cho ảnh gọn, đỡ tốn khi xem.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from ezdxf.addons.drawing import RenderContext, Frontend  # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # noqa: E402
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from dt02 import read_dxf_cached  # noqa: E402


def pts_of(e):
    t = e.dxftype()
    try:
        if t == "LINE":
            return [e.dxf.start, e.dxf.end]
        if t == "LWPOLYLINE":
            return [(p[0], p[1]) for p in e.get_points()]
        if t in ("CIRCLE", "ARC"):
            c, r = e.dxf.center, e.dxf.radius
            return [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]
        if t in ("TEXT", "MTEXT", "INSERT"):
            return [e.dxf.insert]
        if t == "DIMENSION":
            return [e.dxf.defpoint]
    except Exception:
        pass
    return None


def main(dxf, out, specs):
    doc = read_dxf_cached(dxf)
    msp = doc.modelspace()
    regs = []
    for spec in specs:
        name, x0, y0, w, h = spec.split(',')
        regs.append((name, float(x0), float(y0), float(w), float(h)))
    m = 20.0                         # lề (đơn vị bản vẽ): chữ, khối chèn có điểm chèn ngoài vùng
    X0 = min(r[1] for r in regs) - m
    Y0 = min(r[2] for r in regs) - m
    X1 = max(r[1] + r[3] for r in regs) + m
    Y1 = max(r[2] + r[4] for r in regs) + m

    def inside(e):
        P = pts_of(e)
        if P is None:
            return e.dxftype() not in ("LINE", "LWPOLYLINE", "TEXT", "MTEXT", "INSERT", "CIRCLE", "ARC", "DIMENSION")
        xs, ys = [p[0] for p in P], [p[1] for p in P]
        return not (max(xs) < X0 or min(xs) > X1 or max(ys) < Y0 or min(ys) > Y1)
    ents = [e for e in msp if inside(e)]
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK, lineweight_scaling=0.3)
    fe = Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg)
    fe.draw_entities(ents)
    ax.axis('off')
    for name, x0, y0, w, h in regs:
        W = 14.0
        fig.set_size_inches(W, W * h / w)
        ax.set_xlim(x0, x0 + w)
        ax.set_ylim(y0, y0 + h)
        fig.savefig(f"{out}/{name}.png", dpi=110)
        print('saved', name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
