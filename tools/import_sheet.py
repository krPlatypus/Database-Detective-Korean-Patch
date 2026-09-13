"""스프레드시트에서 받은 제안을 원래 자리에 도로 넣는다.

export_sheet.py가 만든 표에 '제안' 칸을 채워 돌려받았을 때 쓴다.
'열쇠' 칸이 그 글이 있던 자리를 가리키므로, 표에서 열쇠를 고쳤거나
행을 지웠다면 그 줄은 넣지 못하고 건너뛴다.

넣기 전에 '지금 번역' 칸이 파일의 현재 내용과 같은지 본다. 다르면
표를 뽑은 뒤에 그 자리를 이미 고쳤다는 뜻이므로, 남의 손을 덮어쓰지
않도록 건너뛰고 알려 준다.

  python tools/import_sheet.py 받은표.csv --dry-run   무엇이 바뀔지만 본다
  python tools/import_sheet.py 받은표.csv             실제로 넣는다

넣은 뒤에는 다시 묶어야 게임에 들어간다.

  python tools/build_translation.py
  python tools/build_clue_images.py     (그림을 고쳤다면)
"""
import argparse
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SLOT = re.compile(r"^(blocks|texts|overlays)\[(\d+)\]$")

applied, skipped = [], []


def skip(row_number, why):
    skipped.append(f"{row_number}행: {why}")


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    # 끝에 줄바꿈을 붙이지 않는다. 기존 파일이 그렇게 되어 있어, 붙이면
    # 한 줄 고칠 때마다 파일 끝이 같이 바뀐 것으로 나온다.
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def put_mapping(path, key, current, proposal, row_number, dry):
    data = load(path)
    if key not in data:
        skip(row_number, f"'{key[:40]}...'를 {os.path.basename(path)}에서 찾지 못했다")
        return
    if data[key] != current:
        skip(row_number, f"'{key[:40]}...'는 표를 뽑은 뒤에 이미 바뀌었다")
        return
    if not dry:
        data[key] = proposal
        save(path, data)
    applied.append(f"{os.path.basename(path)}  {key[:40]}")


def put_line(path, index, current, proposal, row_number, dry):
    with io.open(path, encoding="utf-8", newline="") as f:
        raw = f.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    trailing = raw.endswith(newline)
    lines = raw.split(newline)
    if trailing:
        lines = lines[:-1]

    if not 0 <= index < len(lines):
        skip(row_number, f"{os.path.basename(path)}에 {index}번 줄이 없다")
        return
    if lines[index] != current:
        skip(row_number, f"{os.path.basename(path)} {index}번 줄은 이미 바뀌었다")
        return
    if not dry:
        lines[index] = proposal
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(newline.join(lines) + (newline if trailing else ""))
    applied.append(f"{os.path.basename(path)}  {index}번 줄")


def put_slot(path, key, current, proposal, row_number, dry):
    found = SLOT.match(key)
    if not found:
        skip(row_number, f"그림 열쇠 모양이 아니다: {key}")
        return
    group, index = found.group(1), int(found.group(2))
    spec = load(path)
    entries = spec.get(group, [])
    if not 0 <= index < len(entries):
        skip(row_number, f"{os.path.basename(path)}에 {key}가 없다")
        return
    if entries[index].get("text") != current:
        skip(row_number, f"{os.path.basename(path)}의 {key}는 이미 바뀌었다")
        return
    if not dry:
        entries[index]["text"] = proposal
        save(path, spec)
    applied.append(f"{os.path.basename(path)}  {key}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="제안이 채워진 CSV")
    parser.add_argument("--dry-run", action="store_true", help="넣지 않고 무엇이 바뀔지만 본다")
    args = parser.parse_args()

    with io.open(args.csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for number, row in enumerate(rows, start=2):
        proposal = (row.get("제안") or "").strip()
        if not proposal:
            continue

        rel = (row.get("파일") or "").strip()
        key = (row.get("열쇠") or "")
        current = row.get("지금 번역") or ""
        path = os.path.join(ROOT, *rel.split("/"))

        if not os.path.exists(path):
            skip(number, f"파일이 없다: {rel}")
            continue

        if rel.endswith("ui.json") or rel.endswith("dynamic.json"):
            put_mapping(path, key, current, proposal, number, args.dry_run)
        elif "/textassets/" in rel:
            if not key.strip().isdigit():
                skip(number, f"줄 번호가 아니다: {key}")
                continue
            put_line(path, int(key), current, proposal, number, args.dry_run)
        elif "/images/" in rel:
            put_slot(path, key.strip(), current, proposal, number, args.dry_run)
        else:
            skip(number, f"어디에 넣을지 모르겠다: {rel}")

    head = "넣을 것" if args.dry_run else "넣었다"
    print(f"  {head} {len(applied)}줄")
    for line in applied:
        print(f"   + {line}")

    if skipped:
        print(f"\n  건너뛴 것 {len(skipped)}줄")
        for line in skipped:
            print(f"   - {line}")

    if applied and not args.dry_run:
        print("\n  다시 묶으십시오:")
        print("    python tools/build_translation.py")
        if any("images" in line or ".json" in line for line in applied):
            print("    python tools/build_clue_images.py     (그림을 고쳤다면)")

    sys.exit(0)


if __name__ == "__main__":
    main()
