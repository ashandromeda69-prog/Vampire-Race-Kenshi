#!/usr/bin/env node

/*
 * Repairs crash-prone Coven City records without requiring the Forgotten
 * Construction Set. The binary parser is intentionally limited to Kenshi's
 * standard mod/level record container and preserves all untouched bytes.
 */

'use strict';

const fs = require('fs');
const path = require('path');

class Reader {
  constructor(buffer) {
    this.buffer = buffer;
    this.offset = 0;
  }

  ensure(length) {
    if (this.offset + length > this.buffer.length) {
      throw new Error(`Unexpected end of file at ${this.offset}; need ${length} bytes`);
    }
  }

  byte() {
    this.ensure(1);
    return this.buffer[this.offset++];
  }

  int() {
    this.ensure(4);
    const value = this.buffer.readInt32LE(this.offset);
    this.offset += 4;
    return value;
  }

  uint() {
    this.ensure(4);
    const value = this.buffer.readUInt32LE(this.offset);
    this.offset += 4;
    return value;
  }

  float() {
    this.ensure(4);
    const value = this.buffer.readFloatLE(this.offset);
    this.offset += 4;
    return value;
  }

  string() {
    const length = this.int();
    if (length < 0 || length > 100_000_000) {
      throw new Error(`Invalid string length ${length} at ${this.offset - 4}`);
    }
    this.ensure(length);
    const value = this.buffer.toString('utf8', this.offset, this.offset + length);
    this.offset += length;
    return value;
  }

  vec3() {
    return [this.float(), this.float(), this.float()];
  }

  vec4() {
    return [this.float(), this.float(), this.float(), this.float()];
  }
}

function parseBuffer(buffer) {
  const reader = new Reader(buffer);
  const type = reader.int();

  if (type === 16 || type === 17) {
    let headerEnd = 0;
    if (type === 17) {
      headerEnd = reader.int() + reader.offset;
    }
    reader.int();
    reader.string();
    reader.string();
    reader.string();
    reader.string();

    if (reader.offset < headerEnd) {
      reader.uint();
      reader.uint();
      const mergeEntryCount = reader.byte();
      for (let i = 0; i < mergeEntryCount; i += 1) {
        reader.string();
        reader.uint();
        reader.uint();
      }
      const deleteRequestCount = reader.byte();
      for (let i = 0; i < deleteRequestCount; i += 1) {
        reader.string();
        reader.uint();
        reader.string();
      }
    }
    if (headerEnd) {
      reader.offset = headerEnd;
    }
  }

  const lastIdOffset = reader.offset;
  const lastId = reader.int();
  const itemCount = reader.int();
  const items = [];

  for (let index = 0; index < itemCount; index += 1) {
    const start = reader.offset;
    const item = {
      start,
      storedLength: reader.int(),
      typeId: reader.int(),
      id: reader.int(),
      name: reader.string(),
      stringId: reader.string(),
      flags: reader.uint(),
      dictionaries: [],
      references: [],
      instances: [],
    };

    const dictionaryReaders = [
      () => Boolean(reader.byte()),
      () => reader.float(),
      () => reader.int(),
      () => reader.vec3(),
      () => reader.vec4(),
      () => reader.string(),
      () => reader.string(),
    ];

    for (const readValue of dictionaryReaders) {
      const entries = [];
      const entryCount = reader.int();
      for (let i = 0; i < entryCount; i += 1) {
        entries.push({key: reader.string(), value: readValue()});
      }
      item.dictionaries.push(entries);
    }

    const categoryCount = reader.int();
    for (let i = 0; i < categoryCount; i += 1) {
      const category = {name: reader.string(), entries: []};
      const referenceCount = reader.int();
      for (let j = 0; j < referenceCount; j += 1) {
        category.entries.push({
          id: reader.string(),
          values: [reader.int(), reader.int(), reader.int()],
        });
      }
      item.references.push(category);
    }

    const instanceCount = reader.int();
    for (let i = 0; i < instanceCount; i += 1) {
      const instance = {
        id: reader.string(),
        targetId: reader.string(),
        position: reader.vec3(),
        rotation: reader.vec4(),
        states: [],
      };
      const stateCount = reader.int();
      for (let j = 0; j < stateCount; j += 1) {
        instance.states.push(reader.string());
      }
      item.instances.push(instance);
    }

    item.end = reader.offset;
    item.actualLength = item.end - start;
    items.push(item);
  }

  return {
    buffer,
    type,
    lastId,
    lastIdOffset,
    itemCount,
    items,
    parsedEnd: reader.offset,
  };
}

