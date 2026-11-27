"""Dựng cột N122 TĂNG DẦN: bước nào đầu vào không đổi (nội dung file mã + DXF + cấu hình tờ) thì dùng lại kết quả cũ.

Chạy:  python3 tools/bvtc/build.py            # chỉ làm lại phần thay đổi
       python3 tools/bvtc/build.py --force    # làm lại tất cả
Dấu từng bước lưu ở out/.stamp/ (xóa thư mục này = làm lại tất cả). Mỗi tờ ~1,3 GB bộ nhớ: chạy tối đa 3 tờ song song.
Kết quả: data/n122/*.json, dist/*.html; kiểm chạm in tóm tắt (đầy đủ ở out/check_<tên>.txt).
"""
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = "tools/bvtc"
DXF = "data/n122/BVTC_COT_N122-3230.dxf"
OUT = ROOT / "out"
STAMP = OUT / ".stamp"
FORCE = "--force" in sys.argv
CODE = [f"{B}/dt02.py", f"{B}/bvtc_read.py", f"{B}/check_dt02.py", f"{B}/fixes.py", "src/section_library.py"]
TAG = {"DT-02": "dt02", "DT-01": "dt01", "DN-02": "dn02", "DN-02s": "dn02s", "DN-01": "dn01", "DN-01s": "dn01s"}

sys.path.insert(0, str(ROOT / B))
from sheets import SHEETS  # noqa: E402

_fh = {}


def fhash(p):
    p = ROOT / p
    k = (str(p), p.stat().st_mtime_ns, p.stat().st_size)
    if k not in _fh:
        _fh[k] = hashlib.sha1(p.read_bytes()).hexdigest()
    return _fh[k]


def key_of(files, extra=""):
    h = hashlib.sha1(extra.encode())
    for f in files:
        h.update(f.encode() + fhash(f).encode())
    return h.hexdigest()


def sheet_cfg(name):
    """Cấu hình tờ + các tờ nó tham chiếu + khung mọi tờ (khung dùng để loại hình chi tiết)."""
    c = SHEETS[name]
    refs = {k: SHEETS[v["sheet"]] for k, v in c.items() if isinstance(v, dict) and v.get("sheet") in SHEETS}
    return json.dumps({"cfg": c, "refs": refs, "boxes": {k: v["box"] for k, v in SHEETS.items()}},
                      sort_keys=True, default=str)


def step(name, cmd, deps, outs, extra=""):
    """Chạy cmd nếu đầu vào đổi hoặc thiếu đầu ra. Trả về True nếu đã chạy."""
    STAMP.mkdir(parents=True, exist_ok=True)
    k = key_of(deps, extra + " ".join(cmd))
    st = STAMP / (name + ".key")
    if not FORCE and st.exists() and st.read_text() == k and all((ROOT / o).exists() for o in outs):
        print(f"  = {name} (không đổi)")
        return False
    t = time.time()
    log = OUT / f"log_{name}.txt"
    with open(log, "w") as f:
        r = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        print(f"  ! {name} LỖI - xem {log.relative_to(ROOT)}")
        print("".join(log.read_text().splitlines(True)[-15:]))
        sys.exit(1)
    st.write_text(key_of(deps, extra + " ".join(cmd)))    # băm lại: đầu ra có thể là đầu vào bước khác
    print(f"  + {name} ({time.time() - t:.0f} s)")
    return True


