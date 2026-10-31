"""Create, configure, and destroy the persistent Fedora LXC environment."""

from __future__ import annotations

import ipaddress
import os
import pwd
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from .lxc_backend import (
    CONTAINER_NAME, FEDORA_RELEASE, GUEST_ID, ID_COUNT, VShellError,
    _account, _arch, _attach, _container_running, _config_path,
    _ensure_guest_x11_socket_path, _ensure_host_desktop_mounts,
    _escape_mount_path, _home, _lxc_path, _report, _rootless_scope, _run,
    _start_container, _stop_container, _wait_for_network, _wait_until_running,
    is_initialized,
)
from .shared_folders import clear_shared_folders, sync_saved_shared_folders

Progress = Callable[[str], None]


def _find_subid_range(
    path: Path, account: pwd.struct_passwd, identity_id: int
) -> tuple[int, int] | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split(":")
        if len(fields) != 3 or fields[0] not in (account.pw_name, str(account.pw_uid)):
            continue
        try:
            start, count = int(fields[1]), int(fields[2])
        except ValueError:
            continue
        if count >= ID_COUNT and not start <= identity_id < start + count:
            return start, count
    return None


def _id_ranges(account: pwd.struct_passwd) -> tuple[tuple[int, int], tuple[int, int]]:
    uid_range = _find_subid_range(Path("/etc/subuid"), account, account.pw_uid)
    gid_range = _find_subid_range(Path("/etc/subgid"), account, account.pw_gid)
    if not uid_range or not gid_range:
        raise VShellError(
            "Virtual Shell could not find a 65,536-ID range for your account. "
            "Run setup again and approve the one-time LXC permission request."
        )
    return uid_range, gid_range


def _has_network_permission(account: pwd.struct_passwd) -> bool:
    config = Path("/etc/lxc/lxc-usernet")
    if not config.is_file():
        return False
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        fields = line.split()
        if len(fields) != 4 or fields[:3] != [account.pw_name, "veth", "lxcbr0"]:
            continue
        try:
            if int(fields[3]) > 0:
                return True
        except ValueError:
            continue
    return False


def _host_network_ready(account: pwd.struct_passwd) -> bool:
    if not Path("/sys/class/net/lxcbr0").exists() or not _has_network_permission(account):
        return False
    try:
        _id_ranges(account)
    except VShellError:
        return False
    return True


def _host_setup(progress: Progress) -> None:
    helper = "/usr/libexec/cubelinux-vshell-host-setup"
    pkexec = shutil.which("pkexec")
    if not pkexec or not Path(helper).is_file():
        raise VShellError(
            "The LXC host setup helper is missing. Install the current Vireak OS image and try again."
        )
    _report(progress, "Requesting one-time permission to enable rootless LXC networking…")
    _run([pkexec, helper], progress, stream=True)


def _mapping_lines(uid_start: int, gid_start: int, uid: int, gid: int) -> list[str]:
    # Keep 50000 available for VShell's guest user and map it to the host user.
    tail_count = ID_COUNT - GUEST_ID - 1
    lines = [
        f"lxc.idmap = u 0 {uid_start} {GUEST_ID}",
        f"lxc.idmap = u {GUEST_ID} {uid} 1",
        f"lxc.idmap = u {GUEST_ID + 1} {uid_start + GUEST_ID} {tail_count}",
        f"lxc.idmap = g 0 {gid_start} {GUEST_ID}",
        f"lxc.idmap = g {GUEST_ID} {gid} 1",
        f"lxc.idmap = g {GUEST_ID + 1} {gid_start + GUEST_ID} {tail_count}",
    ]
    return lines


def _expire_cached_template() -> Path | None:
    """Make LXC check an existing Fedora cache against its current image index."""
    cache_roots = (Path.home() / ".cache/lxc", Path("/var/cache/lxc"))
    image_path = Path("download") / "fedora" / FEDORA_RELEASE / _arch() / "default"

    for cache_base in cache_roots:
        cache = cache_base / image_path
        build_ids = list(cache.glob("build_id*"))
        if not build_ids:
            continue

        try:
            for build_id in build_ids:
                expiry_name = build_id.name.replace("build_id", "expiry", 1)
                (cache / expiry_name).write_text("0\n", encoding="utf-8")
        except OSError:
            continue
        return cache_base
    return None


