# Dựng 3D cột thép từ bản vẽ chế tạo (N122) — hướng dẫn cho Claude

Người dùng là kỹ sư kết cấu, soát mô hình 3D theo bản vẽ chế tạo (BVTC). Luôn trả lời **tiếng Việt**.

## Cách làm việc người dùng yêu cầu
- Điều gì không rõ trên bản vẽ: **hỏi lại trước khi làm**, không đoán. Nêu cách hiểu đề xuất kèm ảnh cắt bản vẽ.
- Số liệu lấy **chính xác từ DXF** (toạ độ, hình chi tiết, nhãn), không "gần đúng". Phần phải suy luận thì ghi rõ là suy luận.
- Mô hình phải **không chạm thép** (thép–thép, bản mã–thép), bu lông xuyên đúng các lớp thép. Chạy kiểm tra trước khi báo xong.
- Khi nhắc ảnh người dùng gửi: gọi theo thứ tự trong tin nhắn + mô tả nội dung, không dùng tên file nội bộ.
- Góp ý ưu tiên dạng **file `gop_y_*.json` xuất từ app** (nút "Góp ý" trong file HTML: ghim lên mô hình, tự ghi số thanh /
  bản mã / bu lông, tọa độ mm, mặt, góc nhìn, ảnh). Đọc: `python3 tools/bvtc/read_feedback.py <file.json> <thư mục ảnh>`
  (in từng ý + tách ảnh + in góc nhìn cho `tools/shot.mjs` để chụp lại sau khi sửa). Số thanh trong file = `id` trong scene.
- Góp ý dạng `cmt.docx` (đoạn chữ + ảnh): `unzip`, ghép đoạn văn với `word/media/imageN.png` qua
  `word/_rels/document.xml.rels`.
- Báo kết quả: nêu cái đã sửa theo từng ý góp ý, số liệu đo được, cái còn suy luận/đề xuất cần xác nhận.
- Xong việc: commit + push lên `main` (người dùng làm trên `main`), gửi file `dist/*.html`.

## Dữ liệu
- `data/n122/BVTC_COT_N122-3230.dxf` — bản vẽ chế tạo cột N122 (mọi tờ trong 1 file, toạ độ DXF, tỉ lệ 1/25,
  chi tiết 1/10). Tờ: DT-02, DT-01, DN-02, DN-01 (đã dựng; DN-01 chỉ ghép vào cột, không xuất riêng).
- `data/NC111-32.dxf` + PDF — dự án đầu (cột NC111-32 dựng từ 3DLINE), app gốc `web/`, `src/`.

## Chương trình (bản đồ mã + khóa cấu hình: `docs/BO_DUNG.md` - đọc trước, chỉ mở đúng đoạn mã cần sửa)
- `tools/bvtc/dt02.py` — bộ dựng mọi đoạn thân (tên cũ). Cấu hình tờ trong `tools/bvtc/sheets.py` (`SHEETS`: khung
  mặt đứng, mặt cắt, sườn chân cột, đặc thù tờ). Thêm tờ mới = thêm mục `SHEETS` rồi chạy, xem `brief.py`.
- `tools/bvtc/fixes.py` — bẻ đầu thanh đỉnh, vát góc cột, tìm cỡ vát nhanh (`EndContact`, `first_ok`).
- `tools/bvtc/bvtc_read.py` — đọc mặt đứng 2D thành thanh (nét mép, đường tâm, nét chiều dày, nhãn tiết diện).
- `tools/bvtc/check_dt02.py` — kiểm tra va chạm (khớp đúng hình app dựng: khung lệch, vát, bẻ cánh, bẻ lệch).
- `tools/bvtc/merge_segments.py` — ghép đoạn trên lên đoạn dưới thành 1 mô hình (khớp bản mã nối + bu lông chung);
  `--replace-above`: đoạn trên vẽ lặp phần đỉnh đoạn dưới (DN-01 / DN-02) -> thay phần trên mối nối A-A.
- `tools/bvtc/combine_faces.py`, `tools/bvtc/dn_plans.py` — đoạn 2 kiểu mặt (DN-02): ghép mặt, dựng vách riêng.
- `tools/bvtc/build_n122.sh` (= `build.py`) — dựng TĂNG DẦN cả cột (DT-02, DT-01, DN-02, DN-01), ghép, kiểm chạm,
  đóng gói HTML: chỉ làm lại bước có đầu vào đổi (~80 s khi `--force`, vài giây khi đổi ít). Nhật ký `out/log_*.txt`.
  Cột đủ: `dist/N122_cot_DT-02+DT-01+DN-02+DN-01.html`.
- `tools/bvtc/brief.py <scene>` — in tóm tắt báo cáo dựng (cảnh báo, gỡ chạm, mặt cắt...).
- `tools/bvtc/render_regions.py` — cắt vùng DXF ra PNG để xem bản vẽ.
- `tools/build_standalone.mjs` — đóng gói `web/` + scene JSON thành 1 file HTML (cần `npm install` một lần).
- `tools/shot.mjs` — chụp mô hình từ HTML theo góc camera.
- `web/app.js` — app three.js (vát cánh `cut1/cut2`, bẻ cánh `bends`, bẻ lệch `prof`, tấm đệm `kind: filler`).

