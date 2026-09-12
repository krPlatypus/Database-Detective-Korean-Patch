"""단서 이미지의 글자를 한글로 바꿔 번역본 PNG를 만든다.

이미지마다 translation/images/<이름>.json 에 편집 사양을 둔다.
사양은 "이 영역을 배경색으로 덮고 여기에 이 한글을 써라"의 목록이다.
원본은 extracted/images/clues/ 에서 읽고 결과는 dist/images/ 로 나간다.

원본 화풍을 살리려고 그림 전체를 다시 그리지 않고 글자 영역만 건드린다.
이름, ID 번호, 날짜, 주소 같은 값은 플레이어가 그대로 SQL에 적어 넣는 데이터이므로
사양에 넣지 않는다. 건드리면 사건을 풀 수 없게 된다.

사양 한 항목의 형태:
  {
    "box":  [x1, y1, x2, y2],     원본에서 지울 영역
    "text": "유출 금지",           그 자리에 쓸 한글
    "color": [214, 65, 24],       글자색
    "fill":  [231, 215, 79],      덮을 배경색. 없으면 box 가장자리에서 뽑는다
    "font":  "malgunbd.ttf",      C:/Windows/Fonts 기준. 없으면 기본값
    "size":  44,                  없으면 box 높이에 맞춘다
    "align": "center"             left | center | right
  }
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(ROOT, "extracted", "images", "clues")
SPEC_DIR = os.path.join(ROOT, "translation", "images")
OUT_DIR = os.path.join(ROOT, "dist", "images")

FONT_DIR = r"C:\Windows\Fonts"
DEFAULT_FONT = "malgunbd.ttf"


def load_font(name, size):
    path = os.path.join(FONT_DIR, name or DEFAULT_FONT)
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, DEFAULT_FONT)
    return ImageFont.truetype(path, size)


def sample_fill(image, box):
    """box 바로 위쪽 띠에서 가장 흔한 색을 배경색으로 본다."""
    x1, y1, x2, y2 = box
    band = image.crop((x1, max(0, y1 - 8), x2, max(1, y1 - 1)))
    colors = band.getcolors(band.width * band.height or 1)
    if not colors:
        return (255, 255, 255)
    return max(colors, key=lambda c: c[0])[1][:3]


def fit_size(draw, text, font_name, box):
    """box 안에 들어가는 가장 큰 글자 크기를 찾는다."""
    x1, y1, x2, y2 = box
    max_w, max_h = x2 - x1, y2 - y1
    size = max_h
    while size > 6:
        font = load_font(font_name, size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if right - left <= max_w and bottom - top <= max_h:
            return size
        size -= 1
    return 6


def apply_edit(image, draw, edit):
    box = tuple(edit["box"])
    x1, y1, x2, y2 = box

    fill = tuple(edit.get("fill") or sample_fill(image, box))
    draw.rectangle(box, fill=fill)

    text = edit.get("text", "").strip()
    if not text:
        return   # 지우기만 하는 항목

    font_name = edit.get("font")
    size = edit.get("size") or fit_size(draw, text, font_name, box)
    font = load_font(font_name, size)

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = right - left, bottom - top

    align = edit.get("align", "center")
    if align == "left":
        tx = x1
    elif align == "right":
        tx = x2 - text_w
    else:
        tx = x1 + (x2 - x1 - text_w) // 2
    ty = y1 + (y2 - y1 - text_h) // 2

    draw.text((tx - left, ty - top), text, font=font, fill=tuple(edit.get("color", [0, 0, 0])))


def build(name):
    source = os.path.join(SOURCE_DIR, name + ".png")
    spec_path = os.path.join(SPEC_DIR, name + ".json")

    if not os.path.exists(source):
        return f"원본 없음: {source}"
    if not os.path.exists(spec_path):
        return f"사양 없음: {spec_path}"

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image)

    for edit in spec.get("edits", []):
        apply_edit(image, draw, edit)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, name + ".png")
    image.save(out)
    return None


def main():
    if not os.path.isdir(SPEC_DIR):
        print(f"사양 폴더가 없습니다: {SPEC_DIR}")
        return

    names = sorted(
        os.path.splitext(f)[0] for f in os.listdir(SPEC_DIR) if f.endswith(".json")
    )
    if len(sys.argv) > 1:
        names = [n for n in names if n in sys.argv[1:]]

    built, failed = 0, []
    for name in names:
        error = build(name)
        if error:
            failed.append(error)
        else:
            built += 1

    print(f"  번역 이미지 {built}개 생성 -> {OUT_DIR}")
    for message in failed:
        print(f"  {message}")


if __name__ == "__main__":
    main()
