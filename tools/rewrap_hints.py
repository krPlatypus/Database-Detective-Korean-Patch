"""번역한 힌트의 줄 수를 원문에 맞춘다.

말풍선과 안내창은 원문 줄 수에 맞춰 크기가 잡혀 있다.
줄이 늘면 아래로 넘치고, 줄면 한 줄이 길어져 옆으로 넘친다.
그래서 뜻은 그대로 두고 끊는 자리만 원문 줄 수에 맞춰 다시 잡는다.

끊는 자리는 띄어쓰기(어절 경계)만 쓴다. 한글은 단어 한가운데서 끊으면 읽기 나쁘다.
줄 길이는 고르게 나눈다. 한 줄만 길고 나머지가 짧으면 넘칠 위험이 크다.

예시 쿼리처럼 줄 나눔 자체가 뜻을 가진 항목은 건드리지 않는다.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textasset_records import TEXTASSET_DIR, read, split_records, join_records  # noqa: E402

BREAK = "\\\\n"
TAG = re.compile(r"</?[a-zA-Z][^>]*>")

# 줄 나눔이 뜻을 가진 항목. 예시 쿼리와 번호 매긴 목록은 손대지 않는다.
CODE_MARKERS = (
    "SELECT", "FROM ", "WHERE", "JOIN", "GROUP BY", "HAVING", "EXCEPT",
    "COUNT(", "SUM(", "MIN(", "POW(", "ORDER BY", " = ", "!=", ">=", "%",
)
LIST_MARKER = re.compile(r"(^|\\\\n)\s*\d+\.")


def visual_width(text):
    """눈에 보이는 너비. 한글과 한자는 라틴 글자 두 칸으로 센다."""
    bare = TAG.sub("", text)
    return sum(2 if "가" <= c <= "힣" or "一" <= c <= "鿿" else 1
               for c in bare)


def is_code(text):
    return any(marker in text for marker in CODE_MARKERS) or bool(LIST_MARKER.search(text))


def wrap_to(words, count):
    """어절을 count줄로 나눈다. 가장 긴 줄이 최대한 짧아지도록 고르게."""
    if count <= 1 or len(words) <= count:
        return None

    total = sum(visual_width(w) for w in words) + len(words) - 1
    limit = total // count

    while limit <= total:
        lines, current = [], ""
        for word in words:
            candidate = word if not current else current + " " + word
            if current and visual_width(candidate) > limit:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)

        if len(lines) == count:
            return lines
        limit += 1

    return None


def rewrap(text, target):
    if is_code(text):
        return None

    words = " ".join(text.split(BREAK)).split()
    if not words:
        return None

    lines = wrap_to(words, target)
    return BREAK.join(lines) if lines else None


def run(name, source_text, dry):
    path = os.path.join(TEXTASSET_DIR, name)
    records, newline, trailing = split_records(read(path))

    originals = [line.split(";", 3)[3]
                 for line in source_text.split("\r\n") if line.count(";") >= 3]

    changed, skipped = 0, 0
    for i, (head, body) in enumerate(records):
        if head is None or i >= len(originals):
            continue

        target = originals[i].count(BREAK) + 1
        if body.count(BREAK) + 1 == target:
            continue

        fixed = rewrap(body, target)
        if fixed is None:
            skipped += 1
            continue

        records[i] = (head, fixed)
        changed += 1

    if not dry:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(join_records(records, newline, trailing))

    print(f"  {name}: {changed}개 줄 수 맞춤, {skipped}개 건너뜀(줄 나눔이 뜻을 가진 항목)")


def main():
    dry = "--dry" in sys.argv
    with open(os.path.join(os.path.dirname(TEXTASSET_DIR), "..", "extracted",
                           "textassets_translate.json"), encoding="utf-8") as f:
        originals = {r["source"]: r["text"] for r in json.load(f)}
    with open(os.path.join(TEXTASSET_DIR, "_manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)

    for name in ("hints__2362.txt", "query-hints__2408.txt"):
        run(name, originals[manifest[name]["source"]], dry)


if __name__ == "__main__":
    main()
