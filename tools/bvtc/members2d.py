"""Tách thanh thép góc trên hình chiếu đứng của bản vẽ chế tạo (2D)."""
import sys, math, json, collections, ezdxf
SC = 25.0
doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace()
x0, y0, x1, y1 = map(float, sys.argv[2:6])
inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
def lt(e):
    l = e.dxf.get('linetype', 'BYLAYER')
    if l.upper() == 'BYLAYER': l = doc.layers.get(e.dxf.layer).dxf.linetype
    l = l.upper()
    return 'A' if l.startswith('CENTER') else ('H' if l.startswith('HIDDEN') or l.startswith('DASH') else 'S')
segs = []
for e in msp:
    t = e.dxftype()
    if e.dxf.layer not in ('0', 'COT'): continue
    if t == 'LINE':
        pts = [(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])]
    elif t == 'LWPOLYLINE':
        pts = [(p[0], p[1]) for p in e.get_points()]
        pts = list(zip(pts, pts[1:]))
        for a, b in pts:
            if inside(a) and inside(b): segs.append((a, b, lt(e)))
        continue
    else: continue
    a, b = pts
    if inside(a) and inside(b): segs.append((a, b, lt(e)))
S = []
for a, b, k in segs:
    dx, dy = b[0] - a[0], b[1] - a[1]; ln = math.hypot(dx, dy)
    if ln * SC < 150: continue
    ang = math.atan2(dy, dx) % math.pi
    S.append({'a': a, 'b': b, 'k': k, 'ang': ang, 'len': ln})
n = len(S); par = list(range(n))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
def rel(l, o):
    ax = (math.cos(l['ang']), math.sin(l['ang'])); nx = (-ax[1], ax[0])
    off = (o['a'][0] - l['a'][0]) * nx[0] + (o['a'][1] - l['a'][1]) * nx[1]
    off2 = (o['b'][0] - l['a'][0]) * nx[0] + (o['b'][1] - l['a'][1]) * nx[1]
    s = sorted([(o['a'][0] - l['a'][0]) * ax[0] + (o['a'][1] - l['a'][1]) * ax[1],
                (o['b'][0] - l['a'][0]) * ax[0] + (o['b'][1] - l['a'][1]) * ax[1]])
    return (off + off2) / 2, s
for i in range(n):
    for j in range(i + 1, n):
        da = abs((S[i]['ang'] - S[j]['ang'] + math.pi / 2) % math.pi - math.pi / 2)
        if da > math.radians(0.8): continue
        off, s = rel(S[i], S[j])
        _, si = rel(S[i], S[i])
        ov = min(s[1], si[1]) - max(s[0], si[0])
        if abs(off) * SC < 160 and ov > 0.3 * min(S[i]['len'], S[j]['len']):
            par[f(i)] = f(j)
G = collections.defaultdict(list)
for i in range(n): G[f(i)].append(i)
out = []
for g in G.values():
    cen = [S[i] for i in g if S[i]['k'] == 'A']
    if not cen: continue
    ref = max(cen, key=lambda l: l['len'])
    items = []
    for i in g:
        off, s = rel(ref, S[i]); items.append((round(off * SC), S[i]['k'], s))
    offs = sorted(items)
    ed = [o for o in offs if o[1] != 'A']
    if len(ed) < 2: continue
    lo, hi = ed[0][0], ed[-1][0]
    width = hi - lo
    cofs = sorted({o[0] for o in offs if o[1] == 'A'})
    thick = [o for o in ed if lo < o[0] < hi]
    heel = None; vis = None; tline = None
    for o in thick:
        if o[0] - lo <= 25: heel, tline, vis = 'lo', o[0] - lo, o[1]
        elif hi - o[0] <= 25: heel, tline, vis = 'hi', hi - o[0], o[1]
    ax = (math.cos(ref['ang']), math.sin(ref['ang']))
    ss = [s for _, _, s in items]
    smin = min(s[0] for s in ss); smax = max(s[1] for s in ss)
    p1 = (ref['a'][0] + ax[0] * smin, ref['a'][1] + ax[1] * smin)
    p2 = (ref['a'][0] + ax[0] * smax, ref['a'][1] + ax[1] * smax)
    out.append({'ang': round(math.degrees(ref['ang']), 2), 'p1': p1, 'p2': p2, 'len_mm': round((smax - smin) * SC),
                'width': width, 'center_from_lo': [c - lo for c in cofs], 'heel': heel, 'tline': tline,
                'tvis': vis, 'edges_vis': ''.join(o[1] for o in ed), 'n_lines': len(g)})
out.sort(key=lambda m: (-m['len_mm']))
for m in out:
    print(f"ang {m['ang']:6.1f} L {m['len_mm']:5d} w {m['width']:4d} center@{m['center_from_lo']} heel={m['heel']} t={m['tline']}{m['tvis']} lines={m['edges_vis']} "
          f"p1=({m['p1'][0]:.1f},{m['p1'][1]:.1f})")
json.dump(out, open(sys.argv[6], 'w'))
