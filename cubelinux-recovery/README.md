# cubelinux Recovery

This directory contains the Qt factory-reset wizard, reset helpers, KDE
Settings module, and recovery runtime update service. The installer owns the
disk layout and initial recovery provisioning. The complete flow still needs
validation with a built ISO and VM.

## User flow

In KDE System Settings, **Reset System** offers **Factory Reset** and a
**Restart to Factory Reset** action. Restarting only schedules a one-time boot
into recovery; it does not erase data. The recovery wizard asks the user to
confirm before formatting `CUBE_ROOT`, installing the local offline image, and
rebooting into first-boot setup. EFI and recovery partitions are preserved.

The installer creates `CUBE_RECOVERY` during a fresh Erase disk installation.
Existing installations without that partition need to be reinstalled to add
recovery. The Settings page reports recovery as unavailable when it cannot
validate the partition or boot entry.

The recovery filesystem is mounted read-only for recovery boot. The live system
uses a temporary writable overlay for its session; the persistent recovery
partition remains unchanged during reset.

## Recovery updates

The recovery update timer copies the already-deployed UI, QML files, and reset
helpers into the inactive runtime slot on `CUBE_RECOVERY`. It verifies the
manifest and switches the selector only after staging is complete. The static
boot image and offline reset payload provisioned by the ISO are left alone, so
this update needs no network access and little free space. Factory Reset
continues to install the image snapshot stored by that ISO.

The runtime slots contain only the recovery interface and its helpers, not a
copy of the complete operating system. Each update stages the new component in
the inactive slot, verifies it, syncs it to disk, and changes the active
selector last. If staging fails, the old slot remains selected. At boot, the
installer checks the overlay and confirms that the UI loads against the static
recovery environment's libraries; if a check fails, it uses the embedded UI
and helpers instead.

The offline reset payload is a separate snapshot. Updating the recovery UI and
helpers does not change which OS version Factory Reset installs; a newer reset
payload requires a newer installer ISO or a separately designed payload update.
If an update fails, the previous slot stays active and the timer retries later;
the failure can be inspected with `journalctl -u cubelinux-recovery-update.service`.

During factory reset, the full backend output is written to
`/run/cubelinux-factory-reset.log` in the recovery environment. If the reset
fails, the wizard shows the end of that log; the file remains available until
the recovery environment reboots.

Recovery reuses Fedora's signed shim and GRUB from the installed EFI system
partition, along with the Fedora kernel from the recovery bundle. It can boot
with Secure Boot enabled on systems that trust Fedora's shim. The external
initramfs and mutable recovery payload use checksums for damage detection; they
are not a verified-boot security boundary. The installer temporarily hides
root encryption, and reset refuses existing encrypted roots.

