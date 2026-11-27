#!/usr/bin/env bash
# Dựng lại toàn bộ cột N122 (DT-02, DT-01, DN-02), ghép, kiểm tra chạm, đóng gói HTML.
# Chạy từ gốc repo: bash tools/bvtc/build_n122.sh
set -euo pipefail
D=data/n122/BVTC_COT_N122-3230.dxf
B=tools/bvtc
python3 $B/dt02.py $D out DT-02 > out/rep_DT-02.txt &
python3 $B/dt02.py $D out DT-01 > out/rep_DT-01.txt &
python3 $B/dt02.py $D out DN-02 > out/rep_DN-02.txt &      # mặt có xà (trước/sau)
python3 $B/dt02.py $D out DN-02s > out/rep_DN-02s.txt &    # mặt bên
wait
python3 $B/combine_faces.py out/dn02_scene.json out/dn02s_scene.json out/dn02_full_scene.json
python3 $B/dn_plans.py $D DN-02 out/dn02_full_scene.json out/dn02_full_scene.json > /dev/null
python3 $B/merge_segments.py out/dt02_scene.json out/dt01_scene.json out/n122_dt02_dt01_scene.json
python3 $B/merge_segments.py out/n122_dt02_dt01_scene.json out/dn02_full_scene.json out/n122_3doan_scene.json DT-01
for f in dt02 dt01 dn02_full n122_dt02_dt01 n122_3doan; do
  echo "== $f"
  python3 $B/check_dt02.py out/${f}_scene.json clash | sed -n 1,2p
  python3 $B/check_dt02.py out/${f}_scene.json plates | sed -n 2p
done
cp out/dt02_scene.json data/n122/dt02_scene.json
cp out/dt01_scene.json data/n122/dt01_scene.json
cp out/dn02_full_scene.json data/n122/dn02_scene.json
cp out/n122_dt02_dt01_scene.json data/n122/dt02_dt01_scene.json
cp out/n122_3doan_scene.json data/n122/dt02_dt01_dn02_scene.json
node tools/build_standalone.mjs data/n122/dt02_scene.json dist/N122_DT-02.html
node tools/build_standalone.mjs data/n122/dt01_scene.json dist/N122_DT-01.html
node tools/build_standalone.mjs data/n122/dn02_scene.json dist/N122_DN-02.html
node tools/build_standalone.mjs data/n122/dt02_dt01_scene.json "dist/N122_DT-02+DT-01.html"
node tools/build_standalone.mjs data/n122/dt02_dt01_dn02_scene.json "dist/N122_DT-02+DT-01+DN-02.html"
