"""번역한 화면 문구 중에 조회 대상 값과 겹치는 것을 찾아낸다.

이 게임은 화면에서 읽은 말을 플레이어가 쿼리나 입력칸에 그대로 옮겨 적는다.
그래서 같은 문자열이 화면 라벨이면서 동시에 테이블 값이거나 정답인 경우가 있다.
그런 것을 번역하면 화면과 데이터가 어긋나 사건을 풀 수 없게 된다.

몹 이름이 그랬다. 위키의 'Slimehead'는 설명 제목이지만, DamageLogGenerator가
피해 기록 테이블에 'Slimehead #17' 같은 값으로 넣는다. 'Corrupted'는 한술 더 떠
lsat.cs가 플레이어의 입력과 글자 그대로 비교한다.

코드 안의 문자열 리터럴을 모아 두고, 번역한 키가 그 안에 조각으로라도 들어
있으면 알린다. 이름 뒤에 번호를 붙여 넣는 경우($"Slimehead #{id}")까지 잡으려면
완전히 같은지만 봐서는 안 되고 이렇게 품고 있는지를 봐야 한다.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "translation", "ui.json")
SRC = os.path.join(ROOT, "decompiled", "Scripts")

LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"')

# 한 번 보고 화면 문구가 맞다고 판단한 것들. 사전은 문자열 전체가 같아야
# 바꾸므로, 코드 쪽 문자열이 이 낱말을 품고만 있는 경우는 영향을 주지 않는다.
# ('Light'는 화면 설정 라벨이고, 'Light Queensfield'는 동네 이름이라 무사하다.)
REVIEWED = {
    # 버튼과 창 제목
    "Cancel", "Close", "Next", "Open", "Skip", "Yes", "No", "Undo", "Redo",
    "Cover", "Hotkeys", "Transcript", "Clue Explorer", "Query History",
    "Instruction Manual", "Reload Level", "Reset Progress", "Thank You!",
    "Apply", "Arrest", "Audio", "Login", "Submit", "Web Browser", "Save Table",
    "Search Tables", "Settings", "Display", "Light", "General",
    # 입력칸 안내와 라벨
    "Username", "Password", "username", "password",
    # 위키 표의 머리말. 실제 컬럼 이름은 snake_case라 겹치지 않는다.
    "Health", "Spawn Location", "Total Damage", "World", "Comment", "Comments",
    # 조각으로만 겹치는 것들
    "HERE", "here", "bad", "sent", "thank you", "None", "Search",
    # 번역하지 않고 원문 그대로 둔 것
    "Richmond Hill Farm", "youthtranslator.com", "Writing SQL queries.",
}


def literals():
    found = set()
    for root, _, files in os.walk(SRC):
        for name in files:
            if not name.endswith(".cs"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                found |= set(LITERAL.findall(f.read()))
    return found


def main():
    if not os.path.isdir(SRC):
        sys.exit(f"디컴파일 결과가 없다: {SRC}")

    with open(UI, encoding="utf-8") as f:
        ui = json.load(f)

    # 너무 짧거나 문장인 것은 뺀다. 값으로 쓰이는 것은 짧은 명사구다.
    translated = {
        key for key, value in ui.items()
        if not key.startswith("_") and value.strip()
        and 3 <= len(key) <= 30 and "\n" not in key and "<" not in key
        and key not in REVIEWED
    }

    found = literals()
    hits = []
    for key in sorted(translated):
        inside = [lit for lit in found if key in lit]
        if inside:
            hits.append((key, ui[key], sorted(inside, key=len)[:3]))

    print(f"  코드 문자열과 겹치는 번역 {len(hits)}건")
    for key, value, inside in hits:
        print(f"    {key!r} -> {value!r}")
        for lit in inside:
            print(f"        코드: {lit!r}")

    if hits:
        print("\n  값으로 쓰이는 것이면 ui.json에서 값을 비워 원문을 지켜야 한다.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
