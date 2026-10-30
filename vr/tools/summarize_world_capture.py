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
    r"d8=0x([0-9A-Fa-f]{8}) dc=0x([0-9A-Fa-f]{8})"
    r"(?: packet_ptr=0x([0-9A-Fa-f]{8}))?")
FACE_BYTES_RE = re.compile(
    r"face=(\d+) face_bytes=([0-9a-f]+) record=([0-9a-f]+) table=([0-9a-f]*)")
FACE_PACKET_RE = re.compile(
    r"face=(\d+) packet_captured=(\d) packet_hash=0x([0-9A-Fa-f]+) "
    r"packet=([0-9a-f]*)")
NATIVE_COMPARE_RE = re.compile(
    r"draw=(\d+) native_compare=1 native=(\d+) overflow=(\d+) unique=(\d+) "
    r"matched=(\d+) missing=(\d+) decoded_only=(\d+) dup=(\d+) "
    r"multi=(\d+) multi_count=(\d+) triangles=(\d+) status=(\d+) "
    r"first_missing=0x([0-9A-Fa-f]{8}) first_dup=0x([0-9A-Fa-f]{8}) "
    r"first_multi=0x([0-9A-Fa-f]{8})"
    r"(?: missing_in_range=(\d+) missing_addrs=([0-9a-fx,]*))?")
VISIBLE_FACES_RE = re.compile(
    r"visible_faces=1 draw=(\d+) status=(\d+) native=(\d+) matched=(\d+) "
    r"missing=(\d+) decoded_only=(\d+) triangles=(\d+) "
    r"first_missing=0x([0-9A-F]{8})")
GP0_RE = re.compile(
    r"gp0=(\d+) src=0x([0-9A-F]{8}) op=0x([0-9A-F]{2}) n=(\d+) "
    r"words=([0-9A-Fa-f]*)")
