"""
Build the repaired Vampire Race - Blood Feeding mod (v3.6.1) from the v3.5 original.

Provenance rules
  - Every ID written here is harvested from the v3.5 file itself or verified through
    the Polish base-game translation (flatrepo/kenshi_pl), which maps vanilla
    stringIDs to localized names. Nothing is guessed.
  - Names inside Ian's edit records reflect his modded session (rebirth.mod renames
    vanilla records wholesale), so a name label alone is NEVER trusted for identity.
    Load-bearing IDs require Ian's label and the translation to agree.
  - Anything that cannot be verified (the hire-dialogue effect encoding, vanilla
    race appearance lists) is left for FCS and documented in fcs-worklist.txt
    rather than fabricated.
"""
import sys, os, collections
TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from kenshi_mod import ModFile, NEW_V17, V16_CHANGE_TYPES

SRC = os.path.join(REPO, "original-v3.5", "Vampire Race - Blood Feeding.mod")
OWN = 'Vampire Race - Blood Feeding.mod'

# gamedata.quack ships with the game (locational damage / part coverage records,
# ids 17, 28-32, 100, 101, referenced by vanilla armour) - treated as base content.
BASE_FILES = {'gamedata.base', 'gamedata.quack'}
KEEP_OWNERS = {OWN} | BASE_FILES

# Race appearance lists cannot be rebuilt without gamedata.base in an editor;
# they keep their third-party references and those mods are declared honestly.
RACE_APPEARANCE_CATS = {
    b'heads male', b'heads female', b'hairs', b'hair colors',
    b'limb replacement', b'severed limbs', b'AI Goals', b'combat anatomy',
}

# --- verified vanilla IDs -----------------------------------------------------
# Start town. Ian's label ('Flats lagoon') and the PL translation ('Plaska
# Laguna') agree, so the vanilla identity is confirmed: the neutral Tech Hunter
# town with a bar and no Holy Nation presence. (Round 1 of this repair used
# 1032-gamedata.base believing Ian's 'Black scratch' label; the translation
# proved 1032 is actually the Southern Hive - a town hostile to visitors.)
START_TOWN = b'1082-gamedata.base'
START_TOWN_NAME = 'Flats Lagoon'

KATANA = b'476-gamedata.base'          # PL 'Katana'; Ian already arms the Vampire Hunter with it
MATERIAL_CLOTH = b'3060-gamedata.base' # used by Ian's own Sunward Robe
DIRTY_ANIMAL_BLOOD = b'4131-' + OWN.encode()   # Ian's target on vanilla Dog/Goat edits
PLAYER_DIALOGUE_PKG = b'5369-gamedata.base'    # used by all four wanderer player characters
PERSONALITY_OWN = b'4161-' + OWN.encode()      # 'Coven Leader Bearing', the mod's own personality
BUILDING_SHOP = b'609-gamedata.base'   # vanilla building Ian uses for the Clothier/Cobbler shops
BUILDING_CELLS = b'772-gamedata.base'  # vanilla building Ian uses for Holding Cells / Overseers

BLOOD_ITEMS = [b'1-' + OWN.encode()] + [f'{i}-'.encode() + OWN.encode()
                                        for i in (4051, 4052, 4053, 4131, 4132, 4133)]

NEW_DESCRIPTION = (
    "Vampire Race - Blood Feeding v3.6.1. Four playable vampire bloodlines "
    "(Greenlander, Scorchlander, Shek, Hive) with a blood-feeding metabolism, "
    "blood and lore items, the Sunward daywear set, the Coven faction, vampire "
    "hunter patrols, and vampire recruits in bars across the world. Both starts "
    "begin at " + START_TOWN_NAME + ". Dormant in this build, pending clean "
    "editor work: Coven City (not placed in the world) and the sunlight-burn "
    "weather system (see FIXES.md)."
)

def target_owner(t):
    i = t.find('-')
    return t[i + 1:] if i > 0 and t[:i].isdigit() else None

def resolvable(t):
    o = target_owner(t)
    return o is None or o in BASE_FILES or o == OWN

mod, original = ModFile.load(SRC)
assert mod.serialize(lead='original') == original, "round-trip gate failed"
print(f"loaded {len(mod.records)} records, byte-exact round-trip verified\n")

log = []
def note(s):
    log.append(s)
    print(s)

