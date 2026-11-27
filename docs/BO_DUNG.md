# Bản đồ bộ dựng N122 (đọc file này trước, rồi chỉ mở đúng đoạn mã cần sửa)

## Chạy
- `bash tools/bvtc/build_n122.sh` (= `python3 tools/bvtc/build.py`): dựng **tăng dần**. Bước nào đầu vào không đổi
  (nội dung file mã, DXF, cấu hình tờ) thì bỏ qua; `--force` làm lại tất cả (~80 s). Dấu ở `out/.stamp/`, nhật ký
  từng bước `out/log_<bước>.txt`, kiểm chạm `out/log_kiem_<dt02|dt01|dn02|cot>.txt`.
- Thời gian (máy ảo 1 phiên, --force): mỗi tờ 5–10 s; vách DN 3 s; ghép 1–3 s; kiểm chạm cột đủ 36 s; HTML < 1 s.
- Sửa 1 tờ trong `sheets.py` -> chỉ dựng lại tờ đó + các bước sau nó.
- Tóm tắt báo cáo 1 scene: `python3 tools/bvtc/brief.py out/<tờ>_scene.json` (đừng in cả JSON).
- Cắt ảnh bản vẽ: `render_regions.py` (~2–3 s, dùng chung bộ nhớ đệm DXF). Cắt vùng nhỏ đúng chỗ cần xem.

## Chuỗi dữ liệu
```
sheets.py ──> dt02.py <tờ> ──> out/<tờ>_scene.json            (DT-02, DT-01, DN-02, DN-02s, DN-01, DN-01s)
DN-02 + DN-02s ─ combine_faces.py ─> dn02_comb ─ dn_plans.py ─> dn02_full     (DN-01 tương tự)
dt02 + dt01 ─ merge_segments ─> n122_dt02_dt01 ─ + dn02_full ─> n122_3doan ─ + dn01_full (--replace-above) ─> n122_4doan
check_dt02.py <scene> all  (bu lông xuyên dọc cánh / thép-thép / bản mã-thép)
data/n122/*.json + dist/*.html (build_standalone.mjs)
```

## File
| File | Nội dung |
|---|---|
| `sheets.py` | Cấu hình từng tờ `SHEETS` (bảng khóa bên dưới) |
| `dt02.py` | Bộ dựng 1 tờ: hàm hình học 2D, `read_elevation` (thanh cánh), `main` (mọi bước, xem bảng mục) |
| `bvtc_read.py` | Đọc nét mặt đứng thành thanh (nét mép, đường tâm, nét chiều dày, nhãn tiết diện) |
| `fixes.py` | `top_bend` (bẻ đầu thanh đỉnh DN-01), `corner_fix` (vát góc cột), `EndContact`/`first_ok` (tìm cỡ vát nhanh) |
| `check_dt02.py` | Hình học kiểm chạm khớp app (`frame`, `samples`, `where_v`, `clashes`, `plate_clashes`, `bolt_issues`) |
| `combine_faces.py` | Ghép mặt có xà (k 0,2) + mặt bên (k 1,3); tính lại vát góc cột với mặt kề thật |
| `dn_plans.py` | Vách ngang đoạn 2 kiểu mặt (thanh chéo góc–góc, bu lông, tấm đệm tâm, vát đầu thanh khe 10 mm) |
| `merge_segments.py` | Ghép đoạn trên lên đoạn dưới; `--replace-above` (DN-01 thay đỉnh DN-02, giữ 214/234) |
| `build.py` | Điều phối dựng tăng dần |

