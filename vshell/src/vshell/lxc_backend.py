"""Rootless Fedora LXC setup and shell entry for VShell."""

from __future__ import annotations

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
    return [
        systemd_run,
        "--user",
        "--scope",
        "--quiet",
        "--property=Delegate=yes",
        "--",
        *command,
    ]


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


def _host_setup(progress: Progress) -> None:
    helper = "/usr/libexec/vshell-host-setup"
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
    deadline = time.monotonic() + 60
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
        if result.returncode == 0 and result.stdout.strip():
            return
        time.sleep(1)
    raise VShellError("Fedora could not connect to the LXC network. Check the host network and retry.")


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


def initialize(progress: Progress = print) -> None:
    """Prepare the host and create a rootless Fedora shell with home shared."""
    if is_initialized():
        _report(progress, "Fedora Virtual Shell is already set up.")
        return
    account = _account()
    lxc_create = shutil.which("lxc-create")
    if not lxc_create:
        raise VShellError("LXC is not installed. Update to the current Vireak OS image and reboot.")

    _host_setup(progress)
    uid_range, gid_range = _id_ranges(account)
    root = _lxc_path()
    config_path = _config_path()
    root.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        _report(progress, "Downloading the Fedora environment…")
        with tempfile.TemporaryDirectory(prefix="vshell-") as temporary:
            create_config = Path(temporary) / "lxc.conf"
            _write_create_config(create_config, account, uid_range, gid_range)
            command = _rootless_scope(
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
                    "--",
                    "--dist",
                    "fedora",
                    "--release",
                    FEDORA_RELEASE,
                    "--arch",
                    _arch(),
                ]
            )
            _run(command, progress, stream=True)

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

    # Restart once so LXC applies the bind mount before the user opens a shell.
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


def enter() -> int:
    """Start the persistent container and attach the mapped Fedora user."""
    if not is_initialized():
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            executable = shutil.which("vshell") or "/usr/bin/vshell"
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
    if not _container_running(print):
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
            print,
            stream=True,
        )
        _wait_until_running(print)

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
        "--",
        "/bin/bash",
        "--login",
        "-c",
        'cd "$HOME"; exec /bin/bash -i',
    ]
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
                ]
            ),
            print,
            stream=True,
        )


def status() -> str:
    if not is_initialized():
        return "not-set-up"
    return "running" if _container_running(print) else "stopped"