def main():
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    py = sys.executable
    print("1. Dựng từng tờ")
    # lần đầu (chưa có out/.cache): phân tích DXF 1 lần trước khi chạy song song
    if not any((OUT / ".cache").glob("dxf_*.pkl")):
        subprocess.run([py, "-c", f"import sys; sys.path.insert(0, '{B}'); import dt02; dt02.read_dxf_cached('{DXF}')"],
                       cwd=ROOT, check=True)
    jobs = [(sh, [py, f"{B}/dt02.py", DXF, "out", sh], CODE + [DXF, f"{B}/sheets.py"],
             [f"out/{TAG[sh]}_scene.json"], sheet_cfg(sh)) for sh in TAG]
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda j: step("to_" + j[0], j[1], j[2], j[3], j[4]), jobs))
    print("2. Ghép 2 kiểu mặt + vách (DN-02, DN-01)")
    for t in ("dn02", "dn01"):
        sh = t.upper().replace("DN0", "DN-0")
        step(f"ghep_mat_{t}", [py, f"{B}/combine_faces.py", f"out/{t}_scene.json", f"out/{t}s_scene.json",
                               f"out/{t}_comb_scene.json"],
             [f"out/{t}_scene.json", f"out/{t}s_scene.json", f"{B}/combine_faces.py"] + CODE, [f"out/{t}_comb_scene.json"])
        step(f"vach_{t}", [py, f"{B}/dn_plans.py", DXF, sh, f"out/{t}_comb_scene.json", f"out/{t}_full_scene.json"],
             [f"out/{t}_comb_scene.json", f"{B}/dn_plans.py", f"{B}/sheets.py"] + CODE, [f"out/{t}_full_scene.json"])
    print("3. Ghép các đoạn")
    M = f"{B}/merge_segments.py"
    step("ghep_dt02_dt01", [py, M, "out/dt02_scene.json", "out/dt01_scene.json", "out/n122_dt02_dt01_scene.json"],
         ["out/dt02_scene.json", "out/dt01_scene.json", M], ["out/n122_dt02_dt01_scene.json"])
    step("ghep_dn02", [py, M, "out/n122_dt02_dt01_scene.json", "out/dn02_full_scene.json", "out/n122_3doan_scene.json",
                       "DT-01"], ["out/n122_dt02_dt01_scene.json", "out/dn02_full_scene.json", M],
         ["out/n122_3doan_scene.json"])
    step("ghep_dn01", [py, M, "out/n122_3doan_scene.json", "out/dn01_full_scene.json", "out/n122_4doan_scene.json",
                       "--replace-above"], ["out/n122_3doan_scene.json", "out/dn01_full_scene.json", M],
         ["out/n122_4doan_scene.json"])
    print("4. Kiểm chạm (cột đủ + DN-02 đủ - phần đỉnh DN-02 được thay trong cột đủ)")
    checks = [("dt02", "out/dt02_scene.json"), ("dt01", "out/dt01_scene.json"), ("dn02", "out/dn02_full_scene.json"),
              ("cot", "out/n122_4doan_scene.json")]

    def chk(c):
        return step("kiem_" + c[0], [py, f"{B}/check_dt02.py", c[1], "all"], [c[1], f"{B}/check_dt02.py"], [])
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(chk, checks))
    bad = False
    for n, _ in checks:
        lines = (OUT / f"log_kiem_{n}.txt").read_text().splitlines()
        summ = [x for x in lines if x.startswith(("bu lông xuyên", "cặp chạm", "bản mã chạm"))]
        print(f"   {n}: " + " | ".join(summ))
        bad |= any(not x.endswith(": 0") for x in summ)
    print("5. Chép dữ liệu + đóng gói HTML")
    pairs = [("out/dt02_scene.json", "data/n122/dt02_scene.json", "dist/N122_DT-02.html"),
             ("out/dt01_scene.json", "data/n122/dt01_scene.json", "dist/N122_DT-01.html"),
             ("out/dn02_full_scene.json", "data/n122/dn02_scene.json", "dist/N122_DN-02.html"),
             ("out/n122_dt02_dt01_scene.json", "data/n122/dt02_dt01_scene.json", "dist/N122_DT-02+DT-01.html"),
             ("out/n122_3doan_scene.json", "data/n122/dt02_dt01_dn02_scene.json", "dist/N122_DT-02+DT-01+DN-02.html"),
             ("out/n122_4doan_scene.json", "data/n122/n122_scene.json", "dist/N122_cot_DT-02+DT-01+DN-02+DN-01.html")]
    for src, dst, html in pairs:
        if fhash(src) != (fhash(dst) if (ROOT / dst).exists() else None):
            (ROOT / dst).write_bytes((ROOT / src).read_bytes())
        step("html_" + Path(html).stem, ["node", "tools/build_standalone.mjs", dst, html],
             [dst, "tools/build_standalone.mjs", "web/app.js", "web/index.html", "web/style.css"], [html])
    print(f"Xong {time.time() - t0:.0f} s" + ("  -- CÒN CHẠM, xem out/log_kiem_*.txt" if bad else ""))
    sys.exit(2 if bad else 0)


if __name__ == "__main__":
    main()
