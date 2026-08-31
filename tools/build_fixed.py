"""
Build the repaired Vampire Race - Blood Feeding mod.

Every change is derived from IDs physically present in the source file. Nothing is
invented. Anything needing an ID from gamedata.base (which we have no copy of) is
emitted as an FCS worklist rather than guessed.

Rules
  1. Keep only records owned by this mod or by base-game data. Records that edit a
     third-party mod cannot apply without it and are dropped.
  2. Re-serialize every record in conforming fileType-17 framing.
  3. Point both game starts at a verified vanilla town instead of the mod's own
     unbuildable Coven City.
  4. Strip references that cannot resolve on a clean install, with ONE exception:
     the playable races' appearance/anatomy lists, which cannot be rebuilt without
     gamedata.base. Those keep their references and their mods are declared honestly.
  5. On records that EDIT base-game content, an emptied category is deleted rather
     than shipped empty - an empty list would overwrite the vanilla list. A base
     record left with nothing to say is dropped so vanilla stands untouched.
"""
import sys, os, collections
TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from kenshi_mod import ModFile, NEW_V17, V16_CHANGE_TYPES

SRC = os.path.join(REPO, "original-v3.5", "Vampire Race - Blood Feeding.mod")
OWN = 'Vampire Race - Blood Feeding.mod'

# gamedata.quack carries core engine data (locational damage / part coverage,
# ids 17, 28-32, 100, 101) referenced by vanilla armour as well as by this mod,
# so it is treated as base-game content, not a third-party dependency.
BASE_FILES = {'gamedata.base', 'gamedata.quack'}
KEEP_OWNERS = {OWN} | BASE_FILES

# Categories on RACE records that define how a character is built. Emptying
# "heads male"/"heads female" leaves a character with no head mesh, so these keep
# their third-party references and the mods are declared. See the FCS worklist for
# the path to a fully vanilla build.
RACE_APPEARANCE_CATS = {
    b'heads male', b'heads female', b'hairs', b'hair colors',
    b'limb replacement', b'severed limbs', b'AI Goals', b'combat anatomy',
}

NEW_START_TOWN = b'1032-gamedata.base'      # "Black scratch", a gamedata.base TOWN
NEW_START_TOWN_NAME = 'Black Scratch'

NEW_DESCRIPTION = (
    "Vampire Race - Blood Feeding v3.6. Four playable vampire bloodlines "
    "(Greenlander, Scorchlander, Shek, Hive) with a blood-feeding metabolism, "
    "blood and lore items, the Sunward daywear set, the Coven faction, vampire "
    "hunter patrols, and vampire recruits in bars across the world. Both starts "
    "begin at " + NEW_START_TOWN_NAME + ". Coven City ships dormant: its records "
    "are present but it is not placed in the world, pending a clean editor rebuild."
)

def target_owner(t):
    i = t.find('-')
    return t[i + 1:] if i > 0 and t[:i].isdigit() else None

def resolvable(tgt_str):
    o = target_owner(tgt_str)
    return o is None or o in BASE_FILES or o == OWN

mod, original = ModFile.load(SRC)
assert mod.serialize(lead='original') == original, "round-trip gate failed"
print(f"loaded {len(mod.records)} records, round-trip verified\n")

log = []
def note(s):
    log.append(s)
    print(s)

# ------------------------------------------------------- 1. drop third-party edits
before = len(mod.records)
dropped = [r for r in mod.records if not (r.owner() is None or r.owner() in KEEP_OWNERS)]
mod.records = [r for r in mod.records if (r.owner() is None or r.owner() in KEEP_OWNERS)]
by_owner = collections.Counter(r.owner() for r in dropped)
note(f"[F6] dropped {len(dropped)} records that edit third-party mods "
     f"({before} -> {len(mod.records)} records)")
for o, n in by_owner.most_common(6):
    note(f"        {n:5d}  {o}")
note(f"        ...across {len(by_owner)} source mods in total")

# ------------------------------------------------------- 2. conforming v17 framing
fixed_ct = sum(1 for r in mod.records if r.change_type in V16_CHANGE_TYPES)
for r in mod.records:
    if r.change_type in V16_CHANGE_TYPES:
        r.change_type = NEW_V17
note(f"\n[F4] normalised {fixed_ct} v16-framed records to v17 "
     f"(change type 0x80000002 -> 0x20; correct byte-length prefix on all records)")

