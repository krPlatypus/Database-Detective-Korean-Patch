import UnityPy, os
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.0f1"
base = r"D:\Program Files (x86)\Steam\steamapps\common\Database Detective\copOS_Data"
env = UnityPy.load(os.path.join(base,"resources.assets"))
rows=[]
for o in env.objects:
    if o.type.name != "TextAsset": continue
    d = o.read()
    name = d.m_Name
    try: raw = d.m_Script.encode("utf-8","surrogateescape")
    except Exception: raw = bytes(d.m_Script)
    rows.append((name, len(raw), raw[:16]))
rows.sort(key=lambda r:-r[1])
for n,l,h in rows:
    print(f"{l:9d}  {n:45s}  {h[:12]!r}")
