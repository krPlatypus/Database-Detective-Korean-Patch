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


# 한글 한 글자가 라틴 글자 몇 칸만큼 넓은지.
# 화면에서 재어 보니 2.25~3.2배 사이였다. 게임 영문 글꼴은 좁은 가변폭인데
# 한글 글꼴은 네모칸을 꽉 채우기 때문이다. 가운데값을 쓴다.
HANGUL_WIDTH = 2.5


def visual_width(text):
    """눈에 보이는 너비를 라틴 글자 칸 수로 환산한다. 서식 태그는 폭이 없다."""
    bare = TAG.sub("", text)
    return sum(HANGUL_WIDTH if "가" <= c <= "힣" or "一" <= c <= "鿿" else 1
               for c in bare)


def is_code(text):
    return any(marker in text for marker in CODE_MARKERS) or bool(LIST_MARKER.search(text))


def greedy(words, limit):
    """주어진 폭에 맞춰 어절 단위로 끊는다."""
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
    return lines


def wrap_within(words, budget, max_lines):
    """폭 budget 안에서 max_lines 줄 이하로 끊는다.

    줄 수가 남으면 폭을 더 좁혀 고르게 나눈다. 한 줄만 길고 나머지가 짧으면
    그 줄이 넘칠 위험이 크기 때문이다.
    """
    lines = greedy(words, budget)
    if len(lines) > max_lines:
        return None, len(lines)

    # 줄 수를 늘리지 않는 선에서 가장 좁은 폭을 찾아 고르게 만든다
    best = lines
    limit = budget
    while limit > 1:
        limit -= 1
        candidate = greedy(words, limit)
        if len(candidate) > len(best):
            break
        best = candidate
    return best, len(best)


def rewrap(text, target_lines, budget):
    if is_code(text):
        return None, "줄 나눔이 뜻을 가진 항목"

    words = " ".join(text.split(BREAK)).split()
    if not words:
        return None, "빈 항목"

    lines, needed = wrap_within(words, budget, target_lines)
    if lines is None:
        return None, f"폭 {budget:.0f} 안에 넣으려면 {needed}줄 필요(원문 {target_lines}줄)"

    return BREAK.join(lines), None


def run(name, source_text, dry):
    path = os.path.join(TEXTASSET_DIR, name)
    records, newline, trailing = split_records(read(path))

    originals = [line.split(";", 3)[3]
                 for line in source_text.split("\r\n") if line.count(";") >= 3]

    changed, skipped = 0, 0
    too_long = []

    for i, (head, body) in enumerate(records):
        if head is None or i >= len(originals):
            continue

        source = originals[i]
        target = source.count(BREAK) + 1
        # 원문에서 가장 넓은 줄이 상자에 들어갔으니 그것이 쓸 수 있는 폭이다.
        budget = max(visual_width(s) for s in source.split(BREAK))

        widest = max(visual_width(s) for s in body.split(BREAK))
        if body.count(BREAK) + 1 == target and widest <= budget:
            continue

        fixed, reason = rewrap(body, target, budget)
        if fixed is None:
            if reason.startswith("폭"):
                too_long.append((i, reason, body.split(BREAK)[0]))
            else:
                skipped += 1
            continue

        records[i] = (head, fixed)
        changed += 1

    if not dry:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(join_records(records, newline, trailing))

    print(f"  {name}: {changed}개 다시 끊음, {skipped}개 건너뜀(줄 나눔이 뜻을 가진 항목)")
    if too_long:
        print(f"    말이 길어 줄여야 하는 항목 {len(too_long)}개:")
        for i, reason, head_text in too_long:
            print(f"      [{i}] {reason}")
            print(f"           {head_text[:46]}")


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
