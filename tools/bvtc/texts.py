import sys, collections, ezdxf
doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace()
out = []
for e in msp:
    t = e.dxftype()
    if t in ('TEXT', 'MTEXT'):
        s = e.dxf.text if t == 'TEXT' else e.plain_text()
        p = e.dxf.insert
        out.append((e.dxf.layer, round(p[0]), round(p[1]), s.replace('\n', ' | ')))
cnt = collections.Counter(o[3] for o in out)
print("distinct texts", len(cnt))
for layer in sorted({o[0] for o in out}):
    xs = [o for o in out if o[0] == layer]
    c = collections.Counter(o[3] for o in xs)
    print(f"\n== {layer} ({len(xs)}) ==")
    for k, v in c.most_common(40): print(f"  {v:4d} {k[:150]}")
