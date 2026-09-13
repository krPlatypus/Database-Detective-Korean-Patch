"""사용 설명서 쪽 그림을 PNG로 뽑아낸다.

설명서는 한 쪽이 그림 한 장이고 이름이 '장-쪽'(1-1, 5-4 ...)이다.
단서 그림과 달리 목록 TextAsset에 적혀 있지 않아 이름 생김새로 찾는다.

같은 이름으로 Texture2D와 Sprite가 함께 들어 있는데, Sprite는 아틀라스의
일부만 잘라낸 것일 수 있어 Texture2D 쪽을 원본으로 본다.

결과는 extracted/images/manual/ 로 나가고, build_clue_images.py가 이 폴더를
원본으로 읽는다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "extracted", "images", "manual")

# 설명서 쪽 이름. '8-3'처럼 장과 쪽을 붙임표로 이었다.
PAGE = re.compile(r"^\d+-\d+$")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 이름마다 Texture2D를 먼저 잡아 두고, 없을 때만 Sprite로 물러선다.
    found = {}
    for file_name in common.ASSET_FILES:
        path = os.path.join(common.DATA_DIR, file_name)
        if not os.path.exists(path):
            continue
        for obj in common.load(file_name).objects:
            if obj.type.name not in ("Sprite", "Texture2D"):
                continue
            try:
                name = obj.peek_name()
            except Exception:
                continue
            if not name or not PAGE.match(name):
                continue
            if obj.type.name == "Texture2D" or name not in found:
                found[name] = obj

    if not found:
        print("설명서 쪽 그림을 찾지 못했습니다.")
        return

    for name in sorted(found):
        image = found[name].read().image
        image.save(os.path.join(OUT_DIR, f"{name}.png"))
        print(f"  {name}  {image.width}x{image.height}")

    print(f"\n  설명서 {len(found)}쪽 -> {OUT_DIR}")


if __name__ == "__main__":
    main()
