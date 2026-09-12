"""줄바꿈 표기가 온전한지 검사하고 고친다.

이 게임의 TextAsset은 본문 안 줄바꿈을 역슬래시 두 개와 n으로 적는다.
역슬래시가 하나만 남으면 게임이 줄을 바꾸지 않고 글자 그대로 뱉는다.

셸을 거쳐 값을 넘기다 보면 역슬래시가 하나 먹히는 일이 있어,
파일에 실제로 무엇이 들어갔는지 확인할 필요가 있다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textasset_records import TEXTASSET_DIR, read, split_records, join_records  # noqa: E402

GOOD = "\\" + "\\" + "n"   # 역슬래시 둘 + n
# 앞뒤로 역슬래시가 더 붙지 않은, 홀로 있는 역슬래시 하나 + n
LONE = re.compile(r"(?<!\\)\\n")


def scan(name, fix):
    path = os.path.join(TEXTASSET_DIR, name)
    records, newline, trailing = split_records(read(path))

    broken = []
    for i, (head, body) in enumerate(records):
        if head is None:
            continue
        if LONE.search(body):
            broken.append(i)
            if fix:
                # 치환 문자열을 그대로 주면 re가 역슬래시를 이스케이프로 읽어
                # 두 개가 하나로 줄어든다. 함수로 넘기면 글자 그대로 들어간다.
                records[i] = (head, LONE.sub(lambda _: GOOD, body))

    if fix and broken:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(join_records(records, newline, trailing))

    state = "고침" if (fix and broken) else "발견"
    print(f"  {name}: 줄바꿈이 깨진 기록 {len(broken)}개 {state}")
    return broken


if __name__ == "__main__":
    fix = "--fix" in sys.argv
    for file_name in sorted(f for f in os.listdir(TEXTASSET_DIR) if f.endswith(".txt")):
        scan(file_name, fix)
