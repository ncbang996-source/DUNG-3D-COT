"""Đọc file góp ý xuất từ app (nút "Tải file góp ý"): in danh sách, tách ảnh, in góc nhìn để chụp lại.

Chạy: python3 tools/bvtc/read_feedback.py <gop_y_*.json> [thư mục ảnh]
- In mỗi góp ý: số, nội dung, đối tượng (thanh số / bản mã / bu lông), mặt, tọa độ (mm), cao độ.
- Ghi ảnh chụp kèm theo ra <thư mục ảnh>/gopy_<số>.jpg (mặc định: out/gopy).
- In chuỗi JSON góc nhìn cho tools/shot.mjs để chụp lại đúng chỗ sau khi sửa.
"""
import base64
import json
import sys
from pathlib import Path


def main(path, outdir="out/gopy"):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Mô hình: {data.get('model', '')} · xuất lúc {data.get('exported', '')} · {len(data['items'])} góp ý\n")
    views = []
    for it in data["items"]:
        t = it["target"]
        extra = {k: v for k, v in t.items() if k not in ("text",) and v is not None}
        print(f"[{it['no']}] {it['text']}")
        print(f"    đối tượng: {t['text']}")
        print(f"    chi tiết : {json.dumps(extra, ensure_ascii=False)}")
        print(f"    vị trí   : {it['face']} · tọa độ {it['point_mm']} mm · cao độ {it['point_mm'][2]} mm")
        img = it.get("image")
        if img and img.startswith("data:image"):
            f = out / f"gopy_{it['no']}.jpg"
            f.write_bytes(base64.b64decode(img.split(",", 1)[1]))
            print(f"    ảnh      : {f}")
        print()
        views.append({"tag": f"gopy_{it['no']}_sau_sua", "t": it["camera"]["target"], "c": it["camera"]["position"]})
    print("Góc nhìn để chụp lại (tools/shot.mjs):")
    print(json.dumps(views, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out/gopy")
