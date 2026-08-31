"""Gate check: prove the parser/serializer is byte-exact before editing anything."""
import sys, os, collections
TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from kenshi_mod import ModFile, NEW_V16, V16_CHANGE_TYPES

# Pass a path to inspect a different file; defaults to the original v3.5 upload.
MOD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, "original-v3.5", "Vampire Race - Blood Feeding.mod")

mod, original = ModFile.load(MOD)
print(f"fileType={mod.file_type} modVersion={mod.mod_version} records={len(mod.records)}")
print(f"trailing bytes after last record: {len(mod.trailing_bytes)}")

rebuilt = mod.serialize(lead='original')
print()
print("=== ROUND-TRIP TEST (lead='original') ===")
if rebuilt == original:
    print(f"  PASS - {len(rebuilt):,} bytes reproduced exactly")
else:
    print(f"  FAIL - original {len(original):,} vs rebuilt {len(rebuilt):,}")
    for i in range(min(len(rebuilt), len(original))):
        if rebuilt[i] != original[i]:
            print(f"  first difference at byte {i}")
            print(f"    original: {original[i-16:i+16].hex()}")
            print(f"    rebuilt : {rebuilt[i-16:i+16].hex()}")
            break
    sys.exit(1)

# Which records are non-conforming?
print()
print("=== FRAMING AUDIT ===")
v16_framed, v17_framed, bad_lead = [], [], []
for rec in mod.records:
    computed = len(rec.serialize_body()) + 4
    if rec.change_type in V16_CHANGE_TYPES:
        v16_framed.append(rec)
    else:
        v17_framed.append(rec)
        if rec.lead_int != computed:
            bad_lead.append((rec, computed))
print(f"  v17-conforming records : {len(v17_framed)}")
print(f"  v16-framed records     : {len(v16_framed)}  <-- non-conforming inside a fileType 17 file")
print(f"  v17 records with wrong length prefix: {len(bad_lead)}")
if v16_framed:
    first = v16_framed[0]
    print(f"  first v16 record: id={first.id} {first.name_str!r} at file offset {first.file_offset}")
    lead_vals = collections.Counter(r.lead_int for r in v16_framed)
    print(f"  their lead-int values: {dict(lead_vals)}  (should be byte length, not 0)")
    ct = collections.Counter(r.change_type for r in v16_framed)
    print(f"  their change types: {[hex(k) for k in ct]}")

print()
print("=== CHANGE TYPE DISTRIBUTION ===")
for ct, n in sorted(collections.Counter(r.change_type for r in mod.records).items()):
    owners = collections.Counter(r.owner() for r in mod.records if r.change_type == ct)
    top = ', '.join(f"{k}x{v}" for k, v in owners.most_common(3))
    print(f"  {hex(ct):>12}  {n:5d} records   top owners: {top}")

# Vanilla ID dictionary harvested from the file itself.
print()
print("=== VANILLA (gamedata.base) RECORDS PRESENT, BY TYPE ===")
base = [r for r in mod.records if r.owner() == 'gamedata.base']
by_type = collections.defaultdict(list)
for r in base:
    by_type[r.type].append(r)
for t in sorted(by_type):
    names = ', '.join(sorted(x.name_str for x in by_type[t])[:8])
    print(f"  type {t:3d} ({by_type[t][0].type_name:<18}) x{len(by_type[t]):4d}: {names}")

print()
print("=== LOOKING FOR THE VANILLA HUB (start-town replacement) ===")
for r in mod.records:
    if 'hub' in r.name_str.lower():
        print(f"  type={r.type} ({r.type_name}) {r.name_str!r} [{r.string_id_str}] change={hex(r.change_type)}")

print()
print("=== ALL TOWN (type 13) RECORDS OWNED BY gamedata.base ===")
towns = sorted((r for r in mod.records if r.type == 13 and r.owner() == 'gamedata.base'),
               key=lambda r: r.name_str)
for r in towns:
    print(f"  {r.string_id_str:<28} {r.name_str}")
