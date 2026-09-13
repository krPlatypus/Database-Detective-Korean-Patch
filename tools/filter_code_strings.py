"""코드 문자열 후보에서 실제로 번역할 것만 남긴다.

extract_code_strings.py가 뽑은 목록에는 세 부류가 섞여 있다.

  1. 이어 붙여 쓰는 조각 - 파서 오류가 대표적이다. 앞뒤에 값이 붙어 한 문장이 되므로
     조각만 따로 번역할 수 없다. 정규식 규칙(patterns.json)으로 이미 다루고 있다.
  2. 개발자용 기록 - 화면에 나오지 않는다.
  3. 실제 화면 문구 - 이것만 남기면 된다.

이미 dynamic.json에 있거나 patterns.json이 잡는 것도 뺀다.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = os.path.join(ROOT, "extracted", "code_strings.json")
DYNAMIC = os.path.join(ROOT, "translation", "dynamic.json")
PATTERNS = os.path.join(ROOT, "translation", "patterns.json")
OUT = os.path.join(ROOT, "extracted", "code_strings_todo.json")

# 개발자용 기록에 흔한 말. 화면에는 나오지 않는다.
DEV = re.compile(
    r"(cannot be called without overriding|not being managed|"
    r"in locations cache|not found, cannot|Setting saved|"
    r"function cannot be called|PanelManager|Tiers|"
    r"is null|Token=|-> |debug|Debug)", re.I)


def is_fragment(text):
    """앞뒤에 값이 붙어야 문장이 되는 조각인지."""
    if text != text.strip():
        return True                      # 앞뒤 공백은 이어 붙이는 자리
    if text.startswith(("'", '"', ")", "(", ",", ".")):
        return True
    first = text.lstrip()[:1]
    if first.islower() and not text.endswith((".", "!", "?")):
        return True
    # 끝이 이어지는 모양
    if text.endswith((" ", ":", "=", "(", "'", '"', "+")):
        return True
    return False


def clearly_ui(text):
    """화면 문구임이 분명한 것만 통과시킨다.

    코드가 테이블에 직접 넣는 값도 섞여 있는데(무기 이름, 농장 이름 등)
    짧은 명사구라 화면 라벨과 생김새가 같다. 잘못 번역하면 쿼리가 깨지므로,
    애매하면 두고 본다. 문장 꼴이거나 여러 줄인 것만 받는다.
    """
    if "\n" in text:                       # 여러 줄짜리 안내문
        return True
    if len(text) >= 25 and text.endswith((".", "!", "?")):
        return True
    return False


def database_values():
    """플레이어가 쿼리로 조회하는 값들. 번역하면 게임이 깨진다.

    원문 유지로 분류해 둔 TextAsset이 곧 게임 테이블의 내용이다.
    구분자로 쪼개 값 하나하나를 모아 두고, 코드 문자열이 그 안에 있으면 뺀다.
    인물명, 주소, 무기 이름, 거래 메모 같은 것이 여기서 걸러진다.
    """
    path = os.path.join(ROOT, "extracted", "textassets_keep_original.json")
    values = set()
    if not os.path.exists(path):
        return values

    with open(path, encoding="utf-8") as f:
        for record in json.load(f):
            for line in record["text"].replace("\r", "\n").split("\n"):
                for cell in line.split(";"):
                    cell = cell.strip()
                    if len(cell) >= 3:
                        values.add(cell)
    return values


def main():
    with open(CANDIDATES, encoding="utf-8") as f:
        candidates = json.load(f)

    data = database_values()

    covered = set()
    if os.path.exists(DYNAMIC):
        with open(DYNAMIC, encoding="utf-8") as f:
            covered |= {k for k in json.load(f) if not k.startswith("_")}

    rules = []
    if os.path.exists(PATTERNS):
        with open(PATTERNS, encoding="utf-8") as f:
            for rule in json.load(f):
                if "match" in rule:
                    rules.append(re.compile(rule["match"], re.S))

    todo, fragments, dev, already, db, holes, risky = [], 0, 0, 0, 0, 0, 0
    for text in candidates:
        if text in covered or any(r.match(text) for r in rules):
            already += 1
        elif text in data:
            db += 1
        elif DEV.search(text):
            dev += 1
        elif "{0}" in text and "\n" not in text and not text.endswith((".", "!", "?")):
            holes += 1            # 값만 끼워 찍는 기록용 문구
        elif is_fragment(text):
            fragments += 1
        elif not clearly_ui(text):
            risky += 1
        else:
            todo.append(text)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(sorted(todo), f, ensure_ascii=False, indent=1)

    print(f"  후보 {len(candidates)}개")
    print(f"    이미 처리됨          {already}")
    print(f"    조회 대상 데이터     {db}")
    print(f"    개발자용 기록        {dev}")
    print(f"    값만 끼우는 기록용   {holes}")
    print(f"    이어 붙이는 조각     {fragments}")
    print(f"    데이터일 수 있어 보류 {risky}")
    print(f"    번역 대상            {len(todo)}")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
