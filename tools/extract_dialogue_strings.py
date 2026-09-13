"""디컴파일한 소스에서 화면에 찍히는 문자열만 호출 지점을 보고 골라낸다.

filter_code_strings.py는 문자열 생김새로 판단한다. 짧은 문구는 화면 라벨인지
테이블에 들어가는 값인지 생김새로 구분할 수 없어 대부분 보류로 빠진다.
(조수가 생각할 때 뜨는 "Let me think..." 같은 것이 그렇게 걸렸다.)

여기서는 반대로 간다. 화면에 찍는 일만 하는 메서드를 정해 두고, 그 호출의
인자로 들어간 문자열만 거둔다. 호출 지점이 보증하므로 길이나 문장부호를
따지지 않아도 된다.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "decompiled", "Scripts")
DYNAMIC = os.path.join(ROOT, "translation", "dynamic.json")
UI = os.path.join(ROOT, "translation", "ui.json")
OUT = os.path.join(ROOT, "extracted", "dialogue_strings_todo.json")

# 화면에 찍는 일만 하는 호출. 이름 뒤 괄호 안의 문자열 인자를 전부 거둔다.
CALLS = [
    "SetText",
    "CreateQuestionAnswer",
    "GetHelpWrapper",
    "GetHelpImpl",
    "GetHelp",
    "LaunchSuccessNotificationPopup",
    "LaunchErrorNotificationPopup",
    "LaunchNotificationPopup",
    "LaunchConfirmationPopup",
    "SetTitle",
    "SetPlaceholder",
]

# C# 문자열 리터럴 하나. 이스케이프(\" \\ \n)를 품는다.
LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"')

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "0": "\0"}


def unescape(raw):
    out, i = [], 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            out.append(ESCAPES.get(raw[i + 1], raw[i + 1]))
            i += 2
        else:
            out.append(raw[i])
            i += 1
    return "".join(out)


def arguments(text, open_at):
    """open_at의 여는 괄호부터 짝이 맞는 닫는 괄호까지를 돌려준다."""
    depth, i = 0, open_at
    while i < len(text):
        c = text[i]
        if c == '"':                       # 문자열 안의 괄호는 세지 않는다
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[open_at + 1:i]
        i += 1
    return ""


def harvest(text):
    found = []
    for call in CALLS:
        for m in re.finditer(r"\b" + call + r"\s*\(", text):
            args = arguments(text, m.end() - 1)
            for lit in LITERAL.finditer(args):
                found.append(unescape(lit.group(1)))
    return found


def looks_like_text(s):
    """애니메이션 이름이나 씬 이름 같은 식별자를 걸러 낸다."""
    if not s.strip() or not re.search(r"[A-Za-z]", s):
        return False
    if len(s) > 500:
        return False
    return True


def main():
    if not os.path.isdir(SRC):
        sys.exit(f"디컴파일 결과가 없다: {SRC}")

    found = set()
    for name in sorted(os.listdir(SRC)):
        if not name.endswith(".cs"):
            continue
        with open(os.path.join(SRC, name), encoding="utf-8", errors="replace") as f:
            found |= {s for s in harvest(f.read()) if looks_like_text(s)}

    covered = set()
    for path in (DYNAMIC, UI):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for key, value in json.load(f).items():
                    if not key.startswith("_") and value:
                        covered.add(key)

    todo = sorted(found - covered)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(todo, f, ensure_ascii=False, indent=1)

    print(f"  화면 문구 {len(found)}개 중 미번역 {len(todo)}개")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