function parseFile(filePath) {
  return parseBuffer(fs.readFileSync(filePath));
}

class Writer {
  constructor() {
    this.parts = [];
  }

  add(buffer) {
    this.parts.push(buffer);
  }

  byte(value) {
    this.add(Buffer.from([value ? 1 : 0]));
  }

  int(value) {
    const buffer = Buffer.allocUnsafe(4);
    buffer.writeInt32LE(value);
    this.add(buffer);
  }

  uint(value) {
    const buffer = Buffer.allocUnsafe(4);
    buffer.writeUInt32LE(value >>> 0);
    this.add(buffer);
  }

  float(value) {
    const buffer = Buffer.allocUnsafe(4);
    buffer.writeFloatLE(value);
    this.add(buffer);
  }

  string(value) {
    const buffer = Buffer.from(value, 'utf8');
    this.int(buffer.length);
    this.add(buffer);
  }

  vec(values) {
    for (const value of values) {
      this.float(value);
    }
  }

  build() {
    return Buffer.concat(this.parts);
  }
}

function serializeItem(item, fileType) {
  const writer = new Writer();
  writer.int(item.storedLength);
  writer.int(item.typeId);
  writer.int(item.id);
  writer.string(item.name);
  writer.string(item.stringId);
  writer.uint(item.flags);

  const dictionaryWriters = [
    (out, value) => out.byte(value),
    (out, value) => out.float(value),
    (out, value) => out.int(value),
    (out, value) => out.vec(value),
    (out, value) => out.vec(value),
    (out, value) => out.string(value),
    (out, value) => out.string(value),
  ];

  item.dictionaries.forEach((entries, index) => {
    writer.int(entries.length);
    for (const entry of entries) {
      writer.string(entry.key);
      dictionaryWriters[index](writer, entry.value);
    }
  });

  writer.int(item.references.length);
  for (const category of item.references) {
    writer.string(category.name);
    writer.int(category.entries.length);
    for (const entry of category.entries) {
      writer.string(entry.id);
      entry.values.forEach(value => writer.int(value));
    }
  }

  writer.int(item.instances.length);
  for (const instance of item.instances) {
    writer.string(instance.id);
    writer.string(instance.targetId);
    writer.vec(instance.position);
    writer.vec(instance.rotation);
    writer.int(instance.states.length);
    instance.states.forEach(state => writer.string(state));
  }

  let result = writer.build();
  if (fileType === 16 || fileType === 17) {
    result.writeInt32LE(result.length, 0);
  }
  return result;
}

function writeModifiedFile(filePath, parsed, modifiedItems, directEdits = []) {
  const parts = [];
  let offset = 0;
  for (const item of parsed.items) {
    parts.push(parsed.buffer.subarray(offset, item.start));
    parts.push(modifiedItems.has(item) ? serializeItem(item, parsed.type) : parsed.buffer.subarray(item.start, item.end));
    offset = item.end;
  }
  parts.push(parsed.buffer.subarray(offset));
  const output = Buffer.concat(parts);

  for (const edit of directEdits) {
    edit(output);
  }
  fs.writeFileSync(filePath, output);
}

function findReference(item, categoryName) {
  return item.references.find(category => category.name === categoryName);
}

