"""몹 이름과 무기 어휘를 원문으로 되돌리고, '적'을 '몹'으로 고친다.

두 가지를 한다.

1. 조회 대상 값으로 쓰이는 낱말의 번역을 지운다.
   DamageLogGenerator의 enum이 그대로 테이블에 들어간다. 무기는
   'Rare Burning Sword'처럼 등급·효과·종류를 이어 붙여 inventory.weapon_name과
   damage_log.weapon_used에 넣고, 몹은 'Slimehead #17'처럼 번호를 붙여
   damage_log.character_damaged에 넣는다. 'Corrupted'는 lsat.cs가 플레이어가
   친 글자와 그대로 비교하기까지 한다. 위키에서 한글로 읽고 그 말을 쿼리에
   적으면 아무것도 나오지 않는다.

2. 적 -> 몹.
   이 위키는 게임 속 MMO의 팬 위키다. 플레이어 캐릭터가 아닌 것을 가리킬 때는
   '적'보다 '몹'이 그 바닥 말씨에 맞는다. 다만 사람이 사람을 적대하는 자리
   (도시 밖의 다른 플레이어, 길드끼리의 싸움)에서는 '적'이 맞으므로 둔다.
"""
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "translation", "ui.json")

# 테이블에 들어가는 값. 번역을 지우고 원문을 쓴다.
DATA_VALUES = [
    # DamageLogGenerator.Weapons
    "Sword", "Dagger", "Mace", "Axe",
    # DamageLogGenerator.WeaponEffects
    "Burning", "Poisoned", "Electrified", "Rusted",
    # DamageLogGenerator.WeaponRarity
    "Rare", "Special", "Uncommon",
    # 몹 이름. damage_log.character_damaged에 번호와 함께 들어간다.
    "Corrupted", "Slimehead", "Slime Father", "Skeletal Warrior", "Lost Peasant",
    # 직업 특수 능력. 값은 아니지만 본문에서 원문으로 쓰고 있어 맞춘다.
    "First Strike", "Sing",
]

# 적 -> 몹. 원문 키로 찾아 값만 바꾼다.
TERM_FIXES = {
    "Enemy Descriptions": ("적 설명", "몹 설명"),
    "World: Enemies": ("세계: 적", "세계: 몹"),
    "<i>The Legends of New Hampshire</i> utilizes a turn based combat system based around these six rules:\n"
    "    1. There can only be two combatants per combat encounter.\n"
    "    2. Player characters initiating combat always attack first.\n"
    "    3. Non player enemy characters never attack first. \n"
    "    4. Combat ends only when one of the two combatants dies.\n"
    "    5. The only time players cannot heal or equip new weapons\n"
    "        is during combat.\n"
    "    6. Entering a new location forces a non-player enemy\n"
    "        combat encounter.\n\n": [("적 NPC는 절대", "몹은 절대"), ("적 NPC와의 전투가", "몹과의 전투가")],
}

# 키가 길어 통째로 적기 번거로운 것은 조각으로 찾는다.
LOOSE_FIXES = [
    ("No one said that being an adventurer", [("적 NPC와의 전투", "몹과의 전투"),
                                              ("어떤 적이 나오는지", "어떤 몹이 나오는지")]),
    ("The game's damage log displays each", [("적 캐릭터가 피해를", "몹이 피해를")]),
    ("When a character is damaged, the damage log", [("아니라면 적 이름이", "아니라면 몹 이름이")]),
    ("takes place in the fictional province", [("적 NPC와 전투", "몹과 전투")]),
    ("Entering any location outside", [("적 NPC", "몹")]),
]


def main():
    with open(UI, encoding="utf-8") as f:
        ui = json.load(f, object_pairs_hook=OrderedDict)

    cleared = []
    for key in DATA_VALUES:
        if key in ui and ui[key].strip():
            cleared.append((key, ui[key]))
            ui[key] = ""

    changed = []
    for key, rules in TERM_FIXES.items():
        if key not in ui:
            print(f"  키를 찾지 못했다: {key[:50]!r}")
            continue
        rules = rules if isinstance(rules, list) else [rules]
        for old, new in rules:
            if old in ui[key]:
                ui[key] = ui[key].replace(old, new)
                changed.append((key[:40], old, new))

    for needle, rules in LOOSE_FIXES:
        for key in ui:
            if key.startswith("_") or needle not in key:
                continue
            for old, new in rules:
                if old in ui[key]:
                    ui[key] = ui[key].replace(old, new)
                    changed.append((key[:40], old, new))

    with open(UI, "w", encoding="utf-8") as f:
        json.dump(ui, f, ensure_ascii=False, indent=1)

    print(f"  원문으로 되돌림 {len(cleared)}개")
    for key, was in cleared:
        print(f"    {key!r} (was {was!r})")
    print(f"  적 -> 몹 {len(changed)}군데")
    for key, old, new in changed:
        print(f"    [{key}...] {old!r} -> {new!r}")


if __name__ == "__main__":
    main()