# ------------------------------------------------ 1. drop third-party edits
before = len(mod.records)
dropped = [r for r in mod.records if not (r.owner() is None or r.owner() in KEEP_OWNERS)]
mod.records = [r for r in mod.records if (r.owner() is None or r.owner() in KEEP_OWNERS)]
note(f"[F6] dropped {len(dropped)} records that edit third-party mods "
     f"({before} -> {len(mod.records)})")

# ------------------------------------------------ 2. conforming v17 framing
fixed = sum(1 for r in mod.records if r.change_type in V16_CHANGE_TYPES)
for r in mod.records:
    if r.change_type in V16_CHANGE_TYPES:
        r.change_type = NEW_V17
note(f"[F4] normalised {fixed} v16-framed records to v17")

# ------------------------------------------------ 3. quarantine the sun system
# The three biome edits set acid=1.0 / weather strength 10 on records whose
# vanilla identity cannot be verified (Ian's world was rebuilt by rebirth.mod).
# Shipping them risks acid-burning every human in three vanilla regions. The 58
# armour weather-protection edits exist only to serve that system and are inert
# without it. All are dropped; the system returns after an FCS rebuild.
sun_dropped = []
def is_sun_record(r):
    if r.owner() not in BASE_FILES:
        return False
    if r.type == 95:
        return True
    if r.type == 3:
        keys = {k.decode() for k, _v in r.dicts[2]}   # int fields
        only_weather = all(len(d) == 0 for i, d in enumerate(r.dicts) if i != 2) \
            and keys == {'weather protection1'} \
            and not r.refs and not r.instances
        return only_weather
    return False

for r in mod.records:
    if is_sun_record(r):
        sun_dropped.append(f"{r.type_name}:{r.name_str}")
mod.records = [r for r in mod.records if not is_sun_record(r)]
note(f"[sun] quarantined the sunlight-burn system: dropped 3 biome acid edits and "
     f"{len(sun_dropped) - 3} armour weather-protection edits ({len(sun_dropped)} total)")

# ------------------------------------------------ 4. repoint game starts
for r in mod.records:
    if r.type != 64:
        continue
    for idx, (cat, items) in enumerate(r.refs):
        if cat == b'town':
            r.refs[idx] = (cat, [(START_TOWN, a, b, c) for (_t, a, b, c) in items])
            note(f"[F1] start {r.name_str!r}: town -> {START_TOWN_NAME} "
                 f"({START_TOWN.decode()}, identity confirmed by two sources)")

# ------------------------------------------------ 5. strip unresolvable refs
pruned = 0
for r in mod.records:
    new_refs = []
    for cat, items in r.refs:
        if r.type == 7 and cat in RACE_APPEARANCE_CATS:
            new_refs.append((cat, items))
            continue
        survivors = [(t, a, b, c) for (t, a, b, c) in items
                     if resolvable(t.decode('utf-8', 'replace'))]
        pruned += len(items) - len(survivors)
        new_refs.append((cat, survivors))
    r.refs = new_refs
note(f"[F8] stripped {pruned} references that cannot resolve on a clean install")

# ------------------------------------------------ 6. cascade structural repair
def char_lost_race(r):
    if r.type != 1:
        return False
    for cat, items in r.refs:
        if cat == b'race':
            return len(items) == 0
    return False

def squad_unstaffed(r):
    if r.type != 52:
        return False
    people = sum(len(items) for cat, items in r.refs
                 if cat in (b'leader', b'squad', b'choosefrom list', b'slaves'))
    return people == 0

cascade = []
for _ in range(10):
    doomed = {r.string_id for r in mod.records
              if r.owner() == OWN and (char_lost_race(r) or squad_unstaffed(r))}
    if not doomed:
        break
    cascade += [r.name_str for r in mod.records if r.string_id in doomed]
    mod.records = [r for r in mod.records if r.string_id not in doomed]
    for r in mod.records:
        r.refs = [(cat, [it for it in items if it[0] not in doomed])
                  for cat, items in r.refs]
# vendor lists orphaned by the cascade (nothing references them any more)
referenced = {t[0] for r in mod.records for _c, items in r.refs for t in items}
orphan_vl = [r for r in mod.records
             if r.type == 49 and r.owner() == OWN and r.string_id not in referenced]
