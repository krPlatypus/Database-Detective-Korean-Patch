import UnityPy, os, collections
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.0f1"
base = r"D:\Program Files (x86)\Steam\steamapps\common\Database Detective\copOS_Data"
for fn in ["resources.assets","sharedassets0.assets","sharedassets1.assets","globalgamemanagers.assets"]:
    env = UnityPy.load(os.path.join(base,fn))
    fonts=[]; sdf=[]
    for o in env.objects:
        if o.type.name=="Font":
            fonts.append(o.read().m_Name)
        elif o.type.name=="MonoBehaviour":
            try:
                n = o.peek_name()
            except Exception:
                continue
            if n and ("SDF" in n or "Font" in n):
                sdf.append(n)
    if fonts or sdf:
        print(f"=== {fn} ===")
        if fonts: print("  Font:", fonts)
        for n in sorted(set(sdf)): print("  MB:", n)
