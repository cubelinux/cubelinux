"""Manage VShell's per-user slirp4netns process and API socket."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


_UNIT = "cubelinux-vshell-slirp4netns.service"
_TAP = "tap0"


def _runtime_dir() -> Path:
    value = os.environ.get("XDG_RUNTIME_DIR")
    if not value:
        raise RuntimeError("The desktop session runtime directory is unavailable.")
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise RuntimeError("The desktop session runtime directory is unavailable.")
    if path.stat().st_uid != os.getuid():
        raise RuntimeError("The desktop session runtime directory has the wrong owner.")
    return path


def api_socket_path() -> Path:
    return _runtime_dir() / "cubelinux-vshell-slirp4netns.sock"


def _pid_path() -> Path:
    return _runtime_dir() / "cubelinux-vshell-slirp4netns.pid"


@contextmanager
def _network_lock() -> Iterator[None]:
    path = _runtime_dir() / "cubelinux-vshell-slirp4netns.lock"
    with path.open("a", encoding="ascii") as lock:
        path.chmod(0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _unit_active() -> bool:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", _UNIT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _stop_unit() -> None:
    stopped = subprocess.run(
        ["systemctl", "--user", "stop", _UNIT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=20,
    )
    if stopped.returncode and _unit_active():
        raise RuntimeError(stopped.stdout.strip() or "systemd could not stop slirp4netns.")
    subprocess.run(
        ["systemctl", "--user", "reset-failed", _UNIT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    for path in (api_socket_path(), _pid_path()):
        path.unlink(missing_ok=True)


def api_request(request: dict[str, Any], *, timeout: float = 2.0) -> dict[str, Any]:
    """Send one JSON request to slirp4netns' local control socket."""
    payload = json.dumps(request, separators=(",", ":")).encode("utf-8")
    response = bytearray()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(api_socket_path()))
        connection.sendall(payload)
        connection.shutdown(socket.SHUT_WR)
        while True:
            chunk = connection.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
            if len(response) > 65536:
                raise RuntimeError("The slirp4netns API returned an oversized response.")
    try:
        decoded = json.loads(response)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("The slirp4netns API returned an invalid response.") from error
    if not isinstance(decoded, dict):
        raise RuntimeError("The slirp4netns API returned an invalid response.")
    if "error" in decoded:
        detail = decoded["error"]
        if isinstance(detail, dict):
            detail = detail.get("desc") or detail.get("class") or detail
        raise RuntimeError(f"slirp4netns rejected a port-forwarding request: {detail}")
    return decoded


def _ready() -> bool:
    if not _unit_active() or not api_socket_path().exists():
        return False
    try:
        result = api_request({"execute": "list_hostfwd"}, timeout=1.0)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return False
    response = result.get("return")
    return isinstance(response, dict) and isinstance(response.get("entries"), list)


def ensure_running(container_pid: int) -> bool:
    """Start or reuse slirp4netns for the running LXC network namespace."""
    with _network_lock():
        return _ensure_running_locked(container_pid)


def _ensure_running_locked(container_pid: int) -> bool:
    if container_pid <= 1:
        raise RuntimeError("LXC did not provide a valid container process ID.")
    _runtime_dir()
    pid_path = _pid_path()
    try:
        active_pid = int(pid_path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        active_pid = -1
    if active_pid == container_pid and _ready():
        return False

    if _unit_active():
        _stop_unit()
    else:
        api_socket_path().unlink(missing_ok=True)
        pid_path.unlink(missing_ok=True)

    executable = shutil.which("slirp4netns")
    if not executable:
        raise RuntimeError("slirp4netns is missing. Install the current Linux Subsystem image and reboot.")
    command = [
        "systemd-run",
        "--user",
        f"--unit={_UNIT}",
        "--collect",
        "--property=Delegate=yes",
        "--property=KillMode=control-group",
        "--",
        executable,
        "--configure",
        "--disable-host-loopback",
        f"--api-socket={api_socket_path()}",
        str(container_pid),
        _TAP,
    ]
    subprocess.run(
        ["systemctl", "--user", "reset-failed", _UNIT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    started = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=20,
    )
    if started.returncode:
        detail = started.stdout.strip() or f"systemd-run exited with status {started.returncode}."
        raise RuntimeError(f"Could not start slirp4netns: {detail}")

    temporary = pid_path.with_suffix(".pid.tmp")
    temporary.write_text(f"{container_pid}\n", encoding="ascii")
    temporary.chmod(0o600)
    temporary.replace(pid_path)

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if _ready():
            return True
        time.sleep(0.1)
    try:
        journal = subprocess.run(
            ["journalctl", "--user", "-u", _UNIT, "-n", "20", "--no-pager"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        journal = ""
    _stop_unit()
    detail = journal[-2000:] if journal else "The API socket did not become ready."
    raise RuntimeError(f"slirp4netns did not become ready: {detail}")


def stop() -> None:
    """Stop the VShell slirp4netns unit and remove its runtime state."""
    with _network_lock():
        _stop_locked()


def _stop_locked() -> None:
    _stop_unit()

