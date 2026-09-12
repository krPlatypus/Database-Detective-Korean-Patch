"""구분자로 나뉜 TextAsset의 본문만 뽑거나 갈아 끼운다.

hints, query-hints는 `레벨;단계;순번;본문` 꼴이고 줄 끝은 CRLF다.
본문 안의 줄바꿈은 역슬래시 두 개와 n(`\\\\n`)으로 적혀 있다.

구분자를 손으로 다루면 틀리기 쉬우므로, 네 번째 칸만 바꾸고
나머지는 원래 바이트 그대로 둔다.

사용법:
    python tools/textasset_records.py dump <파일명>          본문 목록 보기
    python tools/textasset_records.py apply <파일명> <배치>   번역 적용
"""
import io
import json
import os
import re
import sys

HANGUL = re.compile(r"[가-힣]")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTASSET_DIR = os.path.join(ROOT, "translation", "textassets")

FIELD_COUNT = 4   # 레벨;단계;순번;본문


def read(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        return f.read()


def split_records(raw):
    """(앞 세 칸, 본문) 목록과 줄 끝 문자를 돌려준다."""
    newline = "\r\n" if "\r\n" in raw else "\n"
    trailing = raw.endswith(newline)
    lines = raw.split(newline)
    if trailing:
        lines = lines[:-1]

    records = []
    for line in lines:
        parts = line.split(";", FIELD_COUNT - 1)
        if len(parts) == FIELD_COUNT:
            records.append((parts[:3], parts[3]))
        else:
            records.append((None, line))   # 형식이 다른 줄은 그대로 둔다
    return records, newline, trailing


def join_records(records, newline, trailing):
    lines = []
    for head, body in records:
        lines.append(";".join(head + [body]) if head else body)
    return newline.join(lines) + (newline if trailing else "")


def dump(name):
    path = os.path.join(TEXTASSET_DIR, name)
    records, _, _ = split_records(read(path))

    seen = set()
    for index, (head, body) in enumerate(records):
        if head is None or not body.strip() or body in seen:
            continue
        seen.add(body)
        print(f"{index:3d}|{'.'.join(head)}|{body}")

    print(f"\n총 {len(records)}줄, 고유 본문 {len(seen)}개", file=sys.stderr)


def apply(name, batch_path):
    path = os.path.join(TEXTASSET_DIR, name)
    with io.open(batch_path, encoding="utf-8") as f:
        batch = json.load(f)

    records, newline, trailing = split_records(read(path))

    # 바꾸기 전 본문을 기억해 둔다. 바꾼 뒤에 견주면 방금 갈아 끼운 것까지
    # 원문에 없었다고 잘못 세게 된다.
    before = {body for head, body in records if head is not None}

    replaced = 0
    for i, (head, body) in enumerate(records):
        if head is None:
            continue
        translated = batch.get(body)
        if translated:
            records[i] = (head, translated)
            replaced += 1

    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(join_records(records, newline, trailing))

    # 한글이 한 글자도 없으면 아직 손대지 않은 줄로 본다.
    # 이미 바꾼 줄을 원문으로 잘못 세지 않으려면 내용으로 판별해야 한다.
    remaining = sum(1 for head, body in records
                    if head is not None and body.strip() and not HANGUL.search(body))
    unused = [k for k in batch if k not in before]

    print(f"  {name}: {replaced}줄 교체, 아직 영문인 줄 {remaining}개")
    if unused:
        print(f"  원문에 없던 항목 {len(unused)}개:")
        for key in unused[:5]:
            print(f"    {key[:60]}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "dump":
        dump(sys.argv[2])
    elif sys.argv[1] == "apply":
        apply(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
