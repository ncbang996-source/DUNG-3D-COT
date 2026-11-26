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
- Đầu thanh = đầu thanh THẬT vẽ trên bản vẽ (đã cách bu lông ngoài cùng đúng khoảng cách), không kéo tới nút
  lý thuyết -> hết thanh đâm xuyên nhau ở nút.
- Chân cột: đọc đúng từ DXF (chi tiết 1/10): bản đế 450x450x40, lưng thanh cánh cách mép ngoài 200; 4 lỗ neo Ø64
  tại 100/350; sườn 1 (545x490, 13 lỗ), sườn 3 (345x490, 13 lỗ), sườn 2 (260x490, không lỗ). Vị trí sườn 1, 3
  khớp lỗ với bu lông chân thanh cánh trên mặt đứng (lệch <= 5 mm); suy ra lưng thanh cánh cách đường tim 79,5 mm
  (bản vẽ ghi 80). Mặt đứng: mặt trên bản đế = đầu dưới thanh cánh = đáy sườn (cao độ 0). Cạnh xiên sườn 2 (độ dốc
  = độ nghiêng thanh cánh) áp dọc mặt ngoài sườn 1 -> đáy sườn 2 dài 188 (khớp mặt bằng), đỉnh rộng 260 (khớp chi tiết).
- Bỏ 24 bu lông mặt cắt không nằm trên thanh nào (cách trục > 100 mm).
- Bu lông: chiều dài theo ký hiệu S.F_D gần nhất cùng đường kính (chọn L ngắn nhất >= kẹp + đai ốc + đệm);
  thân xuyên qua các lớp thép (kẹp tính theo thanh + thanh chủ/bản mã), đầu bu lông phía trong, đai ốc ra ngoài.
  Chân cột: 13 lỗ mỗi sườn theo chi tiết D322/D323 (10 lỗ 12.20_70 kẹp sườn + cánh thanh cánh, 3 lỗ 3.20_60 kẹp
  sườn + thanh xiên chính áp mặt trong sườn).
- Vát cánh theo ghi chú: 40x60 đầu dưới thanh xiên chính (bắt sườn chân cột); 45x45 đầu 4 thanh xiên L90x7 tại bản mã giữa
  (mũi tên ghi chú chỉ vào thanh xiên, KHÔNG phải thanh ngang - đã sửa);
  30x30 (mặt cắt 1-1, 3-3, 4-4) và 45x45 (2-2) ở cánh nằm ngang của thanh ngang mặt cột tại thanh cánh.
- Quy tắc (người dùng xác nhận): ở liên kết, thanh luôn ÉP SÁT bản mã/thanh chủ, mặt tiếp xúc trùng khít; độ uốn nhẹ
  trên chiều dài thanh không ghi trên bản vẽ và không cần thể hiện. Mô hình: mỗi đầu thanh có độ sâu riêng = mặt tiếp
  xúc, thanh nối thẳng giữa hai đầu (xiên tối đa 0,16° với L90x7 dài 6,6 m; 0,9° với thanh ngắn nhất 836 mm);
  sai lệch mặt tiếp xúc trên vùng bu lông < 1 mm.
- Đầu thanh tối thiểu = tim bu lông ngoài cùng + khoảng cách tới đầu thanh (25/30/40) khi nét vẽ đầu thanh bị khuất
  sau thanh cánh (32 đầu thanh được kéo dài; thanh ngang giờ tới cách lưng thanh cánh 55 mm).
- Thanh giằng vách đặt TRÊN cánh nằm ngang của thanh ngang mặt cột (theo mặt cắt, bắt 1.16_40); bu lông kẹp
  thanh giằng + cánh ngang.
- Mặt cắt vách: đường tâm thanh ngang mặt cột = đường đinh CÁNH NẰM NGANG (nơi bắt thanh giằng), nằm lệch vào trong
  mặt cột một đoạn = độ sâu lưng thanh ngang - đường đinh (L60x5: 68 - 30 = 38 mm; L80x6: 68 - 40 = 28 mm).
  Đã kiểm: mọi bu lông đầu thanh giằng vách nằm trên cánh ngang của thanh ngang.
