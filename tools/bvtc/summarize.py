import json, math, sys, collections
CX = float(__import__("os").environ.get("CX", "0"))
M = json.load(open(sys.argv[1]))
rows = []
for m in M:
    a = math.radians(m['ang'])
    ax = (math.cos(a), math.sin(a)); n = (-ax[1], ax[0])
    if m['heel'] is None: kind = '?'
    else:
        hv = n if m['heel'] == 'hi' else (-n[0], -n[1])     # hướng từ đường tâm về phía góc lưng
        kind = None
    ang = m['ang'] % 180
    if m['width'] >= 120 and 60 < ang < 120: cls = 'leg'
    elif ang < 3 or ang > 177: cls = 'hor'
    elif 87 < ang < 93: cls = 'vert'
    else: cls = 'diag-upR' if ang < 90 else 'diag-upL'
    side = {'H': 'TRONG', 'S': 'NGOAI'}.get(m['tvis'], '?')
    if m['heel'] is None: heel = '?'
    elif cls == 'leg': heel = 'ra ngoai' if (hv[0] * (m['p1'][0] - CX)) > 0 else 'vao trong'
    elif cls == 'vert': heel = 'phai' if hv[0] > 0 else 'trai'
    else: heel = 'tren' if hv[1] > 0 else 'duoi'
    rows.append((cls, m['width'], side, heel, m['center_from_lo'], m['len_mm']))
    print(f"{cls:9s} b={m['width']:4d} {side:6s} lưng {heel:9s} tâm@{m['center_from_lo']} L={m['len_mm']}")
print(collections.Counter((r[0], r[2], r[3]) for r in rows))
