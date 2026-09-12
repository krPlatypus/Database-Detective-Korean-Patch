"""추출한 텍스트를 번역용 편집 파일로 만든다.

UI 문자열은 translation/ui.json 하나에 모은다 (원문 -> 번역).
TextAsset은 구분자 구조를 사람이 직접 봐야 하므로 파일별 원문 그대로 떨어뜨린다.
번역자는 구분자를 건드리지 않고 텍스트 부분만 고치면 된다.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(ROOT, "extracted")
TRANSLATION = os.path.join(ROOT, "translation")

# 번역해도 의미 없는 것들: 숫자, 기호, 한 글자, 서식 자리표시자만 있는 문자열
NOISE = re.compile(r"^[\s\d\W_]*$")
PLACEHOLDER_ONLY = re.compile(r"^[\s{}\d]*$")


def is_translatable(text):
    stripped = text.strip()
    if len(stripped) < 2:
        return False
    if NOISE.match(stripped) or PLACEHOLDER_ONLY.match(stripped):
        return False
    # 라틴 문자가 하나도 없으면 번역 대상이 아니다
    return bool(re.search(r"[A-Za-z]", stripped))


def safe_name(name, path_id):
    cleaned = re.sub(r"[^A-Za-z0-9가-힣 _-]", "_", name).strip() or "unnamed"
    return f"{cleaned}__{path_id}.txt"


def build_ui_template():
    with open(os.path.join(EXTRACTED, "ui_text.json"), encoding="utf-8") as f:
        entries = json.load(f)

    # 원문 -> 등장 위치들. 번역자가 맥락을 볼 수 있게 남긴다.
    occurrences = {}
    for entry in entries:
        text = entry["text"]
        if not is_translatable(text):
            continue
        occurrences.setdefault(text, []).append(entry["path"] or entry["source"])

    out_path = os.path.join(TRANSLATION, "ui.json")
    existing = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)

    # 기존 번역은 보존하고 새 문자열만 빈칸으로 추가한다
    merged = {text: existing.get(text, "") for text in sorted(occurrences)}

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)

    context_path = os.path.join(TRANSLATION, "ui_context.json")
    with open(context_path, "w", encoding="utf-8") as f:
        json.dump({t: sorted(set(p))[:5] for t, p in sorted(occurrences.items())},
                  f, ensure_ascii=False, indent=1)

    done = sum(1 for v in merged.values() if v.strip())
    return len(merged), done


def build_textasset_templates():
    with open(os.path.join(EXTRACTED, "textassets_translate.json"), encoding="utf-8") as f:
        records = json.load(f)

    out_dir = os.path.join(TRANSLATION, "textassets")
    os.makedirs(out_dir, exist_ok=True)

    manifest = {}
    created = 0
    for record in records:
        path_id = record["source"].split(":")[1]
        file_name = safe_name(record["name"], path_id)
        manifest[file_name] = {"name": record["name"], "source": record["source"]}

        target = os.path.join(out_dir, file_name)
        if not os.path.exists(target):
            # 원문을 그대로 떨어뜨린다. 번역자가 제자리에서 고친다.
            with open(target, "w", encoding="utf-8", newline="") as f:
                f.write(record["text"])
            created += 1

    with open(os.path.join(out_dir, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    return len(records), created


def main():
    os.makedirs(TRANSLATION, exist_ok=True)

    total_ui, done_ui = build_ui_template()
    total_ta, created_ta = build_textasset_templates()

    print(f"  UI 문자열      : {total_ui}개 (번역 완료 {done_ui}개)")
    print(f"                   -> translation/ui.json")
    print(f"  TextAsset      : {total_ta}개 (새로 만든 파일 {created_ta}개)")
    print(f"                   -> translation/textassets/")


if __name__ == "__main__":
    main()
