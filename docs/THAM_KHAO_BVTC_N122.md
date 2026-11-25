# Tham khảo bản vẽ chế tạo cột N122-23(30) / N122-32(30)

Nguồn: `BVTC_COT_N122-3230.dxf` (AC1032, 6 tờ A1: ghi chú chung, xà X1/X2, đoạn ngọn DN-01, DN-02,
đoạn thân DT-01, DT-02). Bản vẽ 2D, tỉ lệ chung 1/25, chi tiết 1/10.

## 1. Quy định trong ghi chú chung (mục 1.4, 1.5)

| Hạng mục | M16 | M20 | M24 |
|---|---|---|---|
| Tim bu lông tới đầu thanh, thanh giằng (min) | 25 | 30 | 40 |
| Tim bu lông tới đầu thanh, thanh chính (min) | 35 | 45 | 50 |
| Tim bu lông tới mép thanh, thanh giằng (min) | 21 | 29 | 32 |
| Khoảng cách 2 tâm bu lông, thanh giằng (min) | 50 | 60 | 70 |
| Lỗ khoan | Ø17 | Ø21 | Ø25 |

- Đường đinh (tim bu lông tới sống thanh) khi không ghi kích thước = b/2 (L50: 25, L60: 30, L65: 33).
- Ký hiệu bu lông `S.F_D`: S con, đường kính F, dài D (vd `4.20_60`).
- Ký hiệu tấm đệm `nD.F_D`: n tấm, cho bu lông F, dày D (vd `2D.20_8`). Tấm đệm vuông 45×45 mm
  hoặc theo vòng đệm phẳng TCVN 2061.
- Lắp dựng: đầu bu lông có đai ốc quay RA NGOÀI cột.
- Thanh giằng chéo vát góc 45° trên cánh (đoạn không khoan lỗ). Có vát cánh 25×25, 30×30 mm ở góc.
- Bu lông leo (C*): bắt trên 2 thanh chính chéo nhau.
- Thép HL (b ≥ 120) là SS540; L (b < 120) và thép tấm là SS400.

## 2. Quan sát chi tiết (tờ DT-01)

- **Nút thanh cánh có thanh xiên**: có BẢN MÃ (vd `d 8` = bản mã dày 8) bắt vào thanh cánh bằng
  3 bu lông (`3.20_70`); mỗi thanh xiên chỉ 2 bu lông (`4.20_60` cho 2 thanh) cùng 2 tấm đệm
  (`2D.20_10`). Tức là bản mã dùng cả khi mỗi thanh giằng chỉ có ≤ 2 bu lông.
- **Nút giao chữ X**: chỉ 1 bu lông (`1.20_70`) + tấm đệm (`2D.20_8`), không có bản mã.
  Tấm đệm dày 8 = khe hở giữa hai thanh xiên.
- **Đỉnh đoạn thân (chỗ gãy độ dốc thanh cánh)**: bản mã lớn, bu lông M24, mối nối thanh cánh
  bu lông so le 2 hàng (đường đinh 45 và 50 từ mép).
- **Mặt bằng vách ngang (mặt cắt 1-1)**: thanh L65×5 / L50×4, đầu thanh UỐN ("trục uốn" cách góc
  300 mm) để áp vào cánh thanh cánh, vát cánh 25×25 ở góc; mỗi đầu 1 bu lông M16 (`1.16_40`),
  nút giao giữa vách 3 bu lông (`3.16_40`).
- Bản mã đế (chân cột) có chi tiết hàn A, B, bản mã đế bu lông neo.

## 3. Đọc tự động mặt đứng (tools/bvtc/members2d.py)

Cách đọc: mỗi thanh thép góc trên mặt đứng (nhìn TỪ NGOÀI vào, tỉ lệ 1/25) gồm 2 nét mép, 1 đường
tâm (CENTER) và 1 nét chiều dày cánh còn lại sát mép LƯNG. Nét chiều dày là nét KHUẤT (HIDDEN) khi
cánh còn lại chĩa vào trong (thanh nằm TRONG), là nét LIỀN khi cánh chĩa ra ngoài (thanh nằm NGOÀI).
Phía có nét chiều dày là phía góc lưng.

