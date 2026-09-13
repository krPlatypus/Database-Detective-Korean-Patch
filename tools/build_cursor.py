"""조수 위에 올렸을 때 나오는 HELP 커서를 한글로 다시 그린다.

이 HELP는 화면 문자열이 아니라 32x32 마우스 커서 그림이다(UI/Cursor/ask).
번역 사전으로는 손댈 수 없어 그림 자체를 바꿔야 한다.

말풍선 테두리와 꼬리는 그대로 두고 글자 자리만 지운 뒤 새로 찍는다.
색은 원본이 쓰는 두 가지(속 색, 글자 색)뿐이라 안티에일리어싱 없이
문턱값으로 잘라 찍는다. 흐릿한 중간색이 섞이면 도트 그림이 아니게 된다.

'어이 조수!' 같은 긴 말은 이 크기에 들어가지 않는다. 속 너비가 24px이라
한글은 두 글자가 한계다.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "dist", "fonts", "neodgm.ttf")
OUT = os.path.join(ROOT, "dist", "images", "cursor-ask.png")

TEXT = "도움"
SIZE = 11

# 말풍선 속 색과 글자 색. 원본에서 이 두 가지만 쓴다.
FILL = (254, 254, 200, 255)
INK = (70, 52, 41, 255)

# 지울 자리. 테두리(x=5, x=30)와 꼬리는 건드리지 않는다.
ERASE = (8, 9, 30, 20)

# 글자를 놓을 중심. 원본 HELP가 앉아 있던 자리다.
CENTER = (18, 14)

# 이 위로는 글자, 아래는 배경. 도트 글꼴이라 경계가 뚜렷해 중간값이 거의 없다.
THRESHOLD = 100


def original():
    """게임에서 ask 커서 원본을 읽어 온다."""
    for name in common.ASSET_FILES:
        env = common.load(name)
        for obj in env.objects:
            if obj.type.name != "Texture2D":
                continue
            data = obj.read()
            if data.m_Name == "ask":
                return data.image.convert("RGBA")
    raise SystemExit("ask 커서를 찾지 못했다")


def stamp(canvas, text):
    """글자를 1비트로 찍는다. 문턱값 위만 남겨 도트 느낌을 지킨다."""
    font = ImageFont.truetype(FONT, SIZE)

    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=255)
    box = mask.getbbox()
    if box is None:
        raise SystemExit("글자가 비었다")

    left = CENTER[0] - (box[2] - box[0]) // 2 - box[0]
    top = CENTER[1] - (box[3] - box[1]) // 2 - box[1]

    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).text((left, top), text, font=font, fill=255)

    pixels = canvas.load()
    read = mask.load()
    for y in range(canvas.height):
        for x in range(canvas.width):
            if read[x, y] >= THRESHOLD:
                pixels[x, y] = INK

    return (left + box[0], top + box[1], left + box[2], top + box[3])


def main():
    image = original()
    ImageDraw.Draw(image).rectangle(
        [ERASE[0], ERASE[1], ERASE[2] - 1, ERASE[3] - 1], fill=FILL)
    placed = stamp(image, TEXT)

    if placed[0] < ERASE[0] or placed[2] > ERASE[2]:
        print(f"  주의: 글자가 지운 자리를 벗어난다 {placed} vs {ERASE}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    image.save(OUT)

    print(f"  '{TEXT}' {SIZE}px, 놓인 자리 {placed}")
    print(f"  -> {OUT}")

    # 눈으로 확인할 수 있게 찍어 준다.
    pixels = image.load()
    for y in range(image.height):
        row = ""
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            row += "." if a < 40 else ("#" if r + g + b < 400 else " ")
        print("   " + row)


if __name__ == "__main__":
    main()
