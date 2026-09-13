"""단서 이미지의 글자를 한글로 바꿔 번역본 PNG를 만든다.

이미지마다 translation/images/<이름>.json 에 편집 사양을 둔다.
원본은 extracted/images/clues/ 에서 읽고 결과는 dist/images/ 로 나간다.

원본 화풍을 살리려고 그림을 다시 그리지 않고 글자만 걷어낸 뒤 한글을 얹는다.
이름, ID 번호, 날짜, 주소 같은 값은 플레이어가 그대로 SQL에 적어 넣는 데이터이므로
건드리지 않는다.

지우는 방법이 두 가지다.

  erase_boxes        네모 영역을 통째로 덮는다. 배경이 평평하고 주변에
                     살릴 것이 없을 때 쓴다.

  erase_ink_within   지정한 영역 안에 **완전히 들어가는** 잉크 덩어리만 지운다.
                     글자와 화살표가 얽혀 있을 때 쓴다. 화살표나 동그라미는
                     영역 밖으로 뻗어 나가므로 살아남는다.

지운 자리는 주변에서 가장 가까운 성한 픽셀 색으로 메운다.
배경에 그늘이나 결이 있어도 단색으로 덮은 티가 덜 난다.
"""
import json
import os
import sys
from collections import deque

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIRS = [
    os.path.join(ROOT, "extracted", "images", "clues"),
    os.path.join(ROOT, "extracted", "images", "manual"),
]
SPEC_DIR = os.path.join(ROOT, "translation", "images")
OUT_DIR = os.path.join(ROOT, "dist", "images")

FONT_DIR = r"C:\Windows\Fonts"

# 윈도우에 없는 글꼴은 프로젝트 안에서 찾는다. 앞에서부터 본다.
EXTRA_FONT_DIRS = [
    os.path.join(ROOT, "dist", "fonts"),
    ROOT,
]

# 게임 UI가 Windows 95풍이라 한글도 그 시절 시스템 폰트인 굴림 계열로 맞춘다.
# gulim.ttc 한 파일에 네 서체가 묶여 있어 인덱스로 고른다.
#   0 굴림(가변폭)  1 굴림체(고정폭)  2 돋움(획이 더 각짐)  3 돋움체(고정폭)
DEFAULT_FONT = "gulim.ttc"
DEFAULT_FONT_INDEX = 0
TTC_FACES = {"gulim": 0, "gulimche": 1, "dotum": 2, "dotumche": 3}

# 손으로 쓴 주석에는 정자체보다 손글씨체가 맞는다. 윈도우에 기본으로 깔린 것들.
#   magic  매직체  - 마커펜으로 그은 획. 현장 사진의 빨간 주석에 잘 맞는다
#   pyunji 편지체  - 펜으로 쓴 편지 글씨. 일기나 쪽지에 어울린다
#   ami    아미체  - 가늘고 동글동글한 손글씨
#   gungso 궁서    - 붓글씨
NAMED_FONTS = {
    "mongtori": ("Griun_Mongtori-Rg.ttf", 0),
    "neodgm": ("neodgm.ttf", 0),
    "magic": ("HMKMMAG.TTF", 0),
    "pyunji": ("HMFMPYUN.TTF", 0),
    "ami": ("HMKMAMI.TTF", 0),
    "yet": ("HMFMOLD.TTF", 0),
    "headline": ("HMKMRHD.TTF", 0),
    "gungso": ("H2GSRB.TTF", 0),
    "post": ("H2PORM.TTF", 0),
    "malgun": ("malgun.ttf", 0),
    "malgunbd": ("malgunbd.ttf", 0),
    "batang": ("batang.ttc", 0),
}

# 손글씨 주석의 기본 잉크 판정. 사양에서 덮어쓸 수 있다.
DEFAULT_INK = {"r_min": 140, "g_max": 100, "b_max": 100}


def locate(file_name):
    """글꼴 파일을 윈도우 폰트 폴더와 프로젝트 안에서 차례로 찾는다."""
    for folder in [FONT_DIR] + EXTRA_FONT_DIRS:
        candidate = os.path.join(folder, file_name)
        if os.path.exists(candidate):
            return candidate
    return None


