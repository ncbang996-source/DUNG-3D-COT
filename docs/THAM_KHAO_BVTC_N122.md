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

## Đợt góp ý cmt.docx (DT-01, lần 2) - quy tắc rút ra

- Ráp DT-01 lên DT-02 (người dùng chốt: bỏ bản đế DT-01). Bản mã chờ ở đỉnh DT-02 = bản mã nối d10 750x290 (chi tiết
  DT-02, hình cắt A-A), có 2 cặp lỗ: cặp dưới cho L90x7 DT-02, cặp trên cho L90x7 DT-01; trong góc thanh cánh có thép
  góc nối HL130x9 dài 750 (vát góc lưng 12x12). DT-01 đọc bản mã này từ tờ DT-02, đặt theo lỗ: 10/10 lỗ trùng bu lông
  chân DT-01 (lệch 0 mm). Khe 2 đầu thanh cánh 10 mm (110 = 50 + 10 + 50); thanh cánh DT-01 vẽ kéo tới mặt bản đế nên
  cắt bớt 56 mm. Cao độ ráp = 9,397 m (cao độ DT-02). Mô hình ghép: `tools/bvtc/merge_segments.py`.
- Thanh cánh DT-02 chỉ lấy nét LIỀN (nét đứt thẳng hàng phía trên là thanh cánh DT-01) -> dừng ở mối nối (z 9,443).
- Thanh cánh cắt ngang (mặt cắt thanh nằm ngang) ở chân, mối nối, đường gãy.
- Lỗ bản mã chi tiết phải trùng bu lông vẽ trên mặt đứng: đặt hình chi tiết rồi khớp cứng theo lỗ -> bu lông đầu thanh
  nằm đúng đường đinh (trước lệch 15-21 mm = "lệch trục" người dùng thấy).
- Vát 40x60 đầu dưới thanh xiên chính chỉ có ở DT-02 (ghi chú tờ DT-02); DT-01 không vát.
- Thanh ngang 1-1 DT-01: không bẻ cục bộ; thanh thẳng nối mặt trong thanh cánh và mặt trong bản mã giữa (lệch 15 mm
  trải đều 2070 mm, 0,42 độ) - người dùng chốt "uốn đều theo chiều dài / ép sát".
- Kiểm tra chạm lấy mẫu dày 3 mm ở 300 mm hai đầu thanh (bước 10 mm bỏ sót chỗ lấn nhỏ ở góc cột). Vát góc mép cánh
  còn lại ở góc cột: vừa đủ hết chạm (người dùng chốt).
- Bu lông đứng (vách ngang) xỏ từ DƯỚI LÊN: đầu bu lông dưới, đai ốc trên; bu lông ngang từ trong ra ngoài.
- Tấm đệm: chiều dày sửa cho vừa khe (2D.20_8 ở khe 20 -> 2 x 10). Tấm đệm sát mép cánh thanh cánh cắt phẳng theo mép.
- Đỉnh DT-01 (đối chiếu DN-02): thanh cánh gãy 8,44 độ tại đầu trên phần nghiêng, phía trên UỐN thẳng đứng 867 mm.
  Bản mã nét khuất = bản mã 301/302 d10 của DN-02 (DN-02 vẽ nét liền ngoài cánh thanh cánh), BẺ GÓC theo đường gãy.
  3 bu lông M24 bắt bản mã vào phần đứng thanh cánh. Lỗ chờ (không đặt bu lông, lắp khi ráp DN-02): 4 lỗ M24 cho
  thanh ngang/xiên DN-02, 6 lỗ M20 nối thanh cánh DN-02.

## Đoạn ngọn DN-02 (dựng: `bash tools/bvtc/build_n122.sh`)

Người dùng đồng ý 4 đề xuất (phạm vi, mặt có xà, B-B, đường tim). Số liệu đọc từ tờ DN-02:
- Đoạn thẳng đứng; z = 0 tại đường gãy thanh cánh (đầu dưới phần đứng DT-01). Tâm 2 thanh cánh cách 1890 (= phần đứng
  DT-01). Số hiệu chi tiết DN-02 là 2xx, DT-01 là 3xx.
