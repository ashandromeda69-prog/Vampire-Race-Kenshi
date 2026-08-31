"""
Exact reader/writer for Kenshi .mod / .base files (fileType 16 and 17).

Design goal: BYTE-EXACT round trip. Every string and float is kept as raw bytes
so that parse -> serialize reproduces the input file identically. Only then is it
safe to make targeted edits to a binary we cannot test in-game.

Format (verified against ashandromeda69-prog/Vampire-Race-Kenshi and against the
community reference implementation Kakrain/KenshiCore, ReverseEngineer.cs):

  header:
    i32 fileType            (16 or 17)
    i32 detailsLen          (byte length of the details blob that follows)
    details blob:
      i32 modVersion
      str author
      str description
      str dependencies      (comma separated file names)
      str references        (comma separated file names)
      u32 saveCount
      u32 lastMerge
      u8  mergeEntryCount + entries
      u8  deleteRequestCount + entries
    i32 lastId
    i32 recordCount

  record (repeated recordCount times):
    i32 leadInt      v17: total byte size of the record INCLUDING this field.
                     v16: instance count. Kenshi's own writer emits the byte size
                     for v17; KenshiCore emits instance count in both. Readers
                     appear to parse sequentially, but a v16-framed record inside
                     a v17 file is non-conforming either way.
    i32 recordType
    i32 recordId
    str name
    str stringId     "<numericId>-<sourceFile>", identifies who owns the record
    u32 changeType   v17: 0x20 new, 0x21 modified, 0x23 modified+renamed
                     v16: 0x80000002 new, 0x80000001 modified, 0x80000003 both
    7 field dictionaries, in order: bool(1 byte), float(4), int(4),
       vec3(12), vec4(16), string(str), filename(str)
       each: i32 count, then count * (str key, value)
    reference categories:
       i32 catCount, then catCount * (str category, i32 n, n * (str target, i32, i32, i32))
    instances:
       i32 count, then count * (str id, str target, 7 floats, i32 stateCount, states)
"""

import struct

NEW_V16      = 0x80000002
CHANGED_V16  = 0x80000001
RENAMED_V16  = 0x80000003
NEW_V17      = 0x00000020
CHANGED_V17  = 0x00000021
RENAMED_V17  = 0x00000023

V16_CHANGE_TYPES = {NEW_V16, CHANGED_V16, RENAMED_V16}

# Field dictionary kinds, in file order. Value is the fixed byte width, or None
# for length-prefixed strings.
FIELD_KINDS = [
    ('bool', 1), ('float', 4), ('int', 4),
    ('vec3', 12), ('vec4', 16),
    ('str', None), ('file', None),
]

RECORD_TYPE_NAMES = {
    1: 'CHARACTER', 2: 'WEAPON', 3: 'ARMOUR', 4: 'ITEM', 5: 'RACE_OLD',
    7: 'RACE', 10: 'FACTION', 13: 'TOWN', 18: 'DIALOGUE', 19: 'DIALOGUE_LINE',
    26: 'PERSONALITY', 49: 'VENDOR_LIST', 52: 'SQUAD_TEMPLATE', 64: 'GAME_START',
    76: 'ANIMAL_CHARACTER', 80: 'WEATHER_OR_EFFECT', 82: 'MAP_ITEM',
    95: 'BIOME_REGION', 100: 'RACE_GROUP',
}


class ModFormatError(Exception):
    pass


class Reader:
    def __init__(self, buf, pos=0):
        self.buf = buf
        self.pos = pos

    def i32(self):
        if self.pos + 4 > len(self.buf):
            raise ModFormatError(f"read past end at {self.pos}")
        v = struct.unpack_from('<i', self.buf, self.pos)[0]
        self.pos += 4
        return v

    def u32(self):
        if self.pos + 4 > len(self.buf):
            raise ModFormatError(f"read past end at {self.pos}")
        v = struct.unpack_from('<I', self.buf, self.pos)[0]
        self.pos += 4
        return v

    def raw(self, n):
        if self.pos + n > len(self.buf):
            raise ModFormatError(f"read past end at {self.pos} (+{n})")
        v = self.buf[self.pos:self.pos + n]
        self.pos += n
        return v

    def string(self, cap=4_000_000):
        n = self.i32()
        if n < 0 or n > cap:
            raise ModFormatError(f"implausible string length {n} at {self.pos - 4}")
        return self.raw(n)


