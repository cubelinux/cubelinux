import hashlib
import json
from contextlib import nullcontext
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import subprocess
import stat
import unittest
from unittest.mock import patch

try:
    import fcntl  # noqa: F401
except ImportError:
    sys.modules["fcntl"] = types.ModuleType("fcntl")

PATH = Path(__file__).parents[1] / "update-recovery"
loader = importlib.machinery.SourceFileLoader("recovery_update", str(PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

GUID = "01234567-1234-5678-9abc-0123456789ab"
LAYOUT = ("format=1\n" + "".join(f"{name}={GUID}\n" for name in
          ("disk_ptuuid", "root_partuuid", "recovery_partuuid", "efi_partuuid")))


class RecoveryUpdateTest(unittest.TestCase):
    def make_slot(self, directory):
        slot = Path(directory)
        for name in module.REQUIRED_FILES:
            path = slot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(LAYOUT if name == "CUBELINUX_LAYOUT" else "content")
        (slot / "SHA256SUMS").write_text("".join(
            f"{hashlib.sha256((slot / name).read_bytes()).hexdigest()}  {name}\n"
            for name in module.REQUIRED_FILES))
        return slot

    def test_verifies_recorded_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            slot = self.make_slot(directory)
            self.assertEqual(module.verify_slot(slot)["root_partuuid"], GUID)

    def test_corrupted_slot_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            slot = self.make_slot(directory)
            (slot / "boot/vmlinuz").write_text("corrupt")
            with self.assertRaises(ValueError):
                module.verify_slot(slot)

    def test_unchecksummed_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            slot = self.make_slot(directory)
            (slot / "CUBELINUX_DIGEST").write_text("sha256:" + "a" * 64)
            with self.assertRaises(ValueError):
                module.verify_slot(slot)

    def test_duplicate_layout_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "layout"
            path.write_text(LAYOUT + f"root_partuuid={GUID}\n")
            with self.assertRaises(ValueError):
                module.parse_layout(path)

    def test_slot_selector_rejects_ambiguous_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "active.cfg").write_text("set recovery_slot=A\nset recovery_slot=B\n")
            with self.assertRaises(ValueError):
                module.active_slot(path)

    def test_image_path_refuses_to_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                module.image_path(Path(directory), "/../outside")

    def test_activation_failure_keeps_previous_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "active.cfg").write_text("set recovery_slot=A\n")
            with patch.object(module.os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    module.activate_slot(path, "B", GUID)
            self.assertEqual(module.active_slot(path), "A")

    def test_activation_switches_to_new_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "active.cfg").write_text("set recovery_slot=A\n")
            # Windows does not support opening a directory for fsync.
            with patch.object(module, "sync_directory"):
                module.activate_slot(path, "B", GUID)
            self.assertEqual(module.active_slot(path), "B")

    def test_stale_owned_scratch_is_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "work"
            scratch.mkdir()
            (scratch / ".cubelinux-recovery-update").write_text(module.SCRATCH_MARKER)
            (scratch / "old-data").write_text("stale")
            # Windows does not expose POSIX root ownership or private modes.
            with patch.object(module, "Path", return_value=scratch), \
                 patch.object(module, "trusted_scratch", return_value=True):
                with module.scratch_directory() as work:
                    self.assertFalse((work / "old-data").exists())
                    self.assertTrue((work / ".cubelinux-recovery-update").exists())
            self.assertFalse(scratch.exists())

    def test_scratch_rejects_untrusted_ownership_and_permissions(self):
        directory = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=0)
        marker = types.SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=0,
                                       st_size=len(module.SCRATCH_MARKER))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            marker_path = path / "marker"
            marker_path.write_text(module.SCRATCH_MARKER)
            with patch.object(Path, "lstat", side_effect=[directory, marker]):
                self.assertTrue(module.trusted_scratch(path, marker_path))
            directory.st_uid = 1000
            with patch.object(Path, "lstat", side_effect=[directory, marker]):
                self.assertFalse(module.trusted_scratch(path, marker_path))
            directory.st_uid = 0
            directory.st_mode = stat.S_IFDIR | 0o777
            with patch.object(Path, "lstat", side_effect=[directory, marker]):
                self.assertFalse(module.trusted_scratch(path, marker_path))
            directory.st_mode = stat.S_IFDIR | 0o700
            marker.st_uid = 1000
            with patch.object(Path, "lstat", side_effect=[directory, marker]):
                self.assertFalse(module.trusted_scratch(path, marker_path))

    def test_unrecognized_scratch_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "work"
            scratch.mkdir()
            data = scratch / "personal-data"
            data.write_text("keep")
            with patch.object(module, "Path", return_value=scratch):
                with self.assertRaises(ValueError):
                    with module.scratch_directory():
                        pass
            self.assertEqual(data.read_text(), "keep")

    def test_booted_image_is_pinned_without_losing_registry_port(self):
        digest = "sha256:" + "a" * 64
        state = {"status": {"booted": {"image": {
            "image": {"transport": "registry", "image": "example.org:5000/team/os:stable"},
            "imageDigest": digest,
        }}}}
        with patch.object(module, "command", return_value=json.dumps(state)):
            reference, actual_digest, pinned = module.booted_image()
        self.assertEqual(reference, "example.org:5000/team/os:stable")
        self.assertEqual(actual_digest, digest)
        self.assertEqual(pinned, "example.org:5000/team/os@" + digest)

    def test_non_registry_image_is_not_fetched(self):
        state = {"status": {"booted": {"image": {
            "image": {"transport": "oci", "image": "/some/image"},
            "imageDigest": "sha256:" + "a" * 64,
        }}}}
        with patch.object(module, "command", return_value=json.dumps(state)):
            with self.assertRaises(ValueError):
                module.booted_image()

    def test_staging_failure_keeps_active_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mount = root / "recovery"
            active = self.make_slot(mount / "slots/A")
            (mount / "slots/B").mkdir()
            (mount / "active.cfg").write_text("set recovery_slot=A\n")
            component = root / "component"
            (component / "runtime").mkdir(parents=True)
            (component / "recovery-ui").write_text("ui")
            for name in ("install-bootc", "cleanup-installed-fstab", "verify-recovery-bundle",
                         "check-recovery-layout", "factory-reset", "install-recovery-boot"):
                (component / "runtime" / name).write_text("helper")
            work = root / "work"
            work.mkdir()

            def fake_command(*args):
                if args[0].endswith("skopeo"):
                    archive_name = args[-1][len("oci-archive:"):].rsplit(":localhost/", 1)[0]
                    Path(archive_name).write_text("payload")
                elif args[0].endswith("unsquashfs"):
                    tree = Path(args[3])
                    (tree / "usr/share/cubelinux").mkdir(parents=True)
                    (tree / "usr/share/cubelinux/payload.oci.tar").write_text("old")
                    (tree / "usr/share/cubelinux/target-image-ref").write_text("old")
                    (tree / "usr/lib/cubelinux-recovery").mkdir(parents=True)
                    (tree / "usr/local/libexec/cubelinux").mkdir(parents=True)
                elif args[0].endswith("mksquashfs"):
                    raise subprocess.CalledProcessError(1, args)
                return ""

            with patch.object(module, "scratch_directory", return_value=nullcontext(work)), \
                 patch.object(module, "command", side_effect=fake_command), \
                 patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=10**12)), \
                 patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
                with self.assertRaises(subprocess.CalledProcessError):
                    module.update(mount, module.parse_layout(active / "CUBELINUX_LAYOUT"), "A",
                                  "registry.example/os:latest", "sha256:" + "a" * 64,
                                  "registry.example/os@sha256:" + "a" * 64, component)
            self.assertEqual(module.active_slot(mount), "A")
            self.assertTrue((active / "LiveOS/squashfs.img").is_file())
            module.verify_slot(active)

    def test_successful_staging_switches_to_verified_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mount = root / "recovery"
            active = self.make_slot(mount / "slots/A")
            (mount / "slots/B").mkdir()
            (mount / "active.cfg").write_text("set recovery_slot=A\n")
            component = root / "component"
            (component / "runtime").mkdir(parents=True)
            (component / "recovery-ui").write_text("ui")
            for name in ("install-bootc", "cleanup-installed-fstab", "verify-recovery-bundle",
                         "check-recovery-layout", "factory-reset", "install-recovery-boot"):
                (component / "runtime" / name).write_text("helper")
            work = root / "work"
            work.mkdir()

            def fake_command(*args):
                if args[0].endswith("skopeo"):
                    archive_name = args[-1][len("oci-archive:"):].rsplit(":localhost/", 1)[0]
                    Path(archive_name).write_text("payload")
                elif args[0].endswith("unsquashfs"):
                    tree = Path(args[3])
                    (tree / "usr/share/cubelinux").mkdir(parents=True)
                    (tree / "usr/share/cubelinux/payload.oci.tar").write_text("old")
                    (tree / "usr/share/cubelinux/target-image-ref").write_text("old")
                    (tree / "usr/lib/cubelinux-recovery").mkdir(parents=True)
                    (tree / "usr/local/libexec/cubelinux").mkdir(parents=True)
                elif args[0].endswith("mksquashfs"):
                    Path(args[2]).write_text("new squashfs")
                return ""

            digest = "sha256:" + "a" * 64
            with patch.object(module, "scratch_directory", return_value=nullcontext(work)), \
                 patch.object(module, "command", side_effect=fake_command), \
                 patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=10**12)), \
                 patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
                 patch.object(module, "sync_directory"):
                module.update(mount, module.parse_layout(active / "CUBELINUX_LAYOUT"), "A",
                              "registry.example/os:latest", digest,
                              "registry.example/os@" + digest, component)
            self.assertEqual(module.active_slot(mount), "B")
            self.assertEqual((mount / "slots/B/CUBELINUX_DIGEST").read_text().strip(), digest)
            module.verify_slot(mount / "slots/B")
            module.verify_slot(active)


if __name__ == "__main__":
    unittest.main()
