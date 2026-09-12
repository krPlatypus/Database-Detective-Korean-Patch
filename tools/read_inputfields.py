import UnityPy, os, json
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
UnityPy.config.FALLBACK_UNITY_VERSION = "6000.5.5f1"
base = r"D:\Program Files (x86)\Steam\steamapps\common\Database Detective\copOS_Data"
gen = TypeTreeGenerator("6000.5.5f1")
gen.load_local_dll_folder(os.path.join(base,"Managed"))
nodes = json.loads(gen.get_nodes_as_json("Unity.TextMeshPro.dll","TMPro.TMP_InputField"))

ggm = UnityPy.load(os.path.join(base,"globalgamemanagers.assets"))
tset = {o.path_id for o in ggm.objects if o.type.name=="MonoScript" and o.read().m_ClassName=="TMP_InputField"}

LINETYPE={0:"SingleLine",1:"MultiLineSubmit",2:"MultiLineNewline"}
INPUTTYPE={0:"Standard",1:"AutoCorrect",2:"Password"}
total=0
for fn in ["resources.assets","level1","level0","level2","sharedassets0.assets","sharedassets1.assets"]:
    env = UnityPy.load(os.path.join(base, fn))
    for o in env.objects:
        if o.type.name!="MonoBehaviour": continue
        try:
            mb=o.read(check_read=False)
            if mb.m_Script.m_FileID==0 or mb.m_Script.m_PathID not in tset: continue
        except Exception: continue
        try: d=o.read_typetree(nodes)
        except Exception as e:
            print(f"  {fn} {o.path_id} FAIL {e}"); continue
        go=None
        try: go=mb.m_GameObject.read().m_Name
        except Exception: pass
        total+=1
        print(f"{fn:18s} {o.path_id:<12} GO={str(go):26s} lineType={LINETYPE.get(d.get('m_LineType')):16s} "
              f"charLimit={d.get('m_CharacterLimit'):<5} lineLimit={d.get('m_LineLimit')} "
              f"richText={d.get('m_RichText')} readOnly={d.get('m_ReadOnly')}")
print("TOTAL:",total)
