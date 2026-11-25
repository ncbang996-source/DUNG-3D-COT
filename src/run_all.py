"""Chạy toàn bộ giai đoạn 1-5 và xuất dữ liệu cho app web.

    python3 src/run_all.py            # dùng data/ và ghi out/, web/data/scene.json
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import merge as MG  # noqa: E402
import orientation as OR  # noqa: E402
import parse_dxf as PD  # noqa: E402
import parse_pdf as PP  # noqa: E402
import plates as PL  # noqa: E402
import section_library as SL  # noqa: E402


def main():
    data, out, web = ROOT / "data", ROOT / "out", ROOT / "web" / "data"
    out.mkdir(exist_ok=True)
    web.mkdir(parents=True, exist_ok=True)

    d = PD.parse(data / "NC111-32.dxf")
    (out / "members.json").write_text(json.dumps(d["members"], indent=1))
    (out / "nodes.json").write_text(json.dumps(d["nodes"], indent=1))
    PD.print_report(d["report"])
    if d["report"]["errors"]:
        sys.exit("Dừng: DXF có lỗi.")

    p = PP.parse_text(PP.pdf_text(data / "TIET_DIEN_NC111-32.pdf"))
    c = PP.check(p)
    groups, secs = PP.build(p)
    (out / "groups.json").write_text(json.dumps(groups, indent=1, ensure_ascii=False))
    (out / "sections.json").write_text(json.dumps(secs, indent=1, ensure_ascii=False))
    PP.print_report(c, secs)
    if c["errors"]:
        sys.exit("Dừng: PDF có lỗi.")

    model, rep = MG.merge(d["members"], groups)
    (out / "model.json").write_text(json.dumps(model, indent=1, ensure_ascii=False))
    (out / "merge_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    MG.print_report(rep)

    lib, problems = SL.build(secs)
    (out / "section_library.json").write_text(json.dumps(lib, indent=1))
    SL.print_report(lib, problems)
    if problems:
        sys.exit("Dừng: thư viện tiết diện có vấn đề, cần người dùng xem.")

    OR.main(out, data / "orientation_override.csv")
    scene = json.loads((out / "scene.json").read_text())
    prep = PL.apply(scene, lib)
    (out / "plates_report.json").write_text(json.dumps(prep, indent=1, ensure_ascii=False))
    PL.print_report(prep)
    scene["nodes"] = d["nodes"]
    scene["report"] = {"total_mass_kg": rep["total_mass_kg"], "plates": prep,
                       "orientation": json.loads((out / "orientation_report.json").read_text())}
    (web / "scene.json").write_text(json.dumps(scene, ensure_ascii=False, separators=(",", ":")))
    print(f"Đã ghi {web / 'scene.json'}")


if __name__ == "__main__":
    main()
