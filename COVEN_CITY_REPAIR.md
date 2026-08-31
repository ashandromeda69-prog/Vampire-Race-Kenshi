# Coven City crash repair notes

This branch contains conservative binary repairs for the Coven City stream-in
crash. The files were parsed and rewritten as Kenshi records; untouched records
and level-data tails were preserved byte-for-byte.

## Installing the test branch on Windows

1. Download the `Chatgpt-changes` branch as a ZIP and extract it.
2. Close Kenshi and its launcher.
3. Double-click `install_chatgpt_changes.bat` in the extracted folder.

The installer locates Steam/Kenshi, backs up any existing
`Vampire Race - Blood Feeding` mod folder, installs only the runtime files under
the exact folder name Kenshi requires, and verifies every copied file by SHA-256.
If Kenshi is in a nonstandard location and cannot be detected, the installer
will ask for the folder containing `kenshi_x64.exe`.

## Applied repairs

- Assigned valid races to all 17 custom humanoid character templates that had
  no `race` reference. `Vampire Hunter` now uses the vanilla Greenlander; the
  Coven characters use the four vampire races already defined by this mod.
- Removed 60 hair references to `Ark Haircuts.mod` from the Greenlander and
  Scorchlander vampire races. That mod was neither included nor declared as a
  dependency. The two vanilla hair choices on each race remain.
- Removed 10 furniture instances from two bar layouts that referenced the
  undeclared `CBT Leisure Objects and Furniture.mod`.
- Repaired the stored lengths of 66 appended custom records and updated the
  mod's last-record ID from 13 to 4243.
- Changed 80 Coven-created world buildings (130 owner fields) from the unrelated
  vanilla faction `42022-rebirth.mod` to `The Coven`.
- Removed all 43 Coven placements that required undeclared third-party building
  mods, their 43 matching building-state records, and two orphaned Forgotten
  Buildings inventory records. Vanilla and legacy base-game `TwoStorey` /
  `D-TwoStorey` placements remain.
- Removed `zone.20.34.zone` and `zone.25.34.zone`. Coven City's town record lists
  only sectors 25.32, 25.33, 26.32, and 26.33; the deleted exports contained
  unrelated Hub/Waystation mod data.
- Added `tools/repair_coven_city.js`, an idempotent repair/verification script.

## Remaining FCS work

1. Clean the shared `zone.26.33.zone` export in FCS. It still contains unrelated
   records from The Hub Re-Established, Narko's Disciples, Advanced Camping,
   and Universal Wasteland Expansion. This sector overlaps Coven City, so the
   whole file cannot safely be deleted automatically.

2. Re-export the supporting world files from a clean load order. The current
   `interiors.level` contains 3,325 merged global layout records, and
   `leveldata.level` contains snapshots for 403 world towns under this mod's
   namespace. The known CBT Leisure references were removed, but FCS should keep
   only the town and layouts intentionally changed by this mod.

3. Wire the defined shop, guard, thrall, archive, robotics, industrial, patrol,
   and recruit squads to the intended buildings or to Coven City's resident
   list. The town currently contains only Lord Veil's Court, Coven City
   Residents, and Blood Merchant Shop, plus its older bar squad.

4. Review the repaired character templates in FCS. Confirm that the four-race
   distribution is desired for each Coven role and that Vampire Hunter should
   remain a Greenlander. Then preview clothing, hair, and body combinations.

5. Regenerate/fix navigation after the world cleanup, then test with a new game
   or imported save: approach from every sector, enter every building, wait for
   resident squads to spawn, save/reload inside town, and test gates and paths.
   If it still crashes, preserve `kenshi.log` and the crash dump from that run.

## Verification

Run from the repository root:

```sh
node tools/repair_coven_city.js
```

On an already repaired checkout, all reported change counts should be zero and
the command should exit successfully.
