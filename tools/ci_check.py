"""저장소 안의 것만 보고 할 수 있는 검사.

게임 파일이나 디컴파일 결과가 없어도 돌아가야 한다. GitHub Actions에서
부르는 것이 이것뿐이라, 여기서 막히는 것은 사람이 손볼 것이다.

보는 것:
  1. translation/ 아래 JSON이 전부 읽히는가
  2. 그림 사양의 상자와 색이 제 모양인가
  3. 그림 사양이 가리키는 원본 이름이 서로 겹치지 않는가
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSLATION = os.path.join(ROOT, "translation")
SPECS = os.path.join(TRANSLATION, "images")

problems = []


def note(where, message):
    problems.append(f"{where}: {message}")


def walk(folder, suffix=".json"):
    for base, _, files in os.walk(folder):
        for name in sorted(files):
            if name.endswith(suffix):
                yield os.path.join(base, name)


def load_all():
    """JSON이 전부 읽히는지 보고, 읽힌 것을 돌려준다."""
    loaded = {}
    for path in walk(TRANSLATION):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            with io.open(path, encoding="utf-8") as f:
                loaded[rel] = json.load(f)
        except Exception as error:
            note(rel, f"읽지 못했다 - {error}")
    return loaded


def check_box(where, box):
    if not isinstance(box, list) or len(box) != 4:
        note(where, f"상자는 숫자 넷이어야 한다: {box}")
        return
    if not all(isinstance(v, (int, float)) for v in box):
        note(where, f"상자에 숫자가 아닌 것이 있다: {box}")
        return
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        note(where, f"상자의 오른쪽·아래가 왼쪽·위보다 작다: {box}")


def check_colour(where, colour):
    if not isinstance(colour, list) or len(colour) != 3:
        note(where, f"색은 숫자 셋이어야 한다: {colour}")
        return
    if not all(isinstance(v, int) and 0 <= v <= 255 for v in colour):
        note(where, f"색은 0~255 사이여야 한다: {colour}")


def check_specs(loaded):
    for rel, spec in loaded.items():
        if "/images/" not in rel:
            continue
        if not isinstance(spec, dict):
            note(rel, "사양은 객체여야 한다")
            continue

        for entry in spec.get("erase_boxes", []):
            box = entry.get("box") if isinstance(entry, dict) else entry
            check_box(rel, box)
            if isinstance(entry, dict) and "fill" in entry:
                check_colour(rel, entry["fill"])

        if "erase_fill" in spec:
            check_colour(rel, spec["erase_fill"])

        for entry in spec.get("blocks", []):
            if "text" not in entry or "box" not in entry:
                note(rel, f"문단에 text나 box가 없다: {str(entry)[:60]}")
                continue
            check_box(rel, entry["box"])
            if "color" in entry:
                check_colour(rel, entry["color"])

        for key in ("texts", "overlays"):
            for entry in spec.get(key, []):
                if "text" not in entry or "at" not in entry:
                    note(rel, f"{key}에 text나 at이 없다: {str(entry)[:60]}")
                    continue
                if not isinstance(entry["at"], list) or len(entry["at"]) != 2:
                    note(rel, f"at은 숫자 둘이어야 한다: {entry['at']}")
                if "color" in entry:
                    check_colour(rel, entry["color"])


def check_spec_names():
    """사양 이름이 겹치면 나중 것이 앞의 것을 덮어 그림 하나가 사라진다."""
    seen = {}
    for folder in (SPECS, os.path.join(SPECS, "manual")):
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".json"):
                continue
            stem = os.path.splitext(name)[0]
            if stem in seen:
                note("translation/images", f"이름이 겹친다: {stem} ({seen[stem]}, {folder})")
            seen[stem] = folder


def main():
    loaded = load_all()
    check_specs(loaded)
    check_spec_names()

    if problems:
        print(f"  문제 {len(problems)}건")
        for line in problems:
            print(f"   - {line}")
        sys.exit(1)

    print(f"  JSON {len(loaded)}개, 이상 없음")


if __name__ == "__main__":
    main()
