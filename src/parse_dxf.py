"""Giai đoạn 1: đọc DXF (AC1009), lấy 3DLINE lớp Beam, TEXT lớp BeamNo/NodeNo.

Ghép số thanh với đường theo khoảng cách nhỏ nhất từ text tới trung điểm thanh,
gộp đầu thanh trùng tọa độ thành nút và so với nhãn NodeNo. Không tự sửa dữ liệu,
chỉ báo cáo chênh lệch.

Chạy:  python3 src/parse_dxf.py data/NC111-32.dxf out/
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

NODE_TOL = 1e-3
MATCH_TOL = 1e-3


def mode_offset(texts, points, nd: int = 3) -> tuple[float, float, float]:
    """Độ lệch (text - điểm) xuất hiện nhiều nhất trên mọi cặp."""
    cnt: dict[tuple, int] = {}
    for tp in texts:
        for q in points:
            off = tuple(round(a - b, nd) for a, b in zip(tp, q))
            cnt[off] = cnt.get(off, 0) + 1
    return max(cnt, key=cnt.get) if cnt else (0.0, 0.0, 0.0)


def read_entities(path: str | Path) -> list[dict]:
    """Trả về danh sách entity trong mục ENTITIES, mỗi entity là dict mã nhóm -> giá trị."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    pairs = [(lines[i].strip(), lines[i + 1].rstrip("\r")) for i in range(0, len(lines) - 1, 2)]
    ents: list[dict] = []
    in_entities = False
    cur: dict | None = None
    for k, (code, val) in enumerate(pairs):
        if code == "2" and k > 0 and pairs[k - 1] == ("0", "SECTION"):
            in_entities = val.strip() == "ENTITIES"
            continue
        if not in_entities:
            continue
        if code == "0":
            if cur is not None:
                ents.append(cur)
            cur = None if val.strip() in ("ENDSEC", "EOF") else {"type": val.strip()}
            if val.strip() == "ENDSEC":
                in_entities = False
        elif cur is not None:
            cur[code] = val.strip()
    if cur is not None:
        ents.append(cur)
    return ents


def _xyz(e: dict, a: str, b: str, c: str) -> tuple[float, float, float]:
    return (float(e[a]), float(e[b]), float(e.get(c, 0.0)))


def dist(p, q) -> float:
    return math.dist(p, q)


