"""번역 배치 파일을 translation/ui.json에 반영한다."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "translation", "ui.json")


def main(batch_path):
    with open(batch_path, encoding="utf-8") as f:
        batch = json.load(f)
    with open(TARGET, encoding="utf-8") as f:
        current = json.load(f)

    applied = []
    unknown = []
    for source, translated in batch.items():
        if source in current:
            current[source] = translated
            applied.append(source)
        else:
            unknown.append(source)

    with open(TARGET, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=1)

    done = sum(1 for v in current.values() if v.strip())
    print(f"  적용 {len(applied)}개, 원문에 없는 키 {len(unknown)}개")
    for key in unknown:
        print(f"    없음: {key!r}")
    print(f"  번역 진행: {done}/{len(current)}")


if __name__ == "__main__":
    main(sys.argv[1])
