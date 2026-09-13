"""번역 대상에서 뺀 코드 문자열을 이유와 함께 적어 둔다.

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


if __name__ == "__main__":
    main()