def _remove_partial_container(root: Path) -> None:
    """Remove only the incomplete VShell directory left by a failed create."""
    container_path = root / CONTAINER_NAME
    if not container_path.exists():
        if container_path.is_symlink():
            raise VShellError("Refusing to remove an unexpected LXC container path.")
        return
    resolved_root = root.resolve()
    resolved_container = container_path.resolve()
    if resolved_container.parent != resolved_root or resolved_container.name != CONTAINER_NAME:
        raise VShellError("Refusing to remove an unexpected LXC container path.")
    shutil.rmtree(resolved_container)


def _write_create_config(path: Path, account: pwd.struct_passwd, uid_range: tuple[int, int], gid_range: tuple[int, int]) -> None:
    uid_start, _ = uid_range
    gid_start, _ = gid_range
    lines = [
        "lxc.include = /usr/share/lxc/config/common.conf",
        "lxc.net.0.type = veth",
        "lxc.net.0.link = lxcbr0",
        "lxc.net.0.flags = up",
        *_mapping_lines(uid_start, gid_start, account.pw_uid, account.pw_gid),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configure_guest(account: pwd.struct_passwd, progress: Progress) -> None:
    username = account.pw_name
    script = (
        "set -eu; "
        # The Fedora container image may use a systemd-resolved stub address,
        # but systemd-resolved is not running yet in this LXC container. Use
        # the DHCP-provided bridge gateway, where lxc-net's dnsmasq serves DNS.
        # The address can appear before DHCP installs the default route, so
        # allow that route time to arrive before reporting a network failure.
        "gateway=\"\"; "
        "attempt=0; "
        "while [ \"$attempt\" -lt 30 ]; do "
        "gateway=\"$(ip -4 route show default | awk 'NR == 1 {print $3}')\"; "
        "if [ -n \"$gateway\" ]; then break; fi; "
        "attempt=$((attempt + 1)); sleep 1; done; "
        "if [ -z \"$gateway\" ]; then "
        "echo 'Fedora did not receive a network gateway after 30 seconds. Current routes and addresses:' >&2; "
        "ip -4 route show >&2; ip -4 address show >&2; exit 1; fi; "
        "rm -f /etc/resolv.conf; "
        "printf 'nameserver %s\\n' \"$gateway\" > /etc/resolv.conf; "
        "dns_ready=0; "
        "for attempt in 1 2 3 4 5; do "
        "if getent ahostsv4 mirrors.fedoraproject.org >/dev/null; then "
        "dns_ready=1; break; fi; sleep 2; done; "
        "if [ \"$dns_ready\" -ne 1 ]; then "
        "echo \"Could not resolve Fedora package servers through $gateway.\" >&2; exit 1; fi; "
        f"if ! getent group {GUEST_ID} >/dev/null; then "
        f"groupadd --gid {GUEST_ID} {username}; fi; "
        f"if getent passwd {GUEST_ID} >/dev/null; then "
        f"test \"$(getent passwd {GUEST_ID} | cut -d: -f1)\" = {username}; "
        "else "
        f"useradd --uid {GUEST_ID} --gid {GUEST_ID} --create-home "
        f"--home-dir /home/{username} --shell /bin/bash {username}; fi; "
        f"usermod --append --groups wheel {username}; "
        "dnf -y install sudo; "
        "install -d -m 0750 /etc/sudoers.d; "
        "printf '%s\\n' '%wheel ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-vshell; "
        "chmod 0440 /etc/sudoers.d/90-vshell"
    )
    _report(progress, "Preparing your Fedora user and shell…")
    _attach("/usr/bin/bash", "-ceu", script, progress=progress)


def _bind_home(account: pwd.struct_passwd) -> None:
    config = _config_path()
    contents = config.read_text(encoding="utf-8")
    marker = "# VShell home bind"
    if marker in contents:
        return
    mount_line = (
        f"{marker}\n"
        f"lxc.mount.entry = {_escape_mount_path(str(_home()))} "
        f"home/{account.pw_name} none bind,create=dir 0 0\n"
    )
    config.write_text(contents.rstrip() + "\n" + mount_line, encoding="utf-8")


def initialize(progress: Progress = print, *, refresh_template: bool = False) -> None:
    """Prepare the host and create a rootless Fedora shell with home shared."""
    if is_initialized():
        _report(progress, "Fedora Virtual Shell is already set up.")
        return
    account = _account()
    lxc_create = shutil.which("lxc-create")
    if not lxc_create:
        raise VShellError("LXC is not installed. Update to the current Vireak OS image and reboot.")

    if _host_network_ready(account):
        _report(progress, "Host container networking is ready.")
    else:
        _host_setup(progress)
    _report(progress, "Checking your rootless container ID mappings…")
    uid_range, gid_range = _id_ranges(account)
    root = _lxc_path()
    config_path = _config_path()
    root.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        cache_base = _expire_cached_template() if refresh_template else None
        if refresh_template and cache_base:
            _report(progress, "Checking for Fedora template updates…")
        else:
            _report(progress, "Downloading the Fedora environment…")
        with tempfile.TemporaryDirectory(prefix="cubelinux-vshell-") as temporary:
            create_config = Path(temporary) / "lxc.conf"
            _write_create_config(create_config, account, uid_range, gid_range)

            def create_command(*, force_cache: bool = False) -> list[str]:
                template_arguments = [
                    "--",
                    "--dist",
                    "fedora",
                    "--release",
                    FEDORA_RELEASE,
                    "--arch",
                    _arch(),
                ]
                if force_cache:
                    template_arguments.append("--force-cache")
                return _rootless_scope(
                    [
                        lxc_create,
                        "--name",
                        CONTAINER_NAME,
                        "--lxcpath",
                        str(root),
                        "--config",
                        str(create_config),
                        "--template",
                        "download",
                        *template_arguments,
                    ],
                    cache_base=cache_base,
                )

            try:
                _run(create_command(), progress, stream=True)
            except VShellError as update_error:
                if not refresh_template or not cache_base:
                    raise
                _report(progress, "Template update check failed; reusing the cached Fedora image…")
                _remove_partial_container(root)
                try:
                    _run(create_command(force_cache=True), progress, stream=True)
                except VShellError as cache_error:
                    raise VShellError(
                        "Could not refresh Fedora's template, and the cached image could not be reused. "
                        f"Update error: {update_error}; cached image error: {cache_error}"
                    ) from cache_error

    if not _container_running(progress):
        _report(progress, "Starting Fedora for first-time setup…")
        _run(
            _rootless_scope(
                [
                    "lxc-start",
                    "--name",
                    CONTAINER_NAME,
                    "--lxcpath",
                    str(root),
                    "--daemon",
                ]
            ),
            progress,
            stream=True,
        )
        _wait_until_running(progress)

    _wait_for_network(progress)
    _configure_guest(account, progress)
    _report(progress, "Sharing your home folder…")
    _bind_home(account)
    sync_saved_shared_folders()
    _report(progress, "Connecting Fedora to your desktop session...")
    _ensure_host_desktop_mounts(account)

    # Restart so LXC applies the home and desktop socket mounts.
    _report(progress, "Restarting Fedora to apply your shared home folder…")
    _run(
        _rootless_scope(
            [
                "lxc-stop",
                "--name",
                CONTAINER_NAME,
                "--lxcpath",
                str(root),
            ]
        ),
        progress,
        stream=True,
    )
    _run(
        _rootless_scope(
            [
                "lxc-start",
                "--name",
                CONTAINER_NAME,
                "--lxcpath",
                str(root),
                "--daemon",
            ]
        ),
        progress,
        stream=True,
    )
    _wait_until_running(progress)
    _ensure_guest_x11_socket_path(progress)
    _report(progress, "Fedora Virtual Shell is ready.")


def destroy_container(progress: Progress = print) -> None:
    """Stop and delete the Fedora container without recreating it."""
    root = _lxc_path()
    if not is_initialized():
        container_path = root / CONTAINER_NAME
        if not container_path.exists() and not container_path.is_symlink():
            clear_shared_folders()
            _report(progress, "The Fedora environment is already destroyed.")
            return
        if _container_running(progress):
            _report(progress, "Stopping the incomplete Fedora container…")
            _stop_container(progress)
        _report(progress, "Cleaning up the incomplete Fedora container…")
        _remove_partial_container(root)
        clear_shared_folders()
        return

    if _container_running(progress):
        _report(progress, "Stopping Fedora before destruction…")
        _stop_container(progress)

    _report(progress, "Destroying the Fedora container and its installed data…")
    _run(
        _rootless_scope(
            [
                "lxc-destroy",
                "--name",
                CONTAINER_NAME,
                "--lxcpath",
                str(root),
                "--force",
            ]
        ),
        progress,
        stream=True,
    )
    clear_shared_folders()
