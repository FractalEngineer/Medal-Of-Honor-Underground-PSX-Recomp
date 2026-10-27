import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ENTRY_HOOKS = {
    "0x80093830", "0x80013B40", "0x80013EB4", "0x80099960",
    "0x8009D828", "0x80090760", "0x80091854", "0x800913A0",
    "0x80079AF8", "0x80076A50", "0x8008AB84", "0x80078E08",
    "0x80053BB4", "0x8006D65C", "0x80018B48", "0x8004356C",
    "0x80018BB8", "0x8006C61C", "0x8006C8B0", "0x80076C28",
    "0x80054BC4", "0x80096EF4", "0x80053CFC", "0x8006B64C",
}

INSTRUCTION_HOOKS = {
    "0x80084CDC", "0x80084B74", "0x80048AAC", "0x80090954",
    "0x80090A78", "0x8009086C", "0x80096F78", "0x800892E8",
    "0x800894DC", "0x80089D30", "0x80089600",
}


class NativeHookConfigTest(unittest.TestCase):
    def test_game_config_declares_registered_vr_hooks(self) -> None:
        with (ROOT / "game.toml").open("rb") as stream:
            recompiler = tomllib.load(stream)["recompiler"]
        self.assertTrue(recompiler["strict"])
        self.assertEqual(set(recompiler["mod_function_entry_funcs"]), ENTRY_HOOKS)
        self.assertEqual(
            set(recompiler["mod_instruction_sites"]), INSTRUCTION_HOOKS
        )

    def test_static_codegen_emits_main_exe_forwarders(self) -> None:
        generated = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "generated").glob("SLUS_012.70_full_*.c")
        )
        for address in ("80013B40", "80013EB4", "80018B48", "80018BB8"):
            self.assertIn(
                f"psx_mod_function_entry(cpu, 0x{address}u)", generated
            )


if __name__ == "__main__":
    unittest.main()
