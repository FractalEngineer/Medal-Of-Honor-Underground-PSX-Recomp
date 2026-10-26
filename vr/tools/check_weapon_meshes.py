"""Validate complete-gun topology for all captured Underground viewmodels.

The inventory is produced by ``inspect_weapon_sets.py --first-person-models``.
This tool reads its saved RAM, verifies the native geometry identity, decodes
the 28-byte triangle/8-byte strip stream, and proves that each selected gun
never shares a triangle with a masked arm vertex.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct

import check_p38_mesh as native_mesh


PROFILES = {
    0: {"name": "P38 pistol", "nodes": {13},
        "partial": (11, set(range(6, 33))),
        "faces": 128, "vertices": 96},
    1: {"name": "MP40", "nodes": {26, 29, 31}, "partial": None,
        "faces": 193, "vertices": 124},
    4: {"name": "Shotgun", "nodes": {18, 20}, "partial": None,
        "faces": 182, "vertices": 137},
    5: {"name": "Scoped rifle", "nodes": {22, 25}, "partial": None,
        "faces": 199, "vertices": 159},
    8: {"name": "Colt .45", "nodes": {13}, "partial": None,
        "faces": 115, "vertices": 68},
    9: {"name": "Silenced pistol", "nodes": {13},
        "partial": (11, set(range(6, 18)) | set(range(26, 32))),
        "faces": 94, "vertices": 75},
    10: {"name": "Stick grenade", "nodes": {23}, "partial": None,
         "faces": 140, "vertices": 58},
    12: {"name": "M1 Garand", "nodes": {22}, "partial": None,
         "faces": 174, "vertices": 136},
    13: {"name": "Panzerfaust", "nodes": {27, 28, 30}, "partial": None,
         "faces": 168, "vertices": 116},
    14: {"name": "Crossbow",
         "nodes": {14, 17, 18, 19, 21, 23, 25, 26, 28}, "partial": None,
         "faces": 187, "vertices": 178},
    15: {"name": "Petrol bomb", "nodes": {25, 26, 27}, "partial": None,
         "faces": 198, "vertices": 99},
    16: {"name": "Sten", "nodes": {26, 29, 30}, "partial": None,
         "faces": 217, "vertices": 166},
    17: {"name": "StG44", "nodes": {27, 29, 31}, "partial": None,
         "faces": 215, "vertices": 161},
}


def geometry_identity(counts, vertex_bytes):
    result = 2166136261
    for node, count in enumerate(counts):
        for value in struct.pack("<I", count) + vertex_bytes[node]:
            result = ((result ^ value) * 16777619) & 0xFFFFFFFF
    return result


def selected(profile, node, vertex):
    if node in profile["nodes"]:
        return True
    partial = profile["partial"]
    return bool(partial and node == partial[0] and
                vertex in partial[1])


def triangle_components(triangles, vertices):
    parent = {vertex: vertex for vertex in vertices}

    def find(vertex):
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    def union(first, second):
        first, second = find(first), find(second)
        if first != second:
            parent[second] = first

    included = [triangle for triangle in triangles
                if all(vertex in parent for vertex in triangle)]
    for triangle in included:
        union(triangle[0], triangle[1])
        union(triangle[1], triangle[2])

    groups = defaultdict(list)
    for triangle in included:
        groups[find(triangle[0])].append(triangle)
    result = []
    for group in groups.values():
        used = {vertex for triangle in group for vertex in triangle}
        result.append({
            "triangles": len(group),
            "vertices": len(used),
            "nodes": sorted({node for node, vertex in used}),
        })
    return sorted(result, key=lambda row: (-row["triangles"], row["nodes"]))


def analyze_capture(capture, ram, profile):
    model = capture["first_person_model"]
    counts = [node["vertices"] for node in model["nodes"]]
    vertex_bytes = []
    vertices = {}
    for node, row in enumerate(model["nodes"]):
        if row["vertices"]:
            address = int(row["address"], 16) - 0x80000000
            data = ram[address:address + row["vertices"] * 8]
            if len(data) != row["vertices"] * 8:
                raise ValueError(f"ID {capture['players'][0]['weapon_id']} "
                                 f"node {node} exceeds RAM")
            vertex_bytes.append(data)
            for vertex in range(row["vertices"]):
                vertices[(node, vertex)] = struct.unpack_from(
                    "<3h", data, vertex * 8
                )
        else:
            vertex_bytes.append(b"")

    geometry = geometry_identity(counts, vertex_bytes)
    expected_geometry = int(model["geometry_fnv32"], 16)
    if geometry != expected_geometry:
        raise ValueError("Geometry identity mismatch")

    face_address = int(model["faces"], 16) - 0x80000000
    if face_address < 0 or face_address >= len(ram):
        raise ValueError("Face stream address is outside captured RAM")
    triangles, consumed = native_mesh.decode_triangles(
        ram[face_address:], model["face_count"],
        {node: count for node, count in enumerate(counts)},
    )
    unused = {vertex for triangle in triangles for vertex in triangle}
    unused = set(vertices) - unused

    selected_triangles = [
        triangle for triangle in triangles
        if all(selected(profile, node, vertex)
               for node, vertex in triangle)
    ]
    mixed = [
        triangle for triangle in triangles
        if any(selected(profile, node, vertex)
               for node, vertex in triangle) and
        not all(selected(profile, node, vertex)
                for node, vertex in triangle)
    ]
    if mixed:
        raise ValueError(f"ID {capture['players'][0]['weapon_id']} "
                         f"has {len(mixed)} mixed gun/arm triangles")

    selected_vertices = {
        (node, vertex) for node, vertex in vertices
        if selected(profile, node, vertex)
    }
    selected_counts = [
        sum(selected(profile, node, vertex)
            for vertex in range(count))
        for node, count in enumerate(counts)
    ]
    if len(selected_triangles) != profile["faces"]:
        raise ValueError(f"ID {capture['players'][0]['weapon_id']} retained "
                         f"{len(selected_triangles)} triangles, expected "
                         f"{profile['faces']}")
    if sum(selected_counts) != profile["vertices"]:
        raise ValueError(f"ID {capture['players'][0]['weapon_id']} retained "
                         f"{sum(selected_counts)} source vertices, expected "
                         f"{profile['vertices']}")

    selected_components = triangle_components(selected_triangles, selected_vertices)
    arm_components = triangle_components(
        triangles, set(vertices) - selected_vertices
    )
    if sum(row["triangles"] for row in selected_components) != profile["faces"]:
        raise ValueError("Selected component triangle accounting failed")

    stream = ram[face_address:face_address + consumed]
    return {
        "id": capture["players"][0]["weapon_id"],
        "name": profile["name"],
        "slot": capture["slot"],
        "switches": capture["switches"],
        "source": str(capture["source"]),
        "geometry_fnv32": f"0x{geometry:08X}",
        "mesh_magic": model["magic"],
        "native": {
            "nodes": model["node_count"],
            "faces": model["face_count"],
            "vertices": sum(counts),
            "triangle_bytes": consumed,
        },
        "gun": {
            "nodes": sorted(profile["nodes"]),
            "partial_node": profile["partial"][0]
            if profile["partial"] else None,
            "partial_vertex_indices": sorted(profile["partial"][1])
            if profile["partial"] else [],
            "faces": len(selected_triangles),
            "vertices": sum(selected_counts),
            "masked_vertices": sum(counts) - sum(selected_counts),
            "unreferenced_vertices": len(unused),
            "selected_components": selected_components,
            "arm_components": arm_components,
        },
        "triangle_stream_sha256": hashlib.sha256(stream).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()

    inventory_path = args.inventory.resolve()
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    captures = {}
    for slot in inventory["slots"]:
        ram_path = inventory_path.parent / f"slot-{slot['slot']:02}/ram.bin"
        ram = ram_path.read_bytes()
        for source in slot["captures"]:
            model = source.get("first_person_model")
            if not model:
                continue
            weapon_id = source["players"][0]["weapon_id"]
            if weapon_id not in captures:
                captures[weapon_id] = ({
                    "slot": slot["slot"],
                    "switches": source["switches"],
                    "players": source["players"],
                    "first_person_model": model,
                    "source": str(inventory_path),
                }, ram, str(ram_path))

    expected = set(PROFILES)
    if set(captures) != expected:
        raise ValueError(f"Expected IDs {sorted(expected)}, got {sorted(captures)}")

    rows = []
    for weapon_id in sorted(captures):
        capture, ram, ram_path = captures[weapon_id]
        row = analyze_capture(capture, ram, PROFILES[weapon_id])
        row["ram_sha256"] = hashlib.sha256(ram).hexdigest()
        row["ram_path"] = ram_path
        rows.append(row)

    receipt = {
        "schema": 1,
        "kind": "W3.4 complete-gun topology and mixed-node islands",
        "complete": True,
        "inventory": str(inventory_path),
        "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        "weapons": rows,
        "scope": "Offline native topology proof; no pose, animation, physical "
                 "attachment, shot alignment or hardware acceptance claim",
    }
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    args.proof.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(rows)} complete-gun profiles; mixed gun/arm triangles 0")


if __name__ == "__main__":
    main()
