# Dựng 3D cột thép NC111-32

Đọc DXF (hình học thanh) và PDF (nhóm thanh, tiết diện), dựng mô hình 3D thép góc L theo đúng
tiết diện, xem trên trình duyệt (three.js). Yêu cầu gốc: `docs/SPEC.md`.

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
- Thanh trên mặt ngoài thân: cánh liên kết nằm trong mặt cột, cánh còn lại hướng vào trong.
- Thanh vách ngang và xà: cánh liên kết nằm ngang, cánh còn lại chĩa xuống. Riêng thanh đứng
  của xà: cánh liên kết nằm trong mặt đứng song song trục X, cánh còn lại chĩa về trục giữa xà.
- Bị cấn thép (ngoài vùng nút, bán kính max(b) + 3 cm) thì lần lượt thử: đổi phía góc lưng,
  lật ra ngoài (lên). Chọn theo NHÓM để giữ đối xứng. Kết quả: `out/orientation_report.json`.
- Ghi đè: `data/orientation_override.csv` gồm hai cột `id,variant`, với variant ∈ `in+ in- out+ out-`.
  App có nút tải file này sau khi sửa hướng trên giao diện.
- Bu lông: ưu tiên số lượng ít nhất trong ba cột M16/M20/M24.
- Hai đầu thanh cắt vuông, chưa xử lý giao cắt tại nút, chưa có bản mã.
