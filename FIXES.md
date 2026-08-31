# What was wrong, and what changed

Diagnosis and repair of **Vampire Race — Blood Feeding v3.5** (commit `9e1bab2`).
Everything below was derived by parsing the binary `.mod`, `.level` and `.zone`
files record by record — first the original, then the repair itself, which was
re-audited and corrected in a second pass. The rebuilt mod (v3.6.1) lives in
`Vampire Race - Blood Feeding/`; the untouched original is in `original-v3.5/`.

> **Not yet tested in-game.** Every change is verified structurally — the files
> parse, round-trip byte-exactly, and pass the assertions listed at the bottom.
> Nobody has launched Kenshi with this yet. Test on a clean install before
> releasing.

---

## The reported symptom

> "When they are attempting to access the site it is not allowing them to further
> play, things aren't loading."

Reproduced from first principles: both custom starts spawned the player **inside
Coven City**, the one location that cannot exist without the author's personal
install of ~120 other mods and world data exported from a live save. New Game →
infinite load.

## Root causes found in v3.5

| # | Problem | Severity |
| --- | --- | --- |
| F1 | Both game starts spawned at the unbuildable Coven City | critical |
| F2 | Terrain files exported from a running save (`-INGAME` ids) | critical |
| F3 | Coven City's buildings belong to mods players don't have | critical |
| F4 | Last 66 records written in v16 format inside a v17 file | critical |
| F5 | `interiors.level` overrode every building interior in the game | critical |
| F6 | ~120 mods referenced, 16 declared, several unpublishable local files | critical |
| F7 | `zone.20.34.zone` overwrote the Hub's own map cell | major |
| F8 | Dangling references throughout, including on vanilla records | major |
| F9 | Repo folder name meant the launcher wouldn't list the mod | major |
| F10 | No README, install steps, or load-order guidance | major |
| F11 | Header description contradicted the data | minor |
| F12 | No `.gitattributes` protecting the binaries | minor |

And one found only by auditing the repair itself:

| # | Problem | Severity |
| --- | --- | --- |
| F13 | Names inside edit records reflect Ian's **modded session**, not vanilla — rebirth.mod renames vanilla records wholesale, so a record labeled "Black scratch" can really be the Southern Hive | critical |

## The verification method (why the IDs can be trusted)

The repair never invents an ID. Sources, in order of strength:

1. **Byte-exact round trip.** The parser reproduces the original 1,931,263-byte
   file identically, proving the format model is exact before anything is edited.
2. **Ian's own data.** Materials, buildings, weapons and packages are reused from
   references Ian himself made elsewhere in the file (e.g. the Sunward Robe
   already uses vanilla material `3060-gamedata.base`).
3. **The Polish base-game translation** (`flatrepo/kenshi_pl`, an FCS
   `.translation` file keyed by vanilla stringIDs) as an independent witness of
   what each vanilla ID really is.
4. **The two-source rule (because of F13):** any *load-bearing* vanilla ID must
   have Ian's label and the translation agree. This rule caught a live bug in
   round 1 of this very repair: the start town had been set to
   `1032-gamedata.base` trusting Ian's "Black scratch" label — the translation
   proved 1032 is **"Południowy Rój", the Southern Hive**, a town that attacks
   visitors on sight. The verified replacement is `1082-gamedata.base`
   (Ian: "Flats lagoon" / PL: "Płaska Laguna" — agreement).

Anything that could not be verified (the hire-dialogue effect encoding, vanilla
race appearance lists, the sun-system biome identities) was **left out and
documented in `fcs-worklist.txt`** rather than guessed.

## What changed

### F4 — binary format normalised
Records 1–2740 were correct fileType-17 records (byte-length prefixed). At byte
1,858,700 the last 66 records — *the entire v3.5 content drop*: Lord Ambrose
Veil, the Coven City population, shops, lore books, the Duskfang — had been
appended by the build script in the **old v16 layout** (lead value `0`, change
type `0x80000002`). All records are re-serialised in conforming v17 framing.

### F6 / F8 — cut loose from the modlist
- Dropped 2,457 records that only edit other mods' records.
- Stripped 1,531 references that cannot resolve on a clean install.
- Declared dependencies: **15 declared / ~120 real → 7, all real, all declared**
  (Ark Haircuts, Newwworld, limbs, rebirth, chareditor, changes_otto,
  small_changes_otto — all supplying race head/hair/limb data only; see
  worklist item 2 for the path to zero).

### F1 / F13 — starts repointed to a two-source-verified town
Both starts now spawn at **Flats Lagoon** (`1082-gamedata.base`) — the neutral
Tech Hunter town with a bar and no Holy Nation presence. The description claimed
the vanilla Hub; no vanilla Hub ID exists anywhere in the mod's data, so the Hub
remains a ten-second FCS swap if wanted.

### Sun-burn system — quarantined (new in v3.6.1)
v3.5 implemented vampire sunlight-burning through the weather system: three
vanilla **biome records** set to acid 1.0 / weather strength 10, 58 vanilla
armours given `weather protection1`, 8 animal races made immune. The biome
records' vanilla identity cannot be verified (F13 — Ian's labels "Central",
"The Desert", "NONE" are session names), only animals were made immune, and
vanilla humans have no protection — on a clean install this could acid-burn
every human in three unknown vanilla regions. All 61 sun-system edits are
dropped. The Sunward gear remains as normal armour. Rebuild instructions:
worklist item 4.