# ------------------------------------------------------- 3. repoint game starts
for r in mod.records:
    if r.type != 64:
        continue
    for idx, (cat, items) in enumerate(r.refs):
        if cat == b'town':
            old = [t[0].decode() for t in items]
            r.refs[idx] = (cat, [(NEW_START_TOWN, a, b, c) for (_t, a, b, c) in items])
            note(f"[F1] start {r.name_str!r}: town {old} -> {NEW_START_TOWN_NAME}")

# ------------------------------------------------------- 4. strip unresolvable refs
pruned = 0
emptied_cats_removed = 0
kept_exceptions = collections.Counter()
for r in mod.records:
    is_base_edit = r.owner() in BASE_FILES
    new_refs = []
    for cat, items in r.refs:
        # exception: race appearance lists keep their third-party references
        if r.type == 7 and cat in RACE_APPEARANCE_CATS:
            for (tgt, _a, _b, _c) in items:
                o = target_owner(tgt.decode('utf-8', 'replace'))
                if o and o not in BASE_FILES and o != OWN:
                    kept_exceptions[o] += 1
            new_refs.append((cat, items))
            continue
        survivors = [(t, a, b, c) for (t, a, b, c) in items
                     if resolvable(t.decode('utf-8', 'replace'))]
        pruned += len(items) - len(survivors)
        if not survivors and items and is_base_edit:
            # never ship an empty list over a vanilla record's list
            emptied_cats_removed += 1
            continue
        new_refs.append((cat, survivors))
    r.refs = new_refs
note(f"\n[F8] stripped {pruned} references that cannot resolve on a clean install")
note(f"[F8] removed {emptied_cats_removed} emptied categories from base-game edits "
     f"(shipping an empty list would have blanked the vanilla list)")

# ------------------------------------------------------- 5. drop no-op base edits
def is_noop(r):
    if r.owner() not in BASE_FILES:
        return False
    has_fields = any(len(d) for d in r.dicts)
    has_refs = any(len(items) for _cat, items in r.refs)
    return not has_fields and not has_refs and not r.instances

noop = [r for r in mod.records if is_noop(r)]
mod.records = [r for r in mod.records if not is_noop(r)]
note(f"[F8] dropped {len(noop)} base-game edits left with nothing to change "
     f"(vanilla now stands untouched for those records)")

# ---------------------------------- 5b. repair characters left without a weapon
# 2064-gamedata.base is the vanilla weapon this mod's own author assigns to Coven
# residents, merchants and guards - a verified vanilla id taken from this file.
VANILLA_WEAPON = b'2064-gamedata.base'
rearmed = []
for r in mod.records:
    if r.type != 1 or r.owner() != OWN:
        continue
    for idx, (cat, items) in enumerate(r.refs):
        if cat == b'weapons' and not items:
            r.refs[idx] = (cat, [(VANILLA_WEAPON, 0, 0, 0)])
            rearmed.append(r.name_str)
note(f"\n[F8] re-armed {len(rearmed)} characters whose only weapon came from a "
     f"dropped mod, using vanilla {VANILLA_WEAPON.decode()}: "
     f"{', '.join(sorted(set(rearmed))[:6])}...")

# ---------------------------------- 5c. cascade-drop records left structurally invalid
# A CHARACTER that HAD a race list and lost every entry has no body to build from.
# Removing it can orphan the squads that only existed to place it, so cascade.
def char_lost_race(r):
    if r.type != 1:
        return False
    for cat, items in r.refs:
        if cat == b'race':
            return len(items) == 0
    return False

def squad_is_empty(r):
    if r.type != 52:
        return False
    people = 0
    for cat, items in r.refs:
        if cat in (b'leader', b'squad', b'choosefrom list', b'slaves', b'vendors'):
            people += len(items)
    return people == 0

cascade_dropped = []
for _round in range(10):
    doomed = {r.string_id for r in mod.records if char_lost_race(r) or squad_is_empty(r)}
    if not doomed:
        break
    cascade_dropped += [r.name_str for r in mod.records if r.string_id in doomed]
    mod.records = [r for r in mod.records if r.string_id not in doomed]
    for r in mod.records:
        r.refs = [(cat, [it for it in items if it[0] not in doomed])
                  for cat, items in r.refs]
note(f"[F8] cascade-dropped {len(cascade_dropped)} records left structurally invalid "
     f"once their mod-provided race or population was gone:")
for n in sorted(set(cascade_dropped)):
    note(f"        - {n}")

