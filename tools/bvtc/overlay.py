"""So sánh: vẽ chồng các thanh đã nhận dạng (đỏ = đường tim dùng dựng 3D, xanh = bị bỏ) lên nét bản vẽ (xám)."""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ezdxf, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import bvtc_read as R, build_n122 as B

doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace(); out = Path(sys.argv[2])
for name, box in B.ELEV.items():
    segs = R.segments(doc, msp, box)
    ms = R.members(doc, msp, box)
    L, Rr = B.legs_of(ms)
    y_mid = (L["c1"][1] + L["c2"][1]) / 2
    xc = (B.line_x_at(L, y_mid) + B.line_x_at(Rr, y_mid)) / 2
    R.assign_labels(ms, R.text_labels(msp, box), xc)
    used = set()
    for m in ms:
        ok = m.get("section") and not m["all_hidden"]
        used.update()
    w, h = box[2] - box[0], box[3] - box[1]
    fig, ax = plt.subplots(figsize=(10, 10 * h / w))
    for s in segs:
        ax.plot([s["a"][0], s["b"][0]], [s["a"][1], s["b"][1]], color="0.75", lw=0.5,
                ls="--" if s["k"] == "H" else "-")
    nmiss = 0
    for m in ms:
        ok = bool(m.get("section")) and not m["all_hidden"]
        col = "red" if ok else "blue"
        nmiss += not ok
        ax.plot([m["c1"][0], m["c2"][0]], [m["c1"][1], m["c2"][1]], color=col, lw=1.6)
        ax.plot([m["p1"][0], m["p2"][0]], [m["p1"][1], m["p2"][1]], color=col, lw=0.6, ls=":")
    ax.set_aspect("equal"); ax.set_title(f"{name}: {len(ms)} thanh nhận dạng, {nmiss} bị bỏ (xanh)")
    ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.axis("off")
    fig.savefig(out / f"overlay_{name}.png", dpi=110, bbox_inches="tight"); plt.close(fig)
    print(name, len(ms), "bỏ", nmiss, "đoạn nét", len(segs))
