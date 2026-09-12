import UnityPy, sys, collections, os
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.0f1"
base = r"D:\Program Files (x86)\Steam\steamapps\common\Database Detective\copOS_Data"
files = ["resources.assets","sharedassets0.assets","sharedassets1.assets","sharedassets2.assets",
         "globalgamemanagers.assets","level0","level1","level2"]
for f in files:
    p = os.path.join(base,f)
    if not os.path.exists(p): continue
    try:
        env = UnityPy.load(p)
    except Exception as e:
        print(f"{f}: LOAD ERROR {e}"); continue
    c = collections.Counter(o.type.name for o in env.objects)
    print(f"=== {f} ===")
    for k,v in c.most_common(30):
        print(f"   {k:35s} {v}")
