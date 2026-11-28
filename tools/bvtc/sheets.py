"""Cấu hình từng tờ bản vẽ BVTC N122 cho bộ dựng dt02.py (khung mặt đứng, mặt cắt, chân cột, đặc thù tờ).

Thêm tờ mới = thêm mục SHEETS. Các khóa: xem docs/BO_DUNG.md (mục "Khóa cấu hình").
"""
# Cấu hình từng tờ bản vẽ (toạ độ DXF). Chân cột: sườn d12 (mm, gốc = góc dưới-trái hình chi tiết 1/10, đọc từ DXF)
SHEETS = {
    "DT-02": {
        "box": (-2380, -122110, -2040, -121674),       # mặt đứng (không lấy hình khai triển thanh cánh)
        "plans": {   # tên: (y vạch cắt trên mặt đứng, khung đọc mặt cắt)
            "1-1": (-121780.0, (-1980, -121766, -1880, -121680)),
            "2-2": (-121852.3, (-1980, -122063, -1812, -121905)),
            "3-3": (-121935.3, (-1980, -121880, -1867, -121785)),
            "4-4": (-122015.4, (-1875, -122170, -1805, -122092)),
        },
        "level_cut": {"1-1": 30, "2-2": 45, "3-3": 30, "4-4": 30},
        "plan_gauge_center": ["1-1"],              # góp ý: trục bu lông vách 1-1 ở giữa cánh nằm thanh mặt cột
        "foot_diag_cut": True,                         # ghi chú vát 40x60 đầu dưới thanh xiên chính (tờ DT-02)
        "top_splice": {"plate_t": 10},                 # bản mã nối d10 ở đỉnh (chi tiết + hình cắt A-A)
        "base": {
            "rib1": [(0, 100), (0, 0), (545, 0), (545, 350), (435, 490), (220, 490)],
            "rib2": [(0, 100), (0, 0), (157, 0), (192, 30), (260, 490), (220, 490)],
            "rib3": [(0, 30), (30, 0), (345, 0), (345, 350), (235, 490), (73, 490)],
            "rib1_h": [(265, 98), (277, 177), (289, 256), (300, 335), (312, 415), (315, 131), (327, 210), (339, 289),
                       (351, 368), (362, 448), (430, 213), (468, 272), (505, 331)],
            "rib3_h": [(71, 138), (83, 217), (95, 296), (106, 375), (110, 91), (118, 454), (122, 171), (133, 250),
                       (145, 329), (157, 408), (230, 213), (268, 272), (305, 331)],
            "diag_u": (430, 230), "heel": 3771.0, "L": {"leg": 70, "diag": 60},
            "labels": {"leg": "12.20_70", "diag": "3.20_60"},
        },
    },
    "DT-01": {
        "box": (-2357, -121515, -2133, -121060),
        "plans": {"1-1": (-121420.53, (-2020, -121345, -1828, -121170))},
        "level_cut": {"1-1": 25},
        # mặt cắt 1-1 ghi "trục uốn" cách góc 300, lệch 15: 2 nửa thanh ngang mặt cột bẻ lệch ra ngoài 15 mm để áp vừa
        # mặt trong bản mã giữa 312 (người dùng xác nhận); thứ tự: thanh xiên ngoài - bản mã - thanh xiên trong
        "center_joggle": {"offset": 15.0, "from_leg": 300.0, "ramp": 45.0, "straight": True},
        # người dùng chốt: bỏ bản đế, đoạn đặt lên DT-02 (bản mã chờ d10 + thép góc nối trong HL130x9 của DT-02)
        "on_top_of": {"sheet": "DT-02", "plate_t": 10},
        # bản mã nét khuất ở đỉnh = bản mã 301/302 d10 của đoạn ngọn DN-02 (DN-02 vẽ nét liền, ngoài cánh thanh
        # cánh, ghi d10), bẻ góc theo đường gãy thanh cánh
        "hidden_inner_plates": {"t": 10, "note": "bản mã 228/228a của DN-02 (DN-02 ghi d10), bẻ góc theo thanh cánh"},
        "top_kink": True,
        "base": {
            "rib1": [(0, 100), (0, 0), (515, 0), (515, 220), (435, 420), (200, 420)],
            "rib2": [(0, 100), (0, 0), (158, 0), (192, 30), (250, 420), (200, 420)],
            "rib3": [(0, 30), (26, 0), (311, 0), (311, 220), (231, 420), (58, 420)],
            "rib1_h": [(265, 98), (277, 177), (288, 256), (300, 335), (315, 131), (327, 210), (339, 289), (350, 368),
                       (428, 120), (476, 156)],
            "rib3_h": [(66, 137), (78, 217), (90, 296), (101, 375), (105, 91), (117, 170), (128, 250), (140, 329),
                       (224, 120), (272, 156)],
            "diag_u": (400, 200), "heel": None, "L": {"leg": 70, "diag": 60},
            "labels": {"leg": "8.20_70", "diag": "3.20_60"},
        },
    },
    # ĐOẠN NGỌN DN-02 (người dùng chốt 4 đề xuất): thẳng đứng, 2 kiểu mặt -> dựng 2 lần rồi ghép theo mặt
    #   DN-02  = mặt có xà (trước/sau, k = 0, 2): L90x7 dài 2840 + L60x5 chống; bỏ L70x6 nghiêng của xà (vẽ cụt)
    #   DN-02s = mặt bên (k = 1, 3)
    # z = 0 tại đường gãy thanh cánh (đầu dưới phần đứng DT-01). Thanh cánh DN-02 HL130x9 (232) từ khe B-B
    # (860 trên đường gãy) tới khe A-A (6260, đo trên DXF: khe 6255..6265; trước ghi 6240 lệch 20 mm so với bu lông và
    # bản nối vẽ - phát hiện khi ráp DN-01), HL130x9 (203) từ A-A tới đỉnh; dưới B-B là phần đứng DT-01
    # (HL150x12 - 301, chữ "HL130x12" ở hình B-B ghi nhầm), lưng thẳng hàng, đường tim cách lưng 80.
    "DN-02": {
        "box": (-2395, -120835, -2195, -120480),
        "plans": {"1-1": (-120567.9, (-1998, -120564, -1880, -120458)),
                  "2-2": (-120727.9, (-1998, -120694, -1880, -120588)),
                  "3-3": (-120787.9, (-1985, -120808, -1893, -120718))},
        "level_cut": {"3-3": 50},
        "no_base": True,
        "faces": [0, 2],
        "drop_rules": [{"sections": ["L70X6", None], "non_horizontal": True}],
        "bottom_stub": {"sheet": "DT-01", "joint_mm": 860.0, "gap": 10.0, "section": "HL150X12"},
        "leg_splices": [{"z": 6260.0, "gap": 10.0, "inner": "HL120X8", "inner_L": 730.0}],
        "waiting_holes": True,
        "detail_hole_max": 15.0,
        "banma_join_gap": 20.0,
        "trim_to_end_lines": True,
    },
}
SHEETS["DN-02"]["xa_keep_horizontal"] = True        # góp ý: thanh chống L60x5 của xà dựng khi làm phần xà
SHEETS["DN-02s"] = dict(SHEETS["DN-02"], box=(-2190, -120835, -2045, -120480), faces=[1, 3])
# ĐOẠN NGỌN DN-01 (trên cùng). Tờ DN-01 vẽ lặp phần đỉnh DN-02 (từ L90x7 1570 qua mối nối A-A HL120x8 tới L70x6
# 1710); người dùng chốt: lấy DN-01 thay phần trùng phía trên A-A, trừ thanh ngang L70x6 (234) và thanh xiên L80x6
# (214) lấy theo DN-02 (đã thống kê ở DN-02) - xem merge_segments.py "replace_above".
# z = 0 tại đầu dưới thanh cánh vẽ trên tờ DN-01 (1117 dưới mối nối A-A của DN-02, đo trên DXF: khe 1112..1122).
# Thanh cánh: HL130x9 201/202 (DN-02) từ A-A lên mối nối A-A của DN-01 (khe 5112..5122), trên đó L100x7 tới đỉnh.
# Mối nối A-A DN-01 (chi tiết 1/10): thép góc nối trong L90x7 dài 550 vát góc 10x10, bản nối ngoài d8 100x530,
# tấm d2 70x240 (L100x7 mỏng hơn HL130x9 2 mm, 2 thanh thẳng mặt trong như B-B DN-02 -> tấm d2 bù ở lưng L100x7).
SHEETS["DN-01"] = {
    "box": (-2395, -120255, -2195, -119850),
    "plans": {"1-1": (-119879.4, (-2000, -119990, -1870, -119855)),
              "2-2": (-120003.4, (-1865, -119985, -1735, -119855)),
              "3-3": (-120059.4, (-1990, -120125, -1860, -119995))},
    "level_cut": {},
    # "vát cánh 20x20mm" (1-1), "60x60mm" (2-2): mũi tên chỉ đầu thanh chéo vách ở góc (không phải thanh mặt cột)
    "plan_end_cut": {"1-1": 20, "2-2": 60},
    "no_base": True,
    "faces": [0, 2],
    "xa_keep_horizontal": True,
    "leg_section": "HL130X9",
    "leg_hidden_ok": True,            # đầu trên L100x7 vẽ nét khuất sau bản mã đỉnh (không có đoạn nào phía trên)
    "bottom_stub": {"sheet": "DN-02", "joint_mm": 1117.0, "gap": 10.0, "section": "HL130X9", "inner": "HL120X8",
                    "inner_L": 730.0, "plate_L": 690.0, "plate_t": 10, "joint_name": "A-A (DN-02)",
                    "inner_name": "thép góc nối trong A-A (229, DN-02)",
                    "stub_name": "thanh cánh 203/204 (DN-02, vẽ để ráp)",
                    "names": ["thanh cánh 201/202 (DN-02)", "thanh cánh L100x7 (DN-01)"]},
    "leg_splices": [{"z": 5117.0, "gap": 10.0, "inner": "L90X7", "inner_sec": "L90X7-NOI", "inner_L": 550.0,
                     "inner_cut": 10.0, "plate_L": 530.0, "plate_t": 8, "above": "L100X7", "name": "A-A (DN-01)",
                     "inner_name": "thép góc nối trong A-A DN-01 (L90x7 dài 550, vát góc 10x10)",
                     "shim": {"w": 70.0, "L": 240.0, "t": 2.0,
                              "note": "tấm d2 70x240 bù chiều dày (lưng L100x7 lùi 2 mm), dưới bản nối ngoài A-A DN-01"}}],
    "waiting_holes": True,
    "detail_hole_max": 15.0,
    "banma_join_gap": 20.0,
    "trim_to_end_lines": True,
    # mặt cắt 1-1: thanh ngang đỉnh L70x6 2080 bẻ 2 đầu 300 VÀO TRONG (chụm theo biên xà X1), dốc 327/1000
    "top_bend": [{"plan": "1-1", "x_mm": 1040.0, "slope": 0.327, "z_m": 8.917,
                 "note": "2080 + 2 x 300, dốc 327/1000"},
                 # người dùng chốt (X1): tai bản mã có tai ở cao độ L60x5 1770 (chỗ biên dưới xà X1 bắt vào) bẻ 18,1 độ
                 # theo mặt xà X1 như bản 117
                 {"plan": "tai bản mã X1", "x_mm": 1040.0, "slope": 0.327, "z_m": 7.367, "plates_only": True,
                  "note": "tai bản mã bắt biên dưới xà X1"}],
}
SHEETS["DN-01s"] = dict(SHEETS["DN-01"], box=(-2190, -120255, -2045, -119850), faces=[1, 3], top_bend=None)