- Đầu thanh giằng vách tại đầu NGOÀI thanh ngang (mặt cắt ghi "140 | 55"): tim bu lông cách đầu thanh ngang 55 mm;
  nếu thanh giằng chạm thép thì tăng 60, 65... (dời bu lông + đầu thanh giằng vào phía góc) tới khi hết chạm
  (người dùng chốt). Kết quả DT-02 (kiểm chạm 2 chiều theo đúng hình thanh): 4-4 = 65, 3-3 = 65/70, 1-1 = 100.
  Góc cánh ngang thanh ngang còn chạm thì vát (DT-02: không có chỗ nào cần).


## Đợt góp ý cmt.docx (5 ý) - quy tắc rút ra

- Bu lông: lớp thép kẹp lấy theo HÌNH HỌC đã dựng (mọi cánh liên kết / bản mã / cánh thanh cánh có lỗ tại tim bu lông),
  không đoán theo thanh gần nhất; kiểm các lớp phải liền nhau. Độ sâu thanh tại điểm bắt = nội suy dọc thanh chủ
  (thanh thẳng), lan truyền lặp tới khi ổn định -> 2 thanh TRONG bắt vào thanh xiên L90x7 (nút cao độ 1-1) ốp đúng
  mặt trong L90x7, thanh NGOÀI ốp mặt ngoài.
- Nét mép thanh vẽ đứt nhiều đoạn (bị thanh khác cắt qua / bản mã che) được cộng dồn. Thanh có đường tâm liền nhưng
  nét mép ngắt tại bản mã (thanh ngang L80x6 qua bản mã giữa) = 2 thanh, mỗi thanh dừng ở bản mã.
- Bản mã giữa mặt: hình dạng + lỗ lấy theo HÌNH CHI TIẾT (số hiệu 418: 340x420 d10, 12 lỗ), tâm chi tiết trùng tâm
  bản mã trên mặt đứng. Dải hẹp vẽ trong bản mã (419: 80x420 d8, có ký hiệu hàn) = bản hàn VUÔNG GÓC
  -> người dùng chốt: chĩa RA NGOÀI, từ mặt ngoài bản mã 418. Bản mã áp lưng các thanh TRONG.
- Vát cánh 45x45 tại bản mã giữa: góc đầu thanh sát bản hàn là góc LƯNG -> cắt tam giác 45x45 ở góc lưng cánh liên
  kết, cánh còn lại lùi 45 mm (đúng hình góc cắt vẽ trên mặt đứng).
- Đầu thanh vẽ rõ (có nét đầu thanh vuông góc trục) thì giữ nguyên; chỉ kéo dài theo bu lông khi đầu thanh bị khuất,
  và chỉ tính bu lông nằm TRÊN đường đinh của thanh (bu lông nối thanh cánh không tính) -> hết đầu L90x7 trên cùng
  chồng lên cánh thanh cánh.
- Vách giao nhau (2-2): thanh có cánh còn lại chĩa LÊN đặt TRÊN cánh nằm ngang thanh chủ, chĩa XUỐNG đặt SÁT MÉP DƯỚI
  (thanh xiên từ góc nằm trên thanh xiên lớn, 2 thanh L70x6 sát dưới thanh xiên lớn). Thanh chạy qua trục đối xứng
  (L70x6 1406 + 1406) ghép thành 1 thanh. Đầu thanh vách = bu lông ngoài cùng + 25/30/40 mm.