def load_font(name, size, index=None):
    """폰트를 연다. 사양의 font는 파일명("gulim.ttc") 또는 서체명("dotum") 둘 다 받는다."""
    key = (name or "").strip().lower()
    if key in TTC_FACES:
        return ImageFont.truetype(os.path.join(FONT_DIR, DEFAULT_FONT), size,
                                  index=TTC_FACES[key])
    if key in NAMED_FONTS:
        file_name, face = NAMED_FONTS[key]
        candidate = locate(file_name)
        if candidate:
            return ImageFont.truetype(candidate, size, index=face)

    path = locate(name or DEFAULT_FONT)
    if not path:
        path, index = os.path.join(FONT_DIR, DEFAULT_FONT), DEFAULT_FONT_INDEX

    if index is None:
        index = DEFAULT_FONT_INDEX if path.lower().endswith(".ttc") else 0
    return ImageFont.truetype(path, size, index=index)


def is_ink(pixel, rule):
    return (pixel[0] >= rule["r_min"]
            and pixel[1] <= rule["g_max"]
            and pixel[2] <= rule["b_max"])


def find_components(image, rule, min_pixels=40):
    """잉크 픽셀을 이어 붙여 덩어리 목록을 만든다."""
    width, height = image.size
    px = image.load()
    ink = [[is_ink(px[x, y], rule) for x in range(width)] for y in range(height)]
    seen = [[False] * width for _ in range(height)]
    neighbours = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))

    components = []
    for y in range(height):
        for x in range(width):
            if not ink[y][x] or seen[y][x]:
                continue
            queue = deque([(x, y)])
            seen[y][x] = True
            pixels = []
            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                for dx, dy in neighbours:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and ink[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        queue.append((nx, ny))
            if len(pixels) >= min_pixels:
                xs = [p[0] for p in pixels]
                ys = [p[1] for p in pixels]
                components.append({
                    "pixels": pixels,
                    "box": (min(xs), min(ys), max(xs), max(ys)),
                })
    return components


def is_tinted(pixel, rule):
    """진한 잉크는 아니지만 잉크 쪽으로 물든 픽셀. 획의 흐린 가장자리를 잡는다."""
    r, g, b = pixel[0], pixel[1], pixel[2]
    return r - max(g, b) >= rule.get("tint_gap", 35)


def bleed(image, seed_pixels, region, margin):
    """진한 획에서 시작해 물든 픽셀까지 번져 나가며 획 전체를 모은다.

    영역 밖으로는 나가지 않게 막아, 가까이 있는 화살표나 동그라미로
    옮겨붙지 않도록 한다.
    """
    width, height = image.size
    px = image.load()
    x1 = max(0, region[0] - margin)
    y1 = max(0, region[1] - margin)
    x2 = min(width - 1, region[2] + margin)
    y2 = min(height - 1, region[3] + margin)

    collected = set(seed_pixels)
    queue = deque(seed_pixels)
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = x + dx, y + dy
            if not (x1 <= nx <= x2 and y1 <= ny <= y2):
                continue
            if (nx, ny) in collected:
                continue
            if is_tinted(px[nx, ny], {}):
                collected.add((nx, ny))
                queue.append((nx, ny))
    return list(collected)


def dilate(pixels, size, radius):
    """지울 자리를 조금 넓힌다. 한 겹 남은 흐린 테두리를 없앤다."""
    if radius <= 0:
        return pixels

    width, height = size
    grown = set(pixels)
    for _ in range(radius):
        edge = list(grown)
        for x, y in edge:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    grown.add((nx, ny))
    return list(grown)


def contained(inner, outer):
    return (inner[0] >= outer[0] and inner[1] >= outer[1]
            and inner[2] <= outer[2] and inner[3] <= outer[3])


def heal(image, holes):
    """지운 자리를 가장 가까운 성한 픽셀 색으로 메운다 (다중 시작점 너비 우선)."""
    if not holes:
        return

    width, height = image.size
    px = image.load()
    hole_set = set(holes)

    queue = deque()
    for x, y in holes:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in hole_set:
                queue.append((x, y, px[nx, ny]))
                break

    filled = set()
    while queue:
        x, y, colour = queue.popleft()
        if (x, y) in filled:
            continue
        filled.add((x, y))
        px[x, y] = colour
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height
                    and (nx, ny) in hole_set and (nx, ny) not in filled):
                queue.append((nx, ny, colour))


