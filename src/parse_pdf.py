"""Giai đoạn 2: đọc PDF tiết diện (pdftotext -layout).

- Bảng nhóm:  "Gr: [ n ] số số ..." (hai cột song song mỗi dòng).
- Bảng kết quả: mỗi dòng bắt đầu bằng số thanh đại diện, Section, Type, A, L, i, ...
  Cuối dòng là hệ số (dạng 1.014) rồi số bu lông theo cột M16 / M20 / M24.

Chạy:  python3 src/parse_pdf.py data/TIET_DIEN_NC111-32.pdf out/
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Chữ trong PDF dùng bảng mã VNI hiển thị sai: Ñ = Đ, ö = ư ... Chỉ cần chuẩn hóa mã Type.
TYPE_MAP = {"XÑ": "XĐ", "CÑ": "CĐ"}
KNOWN_TYPES = {"G", "X", "XĐ", "XAT", "XAD", "XCS", "C", "CĐ"}

GR_RE = re.compile(r"Gr:\s*\[\s*(\d+)\s*\]\s*((?:\d+\s*)+?)(?=Gr:|$)")
ROW_RE = re.compile(r"^\s*(\d{3,4})\s+(H?L\d+[xX]\d+)\s+(\S+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(.*)$")
FACTOR_RE = re.compile(r"\b\d\.\d{3}\b")


def pdf_text(path: str | Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(path), "-"],
                          check=True, capture_output=True, text=True).stdout


def norm_section(s: str) -> str:
    return s.upper()


def norm_type(t: str) -> str:
    return TYPE_MAP.get(t, t)


def parse_text(txt: str) -> dict:
    groups: dict[int, list[int]] = {}
    results: list[dict] = []
    errors: list[str] = []
    bolt_cols: list[int] | None = None

    for line in txt.splitlines():
        if "Gr:" in line:
            for m in GR_RE.finditer(line):
                g = int(m.group(1))
                mem = [int(x) for x in m.group(2).split()]
                if g in groups:
                    errors.append(f"Nhóm {g} xuất hiện 2 lần")
                groups[g] = mem
            continue
        if "M16" in line and "M20" in line:
            bolt_cols = [line.index("M16"), line.index("M20"), line.index("M24")] if "M24" in line \
                else [line.index("M16"), line.index("M20")]
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        no, sec, typ, A, L, i_, rest = m.groups()
        # Bu lông: các số nguyên sau hệ số dạng x.xxx ở cuối dòng, gán cột theo vị trí ký tự.
        fm = list(FACTOR_RE.finditer(line))
        bolts = {"M16": None, "M20": None, "M24": None}
        if not fm:
            errors.append(f"Thanh {no}: không thấy hệ số/bu lông")
            factor = None
        else:
            f = fm[-1]
            factor = float(f.group())
            for bm in re.finditer(r"\d+", line[f.end():]):
                pos = f.end() + bm.start() + len(bm.group()) - 1  # căn phải theo chữ số cuối
                if bolt_cols:
                    centers = [c + 2 for c in bolt_cols]  # tâm nhãn "M16" (3 ký tự)
                    k = min(range(len(centers)), key=lambda j: abs(centers[j] - pos))
                    key = ["M16", "M20", "M24"][k]
                else:
                    key = "M16"
                if bolts[key] is not None:
                    errors.append(f"Thanh {no}: 2 giá trị bu lông cùng cột {key}")
                bolts[key] = int(bm.group())
        t = norm_type(typ)
        if t not in KNOWN_TYPES:
            errors.append(f"Thanh {no}: Type lạ '{typ}'")
        results.append({
            "rep_member": int(no), "section": norm_section(sec), "section_raw": sec,
            "type": t, "A_cm2": float(A), "L_m": float(L), "i_cm": float(i_),
            "factor": factor, "bolts": bolts, "raw": line.strip(),
        })
    return {"groups": groups, "results": results, "errors": errors}


def check(d: dict) -> dict:
    groups, results = d["groups"], d["results"]
    all_mem = [m for g in groups.values() for m in g]
    dup = sorted({m for m in all_mem if all_mem.count(m) > 1})
    first = {g: mem[0] for g, mem in groups.items()}
    reps = [r["rep_member"] for r in results]
    rep_set = set(reps)
    not_first = [r for r in reps if r not in first.values()]
    groups_no_result = [g for g, f in first.items() if f not in rep_set]
    return {
        "n_groups": len(groups),
        "group_ids_contiguous": sorted(groups) == list(range(1, len(groups) + 1)),
        "n_members": len(all_mem),
        "duplicate_members": dup,
        "n_result_rows": len(results),
        "duplicate_result_rows": sorted({r for r in reps if reps.count(r) > 1}),
        "rep_not_first_of_group": not_first,
        "groups_without_result": groups_no_result,
        "sections": sorted({r["section"] for r in results}),
        "types": sorted({r["type"] for r in results}),
        "errors": d["errors"],
    }


def build(d: dict) -> tuple[list[dict], dict]:
    """groups.json: nhóm + danh sách thanh + dữ liệu kết quả của nhóm.
    sections.json: tiết diện -> A (cm2) theo PDF (kiểm tra nhất quán)."""
    by_rep = {r["rep_member"]: r for r in d["results"]}
    groups_out = []
    for g in sorted(d["groups"]):
        mem = d["groups"][g]
        r = by_rep.get(mem[0])
        groups_out.append({"group": g, "members": mem, **({k: v for k, v in r.items() if k != "raw"} if r else {})})
    sections: dict[str, dict] = {}
    for r in d["results"]:
        s = sections.setdefault(r["section"], {"A_cm2": r["A_cm2"], "A_values": set()})
        s["A_values"].add(r["A_cm2"])
    sec_out = {k: {"A_cm2": v["A_cm2"], "A_consistent": len(v["A_values"]) == 1,
                   "A_values": sorted(v["A_values"])} for k, v in sorted(sections.items())}
    return groups_out, sec_out


def print_report(c: dict, sections: dict) -> None:
    print("=== PDF ===")
    print(f"Số nhóm              : {c['n_groups']}  (đánh số liên tục 1..n: {c['group_ids_contiguous']})")
    print(f"Số thanh trong nhóm  : {c['n_members']}")
    print(f"Thanh trùng nhóm     : {c['duplicate_members'] or 'không'}")
    print(f"Dòng kết quả         : {c['n_result_rows']}  (trùng: {c['duplicate_result_rows'] or 'không'})")
    print(f"Đại diện ≠ thanh đầu : {c['rep_not_first_of_group'] or 'không'}")
    print(f"Nhóm thiếu kết quả   : {c['groups_without_result'] or 'không'}")
    print(f"Type                 : {', '.join(c['types'])}")
    print("Tiết diện (A cm2)    : " + ", ".join(
        f"{k}={v['A_cm2']}" + ("" if v["A_consistent"] else f"(!{v['A_values']})") for k, v in sections.items()))
    for e in c["errors"]:
        print("LỖI:", e)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/TIET_DIEN_NC111-32.pdf"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "out")
    out.mkdir(parents=True, exist_ok=True)
    d = parse_text(pdf_text(src))
    c = check(d)
    groups_out, sec_out = build(d)
    (out / "groups.json").write_text(json.dumps(groups_out, indent=1, ensure_ascii=False))
    (out / "sections.json").write_text(json.dumps(sec_out, indent=1, ensure_ascii=False))
    (out / "pdf_report.json").write_text(json.dumps(c, indent=1, ensure_ascii=False))
    print_report(c, sec_out)
