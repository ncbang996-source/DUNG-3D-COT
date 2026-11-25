# Dựng 3D cột thép NC111-32

Đọc DXF (hình học thanh) và PDF (nhóm thanh, tiết diện), dựng mô hình 3D thép góc L theo đúng
tiết diện, xem trên trình duyệt (three.js). Yêu cầu gốc: `docs/SPEC.md`.

## Xem nhanh (không cần cài gì)
Tải file **`dist/NC111-32_3D.html`** về máy rồi bấm đúp để mở bằng Chrome, Edge hoặc Firefox.
File này đã chứa sẵn dữ liệu và three.js, không cần server, không cần mạng.
Lưu ý: `web/index.html` KHÔNG mở được bằng bấm đúp, phải chạy qua server (xem bên dưới).

Sau khi sửa dữ liệu hoặc code, đóng gói lại file độc lập:
```bash
npm install
python3 src/run_all.py
node tools/build_standalone.mjs
```

## Chạy nhanh
```bash
pip install -r requirements.txt          # cần thêm pdftotext (poppler-utils)
python3 src/run_all.py                   # giai đoạn 1-5, ghi out/ và web/data/scene.json
python3 -m pytest -q tests               # test tự động
python3 -m http.server 8000 -d web       # rồi mở http://localhost:8000
```
`web/data/scene.json` đã được sinh sẵn trong repo, nên chỉ cần chạy bước cuối để xem.
Thư viện three.js 0.160.0 đã nằm sẵn trong `web/vendor/`, chạy được khi không có mạng.

## Cấu trúc
| Đường dẫn | Nội dung |
|---|---|
| `data/` | File gốc DXF, PDF (không sửa). Tùy chọn `orientation_override.csv` |
| `src/parse_dxf.py` | GĐ1: 3DLINE/TEXT, ghép số thanh (text lệch −0,4 m), nút (nhãn lệch −0,8 m) |
| `src/parse_pdf.py` | GĐ2: bảng nhóm, bảng kết quả, Type (XÑ→XĐ, CÑ→CĐ), bu lông M16/M20/M24 |
| `src/merge.py` | GĐ3: thanh → nhóm → tiết diện, khối lượng A×L×7850 |
| `src/section_library.py` | GĐ4: JIS G3192 (b, t, r1, r2), diện tích/trọng tâm tính từ hình học |
| `src/orientation.py` | GĐ5: hệ trục địa phương, hướng cánh, dịch tim theo đường đinh, kiểm tra cấn |
| `src/run_all.py` | Chạy GĐ1-5, xuất `web/data/scene.json` |
| `src/preview.py` | Ảnh khung dây theo Type |
| `web/` | GĐ6-7: app three.js |
| `tests/` | pytest (GĐ1-5) và `tests/e2e/smoke.mjs` (Playwright, chạy app không cần server) |

## Quy ước hình học (đã thống nhất)
- Tiết diện: thép góc đều cạnh JIS G3192. HL = cùng kích thước với L.
- Đường tim DXF = đường đinh, ở giữa bề rộng cánh (b/2), trên mặt lưng cánh liên kết.
  Thanh cánh C, CĐ: giao hai đường đinh, tức điểm (b/2, b/2) tính từ góc lưng.
- Thanh cánh C, CĐ: lưng quay ra ngoài góc thân, hai cánh nằm trên hai mặt kề nhau.
- Thanh trên mặt cột: lưng ép sát cánh thanh cánh.
  - Cặp chữ X: nhìn từ ngoài vào, thanh đi lên về bên phải nằm NGOÀI (áp mặt ngoài cánh thanh
    cánh), thanh kia nằm TRONG (áp mặt trong). Hai thanh hở nhau bằng chiều dày cánh thanh cánh.
    Cả cụm X lấy tiết diện thanh cánh tại cao độ nút giao.
  - Mọi thanh khác trên mặt cột nằm TRONG. Không tự lật; chỉ tự đổi phía góc lưng nếu bị cấn.
- Thanh vách ngang và xà: cánh liên kết nằm ngang, cánh còn lại chĩa xuống; riêng XAD chĩa LÊN.
  Thanh đứng của xà: cánh liên kết nằm trong mặt đứng song song trục X, chĩa về trục giữa xà.
- Vẫn cấn: dời điểm bắt dọc thanh bị cấn 3d (làm tròn LÊN 5 mm); chỉ giữ nếu gỡ được cấn.
- Bu lông: ít con nhất trong M16/M20/M24, bằng nhau lấy đường kính nhỏ hơn. Một hàng trên đường
  đinh, cách đầu thanh 1,5d, khoảng cách 3d (không vẽ bu lông mối nối thanh cánh).
- Bản mã (`src/plates.py`): ở nút có thanh (không tính thanh cánh) hơn 2 bu lông. Dày = thanh nối
  mỏng nhất làm tròn lên 6/8/10/12/14/16 mm. Hình = bao lồi bu lông + 1,5d. Trên thanh cánh: bản mã
  áp cánh thanh cánh, đầu thanh nối đẩy ra bằng chiều dày bản mã. Nút giao chữ X: một bản đệm lấp
  khe hở (dày = chiều dày cánh thanh cánh).
- Hai đầu thanh cắt vuông, chưa xử lý giao cắt tại nút, chưa có bản mã.