## Lệnh
```bash
bash tools/bvtc/build_n122.sh                   # dựng tăng dần + ghép + kiểm + HTML (--force: làm lại tất cả)
D=data/n122/BVTC_COT_N122-3230.dxf
python3 tools/bvtc/dt02.py $D out DT-01          # 1 tờ (5-10 s; DXF đã phân tích lưu ở out/.cache)
python3 tools/bvtc/check_dt02.py out/dt01_scene.json all      # bu lông + thép–thép + bản mã–thép (1 lần nạp)
python3 tools/bvtc/check_dt02.py out/dt01_scene.json clash    # thép–thép: phải "cặp chạm: 0"
python3 tools/bvtc/check_dt02.py out/dt01_scene.json plates   # bản mã–thép: phải "bản mã chạm thép: 0"
cp out/dt01_scene.json data/n122/dt01_scene.json
node tools/build_standalone.mjs data/n122/dt01_scene.json dist/N122_DT-01.html
python3 tools/bvtc/merge_segments.py out/dt02_scene.json out/dt01_scene.json data/n122/dt02_dt01_scene.json   # ghép DT-01 lên DT-02
node tools/build_standalone.mjs data/n122/dt02_dt01_scene.json dist/N122_DT-02+DT-01.html
node tools/shot.mjs dist/N122_DT-01.html <thư mục ảnh> '[{"tag":"tong","t":[0,0,5],"c":[9,-13,9]}]'
python3 tools/bvtc/render_regions.py $D <thư mục ảnh> ten,x0,y0,rong,cao   # cắt bản vẽ (toạ độ DXF)
python3 -m pytest -q
```
Sau khi sửa bộ dựng: chạy `build.py` và so `data/n122/*.json` với `git show HEAD:...` (members/bolts phải giữ
nguyên nếu không cố ý đổi) để không làm hỏng đoạn đã được duyệt.
Tiết kiệm: in tóm tắt (`brief.py`, `check ... all`), không in cả JSON; cắt ảnh bản vẽ vùng nhỏ; chạy lại đúng phần sửa.

## Hệ toạ độ mô hình
Mét; z = 0 tại đầu dưới thanh cánh (mặt trên bản đế); mặt trước y = −h(z). Độ sâu δ (mm) tính từ mặt phẳng qua
đường tim thanh cánh, dương ra ngoài: cánh thanh cánh δ 68..80 (HL150x12, g = 80). 4 mặt giống nhau xoay 90°.

## Quy tắc đã chốt với người dùng (chi tiết: `docs/THAM_KHAO_BVTC_N122.md`)
- Đọc mặt đứng: nét chiều dày KHUẤT → thanh TRONG (cánh còn lại chĩa vào), LIỀN → NGOÀI. Mặt cắt: LIỀN → chĩa LÊN.
- TRONG áp mặt trong thanh chủ/bản mã, NGOÀI áp mặt ngoài; thanh ép sát (cho phép ép vài mm), không thể hiện uốn.
- Bản mã tại thanh cánh áp mặt ngoài cánh. Thanh TRONG có bu lông qua cánh thanh cánh thì ốp mặt trong thanh cánh;
  khe với bản mã lấp bằng tấm đệm (khối "D", ký hiệu `nD.F_T`).
- Bản mã có số hiệu → lấy hình + lỗ từ hình chi tiết (khớp xoay/lật). Bản hàn vuông góc (DT-02 bản 419) chĩa RA NGOÀI.
- Đầu thanh = nét đầu thanh vẽ rõ; nếu khuất thì = bu lông ngoài cùng trên đường đinh + 25/30/40 (M16/20/24).
- Thanh giằng vách: tựa trên/dưới cánh ngang thanh mặt cột; cánh ngang **bẻ cục bộ** thành nằm ngang tại chỗ bắt.
  Tim bu lông cách đầu ngoài thanh ngang 55, chạm thì tăng 5 mm/lần; góc thừa thì vát.
- Vách giao nhau: thanh chĩa LÊN đặt trên thanh chủ, chĩa XUỐNG đặt sát mép dưới.
- DT-01 đặt trên DT-02 (không bản đế); đỉnh DT-01 thanh cánh uốn thẳng đứng, bản mã DN-02 bẻ góc; bu lông đứng xỏ từ dưới lên.
- DN-02: 2 kiểu mặt (mặt có xà trước/sau); không dựng thanh xà; mối nối B-B lưng HL130x9 lùi 3 mm (tấm d3 ngoài).
- Chạm còn lại: vát góc (bội 5 mm, vừa đủ); cái bản vẽ không ghi thì ghi "ĐỀ XUẤT" và báo người dùng.
- 3 thanh giao nhau: ít nhất 1 thanh chạy thẳng (DT-02 nút giữa: thanh xiên dừng ở bản mã -> thanh ngang liền).
- Vát góc thanh vách: khe >= 10 mm với thép quanh góc (trừ thanh chủ). Vát góc cột tính lại sau khi ghép 2 kiểu mặt.
- Phần xà dựng sau: bỏ thanh xiên/chống của xà; giữ thanh ngang mặt cột đủ dài + bản mã có tai (lỗ chờ).
- DN-01 thay phần trùng trên mối nối A-A của DN-02, trừ thanh 214 (L80x6) và 234 (L70x6) giữ theo DN-02.
