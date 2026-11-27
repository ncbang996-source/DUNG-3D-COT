"""In tóm tắt báo cáo dựng (report.build) của scene: cảnh báo, thanh cánh, mặt cắt, gỡ chạm.
Chạy: python3 tools/bvtc/brief.py out/dn01_scene.json"""
import collections
import json
import sys

s = json.load(open(sys.argv[1]))
r = s["report"]["build"]
print("thanh", len(s["members"]), "bản mã/tấm", len(s["plates"]), "bu lông", len(s["bolts"]), "z", r.get("z_range_m"))
for k in ("leg", "n_brace_drawing", "n_brace_kept", "split_at_plate", "ends_trimmed", "holes_waiting", "plans",
          "clash_fix", "warnings", "plan_brace_end_55", "fillers", "joint", "top_bend", "split_at_plate"):
    if k in r:
        v = json.dumps(r[k], ensure_ascii=False)
        print(f"- {k}: {v[:1500]}")
c = collections.Counter((m["section"], m.get("side"), m["rule"]) for m in s["members"] if m.get("face_k") in (0, -1))
for k, v in sorted(c.items(), key=str):
    print("  ", k, v)
