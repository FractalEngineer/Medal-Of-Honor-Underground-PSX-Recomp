#!/usr/bin/env python3
"""Rank likely engine-function equivalents between two PS-X executables.

This is a discovery aid, not an automatic hook generator. It decodes MIPS I
without third-party dependencies, normalizes addresses, and compares instruction
structure, GTE operations, call/branch/memory shape, and length.

Overlay captures from `overlay_captures.json` may be supplied for either
executable. A capture is treated as a distinct code generation; an address in an
overlay is never assumed to describe the main executable or another capture.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Sequence


PSX_EXE_MAGIC = b"PS-X EXE"
PSX_EXE_HEADER = 0x800
MAX_FUNCTION_INSTRUCTIONS = 2048

DEFAULT_LANDMARKS = (
    (0x80084718, "entity transform"),
    (0x800814C4, "geometry entry"),
    (0x80080DD4, "geometry filter"),
    (0x800824D0, "per-model render entry"),
    (0x8008B3E8, "level vertex transformer"),
    (0x80016E38, "VSync wrapper"),
    (0x80090B80, "gameplay render wait"),
    (0x8007E414, "multiplayer weapon geometry"),
    (0x800836C0, "weapon vertex filter"),
    (0x8006591C, "multiplayer shot basis"),
    (0x8006A76C, "primary shot basis"),
    (0x8008CE50, "multiplayer render wait"),
    (0x8008A440, "multiplayer level entry"),
)

GTE_OPS = {
    0x01: "RTPS",
    0x06: "NCLIP",
    0x0C: "OP",
    0x0E: "DPCS",
    0x11: "INTPL",
    0x12: "MVMVA",
    0x13: "NCDS",
    0x14: "CDP",
    0x16: "NCDT",
    0x1B: "NCCS",
    0x1C: "CC",
    0x1E: "NCS",
    0x20: "NCT",
    0x28: "SQR",
    0x29: "DCPL",
    0x2A: "DPCT",
    0x2D: "AVSZ3",
    0x2E: "AVSZ4",
    0x30: "RTPT",
    0x3D: "GPF",
    0x3E: "GPL",
    0x3F: "NCCT",
}

SPECIAL_NAMES = {
    0x00: "sll",
    0x02: "srl",
    0x03: "sra",
    0x04: "sllv",
    0x06: "srlv",
    0x07: "srav",
    0x08: "jr",
    0x09: "jalr",
    0x0C: "syscall",
    0x0D: "break",
    0x10: "mfhi",
    0x11: "mthi",
    0x12: "mflo",
    0x13: "mtlo",
    0x18: "mult",
    0x19: "multu",
    0x1A: "div",
    0x1B: "divu",
    0x20: "add",
    0x21: "addu",
    0x22: "sub",
    0x23: "subu",
    0x24: "and",
    0x25: "or",
    0x26: "xor",
    0x27: "nor",
    0x2A: "slt",
    0x2B: "sltu",
}

REGIMM_NAMES = {
    0x00: "bltz",
    0x01: "bgez",
    0x10: "bltzal",
    0x11: "bgezal",
}

BRANCH_NAMES = {
    0x01: "bgez",
    0x04: "beq",
    0x05: "bne",
    0x06: "blez",
    0x07: "bgtz",
}

LOAD_STORE_NAMES = {
    0x20: "lb",
    0x21: "lh",
    0x22: "lwl",
    0x23: "lw",
    0x24: "lbu",
    0x25: "lhu",
    0x26: "lwr",
    0x28: "sb",
    0x29: "sh",
    0x2A: "swl",
    0x2B: "sw",
    0x2E: "swr",
    0x32: "lwc2",
    0x3A: "swc2",
}

IMMEDIATE_NAMES = {
    0x08: "addi",
    0x09: "addiu",
    0x0A: "slti",
    0x0B: "sltiu",
    0x0C: "andi",
    0x0D: "ori",
    0x0E: "xori",
    0x0F: "lui",
}

STATUS_LABELS = (
    (0.93, "near-identical candidate"),
    (0.84, "strong candidate"),
    (0.74, "tentative candidate"),
    (0.60, "weak candidate"),
)


@dataclass(frozen=True)
class Instruction:
    address: int
    word: int
    mnemonic: str
    token: str
    kind: str
    gte_op: str | None = None
    branch_target: int | None = None


@dataclass(frozen=True)
class MemoryImage:
    label: str
    path: Path
    load_addr: int
    data: bytes
    kind: str
    identity: str
    sha256: str
    seeds: tuple[int, ...] = ()

    @property
    def end(self) -> int:
        return self.load_addr + len(self.data)

    def contains(self, address: int, size: int = 4) -> bool:
        return self.load_addr <= address and address + size <= self.end


@dataclass(frozen=True)
class PsxExe:
    path: Path
    entry_pc: int
    load_addr: int
    text_size: int
    data: bytes
    file_sha256: str


@dataclass(frozen=True)
class Function:
    image: MemoryImage
    address: int
    instructions: tuple[Instruction, ...]
    mnemonics: tuple[str, ...]
    tokens: tuple[str, ...]
    gte_ops: Counter[str]
    calls: int
    branches: int
    loads: int
    stores: int
    returns: int


@dataclass(frozen=True)
class RankedCandidate:
    function: Function
    score: float
    token_ratio: float
    opcode_ratio: float
    gte_ratio: float
    length_ratio: float
    profile_ratio: float

    @property
    def label(self) -> str:
        for threshold, label in STATUS_LABELS:
            if self.score >= threshold:
                return label
        return "low similarity"


def _reg(number: int) -> str:
    return f"r{number}"


def _branch_direction(pc: int, target: int) -> str:
    return "back" if target <= pc else "forward"


def _immediate_token(value: int) -> str:
    if -0x100 <= value <= 0x100 or value in (0x1F8, 0x7FFF, 0x8000, 0xFFFF):
        return f"{value:+d}"
    if value > 0 and value & (value - 1) == 0:
        return f"2pow{value.bit_length() - 1}"
    return "imm"


def _sign16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def decode_instruction(word: int, address: int) -> Instruction:
    """Decode the MIPS I subset used to fingerprint PS-X code."""

    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    sa = (word >> 6) & 0x1F
    funct = word & 0x3F
    signed_imm = _sign16(word & 0xFFFF)
    jump_target = ((address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
    branch_target = (address + 4 + (signed_imm << 2)) & 0xFFFFFFFF

    if op == 0x00:
        mnemonic = SPECIAL_NAMES.get(funct, f"special_{funct:02x}")
        if word == 0:
            return Instruction(address, word, "nop", "nop", "nop")
        if mnemonic == "jr":
            return Instruction(
                address,
                word,
                mnemonic,
                f"jr:{_reg(rs)}",
                "return" if rs == 31 else "jump",
            )
        if mnemonic == "jalr":
            return Instruction(
                address,
                word,
                mnemonic,
                f"jalr:{_reg(rd)}:{_reg(rs)}",
                "call",
            )
        if mnemonic in {"sll", "srl", "sra"}:
            return Instruction(
                address,
                word,
                mnemonic,
                f"{mnemonic}:{_reg(rd)}:{_reg(rt)}:{sa}",
                "shift",
            )
        if mnemonic in {"sllv", "srlv", "srav"}:
            return Instruction(
                address,
                word,
                mnemonic,
                f"{mnemonic}:{_reg(rd)}:{_reg(rt)}:{_reg(rs)}",
                "shift",
            )
        if mnemonic in {"mfhi", "mflo"}:
            return Instruction(
                address, word, mnemonic, f"{mnemonic}:{_reg(rd)}", "move"
            )
        if mnemonic in {"mthi", "mtlo"}:
            return Instruction(
                address, word, mnemonic, f"{mnemonic}:{_reg(rs)}", "move"
            )
        if mnemonic in {"mult", "multu", "div", "divu"}:
            return Instruction(
                address,
                word,
                mnemonic,
                f"{mnemonic}:{_reg(rs)}:{_reg(rt)}",
                "multiply" if "mult" in mnemonic else "divide",
            )
        if mnemonic in {"syscall", "break"}:
            return Instruction(address, word, mnemonic, mnemonic, "special")
        return Instruction(
            address,
            word,
            mnemonic,
            f"{mnemonic}:{_reg(rd)}:{_reg(rs)}:{_reg(rt)}",
            "alu",
        )

    if op == 0x01:
        mnemonic = REGIMM_NAMES.get(rt, f"regimm_{rt:02x}")
        direction = _branch_direction(address, branch_target)
        return Instruction(
            address,
            word,
            mnemonic,
            f"{mnemonic}:{_reg(rs)}:{direction}",
            "branch",
            branch_target=branch_target,
        )

    if op in (0x02, 0x03):
        mnemonic = "j" if op == 0x02 else "jal"
        kind = "jump" if op == 0x02 else "call"
        return Instruction(
            address,
            word,
            mnemonic,
            f"{mnemonic}:{'internal' if (jump_target & 0x0F000000) == 0x08000000 else 'target'}",
            kind,
            branch_target=jump_target,
        )

    if op in BRANCH_NAMES and op != 0x01:
        mnemonic = BRANCH_NAMES[op]
        direction = _branch_direction(address, branch_target)
        if op in (0x06, 0x07):
            token = f"{mnemonic}:{_reg(rs)}:{direction}"
        else:
            token = f"{mnemonic}:{_reg(rs)}:{_reg(rt)}:{direction}"
        return Instruction(
            address,
            word,
            mnemonic,
            token,
            "branch",
            branch_target=branch_target,
        )

    if op in LOAD_STORE_NAMES:
        mnemonic = LOAD_STORE_NAMES[op]
        kind = "load" if op < 0x28 else "store"
        token = f"{mnemonic}:{_reg(rt)}:{_reg(rs)}:{signed_imm}"
        return Instruction(address, word, mnemonic, token, kind)

    if op in IMMEDIATE_NAMES:
        mnemonic = IMMEDIATE_NAMES[op]
        if op == 0x0F:
            value = word & 0xFFFF
            token = f"lui:{_reg(rt)}:0x{value:04X}"
        else:
            token = (
                f"{mnemonic}:{_reg(rt)}:{_reg(rs)}:"
                f"{_immediate_token(signed_imm)}"
            )
        return Instruction(address, word, mnemonic, token, "alu")

    if op == 0x10:
        mnemonic = {
            0x00: "mfc0",
            0x04: "mtc0",
            0x10: "rfe",
        }.get(rs, f"cop0_{rs:02x}")
        if mnemonic in {"mfc0", "mtc0"}:
            token = f"{mnemonic}:{_reg(rt)}:{_reg(rd)}"
        else:
            token = mnemonic
        return Instruction(address, word, mnemonic, token, "cop0")

    if op == 0x12:
        if rs == 0x10:
            gte_name = GTE_OPS.get(funct, f"GTE_{funct:02X}")
            return Instruction(
                address,
                word,
                gte_name.lower(),
                f"gte:{gte_name}",
                "gte",
                gte_op=gte_name,
            )
        mnemonic = {
            0x00: "mfc2",
            0x02: "cfc2",
            0x04: "mtc2",
            0x06: "ctc2",
            0x08: "bc2f",
            0x09: "bc2t",
            0x0A: "bc2fl",
            0x0B: "bc2tl",
        }.get(rs, f"cop2_{rs:02x}")
        kind = "branch" if rs >= 0x08 else "cop2"
        token = f"{mnemonic}:{_reg(rt)}:{_reg(rd)}"
        return Instruction(address, word, mnemonic, token, kind)

    return Instruction(address, word, f".word_{op:02x}", ".word", "unknown")


def parse_seed_file(path: Path) -> tuple[int, ...]:
    addresses: set[int] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split()[0].rstrip(",")
        if token.lower().startswith("0x"):
            try:
                addresses.add(int(token, 16))
            except ValueError:
                pass
    return tuple(sorted(addresses))


def parse_psx_exe(path: Path, label: str = "main") -> PsxExe:
    raw = path.read_bytes()
    if len(raw) < PSX_EXE_HEADER or raw[:8] != PSX_EXE_MAGIC:
        raise ValueError(f"{path} is not a PS-X executable")
    entry_pc = struct.unpack_from("<I", raw, 0x10)[0]
    load_addr = struct.unpack_from("<I", raw, 0x18)[0]
    text_size = struct.unpack_from("<I", raw, 0x1C)[0]
    if text_size == 0 or PSX_EXE_HEADER + text_size > len(raw):
        raise ValueError(f"{path} has an invalid text size")
    return PsxExe(
        path=path,
        entry_pc=entry_pc,
        load_addr=load_addr,
        text_size=text_size,
        data=raw[PSX_EXE_HEADER : PSX_EXE_HEADER + text_size],
        file_sha256=hashlib.sha256(raw).hexdigest(),
    )


def image_from_exe(exe: PsxExe, label: str) -> MemoryImage:
    payload_hash = hashlib.sha256(exe.data).hexdigest()
    return MemoryImage(
        label=label,
        path=exe.path,
        load_addr=exe.load_addr,
        data=exe.data,
        kind="main-exe",
        identity=f"main-{payload_hash[:12]}",
        sha256=exe.file_sha256,
    )


def load_overlay_captures(path: Path, label_prefix: str) -> list[MemoryImage]:
    document = json.loads(path.read_text(encoding="utf-8"))
    captures = document if isinstance(document, list) else document.get("captures", [])
    if not isinstance(captures, list):
        raise ValueError(f"{path} does not contain a capture list")

    images: list[MemoryImage] = []
    for index, capture in enumerate(captures):
        try:
            load_addr = int(str(capture["load_addr"]), 0)
            encoded = str(capture["bytes_b64"])
            data = base64.b64decode(encoded, validate=True)
            declared_size = int(capture.get("size", len(data)))
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"invalid capture {index} in {path}: {exc}") from exc
        if declared_size != len(data):
            raise ValueError(
                f"capture {index} in {path} declares {declared_size} bytes "
                f"but decodes to {len(data)}"
            )
        seeds: set[int] = set()
        for key in ("seeds", "function_entry_pcs", "dispatch_entry_pcs"):
            for item in capture.get(key, []):
                try:
                    seeds.add(int(str(item), 0))
                except ValueError:
                    pass
        digest = hashlib.sha256(data).hexdigest()
        images.append(
            MemoryImage(
                label=(
                    f"{label_prefix} overlay {index + 1} "
                    f"@0x{load_addr:08X} {digest[:8]}"
                ),
                path=path,
                load_addr=load_addr,
                data=data,
                kind="overlay",
                identity=f"overlay-{digest[:12]}",
                sha256=digest,
                seeds=tuple(sorted(seeds)),
            )
        )
    return images


def read_word(image: MemoryImage, address: int) -> int | None:
    if not image.contains(address):
        return None
    offset = address - image.load_addr
    return struct.unpack_from("<I", image.data, offset)[0]


def decode_function(
    image: MemoryImage,
    address: int,
    *,
    boundary: int | None = None,
    max_instructions: int = MAX_FUNCTION_INSTRUCTIONS,
) -> Function:
    if address & 3:
        raise ValueError(f"function address 0x{address:08X} is not 4-byte aligned")
    if not image.contains(address):
        raise ValueError(f"0x{address:08X} is not inside {image.label}")

    limit = min(image.end, boundary if boundary is not None else image.end)
    available = max(0, (limit - address) // 4)
    count = min(available, max_instructions)
    instructions: list[Instruction] = []
    delay_after_return = False

    for index in range(count):
        pc = address + index * 4
        word = read_word(image, pc)
        if word is None:
            break
        instruction = decode_instruction(word, pc)
        instructions.append(instruction)
        if delay_after_return:
            break
        if instruction.kind == "return":
            delay_after_return = True

    if not instructions:
        raise ValueError(f"no instructions decoded at 0x{address:08X}")

    gte_ops = Counter(
        instruction.gte_op
        for instruction in instructions
        if instruction.gte_op is not None
    )
    return Function(
        image=image,
        address=address,
        instructions=tuple(instructions),
        mnemonics=tuple(instruction.mnemonic for instruction in instructions),
        tokens=tuple(instruction.token for instruction in instructions),
        gte_ops=gte_ops,
        calls=sum(instruction.kind == "call" for instruction in instructions),
        branches=sum(instruction.kind == "branch" for instruction in instructions),
        loads=sum(instruction.kind == "load" for instruction in instructions),
        stores=sum(instruction.kind == "store" for instruction in instructions),
        returns=sum(instruction.kind == "return" for instruction in instructions),
    )


def bound_for_seed(
    image: MemoryImage, address: int, all_seeds: Iterable[int]
) -> int | None:
    higher = [seed for seed in all_seeds if address < seed < image.end]
    return min(higher) if higher else None


def inventory_functions(
    images: Sequence[MemoryImage],
    main_seeds: Sequence[int],
) -> list[Function]:
    functions: list[Function] = []
    for image in images:
        seeds = set(image.seeds)
        if image.kind == "main-exe":
            seeds.update(main_seeds)
        for address in sorted(seeds):
            if not image.contains(address):
                continue
            try:
                function = decode_function(
                    image,
                    address,
                    boundary=bound_for_seed(image, address, seeds),
                )
            except ValueError:
                continue
            if len(function.instructions) >= 2:
                functions.append(function)
    return functions


def source_functions_at(
    images: Sequence[MemoryImage],
    main_seeds: Sequence[int],
    address: int,
) -> list[Function]:
    functions: list[Function] = []
    for image in images:
        if not image.contains(address):
            continue
        seeds = set(image.seeds)
        if image.kind == "main-exe":
            seeds.update(main_seeds)
        seeds.add(address)
        try:
            functions.append(
                decode_function(
                    image,
                    address,
                    boundary=bound_for_seed(image, address, seeds),
                )
            )
        except ValueError:
            continue
    return functions


def counter_cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    dot = sum(left[key] * right[key] for key in left.keys() & right.keys())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def rate_profile(function: Function) -> dict[str, float]:
    count = max(1, len(function.instructions))
    return {
        "calls": function.calls / count,
        "branches": function.branches / count,
        "loads": function.loads / count,
        "stores": function.stores / count,
        "returns": function.returns / count,
        "gte": sum(function.gte_ops.values()) / count,
    }


def profile_similarity(left: Function, right: Function) -> float:
    left_profile = rate_profile(left)
    right_profile = rate_profile(right)
    difference = sum(
        abs(left_profile[key] - right_profile[key]) for key in left_profile
    )
    return max(0.0, 1.0 - difference / 2.0)


def score_pair(source: Function, target: Function) -> RankedCandidate:
    token_ratio = SequenceMatcher(
        None, source.tokens, target.tokens, autojunk=False
    ).ratio()
    opcode_ratio = SequenceMatcher(
        None, source.mnemonics, target.mnemonics, autojunk=False
    ).ratio()
    gte_ratio = counter_cosine(source.gte_ops, target.gte_ops)
    length_ratio = min(len(source.instructions), len(target.instructions)) / max(
        len(source.instructions), len(target.instructions)
    )
    profile_ratio = profile_similarity(source, target)
    score = (
        0.45 * token_ratio
        + 0.25 * opcode_ratio
        + 0.10 * gte_ratio
        + 0.10 * length_ratio
        + 0.10 * profile_ratio
    )
    if (
        min(len(source.instructions), len(target.instructions)) < 6
        and token_ratio < 0.99
    ):
        score *= 0.85
    return RankedCandidate(
        function=target,
        score=score,
        token_ratio=token_ratio,
        opcode_ratio=opcode_ratio,
        gte_ratio=gte_ratio,
        length_ratio=length_ratio,
        profile_ratio=profile_ratio,
    )


def choose_candidates(
    source: Function, targets: Sequence[Function], top: int
) -> list[RankedCandidate]:
    ranked = [score_pair(source, target) for target in targets]
    ranked.sort(
        key=lambda item: (
            -item.score,
            item.function.address,
            item.function.image.label,
        )
    )
    return ranked[:top]


def format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{name}:{count}" for name, count in counter.most_common())


def path_for_report(path: Path, cwd: Path) -> str:
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return str(path)


def build_report(
    *,
    source_exe: PsxExe,
    target_exe: PsxExe,
    source_functions: Sequence[Function],
    target_functions: Sequence[Function],
    landmarks: Sequence[tuple[int, str]],
    top: int,
    source_overlays: Sequence[Path],
    target_overlays: Sequence[Path],
    cwd: Path,
) -> tuple[str, dict]:
    lines = [
        "# Engine Equivalence Candidates",
        "",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}.",
        "",
        "> Discovery aid only. Similarity does not prove function equivalence.",
        "> Every mapping still requires disassembly review, overlay identity,",
        "> a calling-contract check, and a live gameplay trace before registration.",
        "",
        "## Inputs",
        "",
        "| Side | Main executable | SHA-256 | Entry | Load | Text size |",
        "| --- | --- | --- | --- | --- | --- |",
        (
            f"| Source | `{path_for_report(source_exe.path, cwd)}` | "
            f"`{source_exe.file_sha256}` | `0x{source_exe.entry_pc:08X}` | "
            f"`0x{source_exe.load_addr:08X}` | `0x{source_exe.text_size:X}` |"
        ),
        (
            f"| Target | `{path_for_report(target_exe.path, cwd)}` | "
            f"`{target_exe.file_sha256}` | `0x{target_exe.entry_pc:08X}` | "
            f"`0x{target_exe.load_addr:08X}` | `0x{target_exe.text_size:X}` |"
        ),
        "",
    ]
    for side, paths in (
        ("source", source_overlays),
        ("target", target_overlays),
    ):
        if paths:
            formatted = ", ".join(f"`{path_for_report(path, cwd)}`" for path in paths)
            lines.append(f"{side.title()} overlay captures: {formatted}  ")
    lines.extend(
        [
            "",
            "Overlay captures are separate code generations. A target address is",
            "meaningful only together with the capture identity shown below.",
            "",
            "## Landmarks",
            "",
        ]
    )

    result: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notice": "Candidates only; no mapping is confirmed.",
        "source": {
            "path": str(source_exe.path),
            "sha256": source_exe.file_sha256,
            "entry": f"0x{source_exe.entry_pc:08X}",
            "load_addr": f"0x{source_exe.load_addr:08X}",
            "text_size": f"0x{source_exe.text_size:X}",
            "overlays": [str(path) for path in source_overlays],
        },
        "target": {
            "path": str(target_exe.path),
            "sha256": target_exe.file_sha256,
            "entry": f"0x{target_exe.entry_pc:08X}",
            "load_addr": f"0x{target_exe.load_addr:08X}",
            "text_size": f"0x{target_exe.text_size:X}",
            "overlays": [str(path) for path in target_overlays],
        },
        "landmarks": [],
    }

    for address, role in landmarks:
        matches = [f for f in source_functions if f.address == address]
        lines.extend([f"### `0x{address:08X}` - {role}", ""])
        landmark_record = {
            "source_address": f"0x{address:08X}",
            "role": role,
            "source_functions": [],
            "candidates": [],
        }
        if not matches:
            lines.extend(
                [
                    "Source region unavailable from the supplied EXE/seeds/captures.",
                    "Capture the active reference overlay before matching this landmark.",
                    "",
                ]
            )
            result["landmarks"].append(landmark_record)
            continue

        for source_function in matches:
            source_record = {
                "image": source_function.image.label,
                "identity": source_function.image.identity,
                "instructions": len(source_function.instructions),
                "gte": dict(source_function.gte_ops),
                "calls": source_function.calls,
                "branches": source_function.branches,
                "loads": source_function.loads,
                "stores": source_function.stores,
                "returns": source_function.returns,
            }
            landmark_record["source_functions"].append(source_record)
            lines.extend(
                [
                    (
                        f"Source: `{source_function.image.label}`; "
                        f"{len(source_function.instructions)} instructions; "
                        f"GTE {format_counter(source_function.gte_ops)}; "
                        f"calls {source_function.calls}; "
                        f"branches {source_function.branches}."
                    ),
                    "",
                    "| Rank | Target address | Region | Score | Insns | GTE | Calls | Classification |",
                    "| ---: | --- | --- | ---: | ---: | --- | ---: | --- |",
                ]
            )
            candidates = choose_candidates(source_function, target_functions, top)
            for rank, candidate in enumerate(candidates, start=1):
                function = candidate.function
                lines.append(
                    f"| {rank} | `0x{function.address:08X}` | "
                    f"{function.image.label} | {candidate.score:.3f} | "
                    f"{len(function.instructions)} | "
                    f"{format_counter(function.gte_ops)} | "
                    f"{function.calls} | {candidate.label} |"
                )
                landmark_record["candidates"].append(
                    {
                        "source_image": source_function.image.label,
                        "target_address": f"0x{function.address:08X}",
                        "target_image": function.image.label,
                        "target_identity": function.image.identity,
                        "score": round(candidate.score, 6),
                        "token_ratio": round(candidate.token_ratio, 6),
                        "opcode_ratio": round(candidate.opcode_ratio, 6),
                        "gte_ratio": round(candidate.gte_ratio, 6),
                        "length_ratio": round(candidate.length_ratio, 6),
                        "profile_ratio": round(candidate.profile_ratio, 6),
                        "instructions": len(function.instructions),
                        "gte": dict(function.gte_ops),
                        "calls": function.calls,
                        "branches": function.branches,
                        "loads": function.loads,
                        "stores": function.stores,
                        "returns": function.returns,
                        "classification": candidate.label,
                    }
                )
            lines.append("")
        result["landmarks"].append(landmark_record)

    lines.extend(
        [
            "## Review checklist",
            "",
            "- Disassemble the source and candidate, not just the matching prefix.",
            "- Confirm arguments, return value, delay-slot behavior, and fatal stores.",
            "- Record the exact active overlay bytes and caller for both sides.",
            "- Add a fail-closed game/overlay/caller guard.",
            "- Prove live invocation and state restoration before enabling stereo.",
            "",
        ]
    )
    return "\n".join(lines), result


def parse_landmark_arguments(values: Sequence[str] | None) -> list[tuple[int, str]]:
    if not values:
        return list(DEFAULT_LANDMARKS)
    landmarks: list[tuple[int, str]] = []
    for value in values:
        address_text, separator, role = value.partition("=")
        if not separator or not role.strip():
            raise ValueError(f"landmark must be ADDRESS=ROLE, got {value!r}")
        landmarks.append((int(address_text, 0), role.strip()))
    return landmarks


def parse_disassembly_request(value: str) -> tuple[str, int]:
    side, separator, address_text = value.partition(":")
    if not separator or side not in {"source", "target"}:
        raise ValueError("--disasm must be source:ADDRESS or target:ADDRESS")
    return side, int(address_text, 0)


def print_disassembly(
    side: str,
    address: int,
    images: Sequence[MemoryImage],
    main_seeds: Sequence[int],
) -> None:
    functions = source_functions_at(images, main_seeds, address)
    if not functions:
        raise SystemExit(f"{side} address 0x{address:08X} is unavailable")
    for function in functions:
        print(f"\n{function.image.label} ({function.image.identity})")
        for instruction in function.instructions:
            print(
                f"0x{instruction.address:08X}  {instruction.word:08X}  "
                f"{instruction.mnemonic:<10} {instruction.token}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe", type=Path, required=True)
    parser.add_argument("--source-seeds", type=Path, required=True)
    parser.add_argument(
        "--source-overlays",
        type=Path,
        action="append",
        default=[],
        help="Reference overlay_captures.json; may be repeated",
    )
    parser.add_argument("--target-exe", type=Path, required=True)
    parser.add_argument("--target-seeds", type=Path, required=True)
    parser.add_argument(
        "--target-overlays",
        type=Path,
        action="append",
        default=[],
        help="Underground overlay_captures.json; may be repeated",
    )
    parser.add_argument(
        "--landmark",
        action="append",
        default=[],
        metavar="ADDRESS=ROLE",
        help="Override built-in landmarks; may be repeated",
    )
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument(
        "--disasm",
        metavar="SIDE:ADDRESS",
        help="Print one source/target function instead of ranking candidates",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error("--top must be at least 1")

    source_exe = parse_psx_exe(args.source_exe)
    target_exe = parse_psx_exe(args.target_exe)
    source_main = image_from_exe(source_exe, "source main EXE")
    target_main = image_from_exe(target_exe, "target main EXE")
    source_seeds = parse_seed_file(args.source_seeds)
    target_seeds = parse_seed_file(args.target_seeds)
    source_images = [source_main]
    target_images = [target_main]
    for path in args.source_overlays:
        source_images.extend(load_overlay_captures(path, "source"))
    for path in args.target_overlays:
        target_images.extend(load_overlay_captures(path, "target"))

    if args.disasm:
        side, address = parse_disassembly_request(args.disasm)
        if side == "source":
            print_disassembly(side, address, source_images, source_seeds)
        else:
            print_disassembly(side, address, target_images, target_seeds)
        return 0

    landmarks = parse_landmark_arguments(args.landmark)
    source_inventory = inventory_functions(source_images, source_seeds)
    target_inventory = inventory_functions(target_images, target_seeds)
    source_keys = {
        (function.image.identity, function.address) for function in source_inventory
    }
    for address, _role in landmarks:
        for function in source_functions_at(source_images, source_seeds, address):
            key = (function.image.identity, function.address)
            if key not in source_keys:
                source_inventory.append(function)
                source_keys.add(key)
    if not source_inventory:
        raise SystemExit("no source functions decoded")
    if not target_inventory:
        raise SystemExit("no target functions decoded")

    report, json_report = build_report(
        source_exe=source_exe,
        target_exe=target_exe,
        source_functions=source_inventory,
        target_functions=target_inventory,
        landmarks=landmarks,
        top=args.top,
        source_overlays=args.source_overlays,
        target_overlays=args.target_overlays,
        cwd=Path.cwd(),
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8", newline="\n")
        print(f"Wrote {args.output}")
    else:
        print(report)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(json_report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