- 2 kiểu mặt: mặt có xà (trước/sau, k = 0, 2: L90x7 dài 2840 chìa ra 2 bên + L60x5 chống, bản mã d8 có tai) và mặt bên
  (k = 1, 3). Dựng 2 lần (tờ cấu hình `DN-02`, `DN-02s`) rồi ghép theo mặt (`combine_faces.py`).
- Không dựng: L70x6 nghiêng chìa ra ngoài (thanh xà X1/X2 vẽ cụt), L70x6 chéo lên ở đỉnh (thanh DN-01). Lỗ của chúng
  trên bản mã = lỗ chờ (báo `holes_waiting`). Ghi chú tờ: lỗ bu lông leo trên thanh 201, 203 - không thể hiện.
- Thanh cánh: HL130x9 203/204 từ khe B-B (860 trên đường gãy) tới khe A-A (6260; trước ghi 6240 - lệch 20 mm so với DXF, đã sửa), HL130x9 201/202 từ A-A tới đỉnh 7568.
- Mối nối B-B (chi tiết DN-02): thép góc nối trong HL130x9 (232) dài 670 vát góc lưng 12x12, bản nối ngoài d10 (233)
  145x670, tấm d3 (231) 145x330. Chữ "HL130x12" trong hình B-B ghi nhầm: số hiệu 301 = HL150x12 (thanh cánh DT-01).
  Tấm d3 rộng 145 (> cánh 130) nên nằm NGOÀI, dưới bản d10, trên lưng HL130x9 -> 2 thanh cánh thẳng MẶT TRONG, lưng
  HL130x9 lùi vào 3 mm so với lưng HL150x12 (khác 3 mm so với đề xuất "lưng thẳng hàng" - suy ra từ kích thước chi tiết).
- Mối nối A-A: thép góc nối trong HL120x8 (229) dài 730 vát góc 12x12, bản nối ngoài d10 (230) 100x690.
- Bản mã 228/228a d10 ở chân (bẻ góc theo đường gãy): tấm đủ dựng ở DT-01; DN-02 chỉ giữ phần đứng (đánh dấu ext).
- Bản mã: hình chi tiết nhận khi >= 75% lỗ trùng bu lông vẽ (<= 15 mm); tim bu lông lấy đúng vị trí trên mặt đứng.
  Bản mã vẽ bằng nét LINE rời / bị thanh che đoạn dài: nối đầu nét gần nhất (<= 20 đơn vị), cạnh còn thiếu khép góc vuông.
- Nét kích thước thẳng hàng mép thanh (L90x7 xà) bị đọc thành thanh dài ra: cắt thanh tại nét đầu thanh vẽ rõ.
- Tấm đệm: số tấm theo khe (giữ chiều dày ghi; VD 4D.20_8 ở nút thanh cánh HL130x9 khe 9 -> 1 tấm 8); không ký hiệu ->
  1-2 tấm dày 8/10 vừa khe; tấm dày hơn khe -> giảm chiều dày cho vừa.
- Vách 1-1, 2-2, 3-3 (`dn_plans.py`, không cắt 1/4 rồi xoay vì vách không đối xứng 4 phía): 2 thanh chéo L60x5 suốt
  góc - góc; nét liền chĩa LÊN đặt trên cánh ngang thanh chủ, nét khuất chĩa XUỐNG đặt dưới; tâm 1 bu lông + tấm đệm 6
  (khe = chiều dày cánh thanh chủ: 7 ở 1-1, 2-2 -> ép 1). ĐỀ XUẤT: vát góc cánh chĩa xuống ở đầu thanh vách 1-1, 2-2
  (25x55 .. 60x100) tránh thanh xiên mặt cột đi vào nút góc.
- Ráp lên DT-02 + DT-01: khớp theo 24 bu lông chung (3 bu lông M24 bản mã 228 vào phần đứng x 8). Cao độ ráp 18,525 m;
  đường gãy trong DT-01 thấp hơn 12 mm so với tờ DN-02 (DT-01 lấy theo đường tim).

## Đợt góp ý gop_y_DT-02_20261127 (5 ý) - quy tắc rút ra

