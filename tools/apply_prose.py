"""구분자 없는 TextAsset(대사, 자막 등)에 번역을 넣는다.

이 파일들은 평문에 줄바꿈이 그대로 들어간 형태다. 화면 상자가 원문 줄 수에
맞춰 잡혀 있으므로 줄 수가 달라지면 넘치거나 빈다.
그래서 줄 수가 원문과 다르면 아예 쓰지 않고 알린다.

줄 끝 문자(CRLF)와 마지막 개행 유무도 원래대로 유지한다.
이것이 달라지면 게임이 줄을 하나 더 세거나 덜 센다.

배치 파일 형태:
    { "파일이름.txt": ["첫 줄", "둘째 줄", ...] }
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTASSET_DIR = os.path.join(ROOT, "translation", "textassets")


def read(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        return f.read()


def apply(name, lines):
    path = os.path.join(TEXTASSET_DIR, name)
    if not os.path.exists(path):
        return f"{name}: 파일이 없습니다"

    raw = read(path)
    newline = "\r\n" if "\r\n" in raw else "\n"
    trailing = raw.endswith(newline)

    body = raw[:-len(newline)] if trailing else raw
    current = body.split(newline)

    if len(lines) != len(current):
        return f"{name}: 줄 수가 다릅니다 (원문 {len(current)}줄, 번역 {len(lines)}줄)"

    text = newline.join(lines) + (newline if trailing else "")
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return None


def main(batch_path):
    with io.open(batch_path, encoding="utf-8") as f:
        batch = json.load(f)

    done, failed = 0, []
    for name, lines in batch.items():
        error = apply(name, lines)
        if error:
            failed.append(error)
        else:
            done += 1
            print(f"  {name}")

    print(f"\n  {done}개 적용")
    for message in failed:
        print(f"  {message}")


if __name__ == "__main__":
    main(sys.argv[1])
