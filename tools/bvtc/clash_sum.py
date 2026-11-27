"""Tóm tắt kiểm chạm theo loại cặp (đánh dấu thanh xà / tiết diện), in vị trí mẫu.
Chạy: python3 tools/bvtc/clash_sum.py <scene>"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_dt02 as CK  # noqa: E402

s = json.load(open(sys.argv[1]))
S = s["sections"]
M = {m["id"]: m for m in s["members"]}
nm = lambda m: "%s/%s" % (m.get("mark") or m["section"], m.get("xa_view") or m["rule"])
res = CK.clashes(s, S)
c = collections.defaultdict(list)
for r in res:
    c[tuple(sorted((nm(M[r["a"]]), nm(M[r["b"]]))))].append(r)
print("cặp chạm:", len(res))
for k, v in sorted(c.items(), key=lambda kv: -len(kv[1])):
    print(" ", len(v), k, "vd", v[0]["at"], "n", v[0]["n"], "id", v[0]["a"], v[0]["b"])
pr = CK.plate_clashes(s, S)
c = collections.defaultdict(list)
for r in pr:
    c[(r["reason"][:40], nm(M[r["m"]]))].append(r)
print("bản mã chạm thép:", len(pr))
for k, v in sorted(c.items(), key=lambda kv: -len(kv[1])):
    print(" ", len(v), k, "vd", v[0]["at"], "n", v[0]["n"])
