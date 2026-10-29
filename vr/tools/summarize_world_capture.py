#!/usr/bin/env python3
"""Summarize and validate a MOHU-SP-WORLD-CAPTURE file.

The capture is produced only by the default-OFF diagnostic build
(MOHU_VR_WORLD_CAPTURE) when MOHU_SP_WORLD_CAPTURE is set. This tool checks the
structural invariants the probe relies on and reports the captured fields. It
does not invent a material mapping: the 12-byte face record is reported as
three 16-bit pairs because that is what the bytes are, and texture page/CLUT
fields stay null until a capture proves where they live.
"""
import argparse
import json
import re
import struct
from pathlib import Path

HEADER = "MOHU-SP-WORLD-CAPTURE 1"
DRAW_RE = re.compile(
    r"draw=(\d+) ra=0x([0-9A-Fa-f]{8}) begin=0x([0-9A-Fa-f]{8}) "
    r"limit=0x([0-9A-Fa-f]{8}) a2=0x([0-9A-Fa-f]{8}) "
    r"a3=0x([0-9A-Fa-f]{8}) sp=0x([0-9A-Fa-f]{8}) "
    r"gp=0x([0-9A-Fa-f]{8}) level=0x([0-9A-Fa-f]{8}) "
    r"sub=0x([0-9A-Fa-f]{8}) root=0x([0-9A-Fa-f]{8}) "
    r"count=(\d+) table=0x([0-9A-Fa-f]{8})")
DRAW_TABLE_RE = re.compile(
    r"draw=(\d+) record_base=0x([0-9A-Fa-f]{8}) "
    r"record_entries=(\d+) records=([0-9a-f]*)")
FACE_RE = re.compile(
    r"face=(\d+) draw=(\d+) ra=0x([0-9A-Fa-f]{8}) "
    r"s7=0x([0-9A-Fa-f]{8}) face=0x([0-9A-Fa-f]{8}) index=(\d+) "
    r"table_base=0x([0-9A-Fa-f]{8}) record_base=0x([0-9A-Fa-f]{8}) "
    r"ok=(\d) flags=0x([0-9A-Fa-f]{8}) gpr27=0x([0-9A-Fa-f]{8}) "
    r"d8=0x([0-9A-Fa-f]{8}) dc=0x([0-9A-Fa-f]{8})")
FACE_BYTES_RE = re.compile(
    r"face=(\d+) face_bytes=([0-9a-f]+) record=([0-9a-f]+) table=([0-9a-f]*)")


