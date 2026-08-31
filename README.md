# Vampire Race — Blood Feeding

Four playable vampire bloodlines for Kenshi, a blood-feeding metabolism, the Coven
faction, vampire hunters, and vampire recruits in bars across the world.

**This branch (`Fable-changes`) contains a repaired v3.6 build.** The v3.5 upload on
`main` does not load on anyone's machine but the author's. See [FIXES.md](FIXES.md)
for what was wrong and exactly what changed.

---

## Install

1. Download or clone this branch.
2. Copy the folder **`Vampire Race - Blood Feeding`** (the whole folder, not just the
   file inside it) into your Kenshi mods directory:

   ```
   Steam/steamapps/common/Kenshi/mods/Vampire Race - Blood Feeding/
   ```

   The folder name and the `.mod` filename inside it must match, or the launcher
   will not list the mod.
3. Launch Kenshi, open the mod list, tick **Vampire Race - Blood Feeding**.
4. Load it **below** the dependency mods listed next.

Do **not** copy `original-v3.5/` or `tools/` into your game. They are reference
material only.

## Dependencies

Base-game Kenshi, plus these seven mods, which supply the head meshes, hair, and
limb data the four vampire races are built from:

| Mod | What it supplies |
| --- | --- |
| Ark Haircuts | hairstyles for the Greenlander and Scorchlander bloodlines |
| Newwworld | male head, limb replacement |
| limbs | severed-limb models |
| rebirth | race AI goals |
| chareditor | Scorchlander and Shek heads |
| changes_otto | Greenlander female head, hair colours |
| small_changes_otto | Hive heads |

Every one of these is declared in the mod header, so the launcher will warn you if
one is missing instead of failing silently.

Getting this list to zero is a small, well-defined job in the Forgotten Construction
Set — see [fcs-worklist.txt](fcs-worklist.txt) for the exact 24 swaps.

## What you get

- **Two starts** — *Wandering Vampire* (one vampire, alone) and *Vampire Coven*
  (thirteen vampires, fully customisable). Both begin at **Black Scratch**.
- **Four bloodlines** — Greenlander, Scorchlander, Shek and Hive, each with rapid
  healing, reduced bleeding, and a metabolism that demands blood.
- **Blood as a resource** — human, Shek, Hive, animal and insect blood, dropped by
  the living across the world.
- **The Coven** — a vampire faction, with Holy Nation hostility baked in.
- **Vampire hunters** — roaming patrols that want you dead.
- **Recruits in bars** — vampires of each bloodline, hireable in taverns.
- **Sunward daywear** — cowl, robe, leggings and boots.
- **Lore books** and the **Duskfang** nodachi.

## Not in this build

**Coven City.** The town's records ship dormant — the faction, Lord Ambrose Veil,
the garrison, shops, tavern and archive all exist in the data, but the town is not
placed in the world. The v3.5 terrain files that placed it were exported from a live
save and cannot work on another machine; rebuilding the town in the Forgotten
Construction Set is the remaining work. See [FIXES.md](FIXES.md) §"Still to do".

## Repository layout

```
Vampire Race - Blood Feeding/   the installable mod — this is the release
original-v3.5/                  the untouched v3.5 upload, for reference only
tools/                          the parser and build script used for the repair
fcs-worklist.txt                the 24 edits to reach zero dependencies
FIXES.md                        full changelog with rationale
```
