"""번역한 화면 문구가 게임 안 어느 쪽에 있는지 찾아 준다.

번역을 눈으로 확인하려면 그 글이 나오는 자리를 게임에서 열어야 하는데,
ui.json에는 원문과 번역만 있어 어디를 열어야 하는지 알 수 없다.

이 게임의 웹 화면은 프리팹 하나가 한 쪽에 대응하고, 그 프리팹 이름이
곧 주소다(newhampshire.wiki-classes 처럼). 그래서 TMP 컴포넌트에서
부모를 타고 올라가다 주소처럼 생긴 이름을 만나면 그것이 그 글이 있는
쪽이다. 주소가 아닌 것(설정 창 같은 것)은 가장 바깥 이름을 쓴다.
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "translation", "ui.json")
OUT = os.path.join(ROOT, "extracted", "text_locations.json")

URL = re.compile(r"\.(com|net|org|wiki)\b")


def roots_by_file():
    """파일별로 {GameObject path_id: (이름, 부모 path_id)}를 만든다."""
    scripts = common.script_path_ids("TextMeshProUGUI", "TextMeshPro")
    ugui = scripts.get("TextMeshProUGUI", set())
    world = scripts.get("TextMeshPro", set())
    every = ugui | world
    nodes = {
        "TextMeshProUGUI": common.nodes_for("Unity.TextMeshPro.dll", "TMPro.TextMeshProUGUI"),
        "TextMeshPro": common.nodes_for("Unity.TextMeshPro.dll", "TMPro.TextMeshPro"),
    }

    found = defaultdict(set)
    for file_name in common.ASSET_FILES:
        path = os.path.join(common.DATA_DIR, file_name)
        if not os.path.exists(path):
            continue

        env = common.load(file_name)
        objects = {o.path_id: o for o in env.objects}

        # GameObject -> 그 오브젝트의 Transform, Transform -> 부모 Transform
        transform_of, parent_of, name_of = {}, {}, {}
        for obj in env.objects:
            if obj.type.name == "GameObject":
                try:
                    go = obj.read()
                except Exception:
                    continue
                name_of[obj.path_id] = go.m_Name
                for comp in go.m_Component:
                    child = objects.get(comp.component.path_id)
                    if child is not None and child.type.name in ("Transform", "RectTransform"):
                        transform_of[obj.path_id] = child.path_id
            elif obj.type.name in ("Transform", "RectTransform"):
                try:
                    tr = obj.read()
                except Exception:
                    continue
                parent_of[obj.path_id] = (tr.m_Father.path_id, tr.m_GameObject.path_id)

        def page_for(game_object_id):
            """부모를 타고 올라가며 주소처럼 생긴 이름을 찾는다."""
            seen, outermost = set(), name_of.get(game_object_id, "?")
            current = transform_of.get(game_object_id)
            while current and current not in seen:
                seen.add(current)
                parent, owner = parent_of.get(current, (0, None))
                name = name_of.get(owner)
                if name:
                    outermost = name
                    if URL.search(name):
                        return name
                if not parent:
                    break
                current = parent
            return outermost

        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                mb = obj.read(check_read=False)
                script = mb.m_Script
                if script.m_FileID != 0 and script.m_PathID in every:
                    kind = "TextMeshProUGUI" if script.m_PathID in ugui else "TextMeshPro"
                    data = obj.read_typetree(nodes[kind])
                else:
                    continue
            except Exception:
                continue

            text = data.get("m_text") or ""
            if not text.strip():
                continue
            found[text].add(page_for(mb.m_GameObject.path_id))

    return found


def main():
    with open(UI, encoding="utf-8") as f:
        ui = json.load(f)

    where = roots_by_file()

    pages = defaultdict(list)
    for text, translated in ui.items():
        if text.startswith("_") or not translated.strip():
            continue
        for page in where.get(text, {"(찾지 못함)"}):
            pages[page].append(text)

    report = {page: len(items) for page, items in sorted(pages.items())}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({page: sorted(items) for page, items in sorted(pages.items())},
                  f, ensure_ascii=False, indent=1)

    web = {p: n for p, n in report.items() if URL.search(p)}
    print(f"  번역문이 있는 자리 {len(report)}곳")
    print(f"  그중 웹 화면 {len(web)}쪽:")
    for page, count in sorted(web.items(), key=lambda kv: -kv[1]):
        print(f"    {count:4d}개  {page}")
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
