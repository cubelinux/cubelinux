"""Rootless Fedora LXC setup and shell entry for Virtual Shell."""

from __future__ import annotations

import ipaddress
import os
import pwd
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Sequence

from . import slirp_network

CONTAINER_NAME = "vshell"
GUEST_ID = 50000
ID_COUNT = 65536
CONTAINER_RUNTIME_DIR = "/mnt/vshell-host-runtime"
CONTAINER_X11_DIR = "/mnt/vshell-host-x11"
CONTAINER_X11_TMPFILES = "/etc/tmpfiles.d/cubelinux-vshell-x11.conf"
SHUTDOWN_HOOK = """#!/bin/sh
# Stop the cubelinux Fedora container before the Plasma user manager exits.
/usr/bin/cubelinux-vshell stop >/dev/null 2>&1 || true
"""
Progress = Callable[[str], None]


class VShellError(RuntimeError):
    """A setup or container operation failed with a user-facing explanation."""


def _home() -> Path:
    return Path.home().resolve()


def _lxc_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return data_home / "vshell" / "containers"


def _config_path() -> Path:
    return _lxc_path() / CONTAINER_NAME / "config"


def _rootfs_path() -> Path:
    return _lxc_path() / CONTAINER_NAME / "rootfs"


def install_shutdown_hook() -> None:
    """Install a Plasma logout script that gracefully stops the container."""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    hook = config_home / "plasma-workspace" / "shutdown" / "cubelinux-vshell-stop"
    try:
        if hook.is_file() and hook.read_text(encoding="utf-8") == SHUTDOWN_HOOK:
            hook.chmod(0o755)
            return
        if hook.exists():
            return
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(SHUTDOWN_HOOK, encoding="utf-8")
        hook.chmod(0o755)
    except OSError as error:
        raise VShellError(
            f"Could not install the Fedora shutdown hook at {hook}: {error}"
        ) from error


def install_runtime_autostart() -> bool:
    """Register a KDE login entry once, leaving Plasma's user choice intact."""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    entry = config_home / "autostart" / "org.cubelinux.VShellRuntime.desktop"
    migration_marker = config_home / "cubelinux-vshell" / "runtime-autostart-migrated"
    if migration_marker.exists():
        return False

    contents = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Virtual Shell Runtime\n"
        "Comment=Start the initialized cubelinux Runtime for this desktop session\n"
        "Exec=/usr/bin/cubelinux-vshell start\n"
        "OnlyShowIn=KDE;\n"
        "X-KDE-autostart-after=panel\n"
        "X-CubeLinux-Managed=true\n"
    )
    try:
        entry.parent.mkdir(parents=True, exist_ok=True)
        created = not entry.exists()
        if created:
            entry.write_text(contents, encoding="utf-8")
            entry.chmod(0o644)
        migration_marker.parent.mkdir(parents=True, exist_ok=True)
        migration_marker.touch(exist_ok=True)
    except OSError as error:
        raise VShellError(f"Could not configure runtime autostart: {error}") from error
    return created


def remove_runtime_autostart() -> None:
    """Remove the managed login entry when the runtime is destroyed."""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    entry = config_home / "autostart" / "org.cubelinux.VShellRuntime.desktop"
    migration_marker = config_home / "cubelinux-vshell" / "runtime-autostart-migrated"
    try:
        if entry.is_file():
            contents = entry.read_text(encoding="utf-8")
            if "X-CubeLinux-Managed=true" in contents:
                entry.unlink()
        migration_marker.unlink(missing_ok=True)
    except OSError as error:
        raise VShellError(f"Could not remove runtime autostart: {error}") from error


def is_initialized() -> bool:
    config = _config_path()
    if not config.is_file() or not (config.parent / "rootfs").is_dir():
        return False
    try:
        contents = config.read_text(encoding="utf-8")
    except OSError:
        return False
    return "# VShell home bind" in contents


def _account() -> pwd.struct_passwd:
    account = pwd.getpwuid(os.getuid())
    if account.pw_uid == 0:
        raise VShellError("Run Virtual Shell from your normal desktop account, not as root.")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]*", account.pw_name):
        raise VShellError("Your account name contains characters VShell cannot use in Fedora.")
    home = _home()
    if not home.is_dir():
        raise VShellError("Your home folder could not be found.")
    if any(character.isspace() for character in str(home)):
        raise VShellError("Your home folder path contains spaces, which LXC cannot bind safely yet.")
    return account


def _report(progress: Progress, message: str) -> None:
    progress(message)


