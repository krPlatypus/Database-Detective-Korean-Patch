"""번역하지 않고 남긴 것들을 이유와 함께 적어 둔다.

두 가지를 다룬다. 코드 문자열(dynamic.json에 넣지 않은 것)과
UI 문자열(ui.json에 값이 비어 있는 것)이다.

ui.json의 빈 값은 '아직 안 함'과 '일부러 안 함'을 구분하지 못한다.
지금 남은 빈 값은 전부 후자다. 인물명, 사용자 이름, 테이블 이름,
단축키 이름처럼 플레이어가 쿼리나 키보드로 그대로 쓰는 것들이라,
번역하면 화면과 데이터가 어긋난다. 다음에 이 목록을 다시 훑을 때
같은 판단을 처음부터 반복하지 않도록 남겨 둔다.


filter_code_strings.py가 화면 문구로 걸러 냈지만, 뜯어 보니 번역하면 안 되는
것들이 남아 있다. 왜 뺐는지 적어 두지 않으면 다음에 또 같은 검토를 하게 된다.

  - 인물 소개글: WikiLevel.SaveDescriptions가 descriptions 테이블
    (username TEXT, description TEXT)에 그대로 넣는다. 플레이어가 조회하는 값이다.
  - 송금 메모: AddTransaction의 마지막 인자로, 거래 테이블의 한 칸이 된다.
  - 개발자 기록과 Steamworks 경고: 화면에 나오지 않는다.

반대로 broker.com 회사 소개글은 Trader.bio를 화면에 그대로 찍기만 해서
(broker_search.cs) 번역해도 안전하다. 이건 뺀 목록에 없다.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODO = os.path.join(ROOT, "extracted", "code_strings_todo.json")
DYNAMIC = os.path.join(ROOT, "translation", "dynamic.json")
OUT = os.path.join(ROOT, "translation", "code_strings_skipped.json")

UI = os.path.join(ROOT, "translation", "ui.json")
UI_TEXT = os.path.join(ROOT, "extracted", "ui_text.json")
UI_OUT = os.path.join(ROOT, "translation", "ui_keep_original.json")

# 원문을 지켜야 하는 자리. 추출할 때 붙은 경로 이름으로 가른다.
# Table Name은 바탕화면 아이콘이자 실제 테이블 이름이고,
# username/Author/name은 인물 식별자다. 둘 다 플레이어가 쿼리에 적는다.
IDENTIFIER_PATHS = ("Table Name", "username", "Author", "name", "Clue Name",
                    "Column Name", "playerName", "General Hotkeys", "Version")

REASONS = [
    ("payup.com/pay/", "인물 소개글 - descriptions 테이블에 들어가는 값"),
    ("[Steamworks.NET]", "Steamworks 경고 - 화면에 나오지 않음"),
]

BY_TEXT = {
    "Please stop targeting me in the Dark Forests. I do not have a lot!":
        "인물 소개글 - descriptions 테이블에 들어가는 값",
    "Founder of the Legends of New Hampshire wiki. If you'd like to join our guild, "
    "please contribute to our wiki page!":
        "인물 소개글 - descriptions 테이블에 들어가는 값",
    "I am the Grand Wizard of the Wise Wizards Guild. Are you worthy of joining our "
    "secret society of Wizards? Find me at night at New Shire City. Make sure you are "
    "not being followed. The verification process will start there.":
        "인물 소개글 - descriptions 테이블에 들어가는 값",
    "I'm the main editor of newhampshire.wiki! Someone please help us I spend all of my "
    "time in the game researching for the page and it has consumed my life. This game "
    "isn't even fun for me anymore.":
        "인물 소개글 - descriptions 테이블에 들어가는 값",
    "NOT taking any new guild applications currently. Also PLEASE do not send me messages "
    "if there's something wrong with guildsofnewhampshire.net and I am in-game. I will "
    "take care of it later.":
        "인물 소개글 - descriptions 테이블에 들어가는 값",
    "Didnt even know I wanted this!": "송금 메모 - 거래 테이블에 들어가는 값",
    "Had to ride again, thanks!": "송금 메모 - 거래 테이블에 들어가는 값",
    "entrance fee payment here?": "송금 메모 - 거래 테이블에 들어가는 값",
    "Checking new save for culprit.": "개발자 기록",
    "Finished loading Level {0}.": "개발자 기록",
    "Instantiate not called beforehand.": "개발자 기록",
    "Tried to Initialize the SteamAPI twice in one session!": "개발자 기록",
}


def reason_for(text):
    if text in BY_TEXT:
        return BY_TEXT[text]
    for needle, why in REASONS:
        if needle in text:
            return why
    return None


def ui_reason(text, paths):
    """ui.json에 빈 값으로 남은 문자열을 왜 남겼는지."""
    for path in paths:
        for known in IDENTIFIER_PATHS:
            if path.startswith(known):
                if known == "General Hotkeys":
                    return "단축키 이름 - 키보드에 적힌 그대로 둔다"
                if known in ("Table Name", "Column Name"):
                    return "테이블·컬럼 이름 - 플레이어가 쿼리에 적는 값"
                if known == "Version":
                    return "판 번호"
                return "인물 식별자 - 플레이어가 쿼리에 적는 값"
    return None


def mark_ui():
    if not (os.path.exists(UI) and os.path.exists(UI_TEXT)):
        return

    with open(UI, encoding="utf-8") as f:
        ui = json.load(f)
    with open(UI_TEXT, encoding="utf-8") as f:
        where = {}
        for record in json.load(f):
            where.setdefault(record["text"], set()).add(record["path"])

    kept, unknown = {}, []
    for text, value in ui.items():
        if text.startswith("_") or value.strip():
            continue
        reason = ui_reason(text, where.get(text, set()))
        if reason:
            kept[text] = reason
        else:
            kept[text] = "고유명사·표기 - 원문을 지킨다"
            unknown.append(text)

    with open(UI_OUT, "w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"  UI 원문 유지 {len(kept)}개 (경로로 못 가른 것 {len(unknown)}개)")
    print(f"  -> {UI_OUT}")


def main():
    with open(TODO, encoding="utf-8") as f:
        todo = json.load(f)
    with open(DYNAMIC, encoding="utf-8") as f:
        translated = {k for k in json.load(f) if not k.startswith("_")}

    skipped, unknown = {}, []
    for text in todo:
        if text in translated:
            continue
        why = reason_for(text)
        if why:
            skipped[text] = why
        else:
            unknown.append(text)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(skipped, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"  번역 {len(translated)}개 / 제외 {len(skipped)}개")
    for text in unknown:
        print(f"    이유 없음: {text[:70]}")
    print(f"  -> {OUT}")

    mark_ui()


if __name__ == "__main__":
    main()