def fit_size(text, font_name, max_w, max_h, font_index=None):
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    size = max_h
    while size > 6:
        font = load_font(font_name, size, font_index)
        left, top, right, bottom = probe.textbbox((0, 0), text, font=font)
        if right - left <= max_w and bottom - top <= max_h:
            return size
        size -= 1
    return 6


def draw_text(image, entry):
    """글자를 얹는다.

    'at'이 어디를 가리키는지는 align/valign으로 정한다. 기본은 가운데인데,
    손으로 갈겨 쓴 주석처럼 가운데를 잡는 편이 쉬운 그림이 있어서다.
    문자 메시지 화면처럼 왼쪽이나 오른쪽 끝이 맞아야 하는 그림에서는
    그 끝을 직접 가리키는 편이 낫다. 여러 줄이면 줄끼리도 같은 쪽으로 맞춘다.
    """
    text = entry.get("text", "").strip()
    if not text:
        return

    font_name = entry.get("font")
    font_index = entry.get("font_index")
    size = entry.get("size") or fit_size(
        text, font_name, entry.get("max_width", 400), entry.get("max_height", 80), font_index)
    font = load_font(font_name, size, font_index)

    align = entry.get("align", "center")
    spacing = entry.get("line_gap", 4)

    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    left, top, right, bottom = probe.multiline_textbbox(
        (0, 0), text, font=font, spacing=spacing, align=align)
    pad = size // 2
    layer = Image.new("RGBA",
                      (int(right - left) + pad * 2, int(bottom - top) + pad * 2),
                      (0, 0, 0, 0))
    ImageDraw.Draw(layer).multiline_text(
        (pad - left, pad - top), text, font=font, spacing=spacing, align=align,
        fill=tuple(entry.get("color", [0, 0, 0])))

    angle = entry.get("angle", 0)
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)

    cx, cy = entry["at"]
    if align == "left":
        x = cx - pad
    elif align == "right":
        x = cx - layer.width + pad
    else:
        x = cx - layer.width / 2

    y = cy - pad if entry.get("valign") == "top" else cy - layer.height / 2
    image.alpha_composite(layer, (int(x), int(y)))


def draw_block(image, entry):
    """상자 안에 문단을 흘려 넣는다. 설명서처럼 본문이 여러 줄인 경우에 쓴다.

    단서 그림의 한 줄짜리 글씨와 달리, 정해진 폭 안에서 어절 단위로 줄을 바꾸고
    줄 간격을 맞춰야 한다. 원본 조판을 그대로 흉내 내기보다 읽기 좋게 다시 짠다.
    """
    text = entry.get("text", "").strip()
    if not text:
        return

    x1, y1, x2, y2 = entry["box"]
    font = load_font(entry.get("font"), entry.get("size", 26), entry.get("font_index"))
    colour = tuple(entry.get("color", [0, 0, 0]))
    spacing = entry.get("line_spacing", 1.35)
    indent = entry.get("indent", 0)

    draw = ImageDraw.Draw(image)
    width = x2 - x1

    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = ""
        first = True
        for word in words:
            candidate = word if not current else current + " " + word
            limit = width - (indent if first else 0)
            if current and draw.textlength(candidate, font=font) > limit:
                lines.append(current)
                current = word
                first = False
            else:
                current = candidate
        if current:
            lines.append(current)

    step = int(entry.get("size", 26) * spacing)
    y = y1
    for i, line in enumerate(lines):
        if y + step > y2 + step:   # 상자를 넘어가면 멈춘다
            break
        x = x1 + (indent if i == 0 else 0)
        draw.text((x, y), line, font=font, fill=colour)
        y += step

    return len(lines), (y - y1)


