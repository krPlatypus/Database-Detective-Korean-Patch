"""게임 애셋 접근 공통 헬퍼."""
import json
import os

import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

GAME_DIR = r"D:\Program Files (x86)\Steam\steamapps\common\Database Detective"
DATA_DIR = os.path.join(GAME_DIR, "copOS_Data")
MANAGED_DIR = os.path.join(DATA_DIR, "Managed")
UNITY_VERSION = "6000.5.5f1"

# 텍스트가 들어 있는 파일들. globalgamemanagers.assets는 MonoScript 표라 별도로 쓴다.
ASSET_FILES = [
    "resources.assets",
    "level0",
    "level1",
    "level2",
    "sharedassets0.assets",
    "sharedassets1.assets",
    "sharedassets2.assets",
]

UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION

_generator = None


def generator():
    global _generator
    if _generator is None:
        _generator = TypeTreeGenerator(UNITY_VERSION)
        _generator.load_local_dll_folder(MANAGED_DIR)
    return _generator


def nodes_for(assembly, fullname):
    """MonoBehaviour를 읽기 위한 타입트리를 list[dict] 형태로 돌려준다."""
    return json.loads(generator().get_nodes_as_json(assembly, fullname))


def script_path_ids(*class_names):
    """globalgamemanagers.assets의 MonoScript 표에서 클래스명 -> path_id 집합."""
    wanted = set(class_names)
    env = UnityPy.load(os.path.join(DATA_DIR, "globalgamemanagers.assets"))
    found = {}
    for obj in env.objects:
        if obj.type.name != "MonoScript":
            continue
        name = obj.read().m_ClassName
        if name in wanted:
            found.setdefault(name, set()).add(obj.path_id)
    return found


def load(file_name):
    return UnityPy.load(os.path.join(DATA_DIR, file_name))


def game_object_path(mono_behaviour):
    """MonoBehaviour가 붙은 GameObject의 계층 경로. 번역 대상 식별용."""
    try:
        go = mono_behaviour.m_GameObject.read()
    except Exception:
        return None

    parts = [go.m_Name]
    seen = 0
    try:
        transform = go.m_Transform.read()
    except Exception:
        return go.m_Name

    while seen < 12:
        seen += 1
        try:
            parent_ptr = transform.m_Father
            if parent_ptr.m_PathID == 0:
                break
            transform = parent_ptr.read()
            parts.append(transform.m_GameObject.read().m_Name)
        except Exception:
            break

    return "/".join(reversed(parts))
