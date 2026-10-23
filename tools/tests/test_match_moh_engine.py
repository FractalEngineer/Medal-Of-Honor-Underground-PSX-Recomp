from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import match_moh_engine as engine  # noqa: E402


class DecodeTests(unittest.TestCase):
    def test_decodes_common_mips_i_instructions(self) -> None:
        self.assertEqual(
            engine.decode_instruction(0x00000000, 0x80010000).mnemonic,
            "nop",
        )
        self.assertEqual(
            engine.decode_instruction(0x03E00008, 0x80010000).kind,
            "return",
        )
        jal = engine.decode_instruction(0x0C001234, 0x80010000)
        self.assertEqual(jal.mnemonic, "jal")
        self.assertEqual(jal.kind, "call")
        self.assertEqual(jal.branch_target, 0x800048D0)

    def test_decodes_gte_projection_ops(self) -> None:
        rtps = engine.decode_instruction(0x4A180001, 0x80010000)
        rtpt = engine.decode_instruction(0x4A180030, 0x80010004)
        self.assertEqual(rtps.gte_op, "RTPS")
        self.assertEqual(rtpt.gte_op, "RTPT")
        self.assertEqual(rtps.kind, "gte")

    def test_decodes_memory_offset(self) -> None:
        instruction = engine.decode_instruction(0x8C280098, 0x80010000)
        self.assertEqual(instruction.mnemonic, "lw")
        self.assertEqual(instruction.kind, "load")
        self.assertEqual(instruction.token, "lw:r8:r1:152")


class ImageTests(unittest.TestCase):
    def test_parse_psx_exe_header(self) -> None:
        header = bytearray(engine.PSX_EXE_HEADER)
        header[:8] = engine.PSX_EXE_MAGIC
        header[0x10:0x14] = (0x8001F844).to_bytes(4, "little")
        header[0x18:0x1C] = (0x80010000).to_bytes(4, "little")
        header[0x1C:0x20] = (16).to_bytes(4, "little")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "game.exe"
            path.write_bytes(header + (0).to_bytes(16, "little"))
            exe = engine.parse_psx_exe(path)
        self.assertEqual(exe.entry_pc, 0x8001F844)
        self.assertEqual(exe.load_addr, 0x80010000)
        self.assertEqual(exe.text_size, 16)
        self.assertEqual(len(exe.data), 16)

    def test_function_stops_after_return_delay_slot(self) -> None:
        words = [
            0x27BDFFE0,  # addiu sp, sp, -32
            0xAFBF001C,  # sw ra, 28(sp)
            0x03E00008,  # jr ra
            0x27BD0020,  # addiu sp, sp, 32
            0x00000000,  # outside function
        ]
        image = engine.MemoryImage(
            label="fixture",
            path=Path("fixture.bin"),
            load_addr=0x80010000,
            data=b"".join(word.to_bytes(4, "little") for word in words),
            kind="main-exe",
            identity="fixture",
            sha256="fixture",
        )
        function = engine.decode_function(image, 0x80010000)
        self.assertEqual(len(function.instructions), 4)
        self.assertEqual(function.returns, 1)
        self.assertEqual(function.stores, 1)
        self.assertEqual(function.loads, 0)

    def test_identical_functions_rank_highest(self) -> None:
        words = [
            0x27BDFFE0,
            0xAFBF001C,
            0x03E00008,
            0x27BD0020,
        ]
        image = engine.MemoryImage(
            label="fixture",
            path=Path("fixture.bin"),
            load_addr=0x80010000,
            data=b"".join(word.to_bytes(4, "little") for word in words),
            kind="main-exe",
            identity="fixture",
            sha256="fixture",
        )
        source = engine.decode_function(image, 0x80010000)
        score = engine.score_pair(source, source)
        self.assertGreater(score.score, 0.99)

    def test_overlay_capture_keeps_identity_and_seeds(self) -> None:
        data = bytes.fromhex("03e0000800000000")
        capture = {
            "load_addr": "0x80090000",
            "size": len(data),
            "bytes_b64": base64.b64encode(data).decode("ascii"),
            "seeds": ["0x80090000"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "overlay_captures.json"
            path.write_text(json.dumps([capture]), encoding="utf-8")
            images = engine.load_overlay_captures(path, "fixture")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].load_addr, 0x80090000)
        self.assertEqual(images[0].seeds, (0x80090000,))
        self.assertTrue(images[0].identity.startswith("overlay-"))


if __name__ == "__main__":
    unittest.main()