### F2 / F3 / F5 / F7 — savegame terrain removed
`interiors.level`, `leveldata.level` and all six zone files carry `-INGAME`
save-session ids referencing undeclared mods ("Kenshi Aftermath - Base",
"Expanded Cities - The Hub Insane"). All moved to `original-v3.5/`, nothing
deleted. Consequence: **Coven City ships dormant** — its records exist but the
town is not placed in the world.

### Structural repairs (fallout from the trim, caught by the audit)
- **14 records cascade-dropped:** the skeleton industrial district (robotics
  engineer/technician, ironworks/power/battery crews, skeleton recruits) lost
  its race (`stick_people.mod`) and could never spawn; removing the staff
  removed their squads and one orphaned vendor list.
- **9 characters re-armed** with the verified vanilla **Katana**
  (`476-gamedata.base`, PL-confirmed) — both starting vampires, the four bar
  recruits, the Vampire Hunter — their weapons had come from `rebirth.mod`.
- **36 reference repairs** from verified IDs: player-dialogue package
  `5369-gamedata.base` restored to recruits and thralls (it is what Ian's own
  wanderer characters use); `Coven Leader Bearing` personality applied to the
  four wanderer characters; vanilla material `3060` applied to the Sunward
  leggings/boots, blood items and lore books; Blood Hound now drops Dirty
  Animal Blood exactly like Ian's vanilla dog/goat edits; dormant-town squads
  reassigned to vanilla buildings `609`/`772`; the Coven Tavern stocks the
  seven blood items.

### What deliberately did NOT change
- The **blood economy**: 126 vanilla characters and 8 vanilla animals drop blood
  on death; vampire recruits appear in the bars of 12 vanilla towns; the Holy
  Nation is -80 hostile to the Coven and fields Vampire Hunter patrols.
- The **special-food gate**: Bread/Rice Bowl/Potatoes are `item function 15`
  and races eat by grant. Note: vanilla Greenlander/Shek edits are missing
  (Ian's other mods covered them), so on a clean install those races can't eat
  these three specific foods. Kept because it is Ian's design; see worklist
  item 3 to complete or revert it.
- The 12 bar-squad town edits are kept even though some labels are session
  names (one is really the Southern Hive) — a bar recruit in an unexpected
  vanilla town is harmless; a missing feature is not.

### F9 – F12 — packaging
Correct `mods/`-ready folder name, README, truthful header description,
`.gitattributes` marking game files binary, reproducible build script.

## Result

| | v3.5 | v3.6.1 |
| --- | ---: | ---: |
| Records | 2,806 | 273 |
| File size | 1,931,263 bytes | 148,062 bytes |
| Non-conforming records | 66 | 0 |
| Mods actually required | ~120 | 7 |
| Mods declared | 15 | 7 |
| Savegame terrain files shipped | 8 | 0 |
| Records that touch vanilla balance outside the blood/food design | many | 0 |

## Verified before commit

- Parser round-trips the original to 1,931,263 identical bytes; the rebuild
  round-trips too.
- Zero records with a wrong length prefix or v16 change type.
- Zero dangling references to own records; zero references to unpublishable
  private files.
- All four playable races keep head meshes; no character has an empty race or
  weapon list; both starts resolve to the two-source-verified Flats Lagoon.
- Remaining empty reference lists are inert by inspection (vendor blueprint
  lists, a dog's strafe animation, and the hire-effect gap documented below).

## Still to do (in priority order — see fcs-worklist.txt for exact steps)

1. **Wire up recruit hiring in FCS (~2 min).** The custom hire line's effects
   lived in `Dialogue.mod` (join squad + 5000-cat fee; original values are
   documented in the worklist). Until re-added, the vampire recruits in bars
   talk but cannot be hired.
2. **Test on a clean install.** No workshop mods: both starts, walk Flats
   Lagoon, hire attempt, save/reload. Static analysis cannot replace this.
3. **Race appearance swaps** — 24 lists across the four bloodlines and the
   Blood Hound still point at the 7 declared mods; swapping in vanilla lists in
   FCS reaches zero dependencies.
4. **Decide the special-food gate** — complete it (add Greenlander/Shek grants)
   or revert the three item-function edits.
5. **Rebuild Coven City** in FCS from vanilla parts on a clean install; ship
   only what that session produces.
6. **Rebuild the sun-burn system** against verified vanilla biomes with proper
   immunities for non-vampire races.
7. Optional: re-issue the dropped 2,457 third-party edits as separate
   compatibility patches ("Blood Feeding × UWE" etc.).

## Reproducing this build

```bash
python tools/build_fixed.py
```

`tools/kenshi_mod.py` is a byte-exact reader/writer for Kenshi `.mod`/`.base`/
`.translation` files (fileType 16/17), cross-checked against
`Kakrain/KenshiCore`. The verified-ID mining used the Polish base-game
translation from `flatrepo/kenshi_pl`.