def _run(
    command: Sequence[str],
    progress: Progress,
    *,
    stream: bool = False,
    cwd: Path | None = None,
) -> str:
    if stream:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
        )
        output_lines: list[str] = []
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line:
                output_lines.append(line)
                _report(progress, line)
        result = process.wait()
        output = "\n".join(output_lines)
    else:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            check=False,
        )
        result = completed.returncode
        output = completed.stdout.strip()

    if result:
        detail = output or f"Command exited with status {result}."
        raise VShellError(detail[-4000:])
    return output


def _rootless_scope(command: Sequence[str]) -> list[str]:
    systemd_run = shutil.which("systemd-run")
    if not systemd_run:
        raise VShellError("systemd-run is required to start an unprivileged LXC container.")
    scope = [
        systemd_run,
        "--user",
        "--scope",
        "--quiet",
        "--property=Delegate=yes",
    ]
    return [*scope, "--", *command]


def _container_running(progress: Progress) -> bool:
    result = subprocess.run(
        [
            "lxc-info",
            "--name",
            CONTAINER_NAME,
            "--lxcpath",
            str(_lxc_path()),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode == 0 and "RUNNING" in result.stdout


def _wait_until_running(progress: Progress) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if _container_running(progress):
            return
        time.sleep(1)
    raise VShellError("Fedora did not finish starting. Check the LXC log and try setup again.")


def _wait_for_network(progress: Progress) -> None:
    _report(progress, "Connecting Fedora to the network…")
    deadline = time.monotonic() + 30
    reported_ips = ""
    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "lxc-info",
                "--name",
                CONTAINER_NAME,
                "--lxcpath",
                str(_lxc_path()),
                "--ips",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        reported_ips = result.stdout.strip()
        if result.returncode == 0:
            for value in reported_ips.split():
                try:
                    address = ipaddress.ip_address(value)
                except ValueError:
                    continue
                if isinstance(address, ipaddress.IPv4Address) and not (
                    address.is_loopback or address.is_unspecified
                ):
                    return
        time.sleep(1)
    if reported_ips:
        detail = f" LXC only reported: {reported_ips}."
    else:
        detail = " LXC reported no IP addresses."
    raise VShellError(
        "Fedora did not receive the slirp4netns network configuration within 30 seconds. "
        "Check that the container network namespace is available and slirp4netns is running."
        + detail
    )


def _ensure_slirp_network(progress: Progress) -> None:
    try:
        result = subprocess.run(
            ["lxc-info", "--name", CONTAINER_NAME, "--lxcpath", str(_lxc_path()), "--pid"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VShellError(f"Could not inspect the running Fedora container: {error}") from error
    match = re.search(r"PID:\s*(\d+)", result.stdout) if result.returncode == 0 else None
    if not match:
        raise VShellError("LXC did not report the running Fedora container process ID.")
    try:
        network_started = slirp_network.ensure_running(int(match.group(1)))
        if network_started:
            _attach(
                "/usr/bin/bash",
                "-ceu",
                "rm -f /etc/resolv.conf; printf 'nameserver 10.0.2.3\\n' > /etc/resolv.conf",
                progress=progress,
            )
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise VShellError(f"Could not connect Fedora to the network: {error}") from error


def _stop_slirp_network() -> None:
    try:
        slirp_network.stop()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise VShellError(f"Could not stop Fedora's user-mode network: {error}") from error


def _ensure_slirp_config() -> bool:
    """Migrate VShell containers to slirp4netns and Flatpak-compatible proc mounts."""
    config = _config_path()
    if not config.is_file():
        return False
    contents = config.read_text(encoding="utf-8")
    lines = contents.splitlines()
    changed = False
    network_lines = [line for line in lines if line.startswith("lxc.net.")]
    updated = lines
    if network_lines != ["lxc.net.0.type = empty"]:
        updated = [line for line in updated if not line.startswith("lxc.net.")]
        updated.insert(
            1 if updated and updated[0].startswith("lxc.include") else 0,
            "lxc.net.0.type = empty",
        )
        changed = True

    # An earlier workaround changed proc:mixed to proc:rw, but it did not let
    # Bubblewrap mount procfs and relaxed the guest's /proc/sys restrictions.
    # Restore the mixed mode; the separate clean procfs below fixes the mount.
    for index, line in enumerate(updated):
        key, separator, value = line.partition("=")
        if not separator or key.strip() != "lxc.mount.auto":
            continue
        mounts = value.split()
        if "proc:rw" in mounts:
            restored_mounts = (
                "proc:mixed" if item == "proc:rw" else item for item in mounts
            )
            updated[index] = f"{key.rstrip()} = {' '.join(restored_mounts)}"
            changed = True

    legacy_proc_target = "var/lib/cubelinux-vshell/proc"
    without_legacy_proc: list[str] = []
    for line in updated:
        fields = line.split()
        if (
            len(fields) >= 5
            and fields[:2] == ["lxc.mount.entry", "="]
            and fields[2] == "proc"
            and fields[3] == legacy_proc_target
            and fields[4] == "proc"
        ):
            changed = True
            continue
        without_legacy_proc.append(line)
    if without_legacy_proc != updated:
        updated = without_legacy_proc

    # A second, unmasked procfs lets Bubblewrap create its own procfs after
    # systemd masks selected paths on /proc (for example, boot_id).
    nested_proc_marker = "# VShell Flatpak nested proc mount"
    nested_proc_entry = (
        "lxc.mount.entry = proc proc2 proc "
        "nosuid,nodev,noexec,relatime,create=dir 0 0"
    )
    nested_proc_marker_index = next(
        (index for index, line in enumerate(updated) if line == nested_proc_marker),
        None,
    )
    has_managed_nested_proc = (
        nested_proc_marker_index is not None
        and nested_proc_marker_index + 1 < len(updated)
        and updated[nested_proc_marker_index + 1].strip() == nested_proc_entry
    )
    if not has_managed_nested_proc:
        before_nested_proc = updated.copy()
        if nested_proc_marker_index is not None:
            del updated[nested_proc_marker_index]
            if (
                nested_proc_marker_index < len(updated)
                and updated[nested_proc_marker_index].strip() == nested_proc_entry
            ):
                del updated[nested_proc_marker_index]
        has_proc2_mount = any(
            len(fields := line.split()) >= 4
            and fields[:2] == ["lxc.mount.entry", "="]
            and fields[3] == "proc2"
            for line in updated
        )
        if not has_proc2_mount:
            updated.extend([nested_proc_marker, nested_proc_entry])
        if updated != before_nested_proc:
            changed = True

    if updated != lines:
        changed = True

    if not changed:
        return False
    temporary = config.with_name(f".{config.name}.tmp")
    temporary.write_text("\n".join(updated) + "\n", encoding="utf-8")
    temporary.chmod(config.stat().st_mode & 0o777)
    temporary.replace(config)
    return True


def _host_runtime_dir(account: pwd.struct_passwd) -> Path | None:
    value = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{account.pw_uid}")
    runtime_dir = Path(value)
    if not runtime_dir.is_absolute() or not runtime_dir.is_dir():
        return None
    try:
        if runtime_dir.stat().st_uid != account.pw_uid:
            return None
    except OSError:
        return None
    return runtime_dir


def _container_runtime_value(value: str, host_runtime_dir: Path) -> str:
    """Rewrite host runtime socket paths to their bind-mounted guest location."""
    host_path = str(host_runtime_dir).rstrip("/")
    return re.sub(
        rf"(?<![A-Za-z0-9_./-]){re.escape(host_path)}(?=/|$)",
        CONTAINER_RUNTIME_DIR,
        value,
    )


def _host_desktop_mount_lines(account: pwd.struct_passwd) -> list[str]:
    lines = ["# VShell host desktop sockets"]
    runtime_dir = _host_runtime_dir(account)
    if runtime_dir:
        lines.append(
            f"lxc.mount.entry = {_escape_mount_path(str(runtime_dir))} "
            f"{CONTAINER_RUNTIME_DIR.lstrip('/')} none rbind,create=dir,rslave 0 0"
        )

    x11_sockets = Path("/tmp/.X11-unix")
    if x11_sockets.is_dir():
        lines.append(
            f"lxc.mount.entry = /tmp/.X11-unix {CONTAINER_X11_DIR.lstrip('/')} "
            "none bind,create=dir 0 0"
        )

    return lines if len(lines) > 1 else []


def _escape_mount_path(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\040")


def _ensure_host_desktop_mounts(account: pwd.struct_passwd) -> bool:
    """Expose the signed-in user's display and audio sockets to Fedora."""
    config = _config_path()
    contents = config.read_text(encoding="utf-8")
    section = _host_desktop_mount_lines(account)
    marker = "# VShell host desktop sockets"
    if not section:
        # Preserve existing mounts when called from a non-graphical shell.
        return False

    lines = contents.rstrip().splitlines()
    host_mount_targets = {
        CONTAINER_RUNTIME_DIR.lstrip("/"),
        CONTAINER_X11_DIR.lstrip("/"),
    }
    preserved_lines: list[str] = []
    for line in lines:
        if line == marker:
            continue
        fields = line.split()
        if (
            len(fields) >= 4
            and fields[0:2] == ["lxc.mount.entry", "="]
            and fields[3] in host_mount_targets
        ):
            continue
        preserved_lines.append(line)
    lines = preserved_lines
    updated = "\n".join([*lines, *section]) + "\n"
    if updated == contents:
        return False
    config.write_text(updated, encoding="utf-8")
    return True


def _attach(*arguments: str, progress: Progress | None = None) -> str:
    command = [
        "lxc-attach",
        "--name",
        CONTAINER_NAME,
        "--lxcpath",
        str(_lxc_path()),
        "--clear-env",
        "--set-var",
        "HOME=/root",
        "--set-var",
        "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
        "--",
        *arguments,
    ]
    if progress is None:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            check=False,
        )
        if completed.returncode:
            raise VShellError(completed.stdout.strip()[-4000:] or "Could not configure the Fedora container.")
        return completed.stdout
    return _run(command, progress, stream=True)


def _ensure_guest_x11_socket_path(progress: Progress | None = None) -> None:
    """Restore the X11 path after the Fedora LXC guest mounts tmpfs on /tmp."""
    if not Path("/tmp/.X11-unix").is_dir():
        return
    script = (
        "set -eu; "
        f"if [ -d {CONTAINER_X11_DIR} ]; then "
        "install -d -m 0755 /etc/tmpfiles.d; "
        f"printf '%s\\n' 'L+ /tmp/.X11-unix - - - - {CONTAINER_X11_DIR}' "
        f"> {CONTAINER_X11_TMPFILES}; "
        f"if [ ! -L /tmp/.X11-unix ] || "
        f"[ \"$(readlink /tmp/.X11-unix)\" != {CONTAINER_X11_DIR} ]; then "
        f"systemd-tmpfiles --create {CONTAINER_X11_TMPFILES}; "
        "fi; fi"
    )
    _attach("/usr/bin/bash", "-ceu", script, progress=progress)


def _ensure_guest_host_runtime_path(
    account: pwd.struct_passwd, progress: Progress | None = None
) -> None:
    """Expose host runtime paths at the absolute paths returned over D-Bus."""
    runtime_dir = _host_runtime_dir(account)
    if runtime_dir is None:
        return

    source = CONTAINER_RUNTIME_DIR
    old_helper_target = runtime_dir / ".flatpak-helper"
    runtime_dir_arg = shlex.quote(str(runtime_dir))
    source_arg = shlex.quote(source)
    old_helper_target_arg = shlex.quote(str(old_helper_target))
    script = (
        "set -eu; "
        f"target={runtime_dir_arg}; "
        f"source={source_arg}; "
        "if [ -L \"$target\" ]; then "
        "if [ \"$(readlink \"$target\")\" = \"$source\" ]; then exit 0; fi; "
        "echo 'VShell found an unexpected host runtime path in the guest.' >&2; "
        "exit 1; "
        "fi; "
        "if [ -d \"$target\" ]; then "
        f"if [ -L {old_helper_target_arg} ] "
        f"&& [ \"$(readlink {old_helper_target_arg})\" = \"$source/.flatpak-helper\" ] "
        f"&& [ -z \"$(find \"$target\" -mindepth 1 -maxdepth 1 "
        "! -name .flatpak-helper -print -quit)\" ]; then "
        f"rm {old_helper_target_arg}; "
        "rmdir \"$target\"; "
        "elif [ -z \"$(find \"$target\" -mindepth 1 -maxdepth 1 -print -quit)\" ]; then "
        "rmdir \"$target\"; "
        "else "
        "echo 'VShell cannot map the host runtime because its guest path is already occupied.' >&2; "
        "exit 1; "
        "fi; "
        "elif [ -e \"$target\" ]; then "
        "echo 'VShell cannot map the host runtime because its guest path is already occupied.' >&2; "
        "exit 1; "
        "fi; "
        "install -d -m 0755 \"$(dirname \"$target\")\"; "
        "ln -s \"$source\" \"$target\""
    )
    _attach("/usr/bin/bash", "-ceu", script, progress=progress)


def _stop_container(progress: Progress) -> None:
    if _container_running(progress):
        _run(
            _rootless_scope(
                [
                    "lxc-stop",
                    "--name",
                    CONTAINER_NAME,
                    "--lxcpath",
                    str(_lxc_path()),
                    "--timeout",
                    "25",
                ]
            ),
            progress,
            stream=True,
        )
    _stop_slirp_network()


def _start_container(progress: Progress) -> None:
    _ensure_slirp_config()
    _run(
        _rootless_scope(
            [
                "lxc-start",
                "--name",
                CONTAINER_NAME,
                "--lxcpath",
                str(_lxc_path()),
                "--daemon",
            ]
        ),
        progress,
        stream=True,
    )
    _wait_until_running(progress)
    _ensure_slirp_network(progress)
    _ensure_flathub_remote(progress)


def start_runtime(progress: Progress = print) -> bool:
    """Start the initialized runtime for the current desktop session."""
    if not is_initialized():
        return False

    account = _account()
    network_config_changed = _ensure_slirp_config()
    mounts_changed = _ensure_host_desktop_mounts(account)
    running = _container_running(progress)
    if (mounts_changed or network_config_changed) and running:
        _report(progress, "Restarting the cubelinux Runtime to apply session settings...")
        _stop_container(progress)
        running = False
    if not running:
        _start_container(progress)
    else:
        _ensure_slirp_network(progress)
    _ensure_guest_host_runtime_path(account, progress)
    _ensure_guest_x11_socket_path(progress)
    return True


def _ensure_flathub_remote(progress: Progress = print) -> bool:
    """Ensure Flathub exists in the mapped guest user's Flatpak configuration."""
    if not is_initialized():
        return False

    account = _account()
    command = [
        "lxc-attach",
        "--name",
        CONTAINER_NAME,
        "--lxcpath",
        str(_lxc_path()),
        "--clear-env",
        "--uid",
        str(GUEST_ID),
        "--gid",
        str(GUEST_ID),
        "--set-var",
        f"HOME=/home/{account.pw_name}",
        "--set-var",
        f"USER={account.pw_name}",
        "--set-var",
        f"LOGNAME={account.pw_name}",
        "--set-var",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "--",
        "/usr/bin/flatpak",
        "remote-add",
        "--user",
        "--if-not-exists",
        "flathub",
        "https://dl.flathub.org/repo/flathub.flatpakrepo",
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        _report(progress, f"Could not configure the user Flathub remote; VShell will retry: {error}")
        return False

    if result.returncode:
        detail = result.stdout.strip()[-1500:]
        _report(
            progress,
            "Could not configure the user Flathub remote; VShell will retry"
            + (f": {detail}" if detail else "."),
        )
        return False
    return True



def enter() -> int:
    """Start the persistent container and attach the mapped Fedora user."""
    if not is_initialized():
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            executable = shutil.which("cubelinux-vshell") or "/usr/bin/cubelinux-vshell"
            subprocess.Popen(
                [executable],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return 0
        raise VShellError("Virtual Shell is not set up yet. Open it from the application menu first.")

    start_runtime()
    account = _account()
    root = _lxc_path()

    term = os.environ.get("TERM", "xterm-256color")
    command = [
        "lxc-attach",
        "--name",
        CONTAINER_NAME,
        "--lxcpath",
        str(root),
        "--clear-env",
        "--uid",
        str(GUEST_ID),
        "--gid",
        str(GUEST_ID),
        "--set-var",
        f"HOME=/home/{account.pw_name}",
        "--set-var",
        f"USER={account.pw_name}",
        "--set-var",
        f"LOGNAME={account.pw_name}",
        "--set-var",
        f"TERM={term}",
    ]
    runtime_dir = _host_runtime_dir(account)
    if runtime_dir:
        command.extend(["--set-var", f"XDG_RUNTIME_DIR={CONTAINER_RUNTIME_DIR}"])
    for name in (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "DBUS_SESSION_BUS_ADDRESS",
        "PULSE_SERVER",
        "PIPEWIRE_REMOTE",
        "XDG_SESSION_TYPE",
        "XDG_CURRENT_DESKTOP",
        "QT_QPA_PLATFORM",
    ):
        value = os.environ.get(name)
        if value:
            if runtime_dir:
                value = _container_runtime_value(value, runtime_dir)
            command.extend(["--set-var", f"{name}={value}"])
    command.extend(
        [
            "--",
            "/bin/bash",
            "--login",
            "-c",
            'cd "$HOME"; exec /bin/bash -i',
        ]
    )
    return subprocess.run(command, check=False).returncode


def stop() -> None:
    if not is_initialized():
        raise VShellError("Virtual Shell is not set up yet.")
    _stop_container(print)


def status() -> str:
    if not is_initialized():
        return "not-set-up"
    return "running" if _container_running(print) else "stopped"
