# cubelinux Recovery

This directory contains the factory reset wizard, reset helpers, KDE Settings
module and recovery update service. These components are integrated with the
installer but have not yet been validated end to end on a virtual machine.

The installer creates the recovery partition on a fresh installation. Existing
installations without it must be reinstalled to get recovery. The Reset System
page reports when recovery is unavailable.

The recovery update timer checks the booted bootc image, downloads the same
image by digest, and stages a verified bundle in the inactive recovery slot.
The active slot is kept until the new slot is ready. This needs network access
for the update and temporary system-disk space of at least three times the
current compressed recovery image plus 10 GiB. Factory reset itself uses the
local bundle and does not need network access.
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

