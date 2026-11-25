"""Vẽ nhanh khung dây theo Type (kiểm tra bằng mắt). python3 src/preview.py out/model.json out/preview.png"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
COL = {"CĐ": "#b00", "C": "#e33", "XĐ": "#06c", "X": "#39f", "G": "#999", "XAD": "#0a0", "XAT": "#7c0", "XCS": "#a0a"}
m = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "out/model.json"))
fig = plt.figure(figsize=(16, 10))
views = [(15, -60, "3D"), (0, -90, "Mặt đứng (nhìn theo +Y)"), (0, 0, "Mặt bên (nhìn theo -X)"), (90, -90, "Mặt bằng")]
for k, (el, az, t) in enumerate(views):
    ax = fig.add_subplot(1, 4, k + 1, projection="3d")
    for x in m:
        a, b = x["p1"], x["p2"]
        ax.plot([a[0], b[0]], [a[1], b[1]], [a[2], b[2]], color=COL[x["type"]],
                lw=2.2 if x["type"] in ("C", "CĐ") else 0.8)
    ax.view_init(el, az); ax.set_title(t); ax.set_box_aspect((7, 6, 33) if k != 3 else (7, 6, 1))
    if k == 0:
        for ty, c in COL.items(): ax.plot([], [], color=c, label=ty)
        ax.legend(loc="upper left", fontsize=8)
plt.tight_layout(); plt.savefig(sys.argv[2] if len(sys.argv) > 2 else "out/preview.png", dpi=110)
