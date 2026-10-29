"""번역 파일들을 플러그인이 읽을 단일 translation.json으로 묶는다.

UI는 원문 -> 번역 사전이다. 코드가 만들어 내는 고정 문구(dynamic.json)도 여기 합친다.
값이 끼워 넣어진 문장은 정규식 규칙(patterns.json)으로 따로 잡는다.
TextAsset은 원문 전체 -> 번역문 전체로 대응시킨다.
이름이 겹치는 TextAsset이 있어(correct, wrong 등) 이름 대신 원문 내용으로 키를 잡는다.
내용이 바뀌지 않은 파일은 번역하지 않은 것으로 보고 건너뛴다.
"""
import json
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(ROOT, "extracted")
TRANSLATION = os.path.join(ROOT, "translation")
DIST = os.path.join(ROOT, "dist")


PLACEHOLDER = re.compile(r"\{(\d+)\}")


def format_pattern(source, translated):
    """string.Format이 값을 넣은 뒤에도 번역하도록 .NET 정규식을 만든다."""
    parts = PLACEHOLDER.split(source)
    if len(parts) == 1:
        return None
    if set(parts[1::2]) != set(PLACEHOLDER.findall(translated)):
        raise ValueError(f"자리표시자가 다릅니다: {source!r}")
    seen = set()
    pattern = re.escape(parts[0])
    for index in range(1, len(parts), 2):
        number = parts[index]
        pattern += (rf"\k<arg{number}>" if number in seen else rf"(?<arg{number}>.*?)")
        seen.add(number)
        pattern += re.escape(parts[index + 1])
    replacement = PLACEHOLDER.sub(lambda m: "${arg" + m[1] + "}", translated.replace("$", "$$"))
    return {"match": "^" + pattern + "$", "replace": replacement}


def source_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_original(info, records):
    """path_id는 게임 빌드마다 바뀐다. 이름과 검수한 원문 해시로 연결한다."""
    candidates = [r for r in records if r["name"] == info["name"]]
    if info.get("sha256"):
        candidates = [r for r in candidates if source_hash(r["text"]) == info["sha256"]]
    else:
        candidates = [r for r in candidates if r["source"] == info["source"]]
    if len(candidates) != 1:
        raise ValueError(f"원문을 확인할 수 없습니다: {info['name']} ({info['source']}). "
                         "게임 원문 변경을 검수하고 manifest를 갱신하세요.")
    return candidates[0]["text"]


def build(original_records=None):
    with open(os.path.join(TRANSLATION, "ui.json"), encoding="utf-8") as f:
        ui_all = json.load(f)
    ui = {src: dst for src, dst in ui_all.items() if dst.strip()}

    # 코드가 만들어 내는 고정 문구. 추출 대상이 아니라 손으로 관리한다.
    dynamic_path = os.path.join(TRANSLATION, "dynamic.json")
    dynamic_count = 0
    format_patterns = []
    if os.path.exists(dynamic_path):
        with open(dynamic_path, encoding="utf-8") as f:
            for src, dst in json.load(f).items():
                if src.startswith("_") or not dst.strip():
                    continue
                ui[src] = dst
                dynamic_count += 1
                rule = format_pattern(src, dst)
                if rule:
                    format_patterns.append(rule)

    # 값이 끼워 넣어진 문장을 위한 정규식 규칙
    patterns_path = os.path.join(TRANSLATION, "patterns.json")
    patterns = []
    if os.path.exists(patterns_path):
        with open(patterns_path, encoding="utf-8") as f:
            for rule in json.load(f):
                if "match" in rule and "replace" in rule:
                    patterns.append({"match": rule["match"], "replace": rule["replace"]})
    # 구체적인 수동 규칙이 먼저 적용된다 (단위가 들어가는 문장 등).
    patterns.extend(format_patterns)

    if original_records is None:
        with open(os.path.join(EXTRACTED, "textassets_translate.json"), encoding="utf-8") as f:
            original_records = json.load(f)

    ta_dir = os.path.join(TRANSLATION, "textassets")
    manifest_path = os.path.join(ta_dir, "_manifest.json")
    text_assets = {}
    changed = 0

    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        for file_name, info in manifest.items():
            path = os.path.join(ta_dir, file_name)
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            with open(path, encoding="utf-8", newline="") as f:
                translated = f.read()

            original = resolve_original(info, original_records)
            if translated == original:
                continue   # 손대지 않은 파일

            text_assets[original] = translated
            changed += 1

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "translation.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"ui": ui, "textAssets": text_assets, "patterns": patterns},
                  f, ensure_ascii=False, indent=1)

    print(f"  UI 문자열   : {len(ui) - dynamic_count}/{len(ui_all)}개 번역됨")
    print(f"  코드 문구   : {dynamic_count}개")
    print(f"  정규식 규칙 : {len(patterns)}개")
    print(f"  TextAsset   : {changed}개 번역됨")
    print(f"  -> {out}")
    return out


if __name__ == "__main__":
    build()