- Mặt cắt: đường đinh cánh nằm ngang thanh mặt cột đọc ngay trên mặt cắt (không lấy theo mặt đứng).
- Cánh nằm ngang thanh mặt cột vuông góc mặt cột (nghiêng ~8,4° theo độ xiên mặt cột). Người dùng chốt (ảnh cột mẫu
  Dz 110kV Hồng Ngự - Vĩnh Hưng): tại chỗ thanh giằng vách bắt vào, BẺ CÁNH CỤC BỘ quanh mép lưng thành mặt phẳng song
  song mặt đất. Mô hình: vùng phẳng = vết thanh giằng trên cánh + 10 mm mỗi bên (~165 mm), chuyển tiếp 40 mm mỗi bên;
  thanh giằng tựa phẳng, hết hở tại bu lông (36 chỗ: 1-1, 2-2, 3-3, 4-4 x 4 mặt).
- Bản 419 chĩa RA NGOÀI (người dùng chốt).
- Gỡ chạm còn lại bằng vát góc (bội 5 mm): góc đầu thanh vách 2-2 lấn vào cánh thanh cánh / bản mã 418 (10x10, 20x20);
  ĐỀ XUẤT (bản vẽ không ghi): 2 thanh L70x6 hai mặt kề nhau bắt vào thanh cánh cùng cao độ 2-2, cánh còn lại đâm nhau
  ở góc cột -> vát góc mép cánh còn lại 45x70 mm.
- Kiểm tra tự động (tools/bvtc/check_dt02.py): thép-thép, bản mã-thép, bu lông xuyên dọc cánh = 0.

## Đoạn thân DT-01 (dựng cùng chương trình: `python3 tools/bvtc/dt02.py <dxf> out DT-01`)

- Cấu hình tờ trong `SHEETS` (khung mặt đứng, mặt cắt 1-1, sườn chân cột đọc từ chi tiết 1/10: 515x420 (10 lỗ),
  250x420, 315x420 (10 lỗ); bản đế 450x450x40). Vị trí lưng thanh cánh ở chân cột tìm bằng cách khớp lỗ sườn với bu
  lông chân cột trên mặt đứng (lệch TB 2,4 mm; bu lông mặt đứng cao hơn lỗ sườn 14 mm khi đặt đáy sườn trên bản đế).
- Bản mã nút: lấy hình chi tiết theo số hiệu (311, 312, 313, 314), đặt khớp đường bao + lỗ (xoay/lật gương).
  Nét bản mã vẽ rời (bị thanh che) được ghép thành đường bao kín.
- Người dùng xác nhận:
  - (A) "trục uốn" mặt cắt 1-1: 2 nửa thanh ngang L65x5 bẻ lệch 15 mm (đoạn 300 mm đầu thanh ốp mặt trong thanh cánh)
    để đoạn giữa áp vừa mặt trong bản mã giữa 312.
  - (B) nút giữa: thanh xiên ngoài - bản mã 312 - thanh xiên trong; 2 nửa thanh ngang sau bản mã, không chạm thanh xiên trong.
    Thanh xiên trong/ngoài ép sát bản mã tại nút giữa (thêm 1 điểm độ sâu giữa thanh).
  - (C) thanh xiên TRONG có bu lông qua cánh thanh cánh -> ốp mặt trong thanh cánh; tấm đệm (khối "D" = vòng nét đứt,
    Ø44-48) tại bu lông ngoài mép thanh cánh: 1 tấm 10 mm/bu lông (khe 12, ép 2). Giao chữ X: "2D" = 2 tấm chồng nhau.
- Nút đầu trên: bản mã vẽ nét khuất (nối đoạn trên) dựng như bản mã nút thanh cánh, dày 10 SUY LUẬN (khe giao chữ X
  ngay dưới = 2 đệm 10). 4 khối D ở nút này không có ký hiệu -> lấy 1 tấm 10.
- Đề xuất (bản vẽ không ghi): 2 thanh xiên TRONG của 2 mặt kề nhau cùng ốp mặt trong thanh cánh tại một nút -> cánh
  còn lại đâm nhau ở góc cột -> vát góc mép cánh còn lại (25x70, 35x45, 50x45 mm).
