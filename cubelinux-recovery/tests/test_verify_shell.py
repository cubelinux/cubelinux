"""Exercise the actual recovery checksum helper without block devices."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if os.name == "nt" and GIT_BASH.exists() else shutil.which("bash")
FILES = ("LiveOS/squashfs.img", "boot/vmlinuz", "boot/initrd.img", "CUBELINUX_IMAGE_REF", "CUBELINUX_LAYOUT")


@unittest.skipUnless(BASH, "bash is unavailable")
class ShellVerificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.slot = Path(self.temp.name)
        for name in FILES:
            path = self.slot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((name + "\n").encode())
        (self.slot / "SHA256SUMS").write_text("".join(
            f"{hashlib.sha256((self.slot / name).read_bytes()).hexdigest()}  {name}\n"
            for name in FILES), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def verify(self):
        script = ROOT / "runtime/verify-recovery-bundle"
        result = subprocess.run([BASH, script.as_posix(), self.slot.as_posix()],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result

    def test_complete_bundle_passes(self):
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_corrupted_bundle_fails(self):
        (self.slot / "boot/vmlinuz").write_text("corrupted")
        self.assertNotEqual(self.verify().returncode, 0)

    def test_duplicate_manifest_entry_fails(self):
        manifest = self.slot / "SHA256SUMS"
        manifest.write_text(manifest.read_text() + manifest.read_text().splitlines()[0] + "\n")
        self.assertNotEqual(self.verify().returncode, 0)


if __name__ == "__main__":
    unittest.main()
