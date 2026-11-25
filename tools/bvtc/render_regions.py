import sys, ezdxf, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace()
out = sys.argv[2]
fig = plt.figure(figsize=(20, 20)); ax = fig.add_axes([0, 0, 1, 1])
cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK, lineweight_scaling=0.3)
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=False)
ax.axis('off')
for spec in sys.argv[3:]:
    name, x0, y0, w, h = spec.split(',')
    x0, y0, w, h = map(float, (x0, y0, w, h))
    W = 14.0
    fig.set_size_inches(W, W * h / w)
    ax.set_xlim(x0, x0 + w); ax.set_ylim(y0, y0 + h)
    fig.savefig(f"{out}/{name}.png", dpi=110)
    print('saved', name, flush=True)
