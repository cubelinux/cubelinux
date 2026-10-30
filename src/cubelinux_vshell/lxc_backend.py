"""Rootless Fedora LXC setup and shell entry for Virtual Shell."""

from __future__ import annotations

import ipaddress
import os
import platform
import pwd
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Sequence

CONTAINER_NAME = "vshell"
FEDORA_RELEASE = "44"
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


def _rootless_scope(
    command: Sequence[str], *, cache_base: Path | None = None
) -> list[str]:
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
    if cache_base:
        scope.append(f"--setenv=LXC_CACHE_PATH={cache_base}")
    return [*scope, "--", *command]


def _arch() -> str:
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "amd64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    raise VShellError(f"Fedora LXC images are not available for this architecture: {machine}.")


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
        "Fedora did not receive an IPv4 DHCP lease within 30 seconds. "
        "Check that lxc-net and dnsmasq are running and the host firewall allows DHCP on lxcbr0."
        + detail
    )


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
    if marker in lines:
        start = lines.index(marker)
        lines = lines[:start]
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


def _stop_container(progress: Progress) -> None:
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


def _start_container(progress: Progress) -> None:
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

    account = _account()
    root = _lxc_path()
    mounts_changed = _ensure_host_desktop_mounts(account)
    if mounts_changed and _container_running(print):
        print("Refreshing Fedora's host desktop socket mounts...")
        _stop_container(print)
    if not _container_running(print):
        _start_container(print)
    _ensure_guest_x11_socket_path()

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
    if _container_running(print):
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
            print,
            stream=True,
        )


def status() -> str:
    if not is_initialized():
        return "not-set-up"
    return "running" if _container_running(print) else "stopped"
