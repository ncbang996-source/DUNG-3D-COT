# SPEC: App dựng 3D cột thép NC111-32 (thanh thép góc L)

## 1. Mục tiêu
Đọc DXF (hình học thanh) + PDF (nhóm thanh, tiết diện) rồi dựng mô hình 3D, mỗi thanh hiện đúng tiết diện thép góc L (cánh, chiều dày), xem xoay/zoom được, bấm vào thanh xem thông tin.

## 2. Dữ liệu đã có (đã kiểm tra)
- `NC111-32.dxf` (AC1009, 25.250 dòng): 664 `3DLINE` lớp `Beam` (2 đầu x,y,z), 664 `TEXT` lớp `BeamNo` (số thanh 561..1224), 238 `TEXT` lớp `NodeNo`. Các lớp Plate/Solid/PropertyName rỗng.
- `TIET_DIEN_NC111-32.pdf` (7 trang, có lớp chữ):
  - Bảng nhóm: 146 nhóm, 664 thanh, không thiếu, không trùng.
  - Bảng kết quả: 146 dòng, mỗi dòng là thanh đầu tiên của nhóm. Có Section, Type, A (cm²), Lef, Nmax/Nmin, bu lông M16/M20/M24.
- Liên kết: thanh -> nhóm -> tiết diện. Khớp 100%.
- Tiết diện xuất hiện: L50X4, L60X5, L65X5, L70X6, L80X6, L90X7, L100x7, HL120X8, HL130X12, HL150X12, HL175X12.
- Đối chiếu A với bảng thép góc đều cánh: khớp (L90X7=12.22, L50X4=3.89, HL175X12=40.52...). Nghĩa là HL = thép góc đều cánh cùng kích thước, cần người dùng xác nhận.

## 3. Thông tin còn thiếu (cần người dùng quyết trước khi dựng)
1. **Hướng cánh L của từng thanh**: không có trong DXF lẫn PDF. Đây là điểm chặn.
2. **Vị trí tim thanh so với tiết diện**: đường tim DXF là trọng tâm tiết diện hay đường chuẩn (mép lưng/đường đinh)?
3. **Ý nghĩa mã Type**: G, X, XĐ (XÑ), XAT, XAD, XCS, C, CĐ (CÑ).
4. Kích thước chi tiết tiết diện (b, t, bán kính góc r, trọng tâm): lấy từ bảng thép góc tiêu chuẩn nào (TCVN/GOST/khác)?
5. Phạm vi dựng: chỉ thanh, hay cả bản mã, bu lông, nút? (file không có bản mã/bu lông; chỉ có số bu lông theo thanh.)
6. Đơn vị DXF: dự kiến mét (cao ~20 đến 22,7). Cần xác nhận.

## 4. Quy trình thực hiện (giao Claude Code theo từng giai đoạn, xong giai đoạn nào kiểm giai đoạn đó)

### Giai đoạn 0. Khởi tạo
- Tạo repo, thư mục `data/` (đặt DXF, PDF), `src/`, `tests/`, `README.md`.
- Chọn công nghệ (đề xuất: Python xử lý dữ liệu + three.js hiển thị web, hoặc app một file HTML). Hỏi người dùng nếu cần.
- Không tự đoán các mục ở mục 3. Nếu thiếu, dừng và hỏi.

### Giai đoạn 1. Đọc DXF
- Parser đọc ENTITIES, lấy 3DLINE (lớp Beam) và TEXT (BeamNo, NodeNo).
- Ghép số thanh với đường: text BeamNo nằm gần trung điểm thanh; lập hàm ghép theo khoảng cách nhỏ nhất và kiểm tra không ghép trùng.
- Đầu ra `members.json`: id, p1, p2, chiều dài.
- Kiểm tra: đủ 664 thanh, id duy nhất 561..1224, mỗi text ghép đúng 1 đường.
- Nút: gộp đầu thanh trùng tọa độ (dung sai 1e-3) tạo danh sách nút; so với NodeNo (238) và báo chênh lệch, không tự sửa.

### Giai đoạn 2. Đọc PDF
- Dùng `pdftotext -layout` hoặc `pdfplumber`. Lưu ý chữ tiếng Việt trong PDF bị lỗi mã (Ñ = Đ, ö = ư...). Chuẩn hóa mã Type.
- Bảng nhóm: regex `Gr: [ n ] số số ...`, hai cột song song mỗi dòng.
- Bảng kết quả: mỗi dòng bắt đầu bằng số thanh đại diện, Section, Type, A, Lef...
- Đầu ra `groups.json`, `sections.json`.
- Kiểm tra: 146 nhóm, 664 thanh, 146 dòng kết quả, thanh đại diện = thanh đầu mỗi nhóm.

### Giai đoạn 3. Ghép dữ liệu
- Mỗi thanh nhận: nhóm, tiết diện, Type, A, số bu lông.
- Kiểm tra mọi thanh trong DXF có tiết diện; báo cáo thanh thiếu.

### Giai đoạn 4. Thư viện tiết diện
- File `section_library.json`: tên, b, t, r, vị trí trọng tâm (cx, cy).
- Kiểm tra: diện tích tính từ hình học ≈ A trong PDF (sai lệch < 1%). Nếu lệch, báo người dùng.

### Giai đoạn 5. Hệ trục địa phương và hướng cánh
- Trục thanh: p1 -> p2. Dựng hệ trục địa phương (x dọc trục).
- Hướng cánh theo quy tắc người dùng chọn: (a) bảng CSV gán theo thanh/nhóm, hoặc (b) quy tắc hình học (ví dụ góc quay quanh trục thanh theo hướng ra ngoài thân cột). Mặc định không có, phải hỏi.
- Hỗ trợ ghi đè hướng từng thanh qua file `orientation_override.csv` và nút lật/xoay trong app.
- Dịch tim theo mục 3.2.

### Giai đoạn 6. Dựng mesh
- Tạo profile L (đa giác 6 cạnh, có thể thêm bo góc r) rồi đùn dọc thanh. Hai đầu thanh để cắt vuông (chưa xử lý giao cắt nút).
- Mỗi tiết diện một màu; hiển thị lưới nút, số thanh bật/tắt.

### Giai đoạn 7. Giao diện
- Xoay, zoom, pan; bấm thanh hiện: số thanh, nhóm, tiết diện, Type, chiều dài, A, khối lượng.
- Lọc theo nhóm hoặc tiết diện, hiện mặt cắt L.
- Xuất bảng thống kê khối lượng theo tiết diện (A x L x 7850 kg/m³).

### Giai đoạn 8. Kiểm tra nghiệm thu
- Số thanh dựng = 664; tổng khối lượng so với tính độc lập từ bảng.
- Soát bằng mắt: 4 thanh cột góc, thanh xiên, thanh giằng, đối xứng 4 mặt.
- Test tự động cho parser DXF, parser PDF, ghép dữ liệu.

## 5. Ràng buộc cho Claude Code
- Khi dữ liệu không rõ thì hỏi lại, không đoán.
- Không sửa file gốc trong `data/`.
- Mọi kiểm tra ở mỗi giai đoạn phải in kết quả rõ ràng (số lượng, thanh lỗi).
