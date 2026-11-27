"""Tờ đang dựng (đặt bằng dt02.use_sheet): dùng chung cho dt02_base và các bước trong tools/bvtc/dung/."""
from sheets import SHEETS

SHEET = "DT-02"
CFG = SHEETS[SHEET]
BOX = CFG["box"]
PLANS = CFG["plans"]
BASE_ZONE = 560.0                                # vùng chân cột (mm từ đáy thanh cánh) = chiều cao sườn + 70
