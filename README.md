# Dựng 3D cột thép NC111-32

Xem yêu cầu chi tiết trong `docs/SPEC.md`.

## Cấu trúc
- `data/`: file gốc (DXF, PDF). Không sửa.
- `src/parse_dxf.py`: giai đoạn 1, đọc DXF, ghép số thanh và số nút.
- `src/parse_pdf.py`: giai đoạn 2, đọc bảng nhóm và bảng kết quả trong PDF.
- `src/merge.py`: giai đoạn 3, ghép thanh với tiết diện, thống kê khối lượng.
- `src/preview.py`: vẽ nhanh khung dây theo Type để soát bằng mắt.
- `tests/`: test tự động.
- `out/`: kết quả sinh ra (không đưa lên git).

## Chạy
```bash
python3 src/parse_dxf.py data/NC111-32.dxf out/
python3 src/parse_pdf.py data/TIET_DIEN_NC111-32.pdf out/
python3 src/merge.py out/
python3 -m pytest -q tests
```
Cần `pdftotext` (poppler-utils), Python 3.10 trở lên, `pytest`, và `matplotlib` cho `preview.py`.