- (1) Nút 3 thanh giao nhau: ít nhất 1 thanh chạy thẳng. DT-02 nút giữa (bản mã 418/419): 4 thanh xiên L90x7 đã dừng ở
  bản mã -> thanh ngang L80x6 chạy LIÊN TỤC qua bản mã (trước tách 2 thanh). Bản mã áp lưng thanh ngang (thanh TRONG
  chạy qua). DT-01 (cắt thanh ngang, 2 thanh xiên chạy thẳng) giữ nguyên.
- (2) Phần xà dựng sau: bỏ thanh xiên / chống của xà (L60x5 chống, L70x6 nghiêng) chìa ra ngoài thân cột; giữ thanh ngang
  mặt cột (L90x7 2840, L70x6 2080) đủ chiều dài, giữ bản mã có tai (lỗ của xà = lỗ chờ). Cấu hình `xa_keep_horizontal`.
- (3) App: xoay quanh cấu kiện được chọn (tâm xoay = điểm nhấn trên cấu kiện, chấm cam); nhấn đúp đặt tâm xoay; phím F
  nhìn sát; nút "Xoay quanh cả cột".
- (4) Vát góc thanh vách (đề xuất): vát tới khi khe >= 10 mm với thép quanh góc vách (trừ thanh chủ thanh vách tựa lên);
  không đạt 10 mm thì vừa hết chạm và ghi rõ trong báo cáo (`vach_dn.vat_goc`, `khe_min_mm`).
- (5) Vát góc cột (đề xuất, 2 thanh mặt kề đâm nhau ở góc): tính lại SAU KHI GHÉP 2 kiểu mặt (combine_faces.py) với mặt kề
  thật -> mặt không cấn thì không vát (VD L90x7 1570 mặt bên DN-02).
- Phát hiện khi ráp DN-01: khe mối nối A-A DN-02 trên DXF ở 6255..6265 (trước đặt 6240, lệch 20 mm so với bản nối và bu lông
  vẽ) -> sửa 6260.

## Đoạn ngọn DN-01 (trên cùng; dựng: `bash tools/bvtc/build_n122.sh`, ghép thẳng vào cột, không xuất riêng)

- Tờ DN-01 vẽ lặp phần đỉnh DN-02 (L90x7 1570 -> mối nối A-A HL120x8 -> L70x6 1710). Người dùng chốt: lấy DN-01 thay phần
  trùng phía trên mối nối A-A, trừ thanh ngang L70x6 (234) và thanh xiên L80x6 (214) giữ theo DN-02 (đã thống kê ở DN-02).
  Ghép: `merge_segments.py ... --replace-above` (cao độ theo thép góc nối trong A-A, tinh chỉnh theo bu lông chung).
- 2 kiểu mặt như DN-02 (tờ `DN-01` mặt có xà k = 0, 2; `DN-01s` mặt bên k = 1, 3), vách 1-1, 2-2, 3-3 dựng bằng dn_plans.py
  (vách 1-1 dùng M20).
- Thanh cánh: HL130x9 201/202 (DN-02) từ A-A DN-02 kéo tới mối nối A-A của DN-01 (khe 5112..5122 trên tờ DN-01), phía
  trên L100x7 tới đỉnh (8952). Thanh cánh vẽ gộp (nét lưng chung) -> nhận thanh cánh rộng 100..130 (`leg_section`).
- Mối nối A-A DN-01 (chi tiết 1/10): thép góc nối trong L90x7 dài 550 vát góc lưng 10x10 (tiết diện riêng `L90X7-NOI`),
  bản nối ngoài d8 100x530, tấm d2 70x240. SUY LUẬN (như B-B DN-02): 2 thanh cánh thẳng MẶT TRONG, lưng L100x7 lùi 2 mm
  -> tấm d2 nằm dưới bản nối ngoài, trên lưng L100x7.
- Mặt cắt 1-1: thanh ngang đỉnh L70x6 2080 (mặt có xà) bẻ 2 đầu 300 ra ngoài, dốc 327/1000 (18,1 độ); bản mã đỉnh 117/117a
  bẻ theo, bu lông phần bẻ xoay theo (`top_bend`). Thanh thể hiện 1 thanh, phần bẻ bằng độ sâu theo chiều dài.