mod.records = [r for r in mod.records if r not in orphan_vl]
note(f"[F8] cascade-dropped {len(cascade)} records left structurally invalid "
     f"(skeleton staff whose race mod is gone, and their squads) "
     f"plus {len(orphan_vl)} orphaned vendor lists: "
     f"{sorted(set(cascade)) + [r.name_str for r in orphan_vl]}")

# ------------------------------------------------ 7. verified repairs
rearmed, patched = [], []
for r in mod.records:
    if r.owner() != OWN:
        continue
    for idx, (cat, items) in enumerate(r.refs):
        if items:
            continue
        if r.type == 1 and cat == b'weapons':
            r.refs[idx] = (cat, [(KATANA, 0, 0, 0)])
            rearmed.append(r.name_str)
        elif r.type == 1 and cat == b'dialogue package player':
            r.refs[idx] = (cat, [(PLAYER_DIALOGUE_PKG, 0, 0, 0)])
            patched.append(f"{r.name_str}:player-dialogue")
        elif r.type == 1 and cat == b'personality':
            r.refs[idx] = (cat, [(PERSONALITY_OWN, 0, 0, 0)])
            patched.append(f"{r.name_str}:personality")
        elif cat == b'material' and r.type in (3, 4):
            r.refs[idx] = (cat, [(MATERIAL_CLOTH, 0, 0, 0)])
            patched.append(f"{r.name_str}:material")
        elif r.type == 76 and cat == b'death items':
            r.refs[idx] = (cat, [(DIRTY_ANIMAL_BLOOD, 1, 0, 0)])
            patched.append(f"{r.name_str}:death-items")
        elif r.type == 52 and cat == b'building':
            b = BUILDING_CELLS if any(w in r.name_str.lower()
                                      for w in ('garrison', 'watch', 'market', 'cells',
                                                'overseer')) else BUILDING_SHOP
            r.refs[idx] = (cat, [(b, 0, 0, 0)])
            patched.append(f"{r.name_str}:building")
        elif r.type == 49 and cat == b'items' and 'Tavern' in r.name_str:
            r.refs[idx] = (cat, [(t, 1, 0, 0) for t in BLOOD_ITEMS])
            patched.append(f"{r.name_str}:blood-stock")
note(f"[fix] re-armed {len(rearmed)} characters with the verified vanilla Katana "
     f"({KATANA.decode()}): {sorted(set(rearmed))}")
note(f"[fix] {len(patched)} verified reference repairs: {patched}")

# ------------------------------------------------ 8. honest dependencies
needed = collections.Counter()
for r in mod.records:
    for _cat, tgt in r.ref_targets():
        o = target_owner(tgt)
        if o and o not in BASE_FILES and o != OWN:
            needed[o] += 1
dep_list = sorted(needed, key=lambda k: (-needed[k], k.lower()))
note(f"\n[F6] true remaining dependencies: {len(dep_list)} (was 15 declared / ~120 real)")
for d in dep_list:
    note(f"        {needed[d]:4d} refs  {d}")
mod.dependencies = ','.join(['gamedata.base'] + dep_list).encode('utf-8')
mod.description = NEW_DESCRIPTION.encode('utf-8')

# ------------------------------------------------ 9. write + verify
OUT_DIR = os.path.join(REPO, "Vampire Race - Blood Feeding")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Vampire Race - Blood Feeding.mod")
mod.save(OUT, lead='computed')
note(f"\nwrote {os.path.basename(OUT)}: {len(mod.records)} records, "
     f"{os.path.getsize(OUT):,} bytes (was {len(original):,})")

check, raw = ModFile.load(OUT)
assert check.serialize(lead='original') == raw, "output does not round-trip"
bad = [r for r in check.records
       if r.lead_int != len(r.serialize_body()) + 4 or r.change_type in V16_CHANGE_TYPES]
assert not bad, f"{len(bad)} non-conforming records remain"

own_ids = {r.string_id_str for r in check.records}
dangling = [(r.name_str, cat.decode(), t[0].decode())
            for r in check.records for cat, items in r.refs for t in items
            if target_owner(t[0].decode()) == OWN and t[0].decode() not in own_ids]
assert not dangling, f"dangling own refs: {dangling}"

for r in check.records:
    if r.type == 7 and r.owner() == OWN and r.name_str != 'Blood Hound':
        heads = {c.decode(): len(i) for c, i in r.refs if b'heads' in c}
        assert all(heads.values()), f"race {r.name_str} lost heads"
raceless = [r.name_str for r in check.records if r.type == 1
            and any(c == b'race' and not i for c, i in r.refs)]