# ------------------------------------------------------- 6. honest dependencies
needed = collections.Counter()
for r in mod.records:
    for _cat, tgt in r.ref_targets():
        o = target_owner(tgt)
        if o and o not in BASE_FILES and o != OWN:
            needed[o] += 1
dep_list = sorted(needed, key=lambda k: (-needed[k], k.lower()))
note(f"\n[F6] true remaining dependencies: {len(dep_list)} "
     f"(header used to declare 15 while the data needed ~120)")
for d in dep_list:
    note(f"        {needed[d]:4d} refs  {d}")

mod.dependencies = ','.join(['gamedata.base'] + dep_list).encode('utf-8')
mod.description = NEW_DESCRIPTION.encode('utf-8')
note("\n[F11] description rewritten to match what the data actually does")

# ------------------------------------------------------- 7. write + verify
OUT_DIR = os.path.join(REPO, "Vampire Race - Blood Feeding")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "Vampire Race - Blood Feeding.mod")
mod.save(OUT, lead='computed')
note(f"\n[F9] wrote {os.path.basename(OUT)}: {len(mod.records)} records, "
     f"{os.path.getsize(OUT):,} bytes (was {len(original):,})")

check, raw = ModFile.load(OUT)
assert check.serialize(lead='original') == raw, "output does not round-trip"
bad = [r for r in check.records
       if r.lead_int != len(r.serialize_body()) + 4 or r.change_type in V16_CHANGE_TYPES]
assert not bad, f"{len(bad)} non-conforming records remain"
unresolved = collections.Counter()
for r in check.records:
    for _cat, tgt in r.ref_targets():
        o = target_owner(tgt)
        if o and o not in BASE_FILES and o != OWN:
            unresolved[o] += 1
note(f"[verify] re-parsed {len(check.records)} records, round-trip OK, "
     f"0 non-conforming, {sum(unresolved.values())} refs into "
     f"{len(unresolved)} declared dependency mods (all race appearance)")

# sanity: the four playable races must still have heads, and no character may be
# left without a race or a weapon
for r in check.records:
    if r.type == 7 and r.owner() == OWN and r.name_str != 'Blood Hound':
        heads = {c.decode(): len(i) for c, i in r.refs if b'heads' in c}
        note(f"[verify] race {r.name_str!r}: {heads}")
raceless = [r.name_str for r in check.records if r.type == 1
            and any(c == b'race' and not i for c, i in r.refs)]
weaponless = [r.name_str for r in check.records if r.type == 1
              and any(c == b'weapons' and not i for c, i in r.refs)]
note(f"[verify] characters with an emptied race list: {raceless or 'none'}")
note(f"[verify] characters with an emptied weapon list: {weaponless or 'none'}")
assert not raceless, "a character was left with no race"
starts = [r for r in check.records if r.type == 64]
for s in starts:
    towns = [t[0].decode() for c, t_ in [(c, i) for c, i in s.refs if c == b'town']
             for t in t_]
    note(f"[verify] start {s.name_str!r} spawns at: {towns}")
assert len(starts) == 2, "both game starts must survive"

# ------------------------------------------------------- 8. FCS worklist
rows = []
for r in check.records:
    for cat, items in r.refs:
        foreign = [t[0].decode() for t in items
                   if not resolvable(t[0].decode())]
        if foreign:
            rows.append((r.type_name, r.name_str, r.string_id_str,
                         cat.decode('utf-8', 'replace'), foreign))
wl = os.path.join(REPO, 'fcs-worklist.txt')
with open(wl, 'w', encoding='utf-8') as fh:
    fh.write("FCS WORKLIST - the last mile to a zero-dependency build\n")
    fh.write("=" * 64 + "\n\n")
    fh.write("Each line is one reference list that still points at a third-party mod.\n")
    fh.write("Open the record in FCS with gamedata.base loaded and swap the target for\n")
    fh.write("the vanilla equivalent. These were left intact because emptying them would\n")
    fh.write("break character construction, and the correct vanilla IDs are not present\n")
    fh.write("anywhere in the mod file - they can only be read out of gamedata.base.\n\n")
    for tname, name, sid, cat, tgts in sorted(rows):
        fh.write(f"{tname:<12} {name!r}  [{sid}]\n")
        fh.write(f"     {cat}: {tgts}\n\n")
note(f"[worklist] {len(rows)} reference lists to swap in FCS -> fcs_worklist.txt")

with open(os.path.join(TOOLS, 'build_log.txt'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(log))
print("\nDONE")