def parse(path: str | Path) -> dict:
    ents = read_entities(path)
    lines = [e for e in ents if e["type"] == "3DLINE" and e.get("8") == "Beam"]
    beam_txt = [e for e in ents if e["type"] == "TEXT" and e.get("8") == "BeamNo"]
    node_txt = [e for e in ents if e["type"] == "TEXT" and e.get("8") == "NodeNo"]

    segs = [(_xyz(e, "10", "20", "30"), _xyz(e, "11", "21", "31")) for e in lines]
    mids = [tuple((a + b) / 2 for a, b in zip(p1, p2)) for p1, p2 in segs]
    texts = [(int(e["1"]), _xyz(e, "10", "20", "30")) for e in beam_txt]

    # Độ lệch text so với trung điểm: ước lượng bằng mode của mọi cặp (text, trung điểm),
    # rồi ghép mỗi text với trung điểm gần nhất sau khi trừ độ lệch.
    beam_off = mode_offset([tp for _, tp in texts], mids)
    report: dict = {"errors": [], "warnings": [], "beam_text_offset": list(beam_off)}
    match: dict[int, int] = {}
    match_d: dict[int, float] = {}
    used: dict[int, int] = {}
    for num, tp in texts:
        target = tuple(a - o for a, o in zip(tp, beam_off))
        ds = sorted((dist(target, m), i) for i, m in enumerate(mids))
        d0, i0 = ds[0]
        if d0 > MATCH_TOL:
            report["errors"].append(f"Text {num}: không có trung điểm nào khớp (gần nhất {d0:.4f} m)")
        if len(ds) > 1 and ds[1][0] - d0 < 1e-6:
            report["errors"].append(f"Text {num}: hai đường cách đều nhau ({d0:.4f})")
        if i0 in used:
            report["errors"].append(f"Đường #{i0} bị ghép trùng: {used[i0]} và {num}")
        used[i0] = num
        match[num] = i0
        match_d[num] = d0

    members = []
    for num in sorted(match):
        p1, p2 = segs[match[num]]
        members.append({
            "id": num,
            "p1": [round(v, 4) for v in p1],
            "p2": [round(v, 4) for v in p2],
            "length": round(dist(p1, p2), 4),
            "text_dist": round(match_d[num], 4),
        })

    # Nút: gộp đầu thanh trùng tọa độ.
    nodes: list[list[float]] = []

    def node_of(p) -> int:
        for i, q in enumerate(nodes):
            if dist(p, q) <= NODE_TOL:
                return i
        nodes.append(list(p))
        return len(nodes) - 1

    for m in members:
        m["n1"] = node_of(m["p1"])
        m["n2"] = node_of(m["p2"])

    # Nhãn nút: text đặt lệch so với nút một độ lệch cố định (ước lượng bằng mode).
    node_labels = [(int(e["1"]), _xyz(e, "10", "20", "30")) for e in node_txt]
    common_off = mode_offset([tp for _, tp in node_labels], nodes)
    labels_of_node: dict[int, list[int]] = {}
    unmatched_labels = []
    for lab, tp in node_labels:
        target = tuple(a - o for a, o in zip(tp, common_off))
        i = min(range(len(nodes)), key=lambda k: dist(nodes[k], target))
        if dist(nodes[i], target) > NODE_TOL:
            unmatched_labels.append(lab)
            continue
        labels_of_node.setdefault(i, []).append(lab)
    multi = {i: v for i, v in labels_of_node.items() if len(v) > 1}
    for i, v in multi.items():
        report["warnings"].append(f"Nút {[round(c, 4) for c in nodes[i]]} có {len(v)} nhãn: {sorted(v)}")
    label_of_node = {i: min(v) for i, v in labels_of_node.items()}
    node_list = [{"idx": i, "xyz": [round(v, 4) for v in p], "label": label_of_node.get(i),
                  "all_labels": sorted(labels_of_node.get(i, []))}
                 for i, p in enumerate(nodes)]
    for m in members:
        m["node1"] = label_of_node.get(m["n1"])
        m["node2"] = label_of_node.get(m["n2"])

    ids = [m["id"] for m in members]
    report.update({
        "n_lines": len(lines),
        "n_beam_texts": len(texts),
        "n_node_texts": len(node_labels),
        "n_members": len(members),
        "id_min": min(ids) if ids else None,
        "id_max": max(ids) if ids else None,
        "ids_unique": len(set(ids)) == len(ids),
        "ids_missing": sorted(set(range(min(ids), max(ids) + 1)) - set(ids)) if ids else [],
        "lines_unmatched": sorted(set(range(len(segs))) - set(used)),
        "max_text_dist": max(match_d.values()) if match_d else None,
        "n_nodes_from_geometry": len(nodes),
        "node_label_offset": list(common_off),
        "nodes_with_multiple_labels": len(multi),
        "node_labels_unmatched": unmatched_labels,
        "nodes_without_label": [i for i in range(len(nodes)) if i not in label_of_node],
        "zero_length_members": [m["id"] for m in members if m["length"] < 1e-6],
    })
    return {"members": members, "nodes": node_list, "report": report}


def print_report(r: dict) -> None:
    print("=== DXF ===")
    print(f"3DLINE lớp Beam      : {r['n_lines']}")
    print(f"TEXT BeamNo          : {r['n_beam_texts']}")
    print(f"Thanh đã ghép        : {r['n_members']}  (id {r['id_min']}..{r['id_max']}, duy nhất={r['ids_unique']})")
    print(f"Id thiếu trong dãy   : {r['ids_missing'] or 'không'}")
    print(f"Đường chưa ghép text : {r['lines_unmatched'] or 'không'}")
    print(f"Độ lệch text BeamNo  : {r['beam_text_offset']}")
    print(f"Sai số ghép lớn nhất : {r['max_text_dist']:.6f} m")
    print(f"Nút từ hình học      : {r['n_nodes_from_geometry']}")
    print(f"TEXT NodeNo          : {r['n_node_texts']}  (độ lệch nhãn {r['node_label_offset']})")
    print(f"Nhãn nút không khớp  : {r['node_labels_unmatched'] or 'không'}")
    print(f"Nút không có nhãn    : {len(r['nodes_without_label'])}")
    print(f"Nút có nhiều nhãn    : {r['nodes_with_multiple_labels']}")
    print(f"Thanh dài 0          : {r['zero_length_members'] or 'không'}")
    for e in r["errors"]:
        print("LỖI:", e)
    for w in r["warnings"]:
        print("CẢNH BÁO:", w)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/NC111-32.dxf"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "out")
    out.mkdir(parents=True, exist_ok=True)
    res = parse(src)
    (out / "members.json").write_text(json.dumps(res["members"], indent=1))
    (out / "nodes.json").write_text(json.dumps(res["nodes"], indent=1))
    (out / "dxf_report.json").write_text(json.dumps(res["report"], indent=1, ensure_ascii=False))
    print_report(res["report"])
