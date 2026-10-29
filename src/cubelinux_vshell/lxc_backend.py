"""Rootless Fedora LXC setup and shell entry for Virtual Shell."""

from __future__ import annotations

import ipaddress
import os
import platform
import pwd
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Sequence


CONTAINER_NAME = "vshell"
FEDORA_RELEASE = "44"
GUEST_ID = 50000
ID_COUNT = 65536
CONTAINER_RUNTIME_DIR = "/mnt/vshell-host-runtime"
SHUTDOWN_HOOK = """#!/bin/sh
# Stop the CubeLinux Fedora container before the Plasma user manager exits.
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
            f"{CONTAINER_RUNTIME_DIR.lstrip('/')} none bind,create=dir 0 0"
        )

    x11_sockets = Path("/tmp/.X11-unix")
    if x11_sockets.is_dir():
        lines.append(
            "lxc.mount.entry = /tmp/.X11-unix tmp/.X11-unix "
            "none bind,create=dir 0 0"
        )

    return lines if len(lines) > 1 else []


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


def _escape_mount_path(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\040")


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
    _report(progress, "Fedora Virtual Shell is ready.")


def reset_container(progress: Progress = print) -> None:
    """Delete and recreate Fedora, refreshing the cached LXC image first."""
    if not is_initialized():
        raise VShellError("Virtual Shell is not set up yet.")

    root = _lxc_path()
    if _container_running(progress):
        _report(progress, "Stopping Fedora before reset…")
        _stop_container(progress)

    _report(progress, "Deleting the Fedora container and its installed data…")
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
    _report(progress, "Checking for a Fedora template update…")
    initialize(progress, refresh_template=True)


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
