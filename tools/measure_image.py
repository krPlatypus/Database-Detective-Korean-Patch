"""단서 그림에서 글줄이 놓인 자리를 재 준다.

번역본을 그리려면 원본의 각 줄이 어디에 어떤 색으로 있는지 알아야 한다.
눈으로 찍으면 어긋나므로 화소를 세어 구한다.

바탕색과 같지 않은 화소를 잉크로 보고, 잉크가 있는 가로줄을 이어 붙여
한 덩어리를 한 줄로 친다. 줄마다 위아래 끝, 좌우 끝, 가장 많이 쓰인 색을
내놓는다. 그 값을 translation/images/<이름>.json의 at과 color에 그대로 쓴다.

    python tools/measure_image.py suspect_diary
    python tools/measure_image.py id_card --box 40,60,600,540
"""
import argparse
import os
import sys
from collections import Counter

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIRS = [
    os.path.join(ROOT, "extracted", "images", "clues"),
    os.path.join(ROOT, "extracted", "images", "manual"),
    os.path.join(ROOT, "extracted", "images"),
]


def locate(name):
    for folder in SOURCE_DIRS:
        path = os.path.join(folder, name + ".png")
        if os.path.exists(path):
            return path
    sys.exit(f"원본을 찾지 못했다: {name}.png")


def background(image, box):
    """가장 많이 쓰인 색을 바탕으로 본다."""
    x1, y1, x2, y2 = box
    counter = Counter()
    px = image.load()
    for y in range(y1, y2, 2):
        for x in range(x1, x2, 2):
            counter[px[x, y]] += 1
    return counter.most_common(1)[0][0]


def far_from(pixel, colour, tolerance):
    return sum(abs(a - b) for a, b in zip(pixel[:3], colour[:3])) > tolerance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--box", help="잴 영역 x1,y1,x2,y2. 없으면 그림 전체")
    parser.add_argument("--tolerance", type=int, default=90,
                        help="바탕색과 이만큼 넘게 다르면 잉크로 본다")
    parser.add_argument("--gap", type=int, default=3,
                        help="빈 가로줄이 이만큼 이어지면 줄이 나뉜 것으로 본다")
    args = parser.parse_args()

    image = Image.open(locate(args.name)).convert("RGB")
    width, height = image.size
    box = tuple(int(v) for v in args.box.split(",")) if args.box else (0, 0, width, height)
    px = image.load()

    paper = background(image, box)
    print(f"  {args.name}  크기 {width}x{height}  바탕색 {paper}")
    print(f"  잰 영역 {box}")

    x1, y1, x2, y2 = box
    rows = []
    for y in range(y1, y2):
        xs = [x for x in range(x1, x2) if far_from(px[x, y], paper, args.tolerance)]
        rows.append((y, xs))

    groups, current, blank = [], None, 0
    for y, xs in rows:
        if xs:
            blank = 0
            if current is None:
                current = [y, y, set(xs)]
            else:
                current[1], _ = y, current[2].update(xs)
        elif current is not None:
            blank += 1
            if blank > args.gap:
                groups.append(current)
                current = None
    if current is not None:
        groups.append(current)

    print(f"  글줄 {len(groups)}개")
    for top, bottom, xs in groups:
        counter = Counter()
        for y in range(top, bottom + 1):
            for x in xs:
                pixel = px[x, y]
                if far_from(pixel, paper, args.tolerance):
                    counter[pixel] += 1
        colour = counter.most_common(1)[0][0] if counter else paper
        print(f"    y {top:4d}..{bottom:4d}  가운데 {(top + bottom) // 2:4d}  "
              f"높이 {bottom - top + 1:3d}  x {min(xs):4d}..{max(xs):4d}  색 {colour}")


if __name__ == "__main__":
    main()
