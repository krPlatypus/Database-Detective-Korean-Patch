import UnityPy, os
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.0f1"
base = r"D:\Program Files (x86)\Steam\steamapps\common\Database Detective\copOS_Data"
env = UnityPy.load(os.path.join(base,"level1"))
n_tt=0; n_no=0; samples=[]
for o in env.objects:
    if o.type.name!="MonoBehaviour": continue
    try:
        tt = o.get_typetree_node() if hasattr(o,'get_typetree_node') else None
    except Exception:
        tt=None
    try:
        d = o.read_typetree()
        n_tt+=1
        if "m_text" in d and d["m_text"]:
            samples.append(d["m_text"][:60])
    except Exception as e:
        n_no+=1
        if n_no==1: print("read_typetree err:", type(e).__name__, e)
print("typetree ok:",n_tt," failed:",n_no)
print("m_text found:",len(samples))
for s in samples[:15]: print("   ", repr(s))
