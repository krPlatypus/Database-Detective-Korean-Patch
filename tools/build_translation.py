"""번역 파일들을 플러그인이 읽을 단일 translation.json으로 묶는다.

UI는 원문 -> 번역 사전이다. 코드가 만들어 내는 고정 문구(dynamic.json)도 여기 합친다.
값이 끼워 넣어진 문장은 정규식 규칙(patterns.json)으로 따로 잡는다.
TextAsset은 원문 전체 -> 번역문 전체로 대응시킨다.
이름이 겹치는 TextAsset이 있어(correct, wrong 등) 이름 대신 원문 내용으로 키를 잡는다.
내용이 바뀌지 않은 파일은 번역하지 않은 것으로 보고 건너뛴다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(ROOT, "extracted")
TRANSLATION = os.path.join(ROOT, "translation")
DIST = os.path.join(ROOT, "dist")


def build():
    with open(os.path.join(TRANSLATION, "ui.json"), encoding="utf-8") as f:
        ui_all = json.load(f)
    ui = {src: dst for src, dst in ui_all.items() if dst.strip()}

    # 코드가 만들어 내는 고정 문구. 추출 대상이 아니라 손으로 관리한다.
    dynamic_path = os.path.join(TRANSLATION, "dynamic.json")
    dynamic_count = 0
    if os.path.exists(dynamic_path):
        with open(dynamic_path, encoding="utf-8") as f:
            for src, dst in json.load(f).items():
                if src.startswith("_") or not dst.strip():
                    continue
                ui[src] = dst
                dynamic_count += 1

    # 값이 끼워 넣어진 문장을 위한 정규식 규칙
    patterns_path = os.path.join(TRANSLATION, "patterns.json")
    patterns = []
    if os.path.exists(patterns_path):
        with open(patterns_path, encoding="utf-8") as f:
            for rule in json.load(f):
                if "match" in rule and "replace" in rule:
                    patterns.append({"match": rule["match"], "replace": rule["replace"]})

    with open(os.path.join(EXTRACTED, "textassets_translate.json"), encoding="utf-8") as f:
        originals = {r["source"]: r["text"] for r in json.load(f)}

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
                continue
            with open(path, encoding="utf-8", newline="") as f:
                translated = f.read()

            original = originals.get(info["source"])
            if original is None or translated == original:
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


if __name__ == "__main__":
    build()
