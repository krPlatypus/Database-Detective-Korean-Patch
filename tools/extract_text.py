"""게임에서 번역 대상 텍스트를 뽑아낸다.

두 갈래가 있다.
  1. 씬/프리팹에 구워진 TMP 텍스트 (UI 라벨, 버튼, 창 제목)
  2. TextAsset (스토리 대사, 힌트, 그리고 SQL 조회 대상 데이터)

SQL 조회 대상 데이터(이름 목록, 영화 제목 등)는 번역하면 플레이어가 쿼리를
못 쓰게 되므로 KEEP_ORIGINAL로 분류해 번역 대상에서 뺀다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extracted")

# SQL 쿼리 대상 데이터. 번역하면 게임이 깨진다.
KEEP_ORIGINAL = {
    "female-first-names", "male-first-names", "last-names", "science", "movies",
    "crops", "family-tree", "players", "player_descriptions", "payup",
    "economics", "squadrons", "philosophy", "foods",
    "animals", "car-parts", "hair-colors", "eye-colors", "farms", "movies_favs",
}

# 아래 셋은 여기 있었으나 뺐다. 칸 전체가 조회 대상인 줄 알았는데, 사람이 읽는
# 소개글 칸은 화면에 찍히기만 하고 테이블에 들어가지 않았다. 칸마다 쓰임이
# 달라 파일 단위로 가르면 놓친다.
#
#   guilds          코드;이름;소개;가입조건
#                   뒤 두 칸만 화면용. LoadGuildProfiles가 GuildProfile로 들고 있다.
#   broker-traders  회사명;주소;소개
#                   소개만 화면용. broker_search가 bio.text에 그대로 넣는다.
#   profiles        아이디;소개;사진;영화;평점;후기
#                   소개와 후기만 화면용. LoadProfileDownloads가 이 둘을 버리고
#                   (title, rating)만 reviews 테이블에 넣는다.
#
# 나머지 칸(코드, 회사명, 아이디, 영화 제목, 평점)은 플레이어가 쿼리에 적는
# 값이므로 번역할 때 원문을 지켜야 한다.

# TMP 내부 설정이거나 게임 텍스트가 아닌 것.
SKIP = {
    "LineBreaking Following Characters", "LineBreaking Leading Characters",
    "PerformanceTestRunInfo", "PerformanceTestRunSettings", "songs",
}


def extract_tmp_text():
    """씬/프리팹의 TMP 컴포넌트에서 표시 문자열을 뽑는다."""
    scripts = common.script_path_ids("TextMeshProUGUI", "TextMeshPro")
    ugui_ids = scripts.get("TextMeshProUGUI", set())
    world_ids = scripts.get("TextMeshPro", set())
    all_ids = ugui_ids | world_ids

    nodes = {
        "TextMeshProUGUI": common.nodes_for("Unity.TextMeshPro.dll", "TMPro.TextMeshProUGUI"),
        "TextMeshPro": common.nodes_for("Unity.TextMeshPro.dll", "TMPro.TextMeshPro"),
    }

    entries = []
    for file_name in common.ASSET_FILES:
        path = os.path.join(common.DATA_DIR, file_name)
        if not os.path.exists(path):
            continue

        env = common.load(file_name)
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                mb = obj.read(check_read=False)
                script = mb.m_Script
                if script.m_FileID == 0 or script.m_PathID not in all_ids:
                    continue
            except Exception:
                continue

            kind = "TextMeshProUGUI" if script.m_PathID in ugui_ids else "TextMeshPro"
            try:
                data = obj.read_typetree(nodes[kind])
            except Exception:
                continue

            text = (data.get("m_text") or "").strip()
            if not text:
                continue

            entries.append({
                "source": f"{file_name}:{obj.path_id}",
                "path": common.game_object_path(mb),
                "text": data["m_text"],
            })

    return entries


def _body(data):
    try:
        return data.m_Script.encode("utf-8", "surrogateescape").decode("utf-8")
    except Exception:
        return str(data.m_Script)


def extract_text_assets():
    """TextAsset을 번역 대상과 원문 유지로 나눠 뽑는다."""
    env = common.load("resources.assets")
    translate, keep = [], []

    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        name = data.m_Name
        if name in SKIP:
            continue

        # 숫자 이름 TextAsset('0'~'9')은 챕터별 단서 이미지의 애셋 이름 목록이다.
        # 번역하면 게임이 단서 이미지를 찾지 못한다.
        if name.isdigit():
            keep.append({"name": name, "source": f"resources.assets:{obj.path_id}",
                         "text": _body(data)})
            continue

        body = _body(data)
        if not body.strip():
            continue

        record = {"name": name, "source": f"resources.assets:{obj.path_id}", "text": body}
        (keep if name in KEEP_ORIGINAL else translate).append(record)

    return translate, keep


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("씬/프리팹의 TMP 텍스트 추출 중...")
    tmp_entries = extract_tmp_text()

    print("TextAsset 추출 중...")
    translate, keep = extract_text_assets()

    with open(os.path.join(OUT_DIR, "ui_text.json"), "w", encoding="utf-8") as f:
        json.dump(tmp_entries, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "textassets_translate.json"), "w", encoding="utf-8") as f:
        json.dump(translate, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "textassets_keep_original.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=1)

    unique = {}
    for entry in tmp_entries:
        unique.setdefault(entry["text"], 0)
        unique[entry["text"]] += 1

    print()
    print(f"  TMP 텍스트 컴포넌트   : {len(tmp_entries):5d}개")
    print(f"  그중 고유 문자열      : {len(unique):5d}개")
    print(f"  번역 대상 TextAsset   : {len(translate):5d}개 "
          f"({sum(len(r['text']) for r in translate):,}자)")
    print(f"  원문 유지 TextAsset   : {len(keep):5d}개 "
          f"({sum(len(r['text']) for r in keep):,}자)")
    print()
    print(f"  -> {OUT_DIR}")


if __name__ == "__main__":
    main()
