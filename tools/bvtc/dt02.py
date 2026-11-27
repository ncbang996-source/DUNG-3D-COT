"""Dựng 3D 1 tờ bản vẽ chế tạo cột N122 (DT-02, DT-01, DN-02, DN-01...) - xem docs/BO_DUNG.md.

Chạy:  python3 tools/bvtc/dt02.py <BVTC.dxf> <thư mục ra> [DT-02|DT-01|DN-02|DN-02s|DN-01|DN-01s]

Mã chia thành:
- dt02_base.py: hàm hình học 2D, đọc DXF (bộ nhớ đệm), bản mã, khớp hình chi tiết, đọc thanh cánh (read_elevation);
- dung/b0..b9: các bước dựng (đọc + lọc thanh, bản mã, nối/tách, độ sâu, vát, bu lông, tấm đệm, 3D, vách, hoàn thiện);
- sheets.py: cấu hình từng tờ; state.py: tờ đang dựng; fixes.py: gỡ chạm / bẻ đầu thanh.
Các bước truyền biến qua từ điển V (tên biến giữ nguyên như khi còn là một hàm).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dt02_base import *  # noqa: F401,F403,E402  (dt02.sec, dt02.inter, dt02.LIB... như trước)
import state as ST  # noqa: E402
from sheets import SHEETS  # noqa: E402

STEPS = ["b0_loc_thanh", "b1_ban_ma", "b2_noi_tach", "b3_do_sau", "b4_vat_ghi_chu", "b5_bu_long", "b6_tam_dem",
         "b7_dung_3d", "b8_vach", "b9_hoan_thien"]


def main(dxf, outdir):
    import importlib
    V = {"dxf": dxf, "outdir": outdir}
    for name in STEPS[:-1]:
        V.update(importlib.import_module("dung." + name).run(V))
    return importlib.import_module("dung." + STEPS[-1]).run(V)


def use_sheet(name):
    ST.SHEET, ST.CFG = name, SHEETS[name]
    ST.BOX, ST.PLANS = ST.CFG["box"], ST.CFG["plans"]
    ST.BASE_ZONE = max(v for _, v in ST.CFG["base"]["rib1"]) + 70.0 if "base" in ST.CFG else 0.0


def __getattr__(name):
    # tương thích: dt02.CFG, dt02.PLANS, dt02.SHEET... (dn_plans.py dùng) = tờ đang dựng
    if name in ("SHEET", "CFG", "BOX", "PLANS", "BASE_ZONE"):
        return getattr(ST, name)
    raise AttributeError(name)


if __name__ == "__main__":
    use_sheet(sys.argv[3] if len(sys.argv) > 3 else "DT-02")
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
