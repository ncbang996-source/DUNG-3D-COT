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
