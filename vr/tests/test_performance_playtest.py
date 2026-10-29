import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which('powershell.exe') or shutil.which('pwsh')


@unittest.skipUnless(POWERSHELL, 'PowerShell is required for launcher isolation controls')
class PerformancePlaytestTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root/'analysis/builds/preflight-enhanced'
        self.build.mkdir(parents=True)
        self.fixture = self.root/'analysis/fixtures/sp-cache-view-key/openbios'
        self.fixture.mkdir(parents=True)
        exe = self.build/'Medal_of_Honor_Underground_Recompiled.exe'
        exe.write_bytes(b'tested-build')
        self.manifest = self.build/'Medal_of_Honor_Underground_Recompiled.execution.json'
        self.manifest.write_text(json.dumps(dict(profile='ENHANCED', identity='tested-identity')))
        flags = dict(CMAKE_BUILD_TYPE='Release', PSX_DEBUG_TOOLS='OFF', PSX_OPENXR='ON',
                     PSX_RUNTIME_IPO='OFF', MOHU_VR_NATIVE_PROFILE='OFF',
                     MOHU_VR_PREFLIGHT_HARNESS='OFF', MOHU_VR_PACKET_HARNESS='OFF',
                     MOHU_VR_HOST_PREFLIGHT='ON', MOHU_VR_HOST_PACKET='ON')
        (self.build/'CMakeCache.txt').write_text(''.join(f'{k}:STRING={v}\n' for k,v in flags.items()))
        hashes = {}
        for ext in ('pst', 'thumb'):
            name = f'state_8001F844_slot02.{ext}'
            content = ('native-'+ext).encode()
            (self.fixture/name).write_bytes(content)
            hashes[name] = hashlib.sha256(content).hexdigest()
        evidence = self.root/'vr/proof/render-kernel-checkpoint-receipt.json'
        evidence.parent.mkdir(parents=True)
        evidence.write_text(json.dumps(dict(final_rebuilt_enhanced_control=dict(
            execution_identity='tested-identity', binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
            fixture_sha256=hashes))))
        self.personal = self.root/'saves'
        self.personal.mkdir()
        (self.personal/'card1.mcd').write_bytes(b'personal-progress')
        self.saves = self.root/'analysis/playtest/render-kernels/saves'
        self.script = self.root/'prepare.ps1'
        quote = lambda p: str(p).replace("'", "''")
        self.script.write_text("$ErrorActionPreference='Stop'\n. '"+
            quote(ROOT/'vr/performance_test.ps1')+"'\nInitialize-PerformancePlaytest -RepositoryRoot '"+
            quote(self.root)+"' | ConvertTo-Json\n")

    def prepare(self):
        return subprocess.run([POWERSHELL,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.script)],
                              capture_output=True, text=True)

    def test_repeated_preparation_preserves_playtest_and_personal_progress(self):
        first = self.prepare()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual((self.saves/'card1.mcd').read_bytes(), b'personal-progress')
        (self.saves/'card1.mcd').write_bytes(b'new-playtest-progress')
        state = self.saves/'openbios/state_8001F844_slot02.pst'
        state.write_bytes(b'new-playtest-state')
        second = self.prepare()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual((self.saves/'card1.mcd').read_bytes(), b'new-playtest-progress')
        self.assertEqual(state.read_bytes(), b'new-playtest-state')
        self.assertEqual((self.personal/'card1.mcd').read_bytes(), b'personal-progress')

    def test_identity_mismatch_stops_before_copying_saves(self):
        self.manifest.write_text(json.dumps(dict(profile='ENHANCED',identity='wrong')))
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('differs from its tested artifact', result.stderr)
        self.assertFalse(self.saves.exists())

    def test_existing_unbound_save_directory_is_not_adopted(self):
        self.saves.mkdir(parents=True)
        (self.saves/'card1.mcd').write_bytes(b'unknown-progress')
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no profile binding', result.stderr)
        self.assertEqual((self.saves/'card1.mcd').read_bytes(), b'unknown-progress')
