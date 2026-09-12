"""추출한 단서 이미지에서 대표본만 골라 모아 보기 판을 만든다.

같은 이름으로 Sprite와 Texture2D가 함께 나오고 해상도 변형도 있어
파일이 이름당 네 개쯤 생긴다. 가장 큰 것 하나만 남겨 눈으로 훑기 좋게 한다.
"""
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "extracted", "images")
CLUE_DIR = os.path.join(IMG_DIR, "clues")

THUMB = 320
COLUMNS = 5
LABEL_HEIGHT = 22
PADDING = 8


def pick_representatives():
    with open(os.path.join(IMG_DIR, "_index.json"), encoding="utf-8") as f:
        index = json.load(f)

    best = {}
    for row in index["exported"]:
        if "file" not in row:
            continue
        width, height = (int(v) for v in row["size"].split("x"))
        area = width * height
        current = best.get(row["name"])
        # 같은 이름이면 가장 큰 것, 크기가 같으면 Texture2D(원본)를 택한다
        if current is None or area > current[0] or (
            area == current[0] and row["type"] == "Texture2D"
        ):
            best[row["name"]] = (area, row)
    return {name: row for name, (_, row) in best.items()}


def main():
    os.makedirs(CLUE_DIR, exist_ok=True)
    chosen = pick_representatives()

    thumbs = []
    for name in sorted(chosen):
        row = chosen[name]
        source = os.path.join(IMG_DIR, row["file"])
        if not os.path.exists(source):
            continue

        image = Image.open(source).convert("RGBA")
        image.save(os.path.join(CLUE_DIR, f"{name}.png"))

        thumb = image.copy()
        thumb.thumbnail((THUMB, THUMB), Image.LANCZOS)
        thumbs.append((name, row, thumb))

    if not thumbs:
        print("이미지가 없습니다.")
        return

    rows = (len(thumbs) + COLUMNS - 1) // COLUMNS
    cell_w = THUMB + PADDING * 2
    cell_h = THUMB + LABEL_HEIGHT + PADDING * 2
    sheet = Image.new("RGB", (cell_w * COLUMNS, cell_h * rows), (32, 32, 36))
    draw = ImageDraw.Draw(sheet)

    for i, (name, row, thumb) in enumerate(thumbs):
        cx = (i % COLUMNS) * cell_w
        cy = (i // COLUMNS) * cell_h
        ox = cx + PADDING + (THUMB - thumb.width) // 2
        oy = cy + PADDING + (THUMB - thumb.height) // 2
        sheet.paste(thumb, (ox, oy), thumb)
        draw.text((cx + PADDING, cy + PADDING + THUMB + 4),
                  f"{name}  ({row['chapters']}장, {row['size']})", fill=(220, 220, 220))

    out = os.path.join(IMG_DIR, "_contact_sheet.png")
    sheet.save(out)

    print(f"  대표 이미지 : {len(thumbs)}개 -> {CLUE_DIR}")
    print(f"  모아 보기   : {out}")
    print(f"  시트 크기   : {sheet.width}x{sheet.height}")


if __name__ == "__main__":
    main()
