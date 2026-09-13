"""번역을 한 장짜리 표로 뽑는다. 스프레드시트에 올려 제안을 받기 위한 것.

JSON과 구분자 텍스트를 사람이 읽기는 어렵다. 특히 번역 제안을 주시는 분은
파일 형식을 모르셔도 되어야 한다. 그래서 원문과 지금 번역을 나란히 놓고
'제안' 칸을 비워 둔 CSV를 만든다.

돌려받는 길도 있다. 제안이 적힌 CSV를 내려받아 tools/import_sheet.py에
넣으면 원래 자리에 도로 넣어 준다. '열쇠' 칸이 그 자리를 가리키므로
표에서 행을 지우거나 열쇠를 고치지 말 것.

  python tools/export_sheet.py            -> release/translation-sheet.csv
  python tools/export_sheet.py --out 경로
"""
import argparse
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATION = os.path.join(ROOT, "translation")
EXTRACTED = os.path.join(ROOT, "extracted")
TEXTASSETS = os.path.join(TRANSLATION, "textassets")

HEADER = ["갈래", "파일", "열쇠", "어디에 나오는가", "원문", "지금 번역", "제안", "남길 말"]

# 그림 사양에는 원문이 들어 있지 않다. 게임에서 원본 버튼으로 견주는 수밖에 없다.
IMAGE_NOTE = "(그림. 게임에서 원본 버튼으로 견주십시오)"


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def locations():
    """locate_text.py가 남긴 쪽 정보. 없으면 빈 채로 간다."""
    data = load_json(os.path.join(EXTRACTED, "text_locations.json"), {})
    where = {}
    for page, items in (data or {}).items():
        for text in items:
            where.setdefault(text, page)
    return where


def ui_rows(where):
    rows = []
    ui = load_json(os.path.join(TRANSLATION, "ui.json"), {})
    keep = load_json(os.path.join(TRANSLATION, "ui_keep_original.json"), {}) or {}
    for source, target in ui.items():
        if source.startswith("_"):
            continue
        if not target.strip():
            # 일부러 원문으로 둔 것. 왜 두었는지를 적어 두어야 다시 묻지 않는다.
            reason = keep.get(source)
            if reason:
                rows.append(["화면 문구", "translation/ui.json", source,
                             where.get(source, ""), source, "(원문 유지)", "",
                             f"일부러 두었습니다 - {reason}"])
            continue
        rows.append(["화면 문구", "translation/ui.json", source,
                     where.get(source, ""), source, target, "", ""])
    return rows


def dynamic_rows():
    rows = []
    data = load_json(os.path.join(TRANSLATION, "dynamic.json"), {}) or {}
    for source, target in data.items():
        if source.startswith("_") or not target.strip():
            continue
        rows.append(["시스템 문구", "translation/dynamic.json", source, "",
                     source, target, "", ""])
    return rows


def textasset_rows():
    """번역본과 원문을 줄 번호로 맞춰 세운다. 줄 수는 손대지 않으므로 맞는다."""
    rows = []
    manifest = load_json(os.path.join(TEXTASSETS, "_manifest.json"), {}) or {}
    records = load_json(os.path.join(EXTRACTED, "textassets_translate.json"), [])
    if not records:
        print("  (!) extracted/textassets_translate.json이 없어 대사는 건너뜁니다.")
        print("      tools/extract_text.py를 먼저 돌리십시오.")
        return rows

    originals = {r["source"]: r["text"] for r in records}

    for file_name, info in sorted(manifest.items()):
        path = os.path.join(TEXTASSETS, file_name)
        original = originals.get(info["source"])
        if original is None or not os.path.exists(path):
            continue
        with io.open(path, encoding="utf-8", newline="") as f:
            translated = f.read()

        before = original.replace("\r\n", "\n").split("\n")
        after = translated.replace("\r\n", "\n").split("\n")
        if len(before) != len(after):
            print(f"  (!) {file_name}: 줄 수가 원문과 다릅니다. 건너뜁니다.")
            continue

        for index, (source, target) in enumerate(zip(before, after)):
            if source == target or not target.strip():
                continue
            rows.append(["대사·웹페이지", f"translation/textassets/{file_name}",
                         str(index), info.get("name", ""), source, target, "", ""])
    return rows


def image_rows():
    rows = []
    base = os.path.join(TRANSLATION, "images")
    for folder, label in ((base, "단서"), (os.path.join(base, "manual"), "설명서")):
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".json"):
                continue
            spec = load_json(os.path.join(folder, name), {})
            rel = os.path.relpath(os.path.join(folder, name), ROOT).replace("\\", "/")
            for key in ("blocks", "texts", "overlays"):
                for index, entry in enumerate(spec.get(key, [])):
                    text = entry.get("text", "")
                    if not text.strip():
                        continue
                    rows.append(["그림", rel, f"{key}[{index}]",
                                 f"{label} {os.path.splitext(name)[0]}",
                                 IMAGE_NOTE, text, "", ""])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(ROOT, "release", "translation-sheet.csv"))
    args = parser.parse_args()

    where = locations()
    rows = ui_rows(where) + dynamic_rows() + textasset_rows() + image_rows()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    # 엑셀이 UTF-8을 알아보게 BOM을 붙인다. 구글 시트도 그대로 읽는다.
    with io.open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row[0]] = counts.get(row[0], 0) + 1
    for kind, count in counts.items():
        print(f"  {kind:12s} {count}줄")
    print(f"\n  모두 {len(rows)}줄 -> {args.out}")


if __name__ == "__main__":
    main()
