"""Scripts.dll 안의 문자열 중 화면에 나오는 것을 골라낸다.

게임 문구가 전부 애셋에 있는 것은 아니다. 조수가 묻는 말처럼 코드가 직접
들고 있는 문구가 있어, 프리팹만 훑어서는 잡히지 않는다.

어셈블리의 사용자 문자열 힙에는 내부용 값도 잔뜩 섞여 있다.
경로, 식별자, 서식 조각, SQL 문 같은 것을 걸러 사람이 읽는 문장만 남긴다.
걸러낸 결과는 사람이 한 번 더 보고 판단해야 한다.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dump_us import dump_us  # noqa: E402
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "extracted", "code_strings.json")

BACKSLASH = chr(92)

# 코드 조각으로 보이는 것들. 화면 문구가 아니다.
SQL = re.compile(r"\b(SELECT|FROM|WHERE|JOIN|INSERT|UPDATE|DELETE|CREATE TABLE|GROUP BY)\b")
TOKEN = re.compile(r"^[\w./" + BACKSLASH + r"\-]+$")
PUNCT_ONLY = re.compile(r"^[\s{}\d,;:'\"()\[\]<>/|._+*=-]+$")


def looks_visible(text):
    t = text.strip()
    if len(t) < 3 or len(t) > 500:
        return False
    if not re.search(r"[A-Za-z]", t):
        return False
    if TOKEN.match(t):            # 경로나 식별자 한 덩어리
        return False
    if PUNCT_ONLY.match(t):
        return False
    if t[0] in "<{#/" + BACKSLASH:
        return False
    if SQL.search(t):
        return False
    if "/" in t and " " not in t:  # 경로
        return False
    # 사람이 읽는 문장은 보통 공백이나 문장부호를 품는다
    return " " in t or t.endswith(("?", "!", "."))


def main():
    path = os.path.join(common.MANAGED_DIR, "Scripts.dll")
    every = dump_us(path)
    candidates = sorted({t for t in every if looks_visible(t)})

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=1)

    print(f"  전체 문자열 {len(every)}개 중 화면 후보 {len(candidates)}개")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