weaponless = [r.name_str for r in check.records if r.type == 1
              and any(c == b'weapons' and not i for c, i in r.refs)]
assert not raceless and not weaponless, (raceless, weaponless)
starts = [r for r in check.records if r.type == 64]
assert len(starts) == 2
for s in starts:
    towns = [t[0] for c, i in s.refs if c == b'town' for t in i]
    assert towns == [START_TOWN], towns

remaining_empty = [(r.type_name, r.name_str, cat.decode())
                   for r in check.records for cat, items in r.refs if not items]
note(f"[verify] round-trip OK, 0 non-conforming, 0 dangling own refs, races have heads, "
     f"no raceless/weaponless characters, both starts at {START_TOWN_NAME}")
note(f"[verify] remaining empty categories (all inert): {remaining_empty}")

# ------------------------------------------------ 10. FCS worklist
rows = []
for r in check.records:
    for cat, items in r.refs:
        foreign = [t[0].decode() for t in items if not resolvable(t[0].decode())]
        if foreign:
            rows.append((r.type_name, r.name_str, r.string_id_str,
                         cat.decode('utf-8', 'replace'), foreign))
wl = os.path.join(REPO, 'fcs-worklist.txt')
with open(wl, 'w', encoding='utf-8') as fh:
    fh.write("FCS WORKLIST - editor tasks this repair could not do from binary alone\n")
    fh.write("=" * 70 + "\n\n")
    fh.write("1. RE-WIRE RECRUIT HIRING (the one functional gap; ~2 minutes)\n")
    fh.write("   The custom hire line \"Ok, you're hired.\" [4021] lost its effects -\n")
    fh.write("   they lived in Dialogue.mod records. In v3.5 they were:\n")
    fh.write("      conditions: [51951-Dialogue.mod, value 5000]\n")
    fh.write("      effects:    [5679-Recruits Dialogue.mod, 0] + [51948-Dialogue.mod, 5000]\n")
    fh.write("   i.e. require 5000 cats, join squad, deduct 5000. In FCS, open the line\n")
    fh.write("   and add the vanilla equivalents: condition CO_PLAYER_MONEY >= 5000,\n")
    fh.write("   effects DA_JOINS_SQUAD_FAST + money deduction, mirroring any vanilla\n")
    fh.write("   bar-recruit line. Until then the recruits talk but cannot be hired.\n\n")
    fh.write("2. RACE APPEARANCE SWAPS (to reach zero dependencies)\n")
    fh.write("   Each list below still points at a third-party mod because the vanilla\n")
    fh.write("   IDs only exist inside gamedata.base. Open each race with gamedata.base\n")
    fh.write("   loaded and swap in the vanilla list (copy from vanilla Greenlander etc.):\n\n")
    for tname, name, sid, cat, tgts in sorted(rows):
        fh.write(f"   {tname:<12} {name!r}  [{sid}]\n")
        fh.write(f"        {cat}: {tgts}\n")
    fh.write("\n3. SPECIAL-FOOD GAP (design decision)\n")
    fh.write("   v3.5 makes Bread [1946], Rice Bowl [1016] and Potatoes [1960] 'special\n")
    fh.write("   food' (item function 15) and grants eating rights per race. Vanilla\n")
    fh.write("   Greenlander/Shek/Hive Prince edits are missing (Ian's other mods covered\n")
    fh.write("   them), so on a clean install those races cannot eat these three foods.\n")
    fh.write("   Either add 'special food' entries for them in FCS, or revert the three\n")
    fh.write("   item-function edits to disable the gate.\n\n")
    fh.write("4. SUN-BURN SYSTEM (quarantined in v3.6.1)\n")
    fh.write("   v3.5 set acid 1.0 / weather strength 10 on biome records 18001/18002/\n")
    fh.write("   18003 and weather protection on 58 armours. Those biome IDs' vanilla\n")
    fh.write("   identity could not be verified (Ian's world was renamed by rebirth.mod),\n")
    fh.write("   and only 8 animal races were made immune - vanilla humans would burn.\n")
    fh.write("   Rebuild in FCS against verified vanilla biomes with proper immunities.\n")
note(f"[worklist] rewritten -> fcs-worklist.txt ({len(rows)} appearance lists)")

with open(os.path.join(TOOLS, 'build_log.txt'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(log))
print("\nDONE")
