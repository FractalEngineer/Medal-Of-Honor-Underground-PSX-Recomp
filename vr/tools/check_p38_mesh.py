"""Verify the P38 barrel island and derive complete-gun calibration.

Native first-person geometry uses a 28-byte triangle followed by 8-byte strip
extensions and a 0x1FFF terminator. This differs from the reference fixed-face
reader. Every decoded index is checked against the captured source nodes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
COUNTS = {9: 20, 11: 149, 13: 69}


def gun_vertex(node, vertex):
    return (node == 13 and 0 <= vertex < 69) or (node == 11 and 6 <= vertex <= 32)


def decode_triangles(data, count, counts):
    triangles = []
    cursor = 0
    def checked(vertices):
        if any(node not in counts or not 0 <= index < counts[node] for node,index in vertices):
            raise ValueError("Invalid native triangle node/vertex index")
        triangles.append(tuple(vertices))
    while len(triangles) < count:
        if cursor + 28 > len(data):
            raise ValueError("Truncated native triangle")
        vertices = [(data[cursor+23] & 0x9F, data[cursor+22]),
                    (data[cursor+25], data[cursor+24]),
                    (data[cursor+27], data[cursor+26])]
        checked(vertices)
        cursor += 28
        while len(triangles) < count:
            if cursor + 4 > len(data):
                raise ValueError("Missing strip terminator")
            code = struct.unpack_from("<H", data, cursor)[0]
            if code == 0x1FFF:
                cursor += 4
                break
            if cursor + 8 > len(data):
                raise ValueError("Truncated strip extension")
            vertex = (code & 31, code >> 8)
            vertices = ([vertices[2], vertices[1], vertex] if code & 128
                        else [vertices[1], vertices[2], vertex])
            checked(vertices)
            cursor += 8
    if cursor + 4 > len(data) or struct.unpack_from("<H",data,cursor)[0] != 0x1FFF:
        raise ValueError("Missing final strip terminator")
    return triangles, cursor + 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("triangle_stream", type=Path)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.capture.read_text(encoding="utf-8"))
    local = {int(node): value["local"] for node,value in raw.items()}
    animated = {int(node): np.array(value["animated"],dtype=float)[:,:3] for node,value in raw.items()}
    h = 2166136261
    for node in range(14):
        vertices = local.get(node, [])
        if len(vertices) != COUNTS.get(node,0):
            raise ValueError("Wrong P38 node layout")
        for byte in struct.pack("<I",len(vertices)) + b"".join(struct.pack("<4h",*v) for v in vertices):
            h = ((h ^ byte)*16777619)&0xFFFFFFFF
    if h != 0x8544F8B9:
        raise ValueError("Wrong complete P38 source geometry")
    stream = args.triangle_stream.read_bytes()
    triangles, consumed = decode_triangles(stream,354,COUNTS)
    if consumed != len(stream):
        raise ValueError("Unexpected trailing P38 triangle bytes")
    kept = [tri for tri in triangles if all(gun_vertex(*v) for v in tri)]
    barrel = [tri for tri in kept if all(node == 11 for node,index in tri)]
    if len(kept) != 128 or len(barrel) != 37:
        raise ValueError("Incomplete gun/barrel triangle selection")
    used = {v for tri in kept for v in tri}
    expected = {(13,index) for index in range(69)} | {(11,index) for index in range(6,33)}
    if used != expected:
        raise ValueError("Gun vertex selection lost or added geometry")
    grip = animated[13][47:65].mean(axis=0)
    muzzle = animated[11][24:29].mean(axis=0)
    barrel_base = animated[11][11:18].mean(axis=0)
    forward = muzzle-barrel_base
    forward /= np.linalg.norm(forward)
    down = np.array([0.,1.,0.])
    down -= down.dot(forward)*forward
    down /= np.linalg.norm(down)
    right = np.cross(down,forward)
    points = np.vstack([animated[13],animated[11][6:33]])
    span = float(np.ptp(points@forward))
    proof = {
        "schema":1, "kind":"P38 complete gun with mixed-node barrel; provisional physical calibration",
        "capture":str(args.capture), "capture_sha256":hashlib.sha256(args.capture.read_bytes()).hexdigest(),
        "triangle_stream_sha256":hashlib.sha256(stream).hexdigest(),
        "geometry_fnv32":f"0x{h:08X}",
        "asset":{"id":0,"node":13,"vertex_count":69,"barrel_node":11,
                 "barrel_vertex_indices":list(range(6,33)),"barrel_triangles":37,
                 "gun_triangles":128,"native_triangles":354,"triangle_stream_bytes":len(stream)},
        "animated_model":{"grip_pivot":grip.tolist(),"muzzle":muzzle.tolist(),
            "barrel_axis_base":barrel_base.tolist(),"right":right.tolist(),
            "up":(-down).tolist(),"forward":forward.tolist(),"forward_span_units":span,
            "model_units_per_metre":span/.216},
        "marker_groups":{"grip_node":13,"grip_vertex_indices":list(range(47,65)),
            "muzzle_node":11,"muzzle_vertex_indices":list(range(24,29)),
            "barrel_base_indices":list(range(11,18))},
        "scale":{"provisional":True,"model_units_per_metre":span/.216,
                 "physical_acceptance":"open; W3.3"},
        "correction":"Prior node13-only profile omitted the barrel and used a receiver cap as muzzle. Historical W3.1 receipt retained.",
    }
    args.proof.write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
    print("PASS: 128 gun triangles, including 37 barrel triangles / 27 mixed-node vertices")


if __name__ == "__main__":
    main()