- "vát cánh 20x20mm" (1-1), "60x60mm" (2-2): mũi tên chỉ đầu thanh chéo vách ở góc -> vát đầu thanh vách (chọn góc vát
  gỡ được chạm), không vát thanh ngang mặt cột (`plan_end_cut`).
- Thanh ngang xà L90x7 2840 (3-3) chìa qua 2 thanh cánh, đầu thanh không nằm trên thanh chủ: độ sâu theo chỗ cắt thanh cánh
  (NGOÀI áp mặt ngoài bản mã 123 trên thanh cánh).

## Người dùng xác nhận (sau khi dựng DN-01)
- Mối nối A-A DN-01: 2 thanh cánh thẳng mặt trong, lưng L100x7 lùi 2 mm, tấm d2 dưới bản nối ngoài d8 - ĐÃ XÁC NHẬN.
- Vát 20x20 (1-1) / 60x60 (2-2) DN-01 ở đầu thanh chéo vách, chọn góc vát gỡ được chạm - ĐÃ XÁC NHẬN.
- Thanh vách 1-1, 2-2 DN-02 có đầu chỉ đạt khe 2-5 mm (không đạt 10 mm bằng vát) - CHẤP NHẬN.
- Vát góc cột (2 thanh mặt kề đâm nhau) - CHẤP NHẬN đề xuất.

## Xà X1, X2 (tờ 2/6) - người dùng chốt trước khi dựng
- Phạm vi: X1 = 1 bộ ở đỉnh DN-01 (z ~ 32,6 m); X2 giống hệt nhau ở 3 cao độ có thanh L90x7 2840 (DN-01 cắt 3-3
  z ~ 28,1 m; DN-02 z ~ 24,0 m và ~ 20,0 m); tay phải đối xứng tay trái (tờ chỉ vẽ tay trái); chỉ ở 2 mặt có xà.
- Biên dưới X2 (L90x7) ỐP CHỒNG lên đầu thanh L90x7 2840 của thân, bắt chung hàng bu lông 80/80/80/40.
- Bản mã xà: có số hiệu -> theo hình chi tiết; không có -> HỎI từng bản. 2 bản d6 170x270 (5 lỗ) không số hiệu ở chỗ
  biên dưới X2 gặp thanh 2840 (mặt bằng 3-3) -> theo chi tiết X215 (người dùng chốt).
- SỬA (đọc lại mặt bằng 1-1 tờ xà): 2 đầu 300 của thanh L70x6 đỉnh DN-01 bẻ VÀO TRONG (chụm theo 2 biên X1), trước dựng
  nhầm ra ngoài. Đã sửa: đầu thanh lệch vào 93 mm, bản mã 117/117a và bu lông phần bẻ xoay theo.

## Xà X2 - đã dựng (tools/bvtc/xa.py, bước "xa_X2" trong build.py)
- Đọc 4 hình tờ xà: mặt đứng tay trái (X201 biên dưới L90x7, X203 biên trên L70x6, X206 đứng L60x5, X205 chéo L60x5),
  mặt bằng 3-3 (L75x6 đầu xà, L65x5 giữa, 4 chéo L60x5), 4-4 (2 L65x5 mặt phẳng biên trên), 6-6 (2 chéo L50x4 giữa
  2 thanh đứng). Mặt sau / tay phải đối xứng; 3 cao độ z = 20,085 / 24,085 / 28,085 m (đường đinh thanh 2840).
- Lưng thanh mặt xà ở +-1025 (mép cánh 2050, người dùng chốt). TRONG áp mặt trong thép chủ/bản mã: X201, X203 ở d = 0;
  X206 áp mặt trong cánh X201/X203; X205 (NGOÀI): đầu dưới áp mặt ngoài bản mã có tai (DN-01: 123 d8; DN-02: 226 d10),
  đầu trên áp mặt ngoài X203. Mặt bằng 3-3: bản mã X213 (d16), X214, X215 (d6) dưới cánh nằm biên dưới; thanh nét liền
  chĩa lên trên cánh nằm, nét khuất chĩa xuống dưới bản mã. 4-4 áp mặt trên cánh còn lại X203; 6-6: 2 thanh ở 2 mặt cánh
  còn lại X206 (khe ở giao = 5 mm, tấm đệm 1D.16_6 giảm còn 5).
