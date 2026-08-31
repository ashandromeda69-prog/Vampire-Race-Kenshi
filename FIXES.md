# What was wrong, and what changed

Diagnosis and repair of **Vampire Race — Blood Feeding v3.5** (commit `9e1bab2`).
Everything below was derived by parsing the binary `.mod`, `.level` and `.zone`
files record by record. The rebuilt mod lives in `Vampire Race - Blood Feeding/`;
the untouched original is preserved in `original-v3.5/`.

> **Not yet tested in-game.** Every change is verified structurally — the file
> parses, round-trips byte-exactly, and passes the assertions listed at the bottom.
> Nobody has launched Kenshi with it. Test on a clean install before releasing.

---

## The reported symptom

> "When they are attempting to access the site it is not allowing them to further
> play, things aren't loading."

Reproduced from first principles. Both custom starts spawned the player **inside
Coven City**, the one location that cannot load without the author's personal
install of ~120 other mods. New Game → infinite load.

## Root causes

The mod was built *inside* a 120-mod load order and its world data exported *from a
live save*, then its newest content was appended in a legacy binary format.

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

## What changed

### F4 — binary format normalised
The file is `fileType 17`, whose records each carry a byte-length prefix. Records
1–2740 were correct. At byte offset 1,858,700 the framing changed: the final 66
records — *the entire v3.5 content drop*, including Lord Ambrose Veil, every Coven
City resident and shop, the lore books and the Duskfang — were appended by the build
script in the **old v16 layout**, with a lead value of `0` instead of a byte length
and the v16 "new record" marker `0x80000002` instead of v17's `0x20`.

All records are now re-serialised with a correct byte-length prefix and change type
`0x20`. Verified: zero non-conforming records remain.

### F6 / F8 — cut loose from the modlist
2,457 records existed only to edit *other mods'* records (a scripted pass making
everything in the author's load order drop blood on death). They cannot apply
without their parent mods and were removed. 1,531 references that could not resolve
on a clean install were stripped.

Kept: the mod's own 118 records, 218 edits to vanilla `gamedata.base` records (the
real feature — blood drops from vanilla characters, vampire recruits in vanilla
bars, Holy Nation hostility), 8 `gamedata.quack` records and 5 engine-template
records.

Declared dependencies went from **15 declared / ~120 actually needed** to **7,
all genuinely required and all declared**.

> `gamedata.quack` is treated as base-game content, not a dependency. Its records
> here are low-id engine data (17, 28–32, 100, 101) used for locational damage and
> part coverage, referenced by vanilla armour as well as by this mod. Worth a
> sanity check in FCS.

### F1 — starts repointed
Both starts pointed at `13-Vampire Race - Blood Feeding.mod` (Coven City). They now
point at `1032-gamedata.base` — **Black Scratch**, a vanilla town whose id was
harvested from a `gamedata.base` record inside this very file, so it is guaranteed
to resolve.

Black Scratch was chosen because it is vanilla, central, lawless, has a bar (so the
mod's own vampire bar-recruits appear there), and has no Holy Nation presence. The
Hub would be the thematic choice, but **no vanilla Hub id exists anywhere in the mod
file** — the only Hub records present belong to Newwworld, UWE and Hub
Re-Established. Rather than invent an id, the swap was made to a verified one.
Changing it in FCS is a ten-second job.

### F2 / F3 / F5 / F7 — savegame terrain removed
`interiors.level`, `leveldata.level` and all six `zone.*.zone` files were exported
from a running game session — they are full of `-INGAME` and `-INGAME-S23` ids that
only exist inside the author's save, referencing mods like *Kenshi Aftermath - Base*
and *Expanded Cities - The Hub Insane* that were never declared. `interiors.level`
was a **global** override of every building interior in the game, and
`zone.20.34.zone` overwrote the Hub's own map cell.

None of them are shippable. All were moved to `original-v3.5/`. Consequence: Coven
City is no longer placed in the world.

### Structural repairs found during the rebuild
Two problems were introduced by the trim itself and fixed before shipping:

- **Seven skeleton NPCs lost their race.** Their only `race` reference pointed at
  `stick_people.mod`. A character with no race has no body to build from, so they
  and the six squads that existed only to place them were cascade-dropped: the Coven
  robotics/ironworks/power-station crews and the skeleton recruits. They are Coven
  City industrial-district flavour, dormant in this build anyway.
- **Twelve characters lost their only weapon** (it came from `rebirth.mod`),
  including both starting vampires and every bar recruit. They were re-armed with
  `2064-gamedata.base`, the vanilla weapon this mod's own author assigns to Coven
  residents and guards.

### F9 / F10 / F11 / F12 — packaging
- The mod now sits in a correctly named folder, `Vampire Race - Blood Feeding/`, so
  the launcher lists it.
- README with install steps, dependencies and load order.
- Header description rewritten — the old one claimed both starts used "the vanilla
  Wanderer's exact Hub spawn configuration", which the data contradicted.
- `.gitattributes` marks all game files binary so a future contributor's line-ending
  config cannot corrupt them.

## Result

| | v3.5 | v3.6 |
| --- | ---: | ---: |
| Records | 2,806 | 336 |
| File size | 1,931,263 bytes | 155,278 bytes |
| Non-conforming records | 66 | 0 |
| Mods actually required | ~120 | 7 |
| Mods declared | 15 | 7 |
| Shipped savegame terrain files | 8 | 0 |

## Verified before commit

- The parser round-trips the original v3.5 file to **1,931,263 identical bytes**,
  proving the format model is exact rather than approximate.
- The rebuilt file re-parses cleanly and round-trips.
- Zero records with a wrong length prefix or a v16 change type.
- All four playable races still have head meshes (character creation intact).
- No character left with an empty race list or an empty weapon list.
- Both game starts survive and point at a resolvable vanilla town.

## Still to do

1. **Test on a clean install** — no workshop mods, both starts, walk to Black
   Scratch, save and reload. This is the one thing no amount of static analysis
   replaces.
2. **Reach zero dependencies** — `fcs-worklist.txt` lists all 24 reference lists
   still pointing at a third-party mod. Every one is on a RACE record (heads, hair,
   limbs, AI goals). Open each in FCS with `gamedata.base` loaded and swap in the
   vanilla equivalent. The correct ids can only be read out of `gamedata.base`, so
   they were deliberately not guessed here.
3. **Rebuild Coven City** — in the Forgotten Construction Set, on a clean install
   with only this mod active, from vanilla building parts. Let FCS generate the zone
   files. Ship only what that clean session produces, and never a wholesale
   `interiors.level`.
4. **Optional: compatibility patches.** The 2,457 dropped records were mostly
   UWE (959), rebirth (314) and Dialogue (222). If you want blood drops from those
   mods' creatures, re-issue them as separate patch mods
   ("Blood Feeding × UWE") rather than folding them back into the core.

## Reproducing this build

```bash
python tools/build_fixed.py
```

`tools/kenshi_mod.py` is a byte-exact reader/writer for the Kenshi `.mod` format
(fileType 16 and 17), written for this repair and usable for any future surgery.
Format notes are in its docstring. Cross-checked against the community reference
implementation, `Kakrain/KenshiCore`.
