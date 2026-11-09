"""Rootless LXC setup and shell entry for cubelinux Runtime."""

from __future__ import annotations

import ipaddress
import os
import pwd
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Sequence

from . import slirp_network

CONTAINER_NAME = "vshell"
FEDORA_CONTAINER_NAME = "fedora-runtime"
CONTAINER_NAMES = (CONTAINER_NAME, FEDORA_CONTAINER_NAME)
GUEST_ID = 50000
ID_COUNT = 65536
CONTAINER_RUNTIME_DIR = "/mnt/vshell-host-runtime"
CONTAINER_X11_DIR = "/mnt/vshell-host-x11"
CONTAINER_X11_TMPFILES = "/etc/tmpfiles.d/cubelinux-vshell-x11.conf"
BUNDLED_RUNTIME_OCI_IMAGE = "oci:/usr/lib/cubelinux-vshell/runtime-oci:main"
SHUTDOWN_HOOK = """#!/bin/sh
# Stop the cubelinux Runtime container before the Plasma user manager exits.
/usr/bin/cubelinux-vshell stop >/dev/null 2>&1 || true
/usr/bin/cubelinux-vshell stop --container fedora-runtime >/dev/null 2>&1 || true
"""
_PREVIOUS_SHUTDOWN_HOOK = """#!/bin/sh
# Stop the CubeLinux Runtime container before the Plasma user manager exits.
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


def _container_name(container_name: str = CONTAINER_NAME) -> str:
    if container_name not in CONTAINER_NAMES:
        raise VShellError("Unknown Linux environment.")
    return container_name


def _config_path(container_name: str = CONTAINER_NAME) -> Path:
    return _lxc_path() / _container_name(container_name) / "config"


def _rootfs_path(container_name: str = CONTAINER_NAME) -> Path:
    return _lxc_path() / _container_name(container_name) / "rootfs"


def install_shutdown_hook() -> None:
    """Install a Plasma logout script that gracefully stops the container."""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    hook = config_home / "plasma-workspace" / "shutdown" / "cubelinux-vshell-stop"
    try:
        if hook.exists():
            existing = hook.read_text(encoding="utf-8") if hook.is_file() else ""
            if existing == SHUTDOWN_HOOK:
                hook.chmod(0o755)
                return
            if existing != _PREVIOUS_SHUTDOWN_HOOK:
                return
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(SHUTDOWN_HOOK, encoding="utf-8")
        hook.chmod(0o755)
    except OSError as error:
        raise VShellError(
            f"Could not install the Runtime shutdown hook at {hook}: {error}"
        ) from error


def is_initialized(container_name: str = CONTAINER_NAME) -> bool:
    container_name = _container_name(container_name)
    config = _config_path(container_name)
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
        raise VShellError("Your account name contains characters VShell cannot use in Runtime.")
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


def _container_running(progress: Progress, container_name: str = CONTAINER_NAME) -> bool:
    container_name = _container_name(container_name)
    result = subprocess.run(
        [
            "lxc-info",
            "--name",
            container_name,
            "--lxcpath",
            str(_lxc_path()),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode == 0 and "RUNNING" in result.stdout


def _wait_until_running(progress: Progress, container_name: str = CONTAINER_NAME) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if _container_running(progress, container_name):
            return
        time.sleep(1)
    raise VShellError("Runtime did not finish starting. Check the LXC log and try setup again.")


def _wait_for_network(progress: Progress, container_name: str = CONTAINER_NAME) -> None:
    _report(progress, "Connecting Runtime to the network…")
    deadline = time.monotonic() + 30
    reported_ips = ""
    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "lxc-info",
                "--name",
                _container_name(container_name),
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
        "Runtime did not receive the slirp4netns network configuration within 30 seconds. "
        "Check that the container network namespace is available and slirp4netns is running."
        + detail
    )


def _ensure_slirp_network(progress: Progress, container_name: str = CONTAINER_NAME) -> None:
    container_name = _container_name(container_name)
    try:
        result = subprocess.run(
            ["lxc-info", "--name", container_name, "--lxcpath", str(_lxc_path()), "--pid"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VShellError(f"Could not inspect the running Runtime container: {error}") from error
    match = re.search(r"PID:\s*(\d+)", result.stdout) if result.returncode == 0 else None
    if not match:
        raise VShellError("LXC did not report the running Runtime container process ID.")
    try:
        slirp_network.ensure_running(int(match.group(1)), container_name)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise VShellError(f"Could not connect Runtime to the network: {error}") from error


def _stop_slirp_network(container_name: str = CONTAINER_NAME) -> None:
    try:
        slirp_network.stop(_container_name(container_name))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise VShellError(f"Could not stop Runtime's user-mode network: {error}") from error


def _ensure_slirp_config(container_name: str = CONTAINER_NAME) -> bool:
    """Migrate existing VShell containers from the host bridge to slirp4netns."""
    config = _config_path(container_name)
    if not config.is_file():
        return False
    contents = config.read_text(encoding="utf-8")
    lines = contents.splitlines()
    network_lines = [line for line in lines if line.startswith("lxc.net.")]
    if network_lines == ["lxc.net.0.type = empty"]:
        return False
    updated = [line for line in lines if not line.startswith("lxc.net.")]
    updated.insert(1 if updated and updated[0].startswith("lxc.include") else 0, "lxc.net.0.type = empty")
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


def _ensure_host_desktop_mounts(
    account: pwd.struct_passwd, container_name: str = CONTAINER_NAME
) -> bool:
    """Expose the signed-in user's display and audio sockets to Runtime."""
    config = _config_path(container_name)
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