- Bản mã khớp hình chi tiết theo LỖ (8 hướng xoay/lật): lỗ lệch bu lông vẽ 0 mm (X213: 7,5 mm).
- Bu lông: lớp thép tính theo hình học dọc trục; bu lông thân trùng lỗ (4 bu lông 2840 - bản 123) thay bằng bu lông xuyên
  cả X201. Tấm đệm theo ký hiệu ở giao thanh chéo (3D.20_8, 2D.20_8, giảm dày cho vừa khe); khe <= 12 mm không ký hiệu
  (đầu thanh chéo nét liền qua mép cánh biên, bản vẽ ghi 1D.20_6) -> 1 tấm dày bằng khe.
- ĐỀ XUẤT (gỡ chạm): X206 đầu trên vát góc lưng 10x10 (cánh còn lại lùi 10); L50x4 (6-6) vát 15x5 góc lưng / 10x5 mép.
- CHƯA RÕ (hỏi người dùng): 2 lỗ to ở tai bản X213 ngoài lưng biên (lỗ treo?), 2 lỗ trên biên dưới sát đầu xà ngoài
  X213, 2 lỗ giữa L75x6 - hiện để lỗ không bắt bu lông.

## Đợt góp ý gop_y_DT-02_20261127_1721 (16 ý + 3 câu trả lời về lỗ xà) - quy tắc rút ra
- Lỗ chỉ qua 1 lớp thép ở xà X2 = lỗ treo (người dùng xác nhận): tai bản X213 -> bu lông M20 treo chuỗi sứ; 2 lỗ biên
  dưới sát đầu xà + 2 lỗ giữa L75x6 -> bu lông M20 treo chuỗi đỡ lèo dây dẫn (kind "treo").
- Vát góc (gỡ chạm, đề xuất): CHỈ vát TAM GIÁC ở góc mép cánh (không vát vuông / chữ nhật / cắt lùi cả cánh), vừa đủ,
  a <= nửa bề rộng cánh (75% với cánh còn lại không có lỗ); bu lông còn đủ khoảng cách tới mép cắt (21 / 29 / 32 mm
  M16 / M20 / M24, không kém hiện trạng); được vát cánh thanh mặt cột thay vì cắt nhiều thanh vách (lấy phương án cắt ít
  nhất); mỗi đầu thanh tối đa 2 vát tam giác (cut1 + cut1b ở 2 cánh). Vát ghi trên mặt cắt (DN-01 60x60) là cỡ lớn nhất.
  Không vát được -> dời bu lông + đầu thanh vào trong dọc trục (bước 5 mm, giữ khoảng cách mép trên thanh chủ); cuối
  cùng mới vát góc lưng (DN-01 1-1: 1 đầu 25x30 - CẦN XEM).
- Trục bu lông vách 1-1 DT-02 đặt GIỮA cánh nằm thanh mặt cột (30 trên L60) - đường đinh vẽ sát lưng làm thanh vách cấn.
- Kiểm thêm: đầu bu lông + vòng đệm (r 0,9d, cao 0,7d+3), đai ốc (0,8d+3) + đuôi ren, thân bu lông cấn thép
  (check_dt02 "bolts" / "all"). Gỡ: bu lông có thanh trên trục -> xếp lại lớp kẹp (khe <= 10 mm giữa 2 đoạn ghép -> tấm
  đệm vừa khe); thanh khác cấn -> vát tam giác đầu thanh (tools/bvtc/hoan_thien.py).
- Thanh vách thò ra ngoài mặt lưng thanh mặt cột -> vát tam giác phần thò.
- Ghép DN-01: bản mã đoạn dưới phía trên mặt cắt mà đoạn trên không vẽ (219/220 ở cao độ L70x6 1710) -> giữ, đầu thanh
  DN-01 áp mặt ngoài thanh cánh đẩy ra đúng chiều dày bản mã; bu lông trùng lỗ giữ bản kẹp nhiều lớp hơn.