GP0_OVERFLOW_RE = re.compile(r"gp0_overflow=(\d+) draw=(\d+)")
ENTRY_RE = re.compile(
    r"entry=(\d+) ra=0x([0-9A-F]+) pc=0x([0-9A-F]+) level=0x([0-9A-F]+) "
    r"sub=0x([0-9A-F]+) root=0x([0-9A-F]+) table=0x([0-9A-F]+) count=(\d+) "
    r"faces=(\d+) selected=(\d+) overflow=(\d+) compare=(\d) status=(\d+) "
    r"matched=(\d+) missing=(\d+) decoded_only=(\d+) triangles=(\d+) "
    r"first_missing=0x([0-9A-F]{8}) visible=(\d+) visible_overflow=(\d+) "
    r"visible_entries=([^ ]*)")


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
    if not any(line.startswith("draws=") for line in lines[1:8]):
        fail("missing draws/faces header")
    summary = {}
    entries = []
    for line in lines[1:]:
        m = ENTRY_RE.match(line)
        if m:
            visible = []
            for item in m.group(21).split(","):
                if not item:
                    continue
                pointer, faces, face_list = item.split(":")
                visible.append({
                    "entry": f"0x{pointer.upper()}",
                    "faces": int(faces),
                    "list": f"0x{face_list.upper()}",
                })
            entries.append({
                "index": int(m.group(1)),
                "ra": f"0x{m.group(2)}",
                "pc": f"0x{m.group(3)}",
                "level": f"0x{m.group(4)}",
                "sub": f"0x{m.group(5)}",
                "root": f"0x{m.group(6)}",
                "table": f"0x{m.group(7)}",
                "vertex_count": int(m.group(8)),
                "faces": int(m.group(9)),
                "selected": bool(int(m.group(10))),
                "overflow": int(m.group(11)),
                "compare": bool(int(m.group(12))),
                "status": int(m.group(13)),
                "matched": int(m.group(14)),
                "missing": int(m.group(15)),
                "decoded_only": int(m.group(16)),
                "triangles": int(m.group(17)),
                "first_missing": f"0x{m.group(18)}",
                "visible_count": int(m.group(19)),
                "visible_overflow": int(m.group(20)),
                "visible": visible,
            })
            continue
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
                "native_compare": None,
                "visible_faces": None,
                "gp0": [],
                "gp0_overflow": 0,
            }
            continue
        m = GP0_RE.match(line)
        if m:
            index = int(m.group(1))
            if index not in summary:
                fail(f"GP0 command before draw {index}")
            text = m.group(5)
            summary[index]["gp0"].append({
                "src": f"0x{m.group(2)}",
                "opcode": int(m.group(3), 16),
                "n_words": int(m.group(4)),
                "words": [f"0x{text[i:i + 8]}" for i in range(0, len(text), 8)],
            })
            continue
        m = GP0_OVERFLOW_RE.match(line)
        if m:
            index = int(m.group(2))
            if index not in summary:
                fail(f"GP0 overflow before draw {index}")
            summary[index]["gp0_overflow"] = int(m.group(1))
            continue
        m = VISIBLE_FACES_RE.match(line)
        if m:
            index = int(m.group(1))
            if index not in summary:
                fail(f"visible faces before draw {index}")
            summary[index]["visible_faces"] = {
                "status": int(m.group(2)),
                "native": int(m.group(3)),
                "matched": int(m.group(4)),
                "missing": int(m.group(5)),
                "decoded_only": int(m.group(6)),
                "triangles": int(m.group(7)),
                "first_missing": f"0x{m.group(8).upper()}",
            }
            continue
        m = NATIVE_COMPARE_RE.match(line)
        if m:
            index = int(m.group(1))
            if index not in summary:
                fail(f"native compare before draw {index}")
            summary[index]["native_compare"] = {
                "native": int(m.group(2)),
                "overflow": int(m.group(3)),
                "unique": int(m.group(4)),
                "matched": int(m.group(5)),
                "missing": int(m.group(6)),
                "decoded_only": int(m.group(7)),
                "duplicate_calls": int(m.group(8)),
                "multi_source": int(m.group(9)),
                "multi_source_triangles": int(m.group(10)),
                "decoded_triangles": int(m.group(11)),
                "status": int(m.group(12)),
                "first_missing": f"0x{m.group(13).upper()}",
                "first_duplicate_call": f"0x{m.group(14).upper()}",
                "first_multi_source": f"0x{m.group(15).upper()}",
                "missing_in_range": (int(m.group(16))
                                     if m.group(16) else None),
                "missing_addrs": (m.group(17).split(",")
                                  if m.group(17) else []),
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
    packets = {}
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
                "packet_ptr": (int(m.group(14), 16)
                               if m.group(14) else None),
            }
            continue
        m = FACE_BYTES_RE.match(line)
        if m:
            blobs[int(m.group(1))] = (bytes.fromhex(m.group(2)),
                                      bytes.fromhex(m.group(3)))
            continue
        m = FACE_PACKET_RE.match(line)
        if m:
            packets[int(m.group(1))] = (int(m.group(2)),
                                        bytes.fromhex(m.group(4)),
                                        int(m.group(3), 16))

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

    def material(record):
        half = struct.unpack("<6H", record)
        return {
            "clut": half[1],                 # word0 high
            "texpage": half[3],              # word1 high
            "uv": [half[0], half[2], half[4]],
            "reserved": half[5],
        }

    def packet_material(words):
        if len(words) < 10 or (words[1] >> 24) != 0x34:
            return None
        return {
            "clut": (words[3] >> 16) & 0xFFFF,
            "texpage": (words[6] >> 16) & 0xFFFF,
            "uv": [words[3] & 0xFFFF, words[6] & 0xFFFF, words[9] & 0xFFFF],
        }

    face_evidence = []
    record_packet_matches = 0
    for index in sorted(faces):
        record = blobs[index][1]
        captured, data, stored_hash = packets.get(index, (0, b'', 0))
        if captured:
            if len(data) != 0x60:
                fail(f"face {index}: expected 96 packet bytes")
            if fnv1a(data) != stored_hash:
                fail(f"face {index}: packet hash mismatch")
        words = (list(struct.unpack("<%dI" % (len(data) // 4), data))
                 if captured else [])
        record_material = material(record)
        packet_material_value = packet_material(words)
        matches = bool(packet_material_value and
                       packet_material_value["clut"] == record_material["clut"] and
                       packet_material_value["texpage"] == record_material["texpage"])
        record_packet_matches += matches
        face_evidence.append({
            "face": index,
            "index": faces[index]["index"],
            "packet_ptr": (f"0x{faces[index]['packet_ptr']:08X}"
                           if faces[index]["packet_ptr"] is not None else None),
            "record_hash": f"0x{fnv1a(record):08X}",
            "record_half_words": list(struct.unpack("<6H", record)),
            "material": record_material,
            "packet_captured": bool(captured),
            "packet_hash": f"0x{stored_hash:08X}" if captured else None,
            "packet_words": ([f"0x{word:08X}" for word in words]
                             if captured else []),
            "packet_material": packet_material_value,
            "record_matches_packet": matches,
        })

    report = {
        "schema": 2,
        "source": str(path),
        "draws": [],
        "entries": entries,
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
            "proven": "word0 = UV0 | CLUT<<16, word1 = UV1 | texpage<<16, "
                      "word2 = UV2; the builder at 80011238..80011338 loads "
                      "these words and writes them to packet words 3, 6 and 9",
            "not_proven": "independent per-vertex UV association in the host "
                          "renderer; the record order is the native packet order",
        },
        "material_fields": {
            "texture_page": "record half_words[3] (word1 high)",
            "clut": "record half_words[1] (word0 high)",
            "shading": None,
            "semi_transparency": None,
            "reason": "CLUT/texpage are the record high halves and match the "
                      "0x34 packet where the packet pointer is fresh; shading "
                      "and semi-transparency are packet draw-mode state, not in "
                      "the 12-byte record",
        },
        "record_packet_matches": record_packet_matches,
        "records": [
            {"hash": f"0x{key:08X}", "indices": value["indices"],
             "half_words": value["half_words"],
             "record_hex": value["record"].hex()}
            for key, value in distinct.items()
        ],
        "face_evidence": face_evidence,
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
            "native_compare": draw["native_compare"],
            "visible_faces": draw["visible_faces"],
            "gp0": draw["gp0"],
            "gp0_overflow": draw["gp0_overflow"],
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