## Các mục trong `dt02.main` (tìm bằng `grep -n "# --- <đầu dòng>" tools/bvtc/dt02.py`)
| Mục (đầu dòng chú thích) | Việc |
|---|---|
| (đầu hàm) | lọc thanh giằng: trong thân / khuất / tờ trên-dưới / xà (`xa_keep_horizontal`, `drop_rules`), cắt theo nét đầu thanh |
| `gốc cao độ` | z = 0 tại đầu dưới thanh cánh |
| `bản mã (lớp Banma)` / `NÉT KHUẤT` / `bản vẽ đứng thấy cạnh` | đọc bản mã mặt đứng, bản mã nét khuất, bản hàn vuông góc |
| `hình chi tiết bản mã` | khớp hình chi tiết theo số hiệu (xoay/lật), khớp lỗ với bu lông vẽ, lỗ chờ |
| `đoạn đặt trên đoạn khác` | DT-01 trên DT-02 (bản mã chờ) |
| `thanh vẽ liền một đường tâm` | tách thanh tại bản mã (trừ khi thanh xiên đã dừng ở đó) |
| `thanh chủ của từng đầu thanh` | thanh chủ, `back_extra`/`leg_sec_at` (thanh cánh nhiều đoạn), độ sâu lan truyền |
| `nút giữa có thanh ngang bẻ lệch` | DT-01 1-1 |
| `vát cánh theo ghi chú` | vát theo ghi chú tờ, `level_cut` |
| `bu lông vẽ` / `đầu thanh` / `chồng lớp thép` / `tấm đệm` | bu lông, đầu thanh theo bu lông, lớp thép, tấm đệm |
| `chiếu sang 3D` / `ĐỈNH ĐOẠN UỐN` | dựng 3D 4 mặt, thanh cánh nhiều đoạn + thép góc nối trong, bản mã |
| `mặt cắt vách ngang` .. `BẺ CÁNH CỤC BỘ` | vách (đoạn thân: 1/4 rồi xoay), đầu thanh vách 55, gỡ chạm, bẻ cánh |
| (cuối hàm) | `top_bend`, `corner_fix`, ghi scene + báo cáo |

## Khóa cấu hình tờ (`sheets.py`)
| Khóa | Ý nghĩa |
|---|---|
| `box`, `plans`, `faces` | khung mặt đứng; mặt cắt {tên: (y vạch cắt, khung)}; mặt lấy khi ghép 2 kiểu mặt |
| `base` / `no_base` / `on_top_of` | chân cột (sườn đọc từ chi tiết) / không chân / đặt trên tờ khác (bản mã chờ) |
| `level_cut`, `plan_end_cut`, `foot_diag_cut` | vát thanh ngang mặt cột tại mặt cắt; vát đầu thanh vách (DN-01); vát 40x60 chân |
| `top_splice`, `top_kink`, `hidden_inner_plates` | bản mã nối đỉnh; đỉnh uốn thẳng đứng; bản mã nét khuất |
| `bottom_stub`, `leg_splices` | thanh cánh nhiều đoạn: đoạn dưới của tờ khác + mối nối (khe, thép góc nối trong, bản nối, tấm bù, `above` = tiết diện phía trên) |
| `leg_section`, `leg_hidden_ok` | ép tiết diện thanh cánh chính; nhận nét khuất ở đầu thanh cánh (đoạn trên cùng) |
| `xa_keep_horizontal`, `drop_rules` | phần xà: chỉ giữ thanh ngang; bỏ thanh theo tiết diện |
| `trim_to_end_lines`, `banma_join_gap`, `detail_hole_max`, `waiting_holes` | cắt thanh tại nét đầu thanh; nối nét bản mã rời; ngưỡng khớp lỗ chi tiết; lỗ chờ |
| `center_joggle`, `top_bend`, `filler_default_t` | bẻ lệch thanh ngang DT-01; bẻ đầu thanh đỉnh DN-01; dày tấm đệm mặc định |

## Quy ước khi sửa (để không làm hỏng đoạn đã duyệt)
- Sau khi sửa: `python3 tools/bvtc/build.py` rồi so `data/n122/*.json` với `git show HEAD:...` (thanh, bu lông, bản mã
  phải giữ nguyên nếu không cố ý đổi); kiểm chạm 4 mô hình phải 0.
- Tìm cỡ vát mới: dùng `fixes.EndContact` + `fixes.first_ok` (đúng như thử lần lượt, nhanh 10–20 lần).