### Kết quả DT-01 (đoạn thân trên)
| Loại thanh | Trong/ngoài | Góc lưng | Số thanh |
|---|---|---|---|
| Thanh cánh HL150x12 | cánh còn lại vào trong | lưng ra góc ngoài | 5 đoạn |
| Chéo chữ X đi lên về bên TRÁI | NGOÀI | trên | 4 |
| Chéo chữ X đi lên về bên PHẢI | TRONG | trên | 4 |
| Thanh ngang | TRONG | trên | 3 |

- Đường tâm thanh xiên = đường đinh b/2 (L80: 40, L90: 45, L60: 30).
- Các đường tâm thanh xiên và thanh ngang gặp nhau ĐÚNG trên đường tâm thanh cánh.
- Đường tâm thanh cánh HL150x12 cách lưng 80 mm (không phải 75); mối nối thanh cánh có thêm 2 đường
  đinh 50 và 95 mm (bu lông so le).

### Kết quả DT-02 (đoạn chân, giằng chữ K / chữ A, không có cặp chữ X)
| Loại thanh | Trong/ngoài | Góc lưng | Số thanh |
|---|---|---|---|
| Thanh cánh HL150x12 | vào trong | ra góc ngoài | 3 |
| Thanh ngang | TRONG | trên | 7 |
| Thanh xiên (L60-L90) | TRONG | trên | 9 |
| Thanh xiên chính chữ A L100x7 | TRONG | DƯỚI | 2 |
| Thanh phụ L50x4 | NGOÀI | dưới | 2 |
| Thanh phụ L65x5 | NGOÀI | trên | 1 |

## 4. Dựng lại đoạn thân DT-02 (tools/bvtc/dt02.py) — bản để góp ý

Mô hình N122 tự động trước đó đã bỏ. Dựng lại riêng DT-02, kiểm từng phần bằng ảnh chồng nét CAD
(`docs/kiemtra_DT-02_matdung.png`, `docs/kiemtra_DT-02_matcat.png`). Xem 3D: `dist/N122_DT-02.html`.

- Mặt đứng: 19/21 thanh (2 thanh toàn nét khuất là thanh phía sau, bỏ), 4 mặt xoay 90°.
  Thanh cánh HL150x12 liền, đường tim cách lưng 80 mm; cao độ 0 = đầu dưới thanh cánh.
- Ở DT-02 các thanh KHÔNG đồng quy một điểm trên thanh cánh: bắt so le (cách 100 mm), phần lớn bắt
  thẳng vào cánh thanh cánh 1 bu lông (1.16_50, 3.16_50), không bản mã.
- Bản mã theo bản vẽ: nút giữa mặt (8.20_60 + 4.20_60) và mối nối đỉnh đoạn (d10, ngoài cánh thanh cánh,
  hình cắt A-A). Bu lông lấy theo khối M16/M20/M24 trên mặt đứng.
- Độ sâu mỗi đầu thanh theo thanh chủ: TRONG áp mặt trong, NGOÀI áp mặt ngoài; ở nút có bản mã thì áp bản mã.
- Vách ngang 1-1, 3-3, 4-4: tam giác giằng góc; 2-2: 1/4 vách (chéo góc, hình thoi nối trung điểm mặt,
  vòng vuông L70x6) — cắt theo 1/4 rồi xoay 4 góc.
- Vách ngang: bu lông đọc từ mặt cắt (19 con / 1/4, xoay 4 góc); mặt cắt không vẽ bản mã (thanh vách bắt trực tiếp).
- Bản mã mối nối đỉnh đoạn (2 bên, trên thanh cánh) giữ lại; 29 bu lông bỏ là của hình chi tiết bản mã (12) và
  hình khai triển thanh cánh (17) - xem `docs/DT-02_chu_thich.png`.
- Thanh L60x5 dựng đứng trong khoang K trên (từ thanh ngang L80x6 z=5,8 m lên thanh xiên L90x7 z=7,6 m):
  đầu thanh cách đường tim thanh chủ 35-50 mm (bản vẽ ghi) -> dung sai tìm thanh chủ 62 mm.
- Chân cột (chi tiết DT-02): bản đế 450x450x40, 4 bu lông neo Ø56 (lỗ Ø64) cách mép 100, 2 sườn d12 áp lưng 2 cánh
  thanh cánh, nghiêng theo thanh cánh (hình sườn lấy gần đúng 515 x 420, vát về 100 hai đầu).
