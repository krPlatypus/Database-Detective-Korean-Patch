"""단서 이미지를 PNG로 뽑아낸다.

챕터별 단서 목록은 숫자 이름을 가진 TextAsset('0'~'9')에 들어 있다.
그 이름으로 Sprite/Texture2D를 찾아 내보내고, 무엇을 찾았는지 색인을 남긴다.

글자가 박힌 이미지는 번역하려면 그림 자체를 고쳐야 하므로,
어떤 이미지가 있고 그 안에 글자가 있는지 눈으로 확인할 목적의 도구다.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "extracted", "images")


def clue_names():
    """숫자 이름 TextAsset에서 단서 이미지 이름을 모은다."""
    env = common.load("resources.assets")
    names = {}
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if not data.m_Name.isdigit():
            continue
        try:
            body = data.m_Script.encode("utf-8", "surrogateescape").decode("utf-8")
        except Exception:
            body = str(data.m_Script)
        for line in body.splitlines():
            line = line.strip()
            if line:
                names.setdefault(line, []).append(data.m_Name)
    return names


def export(obj, name, chapter_tag, seen):
    try:
        image = obj.read().image
    except Exception as exc:
        return {"name": name, "error": str(exc)}

    if image is None:
        return {"name": name, "error": "이미지 없음"}

    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    file_name = f"{safe}.png"
    index = 2
    while file_name in seen:
        file_name = f"{safe}__{index}.png"
        index += 1
    seen.add(file_name)

    path = os.path.join(OUT_DIR, file_name)
    image.save(path)
    return {
        "name": name,
        "file": file_name,
        "size": f"{image.width}x{image.height}",
        "chapters": chapter_tag,
        "type": obj.type.name,
        "source": f"{obj.assets_file.name}:{obj.path_id}",
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    wanted = clue_names()
    print(f"단서 이미지 이름 {len(wanted)}개를 목록에서 찾았습니다.\n")

    records = []
    seen = set()
    found_names = set()

    for file_name in common.ASSET_FILES:
        path = os.path.join(common.DATA_DIR, file_name)
        if not os.path.exists(path):
            continue
        env = common.load(file_name)
        for obj in env.objects:
            if obj.type.name not in ("Sprite", "Texture2D"):
                continue
            try:
                name = obj.peek_name()
            except Exception:
                continue
            if name not in wanted:
                continue
            # Sprite와 Texture2D가 같은 이름으로 겹치면 Texture2D 쪽이 원본이다
            record = export(obj, name, ",".join(sorted(wanted[name])), seen)
            records.append(record)
            if "file" in record:
                found_names.add(name)

    missing = sorted(set(wanted) - found_names)

    with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as f:
        json.dump({"exported": records, "missing": missing}, f, ensure_ascii=False, indent=1)

    ok = [r for r in records if "file" in r]
    print(f"  내보낸 이미지 : {len(ok)}개")
    print(f"  목록에 있으나 못 찾음 : {len(missing)}개 {missing if missing else ''}")
    print(f"  -> {OUT_DIR}")


if __name__ == "__main__":
    main()