def _attach(
    *arguments: str,
    progress: Progress | None = None,
    container_name: str = CONTAINER_NAME,
) -> str:
    container_name = _container_name(container_name)
    command = [
        "lxc-attach",
        "--name",
        container_name,
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
            raise VShellError(completed.stdout.strip()[-4000:] or "Could not configure the Runtime container.")
        return completed.stdout
    return _run(command, progress, stream=True)


def _ensure_guest_x11_socket_path(
    progress: Progress | None = None, container_name: str = CONTAINER_NAME
) -> None:
    """Restore the X11 path after the Runtime guest mounts tmpfs on /tmp."""
    if not Path("/tmp/.X11-unix").is_dir():
        return
    _attach(
        "/usr/bin/systemd-tmpfiles", "--create", CONTAINER_X11_TMPFILES,
        progress=progress, container_name=container_name,
    )


def _stop_container(progress: Progress, container_name: str = CONTAINER_NAME) -> None:
    container_name = _container_name(container_name)
    if _container_running(progress, container_name):
        _run(
            _rootless_scope(
                [
                    "lxc-stop",
                    "--name",
                    container_name,
                    "--lxcpath",
                    str(_lxc_path()),
                    "--timeout",
                    "25",
                ]
            ),
            progress,
            stream=True,
        )
    _stop_slirp_network(container_name)


def _start_container(progress: Progress, container_name: str = CONTAINER_NAME) -> None:
    container_name = _container_name(container_name)
    _ensure_slirp_config(container_name)
    _run(
        _rootless_scope(
            [
                "lxc-start",
                "--name",
                container_name,
                "--lxcpath",
                str(_lxc_path()),
                "--daemon",
            ]
        ),
        progress,
        stream=True,
    )
    _wait_until_running(progress, container_name)
    _ensure_slirp_network(progress, container_name)


def enter(container_name: str = CONTAINER_NAME) -> int:
    """Start the persistent container and attach the mapped Runtime user."""
    container_name = _container_name(container_name)
    if not is_initialized(container_name):
        if container_name != CONTAINER_NAME:
            raise VShellError("The Fedora environment has not been created yet.")
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
    network_config_changed = _ensure_slirp_config(container_name)
    mounts_changed = _ensure_host_desktop_mounts(account, container_name)
    if (mounts_changed or network_config_changed) and _container_running(print, container_name):
        print("Restarting Runtime to apply its network and desktop settings...")
        _stop_container(print, container_name)
    if not _container_running(print, container_name):
        _start_container(print, container_name)
    else:
        _ensure_slirp_network(print, container_name)
    _ensure_guest_x11_socket_path(container_name=container_name)

    term = os.environ.get("TERM", "xterm-256color")
    command = [
        "lxc-attach",
        "--name",
        container_name,
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


def stop(container_name: str = CONTAINER_NAME) -> None:
    container_name = _container_name(container_name)
    if not is_initialized(container_name):
        raise VShellError("Virtual Shell is not set up yet.")
    _stop_container(print, container_name)


def status(container_name: str = CONTAINER_NAME) -> str:
    container_name = _container_name(container_name)
    if not is_initialized(container_name):
        return "not-set-up"
    return "running" if _container_running(print, container_name) else "stopped"
