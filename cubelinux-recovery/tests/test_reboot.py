import importlib.machinery
import importlib.util
import hashlib
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PATH = pathlib.Path(__file__).parents[1] / "reboot-to-recovery"
loader = importlib.machinery.SourceFileLoader("recovery_reboot", str(PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

EFI_ID = "01234567-1234-5678-9abc-0123456789ab"
ENTRIES = ("BootNext: 0001\nBootOrder: 0001,0002\n"
           f"Boot0002* cubelinux recovery HD(1,GPT,{EFI_ID},0x800,0x1000)/File(\\EFI\\cubelinux-recovery\\recovery.efi)\n")


class RecoveryRebootTest(unittest.TestCase):
    def run_helper(self, entries=ENTRIES, fail_reboot=False, secure_state=0):
        calls = []

        def fake_run(*args):
            calls.append(args)
            if args[0].endswith("findmnt"):
                return "/dev/test1"
            if args[0].endswith("blkid"):
                return EFI_ID
            if args == ("/usr/sbin/efibootmgr", "-v"):
                return entries
            if args[0].endswith("systemctl") and fail_reboot:
                raise subprocess.CalledProcessError(1, args)
            return ""

        with patch.object(module.os, "geteuid", return_value=0, create=True), \
             patch.object(module.os.path, "isfile", return_value=True), \
             patch.object(module.Path, "is_file", return_value=True), \
             patch.object(module.Path, "read_bytes", return_value=b"\x07\x00\x00\x00" + bytes([secure_state])), \
             patch.object(module, "boot_layout", return_value=(EFI_ID, EFI_ID)), \
             patch.object(module, "recovery_partition_present", return_value=True), \
             patch.object(module.sys, "argv", ["reboot-to-recovery"]), \
             patch.object(module, "run", side_effect=fake_run):
            try:
                module.main()
            except (ValueError, subprocess.CalledProcessError):
                pass
        return calls

    def test_sets_one_time_boot_then_reboots(self):
        calls = self.run_helper()
        self.assertIn(("/usr/sbin/efibootmgr", "--bootnext", "0002"), calls)
        self.assertEqual(calls[-1], ("/usr/bin/systemctl", "reboot"))

    def test_ambiguous_entries_do_not_reboot(self):
        calls = self.run_helper(ENTRIES + ENTRIES.splitlines()[-1] + "\n")
        self.assertFalse(any("--bootnext" in call for call in calls))
        self.assertFalse(any(call[0].endswith("systemctl") for call in calls))

    def test_failed_reboot_restores_previous_bootnext(self):
        calls = self.run_helper(fail_reboot=True)
        self.assertEqual(calls[-1], ("/usr/sbin/efibootmgr", "--bootnext", "0001"))

    def test_secure_boot_does_not_select_unsigned_recovery(self):
        calls = self.run_helper(secure_state=1)
        self.assertFalse(any("--bootnext" in call for call in calls))
        self.assertFalse(any(call[0].endswith("systemctl") for call in calls))

    def test_status_reports_missing_recovery_without_reboot(self):
        with tempfile.TemporaryDirectory() as directory:
            status = pathlib.Path(directory) / "status"
            with patch.object(module.os, "geteuid", return_value=0, create=True), \
                 patch.object(module.sys, "argv", ["reboot-to-recovery", "--status"]), \
                 patch.object(module, "Path", return_value=status), \
                 patch.object(module, "recovery_entry", side_effect=ValueError("Recovery is not installed.")):
                self.assertEqual(module.main(), 0)
            self.assertEqual(status.read_text(), "unavailable\nRecovery is not installed.\n")

    def test_partition_status_rejects_wrong_root(self):
        with tempfile.TemporaryDirectory() as directory:
            mount = pathlib.Path(directory)
            slot = mount / "slots/A"
            (slot / "LiveOS").mkdir(parents=True)
            (slot / "boot").mkdir()
            (mount / "active.cfg").write_text("set recovery_slot=A\n")
            (slot / "CUBELINUX_LAYOUT").write_text(
                f"format=1\nroot_partuuid=wrong\nefi_partuuid={EFI_ID}\n"
                f"recovery_partuuid={EFI_ID}\ndisk_ptuuid={EFI_ID}\n")
            for name in ("LiveOS/squashfs.img", "boot/vmlinuz", "boot/initrd.img", "SHA256SUMS"):
                (slot / name).write_text("content")

            class Mounted:
                def __enter__(self): return directory
                def __exit__(self, *args): return False

            def fake_run(*args):
                if args[0].endswith("findmnt"): return "/dev/root"
                if args[0].endswith("blkid"): return "ext4" if "TYPE" in args else EFI_ID
                return ""

            completed = subprocess.CompletedProcess([], 0, stdout="/dev/recovery\n", stderr="")
            with patch.object(module, "run", side_effect=fake_run), \
                 patch.object(module, "parent_device", side_effect=lambda device, kind: "/dev/root-part" if kind == "part" else "/dev/disk"), \
                 patch.object(module.tempfile, "TemporaryDirectory", return_value=Mounted()), \
                 patch.object(module.subprocess, "run", return_value=completed):
                self.assertFalse(module.recovery_partition_present(EFI_ID, EFI_ID, EFI_ID))

    def test_encrypted_root_is_reported_unavailable(self):
        def fake_run(*args):
            if args[0].endswith("findmnt"): return "/dev/root"
            if "TYPE" in args: return "crypto_LUKS"
            return EFI_ID

        with patch.object(module, "run", side_effect=fake_run), \
             patch.object(module, "parent_device", side_effect=lambda device, kind: "/dev/part" if kind == "part" else "/dev/disk"):
            with self.assertRaisesRegex(ValueError, "encrypted"):
                module.recovery_partition_present(EFI_ID, EFI_ID, EFI_ID)

    def test_bootloader_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            boot = pathlib.Path(directory)
            binary = boot / "recovery.efi"
            binary.write_bytes(b"original")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            (boot / "boot-layout").write_text(
                f"recovery_partuuid={EFI_ID}\nrecovery_fs_uuid={EFI_ID}\n"
                f"efi_partuuid={EFI_ID}\nboot_sha256={digest}\n")
            with patch.object(module, "Path", return_value=boot):
                self.assertEqual(module.boot_layout(EFI_ID), (EFI_ID, EFI_ID))
                binary.write_bytes(b"corrupt")
                with self.assertRaisesRegex(ValueError, "damaged"):
                    module.boot_layout(EFI_ID)


if __name__ == "__main__":
    unittest.main()