def build(name):
    source = next((os.path.join(d, name + ".png")
                   for d in SOURCE_DIRS
                   if os.path.exists(os.path.join(d, name + ".png"))), None)
    spec_path = next((p for p in (
        os.path.join(SPEC_DIR, name + ".json"),
        os.path.join(SPEC_DIR, "manual", name + ".json"),
    ) if os.path.exists(p)), os.path.join(SPEC_DIR, name + ".json"))

    if source is None:
        return f"원본 없음: {name}.png"

    if not os.path.exists(spec_path):
        return f"사양 없음: {spec_path}"

    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    image = Image.open(source).convert("RGBA")
    rule = dict(DEFAULT_INK)
    rule.update(spec.get("ink", {}))

    holes = []

    # 배경이 단색인 문서 페이지는 그 색으로 덮는 편이 낫다.
    # 주변 색으로 메우는 방식은 상자 경계에 원본 글자가 걸쳐 있을 때
    # 그 검은색을 안쪽으로 번지게 해 세로줄 자국을 남긴다.
    # 한 그림 안에 바탕색이 여럿인 경우가 있다(문자 메시지 화면은 본문이 흰색,
    # 위아래 띠가 검정). 상자마다 색을 따로 줄 수 있게 두 가지 적는 법을 받는다.
    #   [x1, y1, x2, y2]                      erase_fill 색으로 덮는다
    #   {"box": [...], "fill": [r, g, b]}     이 상자만 다른 색으로 덮는다
    flat = spec.get("erase_fill")
    painter = ImageDraw.Draw(image)
    for box in spec.get("erase_boxes", []):
        if isinstance(box, dict):
            painter.rectangle(box["box"], fill=tuple(box.get("fill", flat or (255, 255, 255))))
            continue
        if flat is not None:
            painter.rectangle(box, fill=tuple(flat))
            continue
        x1, y1, x2, y2 = box
        for y in range(max(0, y1), min(image.height, y2)):
            for x in range(max(0, x1), min(image.width, x2)):
                holes.append((x, y))

    # 영역 안에 완전히 들어가는 잉크 덩어리만 지우기
    regions = spec.get("erase_ink_within", [])
    if regions:
        rgb = image.convert("RGB")
        margin = spec.get("bleed_margin", 6)
        for component in find_components(rgb, rule, spec.get("min_ink_pixels", 40)):
            region = next((r for r in regions if contained(component["box"], tuple(r))), None)
            if region is None:
                continue
            # 진한 속살만 지우면 흐린 테두리가 유령처럼 남는다.
            # 느슨한 판정으로 번지게 해서 획 전체를 걷어낸다.
            holes.extend(bleed(rgb, component["pixels"], region, margin))

    if holes:
        holes = dilate(holes, image.size, spec.get("ink_dilate", 2))

    heal(image, holes)

    for entry in spec.get("texts", []):
        draw_text(image, entry)

    # 여러 줄짜리 본문. 정해진 폭 안에서 어절 단위로 줄을 바꿔 흘려 넣는다.
    for entry in spec.get("blocks", []):
        draw_block(image, entry)

    os.makedirs(OUT_DIR, exist_ok=True)
    image.convert("RGBA").save(os.path.join(OUT_DIR, name + ".png"))
    return None


def main():
    if not os.path.isdir(SPEC_DIR):
        print(f"사양 폴더가 없습니다: {SPEC_DIR}")
        return

    names = []
    for folder in (SPEC_DIR, os.path.join(SPEC_DIR, "manual")):
        if os.path.isdir(folder):
            names += [os.path.splitext(f)[0] for f in os.listdir(folder) if f.endswith(".json")]
    names = sorted(set(names))
    if len(sys.argv) > 1:
        names = [n for n in names if n in sys.argv[1:]]

    built, failed = 0, []
    for name in names:
        error = build(name)
        if error:
            failed.append(error)
        else:
            built += 1
            print(f"  {name}")

    print(f"\n  번역 이미지 {built}개 생성 -> {OUT_DIR}")
    for message in failed:
        print(f"  {message}")


if __name__ == "__main__":
    main()