class Writer:
    def __init__(self):
        self.parts = []

    def i32(self, v):
        self.parts.append(struct.pack('<i', v))

    def u32(self, v):
        self.parts.append(struct.pack('<I', v))

    def raw(self, b):
        self.parts.append(b)

    def string(self, b):
        self.parts.append(struct.pack('<i', len(b)))
        self.parts.append(b)

    def bytes(self):
        return b''.join(self.parts)


class Record:
    __slots__ = ('lead_int', 'type', 'id', 'name', 'string_id', 'change_type',
                 'dicts', 'refs', 'instances', 'file_offset')

    def __init__(self):
        self.lead_int = 0
        self.type = 0
        self.id = 0
        self.name = b''
        self.string_id = b''
        self.change_type = 0
        # dicts[i] is a list of (key_bytes, value_bytes) matching FIELD_KINDS[i]
        self.dicts = [[] for _ in FIELD_KINDS]
        # refs is a list of (category_bytes, [(target_bytes, a, b, c), ...])
        self.refs = []
        # instances is a list of (id_bytes, target_bytes, transform_bytes, [state_bytes])
        self.instances = []
        self.file_offset = 0

    # -- convenience accessors, decoded lazily; never used for serialization --
    @property
    def name_str(self):
        return self.name.decode('utf-8', 'replace')

    @property
    def string_id_str(self):
        return self.string_id.decode('utf-8', 'replace')

    @property
    def type_name(self):
        return RECORD_TYPE_NAMES.get(self.type, f'TYPE_{self.type}')

    def owner(self):
        """The file this record belongs to, from '<id>-<file>'. None if unusual."""
        s = self.string_id_str
        i = s.find('-')
        if i <= 0 or not s[:i].isdigit():
            return None
        return s[i + 1:]

    def is_v16_framed(self, computed_len):
        return self.change_type in V16_CHANGE_TYPES or self.lead_int != computed_len

    def ref_targets(self):
        for cat, items in self.refs:
            for tgt, a, b, c in items:
                yield cat.decode('utf-8', 'replace'), tgt.decode('utf-8', 'replace')

    def serialize_body(self):
        """Everything after the lead int."""
        w = Writer()
        w.i32(self.type)
        w.i32(self.id)
        w.string(self.name)
        w.string(self.string_id)
        w.u32(self.change_type)
        for entries in self.dicts:
            w.i32(len(entries))
            for key, val in entries:
                w.string(key)
                if isinstance(val, tuple):
                    w.string(val[0])   # length-prefixed string value
                else:
                    w.raw(val)         # fixed-width value, kept as raw bytes
        w.i32(len(self.refs))
        for cat, items in self.refs:
            w.string(cat)
            w.i32(len(items))
            for tgt, a, b, c in items:
                w.string(tgt)
                w.i32(a)
                w.i32(b)
                w.i32(c)
        w.i32(len(self.instances))
        for iid, tgt, transform, states in self.instances:
            w.string(iid)
            w.string(tgt)
            w.raw(transform)
            w.i32(len(states))
            for s in states:
                w.string(s)
        return w.bytes()

    def serialize(self, lead='computed'):
        """lead='computed' writes the conforming v17 byte length.
           lead='original' writes back whatever the file had (for round-trip tests)."""
        body = self.serialize_body()
        lead_val = len(body) + 4 if lead == 'computed' else self.lead_int
        return struct.pack('<i', lead_val) + body