function repairMod(filePath) {
  const parsed = parseFile(filePath);
  if (parsed.type !== 17) {
    throw new Error(`${filePath} is not a Kenshi MergeMod file`);
  }

  const modified = new Set();
  let removedHairReferences = 0;
  const raceIds = [
    '2-Vampire Race - Blood Feeding.mod',
    '3-Vampire Race - Blood Feeding.mod',
    '4-Vampire Race - Blood Feeding.mod',
    '5-Vampire Race - Blood Feeding.mod',
  ];

  for (const stringId of raceIds.slice(0, 2)) {
    const race = parsed.items.find(item => item.stringId === stringId);
    if (!race || race.typeId !== 7) {
      throw new Error(`Expected vampire race record ${stringId}`);
    }
    const hair = findReference(race, 'hairs');
    if (!hair) {
      throw new Error(`Expected hair references on ${stringId}`);
    }
    const before = hair.entries.length;
    hair.entries = hair.entries.filter(entry => !entry.id.endsWith('-Ark Haircuts.mod'));
    removedHairReferences += before - hair.entries.length;
    if (hair.entries.length !== before) {
      modified.add(race);
    }
  }

  const expectedRaceLessCharacters = new Set([
    '3001-Vampire Race - Blood Feeding.mod',
    '4111-Vampire Race - Blood Feeding.mod',
    '4141-Vampire Race - Blood Feeding.mod',
    '4151-Vampire Race - Blood Feeding.mod',
    '4181-Vampire Race - Blood Feeding.mod',
    '4183-Vampire Race - Blood Feeding.mod',
    '4185-Vampire Race - Blood Feeding.mod',
    '4187-Vampire Race - Blood Feeding.mod',
    '4189-Vampire Race - Blood Feeding.mod',
    '4191-Vampire Race - Blood Feeding.mod',
    '4193-Vampire Race - Blood Feeding.mod',
    '4194-Vampire Race - Blood Feeding.mod',
    '4198-Vampire Race - Blood Feeding.mod',
    '4206-Vampire Race - Blood Feeding.mod',
    '4214-Vampire Race - Blood Feeding.mod',
    '4232-Vampire Race - Blood Feeding.mod',
    '4234-Vampire Race - Blood Feeding.mod',
  ]);
  const customCharacters = parsed.items.filter(
    item => item.typeId === 1 &&
      item.stringId.endsWith('-Vampire Race - Blood Feeding.mod'),
  );
  const actualRaceLessCharacters = customCharacters.filter(item => !findReference(item, 'race'));
  const actualIds = new Set(actualRaceLessCharacters.map(item => item.stringId));
  if ([...actualIds].some(id => !expectedRaceLessCharacters.has(id))) {
    throw new Error(`Unexpected race-less character set: ${[...actualIds].join(', ')}`);
  }

  for (const stringId of expectedRaceLessCharacters) {
    if (!customCharacters.some(item => item.stringId === stringId)) {
      throw new Error(`Expected custom character record ${stringId}`);
    }
  }

  for (const character of actualRaceLessCharacters) {
    const entries = character.stringId === '4111-Vampire Race - Blood Feeding.mod'
      ? [{id: '17-gamedata.quack', values: [1000, 0, 0]}]
      : raceIds.map(id => ({id, values: [100, 0, 0]}));
    character.references.push({name: 'race', entries});
    modified.add(character);
  }

  const zeroLengthRecords = parsed.items.filter(item =>
    item.storedLength === 0 &&
    item.stringId.endsWith('-Vampire Race - Blood Feeding.mod'),
  );
  zeroLengthRecords.forEach(item => modified.add(item));

  const highestCustomId = Math.max(...parsed.items
    .map(item => item.stringId.match(/^(\d+)-Vampire Race - Blood Feeding\.mod$/))
    .filter(Boolean)
    .map(match => Number(match[1])));
  const directEdits = parsed.lastId === highestCustomId
    ? []
    : [output => output.writeInt32LE(highestCustomId, parsed.lastIdOffset)];

  if (removedHairReferences !== 0 && removedHairReferences !== 60) {
    throw new Error(`Expected to remove 0 or 60 Ark Haircuts references, removed ${removedHairReferences}`);
  }

  writeModifiedFile(filePath, parsed, modified, directEdits);
  return {
    assignedRaces: actualRaceLessCharacters.length,
    removedHairReferences,
    normalizedRecordLengths: zeroLengthRecords.length,
    updatedLastId: directEdits.length === 1,
  };
}

function repairZone(filePath) {
  const parsed = parseFile(filePath);
  if (parsed.type !== 15) {
    throw new Error(`${filePath} is not a Kenshi level-data file`);
  }

  const modified = new Set();
  let ownerFieldsChanged = 0;
  for (const item of parsed.items) {
    if (
      item.typeId !== 35 ||
      !item.stringId.includes('Vampire Race - Blood Feeding')
    ) {
      continue;
    }
    for (const dictionary of item.dictionaries) {
      for (const entry of dictionary) {
        if (
          (entry.key === 'owner faction ID' || entry.key === 'owner faction ID0') &&
          entry.value === '42022-rebirth.mod'
        ) {
          entry.value = '4071-Vampire Race - Blood Feeding.mod';
          ownerFieldsChanged += 1;
          modified.add(item);
        }
      }
    }
  }

  if (modified.size > 0) {
    writeModifiedFile(filePath, parsed, modified);
  }
  return {buildingsChanged: modified.size, ownerFieldsChanged};
}

