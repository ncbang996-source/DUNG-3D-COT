#!/usr/bin/env bash
# Dựng lại toàn bộ cột N122 (DT-02, DT-01, DN-02, DN-01), ghép, kiểm tra chạm, đóng gói HTML.
# Chạy từ gốc repo: bash tools/bvtc/build_n122.sh
set -euo pipefail
D=data/n122/BVTC_COT_N122-3230.dxf
B=tools/bvtc
mkdir -p out
python3 $B/dt02.py $D out DT-02 > /dev/null   # lần đầu: phân tích DXF, lưu out/.cache cho các lần sau
# chạy 3 tờ một lượt (6 lượt song song vượt bộ nhớ máy ảo)
run3() {
  local pids=()
  for sh in "$@"; do python3 $B/dt02.py $D out $sh > out/rep_$sh.txt & pids+=($!); done
  for p in "${pids[@]}"; do wait "$p"; done                          # dừng nếu một lần dựng lỗi
}
run3 DT-02 DT-01 DN-02          # DN-02 / DN-01: mặt có xà (trước/sau)
run3 DN-02s DN-01 DN-01s        # DN-02s / DN-01s: mặt bên
python3 $B/combine_faces.py out/dn02_scene.json out/dn02s_scene.json out/dn02_full_scene.json
python3 $B/combine_faces.py out/dn01_scene.json out/dn01s_scene.json out/dn01_full_scene.json
python3 $B/dn_plans.py $D DN-02 out/dn02_full_scene.json out/dn02_full_scene.json > out/rep_DN-02_vach.txt &
python3 $B/dn_plans.py $D DN-01 out/dn01_full_scene.json out/dn01_full_scene.json > out/rep_DN-01_vach.txt &
wait
python3 $B/merge_segments.py out/dt02_scene.json out/dt01_scene.json out/n122_dt02_dt01_scene.json
python3 $B/merge_segments.py out/n122_dt02_dt01_scene.json out/dn02_full_scene.json out/n122_3doan_scene.json DT-01
# DN-01: tờ vẽ lặp phần đỉnh DN-02 -> lấy DN-01 thay phần trên mối nối A-A (trừ thanh 214, 234 của DN-02)
python3 $B/merge_segments.py out/n122_3doan_scene.json out/dn01_full_scene.json out/n122_4doan_scene.json --replace-above
for f in dt02 dt01 dn02_full dn01_full n122_4doan; do
  echo "== $f"
  python3 $B/check_dt02.py out/${f}_scene.json clash | sed -n 1,2p
  python3 $B/check_dt02.py out/${f}_scene.json plates | sed -n 2p
done
cp out/dt02_scene.json data/n122/dt02_scene.json
cp out/dt01_scene.json data/n122/dt01_scene.json
cp out/dn02_full_scene.json data/n122/dn02_scene.json
cp out/n122_dt02_dt01_scene.json data/n122/dt02_dt01_scene.json
cp out/n122_3doan_scene.json data/n122/dt02_dt01_dn02_scene.json
cp out/n122_4doan_scene.json data/n122/n122_scene.json
node tools/build_standalone.mjs data/n122/dt02_scene.json dist/N122_DT-02.html
node tools/build_standalone.mjs data/n122/dt01_scene.json dist/N122_DT-01.html
node tools/build_standalone.mjs data/n122/dn02_scene.json dist/N122_DN-02.html
node tools/build_standalone.mjs data/n122/dt02_dt01_scene.json "dist/N122_DT-02+DT-01.html"
node tools/build_standalone.mjs data/n122/dt02_dt01_dn02_scene.json "dist/N122_DT-02+DT-01+DN-02.html"
node tools/build_standalone.mjs data/n122/n122_scene.json "dist/N122_cot_DT-02+DT-01+DN-02+DN-01.html"