- App: bản mã có chỗ lõm (123, 226) chia tam giác đúng hình (trước tô lấp chỗ lõm).

## Xà X1 - đã dựng (xa.py build_x1), người dùng chốt
- Mặt bên X1 = mặt đứng xoay 18,1 độ quanh chỗ bẻ (x = +-1040, lưng cột); mặt đứng tờ xà là hình thật mặt này. Biên trên
  ốp chồng đoạn bẻ L70x6 đỉnh DN-01 (bản 117 ở giữa, biên trên TRONG áp mặt trong). Biên dưới vào tai bản mã có tai cao độ
  L60x5 1770 - tai bản này bẻ 18,1 độ (top_bend mục 2 trong sheets.py). Lỗ 1 lớp = bu lông treo M20.
- Bản X114 d12 (đầu xà) đặt TRÊN cánh nằm biên trên (biên trên lưng ở trên, cánh đứng thõng xuống; hình 1-1 nét liền).
- ĐỂ LỆCH (người dùng: để xem thực tế): 2 biên dưới / 2 thanh đứng nằm trên 2 mặt xoay ngược nhau -> cánh tựa của thanh
  2-2 lệch 8,6 độ mỗi đầu (gập 8,3, xoắn 2-3), thanh chéo 5-5 lệch 18 độ mỗi đầu. Thanh 2-2 nâng theo pháp tuyến mặt 2-2
  cho khỏi lấn biên; vòng đệm / tấm đệm lún vài mm ở 1 mép (kiểm còn báo ~26 bu lông, ~18 tấm) - chờ người dùng quyết.
- Người dùng chốt (28/11): 2-2 giữ nguyên, BỎ vòng đệm (bu lông 2-2 `no_filler`, qua khe tới 25 mm, ghi `khe_lop_mm`).
  5-5: BẺ CỤC BỘ cánh còn lại 2 thanh đứng X1 18,1 độ tại bu lông thanh chéo (`bends`, vùng b/sin + 10, ramp 40) cho
  nằm trong mặt phẳng x = lưng thanh đứng; thanh chéo L50x4 áp phẳng mặt đó, bu lông dọc x. Chỉ 2 bu lông trên thanh
  chéo lấy từ hình 5-5 (2 bu lông kia = thanh đứng - biên, đã có ở mặt đứng). Còn lại: đầu/đai ốc tì mặt nghiêng tại
  biên dưới (lệch 8,9 độ) ~19 bu lông, 2 chỗ bản 117/117a - L60x5 mặt bằng 1-1.

## Góp ý 28/11 (gop_y_DT-02_20261128_2037.json) - người dùng chốt
- Lỗ chỉ qua 1 lớp thép (trước là bu lông treo M20/M16): CHỈ THỂ HIỆN LỖ (bolt `kind: "lo"`, app vẽ lỗ đen Ø d+2,
  không tính bu lông; thống kê ghi "Lỗ Ø..").
- X114: bỏ cụm 4 lỗ M16 giữa bản (hình 1-1 / chi tiết có vẽ nhưng người dùng xác nhận không có).
- 2-2 X1: thanh ngang L50x4 phía cột (sát thanh đứng) dời 50 mm DỌC BIÊN về phía đầu xà (mỗi đầu trượt theo biên
  của nó). Thanh chéo L60x5 úp xuống MẶT DƯỚI cánh biên dưới (cánh còn lại chĩa xuống); đầu phía cột vát góc lưng
  5x15 / 5x20 tránh tai bản mã 119/119a (CẦN XEM).
- Bu lông vẽ trên mặt đứng nằm trong bản mã có chi tiết nhưng không có lỗ chi tiết nào trong 15 mm (lỗ chi tiết lệch
  mặt đứng > ngưỡng) -> giữ bu lông vẽ (b5_bu_long). Trước bị mất: đầu thanh xiên DN-02 (bản 222/225/227), DN-01.