function repairInteriors(filePath) {
  const parsed = parseFile(filePath);
  if (parsed.type !== 15) {
    throw new Error(`${filePath} is not a Kenshi level-data file`);
  }

  const modified = new Set();
  let removedFurnitureInstances = 0;
  for (const item of parsed.items) {
    const before = item.instances.length;
    item.instances = item.instances.filter(instance =>
      !instance.targetId.endsWith('-CBT Leisure Objects and Furniture.mod'),
    );
    removedFurnitureInstances += before - item.instances.length;
    if (item.instances.length !== before) {
      modified.add(item);
    }
  }

  if (removedFurnitureInstances !== 0 && removedFurnitureInstances !== 10) {
    throw new Error(`Expected to remove 0 or 10 CBT Leisure instances, removed ${removedFurnitureInstances}`);
  }
  if (modified.size > 0) {
    writeModifiedFile(filePath, parsed, modified);
  }
  return {layoutsChanged: modified.size, removedFurnitureInstances};
}

function verifyMod(filePath) {
  const parsed = parseFile(filePath);
  if (parsed.parsedEnd !== parsed.buffer.length) {
    throw new Error(`${filePath} has ${parsed.buffer.length - parsed.parsedEnd} unexpected trailing bytes`);
  }
  const arkReferences = parsed.items.flatMap(item => item.references)
    .flatMap(category => category.entries)
    .filter(entry => entry.id.endsWith('-Ark Haircuts.mod'));
  if (arkReferences.length !== 0) {
    throw new Error(`${filePath} still contains Ark Haircuts references`);
  }
  const raceLess = parsed.items.filter(
    item => item.typeId === 1 &&
      item.stringId.endsWith('-Vampire Race - Blood Feeding.mod') &&
      !findReference(item, 'race'),
  );
  if (raceLess.length !== 0) {
    throw new Error(`${filePath} still contains race-less custom characters`);
  }
  const invalidLengths = parsed.items.filter(item =>
    item.stringId.endsWith('-Vampire Race - Blood Feeding.mod') &&
    item.storedLength !== item.actualLength,
  );
  if (invalidLengths.length !== 0) {
    throw new Error(`${filePath} still contains ${invalidLengths.length} invalid custom record lengths`);
  }
  if (parsed.lastId !== 4243) {
    throw new Error(`${filePath} has last item ID ${parsed.lastId}; expected 4243`);
  }
}

function verifyZone(filePath) {
  const parsed = parseFile(filePath);
  const badOwners = parsed.items.filter(item =>
    item.typeId === 35 &&
    item.stringId.includes('Vampire Race - Blood Feeding') &&
    item.dictionaries.flat().some(entry =>
      (entry.key === 'owner faction ID' || entry.key === 'owner faction ID0') &&
      entry.value === '42022-rebirth.mod',
    ),
  );
  if (badOwners.length !== 0) {
    throw new Error(`${filePath} still contains ${badOwners.length} mis-owned Coven buildings`);
  }
}

function verifyInteriors(filePath) {
  const parsed = parseFile(filePath);
  const remaining = parsed.items.flatMap(item => item.instances)
    .filter(instance => instance.targetId.endsWith('-CBT Leisure Objects and Furniture.mod'));
  if (remaining.length !== 0) {
    throw new Error(`${filePath} still contains ${remaining.length} CBT Leisure instances`);
  }
}

function main() {
  const repository = path.resolve(__dirname, '..');
  const modPath = path.join(repository, 'Vampire Race - Blood Feeding.mod');
  const interiorsPath = path.join(repository, 'interiors.level');
  const zonePaths = [
    'zone.25.32.zone',
    'zone.25.33.zone',
    'zone.26.32.zone',
    'zone.26.33.zone',
  ].map(file => path.join(repository, file));

  const modResult = repairMod(modPath);
  const zoneResults = zonePaths.map(filePath => ({
    file: path.basename(filePath),
    ...repairZone(filePath),
  }));
  const interiorsResult = repairInteriors(interiorsPath);

  verifyMod(modPath);
  zonePaths.forEach(verifyZone);
  verifyInteriors(interiorsPath);

  console.log(JSON.stringify({mod: modResult, zones: zoneResults, interiors: interiorsResult}, null, 2));
}

if (require.main === module) {
  main();
}

module.exports = {
  parseBuffer,
  parseFile,
  repairInteriors,
  repairMod,
  repairZone,
  verifyInteriors,
  verifyMod,
  verifyZone,
};