class ModFile:
    def __init__(self):
        self.file_type = 17
        self.mod_version = 1
        self.author = b''
        self.description = b''
        self.dependencies = b''
        self.references = b''
        self.details_trailer = b''   # saveCount / lastMerge / merge / delete blobs
        self.last_id = 0
        self.records = []

    # ---------------- reading ----------------
    @classmethod
    def load(cls, path):
        with open(path, 'rb') as fh:
            data = fh.read()
        return cls.parse(data), data

    @classmethod
    def parse(cls, data):
        m = cls()
        r = Reader(data)
        m.file_type = r.i32()
        if m.file_type not in (16, 17):
            raise ModFormatError(f"unexpected fileType {m.file_type}")
        details_len = r.i32()
        details_end = r.pos + details_len
        m.mod_version = r.i32()
        m.author = r.string()
        m.description = r.string()
        m.dependencies = r.string()
        m.references = r.string()
        m.details_trailer = data[r.pos:details_end]
        r.pos = details_end
        m.last_id = r.i32()
        record_count = r.i32()

        for _ in range(record_count):
            m.records.append(cls._parse_record(r))
        m.trailing_bytes = data[r.pos:]
        return m

    @staticmethod
    def _parse_record(r):
        rec = Record()
        rec.file_offset = r.pos
        rec.lead_int = r.i32()
        rec.type = r.i32()
        rec.id = r.i32()
        rec.name = r.string()
        rec.string_id = r.string()
        rec.change_type = r.u32()

        for idx, (kind, width) in enumerate(FIELD_KINDS):
            n = r.i32()
            if n < 0 or n > 200_000:
                raise ModFormatError(f"implausible {kind} field count {n} at {r.pos - 4}")
            entries = rec.dicts[idx]
            for _ in range(n):
                key = r.string()
                if width is None:
                    entries.append((key, (r.string(),)))
                else:
                    entries.append((key, r.raw(width)))

        n = r.i32()
        if n < 0 or n > 200_000:
            raise ModFormatError(f"implausible ref category count {n} at {r.pos - 4}")
        for _ in range(n):
            cat = r.string()
            k = r.i32()
            if k < 0 or k > 500_000:
                raise ModFormatError(f"implausible ref count {k} at {r.pos - 4}")
            items = [(r.string(), r.i32(), r.i32(), r.i32()) for _ in range(k)]
            rec.refs.append((cat, items))

        n = r.i32()
        if n < 0 or n > 200_000:
            raise ModFormatError(f"implausible instance count {n} at {r.pos - 4}")
        for _ in range(n):
            iid = r.string()
            tgt = r.string()
            transform = r.raw(28)          # 3 floats position + 4 floats rotation
            sc = r.i32()
            if sc < 0 or sc > 100_000:
                raise ModFormatError(f"implausible state count {sc} at {r.pos - 4}")
            states = [r.string() for _ in range(sc)]
            rec.instances.append((iid, tgt, transform, states))

        return rec

    # ---------------- writing ----------------
    def serialize(self, lead='computed'):
        details = Writer()
        details.i32(self.mod_version)
        details.string(self.author)
        details.string(self.description)
        details.string(self.dependencies)
        details.string(self.references)
        details.raw(self.details_trailer)
        details_bytes = details.bytes()

        w = Writer()
        w.i32(self.file_type)
        w.i32(len(details_bytes))
        w.raw(details_bytes)
        w.i32(self.last_id)
        w.i32(len(self.records))
        for rec in self.records:
            w.raw(rec.serialize(lead=lead))
        w.raw(getattr(self, 'trailing_bytes', b''))
        return w.bytes()

    def save(self, path, lead='computed'):
        with open(path, 'wb') as fh:
            fh.write(self.serialize(lead=lead))

    # ---------------- helpers ----------------
    def dependency_list(self):
        s = self.dependencies.decode('utf-8', 'replace')
        return [x for x in (p.strip() for p in s.split(',')) if x]

    def referenced_files(self):
        """Every distinct source file this mod's data points at."""
        seen = {}
        for rec in self.records:
            for _cat, tgt in rec.ref_targets():
                i = tgt.find('-')
                if i > 0 and tgt[:i].isdigit():
                    seen[tgt[i + 1:]] = seen.get(tgt[i + 1:], 0) + 1
        return seen