def fnv1a(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def fail(message):
    raise ValueError(message)


def summarize(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != HEADER:
        fail("not a MOHU-SP-WORLD-CAPTURE version 1 file")
    if not lines[1].startswith("draws="):
        fail("missing draws/faces header")
    summary = {}
    for line in lines[1:]:
        m = DRAW_RE.match(line)
        if m:
            index = int(m.group(1))
            if index in summary:
                fail(f"duplicate draw {index}")
            summary[index] = {
                "ra": int(m.group(2), 16),
                "begin": int(m.group(3), 16),
                "limit": int(m.group(4), 16),
                "a2": int(m.group(5), 16),
                "a3": int(m.group(6), 16),
                "level": int(m.group(9), 16),
                "sub": int(m.group(10), 16),
                "root": int(m.group(11), 16),
                "count": int(m.group(12)),
                "table": int(m.group(13), 16),
                "record_base": None,
                "record_entries": 0,
                "records": b"",
            }
            continue
        m = DRAW_TABLE_RE.match(line)
        if m:
            index = int(m.group(1))
            if index not in summary:
                fail(f"record table before draw {index}")
            summary[index]["record_base"] = int(m.group(2), 16)
            summary[index]["record_entries"] = int(m.group(3))
            summary[index]["records"] = bytes.fromhex(m.group(4))
            continue
        if line.startswith("draw=") and "faces=" not in line:
            # Scratch/range hex lines are evidence, not parsed fields.
            continue

    faces = {}
    blobs = {}
    for line in lines:
        m = FACE_RE.match(line)
        if m:
            index = int(m.group(1))
            if index in faces:
                fail(f"duplicate face {index}")
            faces[index] = {
                "draw": int(m.group(2)),
                "ra": int(m.group(3), 16),
                "s7": int(m.group(4), 16),
                "face": int(m.group(5), 16),
                "index": int(m.group(6)),
                "table_base": int(m.group(7), 16),
                "record_base": int(m.group(8), 16),
                "ok": int(m.group(9)),
                "flags": int(m.group(10), 16),
                "gpr27": int(m.group(11), 16),
                "d8": int(m.group(12), 16),
                "dc": int(m.group(13), 16),
            }
            continue
        m = FACE_BYTES_RE.match(line)
        if m:
            blobs[int(m.group(1))] = (bytes.fromhex(m.group(2)),
                                      bytes.fromhex(m.group(3)))

    if not summary:
        fail("no draw records")
    if not faces:
        fail("no face records")
    if set(faces) != set(blobs):
        fail("face summary and byte rows do not match")

    distinct = {}
    for index, face in sorted(faces.items()):
        face_bytes, record = blobs[index]
        if len(face_bytes) != 16:
            fail(f"face {index}: expected 16 face bytes")
        if len(record) != 12:
            fail(f"face {index}: expected 12 record bytes")
        if face["s7"] != face["face"] + 8:
            fail(f"face {index}: s7 is not face+8")
        if struct.unpack("<H", face_bytes[6:8])[0] != face["index"]:
            fail(f"face {index}: index is not half[face+6]")
        if face["record_base"] != face["table_base"] + face["index"] * 12:
            fail(f"face {index}: record base is not table+index*12")
        if face["ok"] != 1:
            fail(f"face {index}: record was not captured")
        if face["table_base"] == 0:
            fail(f"face {index}: empty record table base")
        record_hash = fnv1a(record)
        entry = distinct.setdefault(record_hash, {
            "indices": [],
            "record": record,
            "half_words": [],
        })
        entry["indices"].append(face["index"])
        if entry["record"] != record:
            fail("record hash collision")
        entry["half_words"] = list(struct.unpack("<6H", record))

    report = {
        "schema": 1,
        "source": str(path),
        "draws": [],
        "faces": len(faces),
        "distinct_records": len(distinct),
        "face_record": {
            "size": 12,
            "layout": [
                {"offset": 0, "width": 2, "field": "half0"},
                {"offset": 2, "width": 2, "field": "half1"},
                {"offset": 4, "width": 2, "field": "half2"},
                {"offset": 6, "width": 2, "field": "half3"},
                {"offset": 8, "width": 2, "field": "half4"},
                {"offset": 10, "width": 2, "field": "half5"},
            ],
            "proven": "six 16-bit fields read at base+index*12; the low halves "
                      "are written to packet +0x38/+0x3C/+0x40 and the high "
                      "halves through other packet fields after adding a base",
            "not_proven": "UV vs coordinate-delta meaning of each half",
        },
        "material_fields": {
            "texture_page": None,
            "clut": None,
            "shading": None,
            "semi_transparency": None,
            "reason": "not present in the captured 12-byte record; the "
                      "packet/preflight fields that may carry them are not "
                      "mapped yet",
        },
        "records": [
            {"hash": f"0x{key:08X}", "indices": value["indices"],
             "half_words": value["half_words"],
             "record_hex": value["record"].hex()}
            for key, value in distinct.items()
        ],
    }
    for index in sorted(summary):
        draw = summary[index]
        if draw["ra"] != 0x8009A51C:
            fail(f"draw {index}: unexpected return address")
        if draw["limit"] < draw["begin"]:
            fail(f"draw {index}: limit precedes begin")
        report["draws"].append({
            "index": index,
            "ra": f"0x{draw['ra']:08X}",
            "begin": f"0x{draw['begin']:08X}",
            "limit": f"0x{draw['limit']:08X}",
            "level": f"0x{draw['level']:08X}",
            "sub": f"0x{draw['sub']:08X}",
            "root": f"0x{draw['root']:08X}",
            "vertex_count": draw["count"],
            "vertex_table": f"0x{draw['table']:08X}",
            # Captured at the NEXT packet entry, so it describes the scratch
            # contents after this draw returned, not necessarily this draw's
            # table. The per-face table_base above is authoritative.
            "record_table_before_call": (
                f"0x{draw['record_base']:08X}"
                if draw["record_base"] is not None else None),
            "record_table_entries_before_call": draw["record_entries"],
            "record_table_hash_before_call": (
                f"0x{fnv1a(draw['records']):08X}" if draw["records"] else None),
        })
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = summarize(args.capture)
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
