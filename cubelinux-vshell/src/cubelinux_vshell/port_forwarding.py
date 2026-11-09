"""Discover Fedora TCP listeners and publish them through slirp4netns."""

from __future__ import annotations

import ipaddress
import json
import os
import subprocess
import time
from pathlib import Path

from . import slirp_network
from .lxc_backend import (
    CONTAINER_NAME, CONTAINER_NAMES, VShellError, _container_running,
    _ensure_slirp_network, _lxc_path,
)

_MIN_AUTOMATIC_PORT = 1024
# systemd-resolved uses this for LLMNR in a base Fedora system. It is not an
# application service to expose on the host.
_NON_APPLICATION_PORTS = {5355}
_STATE_MAX_AGE = 15
_SLIRP_GUEST_IPV4 = "10.0.2.100"


def _data_dir() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return data_home / "vshell"


def _settings_path(container_name: str = CONTAINER_NAME) -> Path:
    suffix = "" if container_name == CONTAINER_NAME else f"-{container_name}"
    return _data_dir() / f"port-forwarding{suffix}.json"


def _state_path(container_name: str = CONTAINER_NAME) -> Path | None:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        return None
    path = Path(runtime_dir)
    suffix = "" if container_name == CONTAINER_NAME else f"-{container_name}"
    return path / f"cubelinux-vshell-port-forwarding{suffix}.json" if path.is_dir() else None


def _read_public_ports(container_name: str = CONTAINER_NAME) -> set[int]:
    path = _settings_path(container_name)
    if not path.exists():
        return set()
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VShellError(f"Could not read port-forwarding settings: {error}") from error
    if not isinstance(values, list):
        raise VShellError("Port-forwarding settings have an invalid format.")
    ports: set[int] = set()
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or not _MIN_AUTOMATIC_PORT <= value <= 65535:
            raise VShellError("Port-forwarding settings contain an invalid port.")
        ports.add(value)
    return ports


def _write_public_ports(ports: set[int], container_name: str = CONTAINER_NAME) -> None:
    path = _settings_path(container_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(sorted(ports), indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def set_public_access(port: int, enabled: bool, container_name: str = CONTAINER_NAME) -> None:
    """Save the network exposure choice for one discovered guest port."""
    if isinstance(port, bool) or not isinstance(port, int) or not _MIN_AUTOMATIC_PORT <= port <= 65535:
        raise VShellError("Only automatically forwarded ports (1024 and above) can be exposed.")
    if not isinstance(enabled, bool):
        raise VShellError("The public access setting must be enabled or disabled.")
    if container_name not in CONTAINER_NAMES:
        raise VShellError("Unknown Linux environment.")
    ports = _read_public_ports(container_name)
    if enabled:
        ports.add(port)
    else:
        ports.discard(port)
    try:
        _write_public_ports(ports, container_name)
    except OSError as error:
        raise VShellError(f"Could not save port-forwarding settings: {error}") from error


def clear_port_forwarding_settings(container_name: str = CONTAINER_NAME) -> None:
    """Clear per-port exposure choices when one environment is reset."""
    _settings_path(container_name).unlink(missing_ok=True)


def list_forwarded_ports(container_name: str | None = None) -> list[dict[str, object]]:
    """Read the fresh status snapshot published by the desktop watcher."""
    names = CONTAINER_NAMES if container_name is None else (container_name,)
    result: list[dict[str, object]] = []
    for name in names:
        if name not in CONTAINER_NAMES:
            continue
        result.extend(_list_forwarded_ports(name))
    return result


def _list_forwarded_ports(container_name: str) -> list[dict[str, object]]:
    path = _state_path(container_name)
    if path is None:
        return []
    try:
        if time.time() - path.stat().st_mtime > _STATE_MAX_AGE:
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        ports = data.get("ports", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return []
    if not isinstance(ports, list):
        return []
    try:
        public_ports = _read_public_ports(container_name)
    except VShellError:
        public_ports = set()
    result: list[dict[str, object]] = []
    for item in ports:
        if not isinstance(item, dict):
            continue
        port = item.get("port")
        label = "Runtime" if container_name == CONTAINER_NAME else "Fedora"
        result.append({**item, "container": container_name, "containerLabel": label,
                       "publicAccess": port in public_ports})
    return result


def _write_state(ports: list[dict[str, object]], container_name: str = CONTAINER_NAME) -> None:
    path = _state_path(container_name)
    if path is None:
        return
    try:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps({"updated": int(time.time()), "ports": ports}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.chmod(0o600)
        temporary.replace(path)
    except OSError:
        return


def _listening_tcp_ports(guest_ip: str, container_name: str = CONTAINER_NAME) -> set[int]:
    command = [
        "lxc-attach", "--name", container_name, "--lxcpath", str(_lxc_path()),
        "--clear-env", "--", "/usr/bin/cat", "/proc/net/tcp", "/proc/net/tcp6",
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode:
        return set()
    ports: set[int] = set()
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4 or fields[3] != "0A":
            continue
        try:
            local_address, port_hex = fields[1].rsplit(":", 1)
            port = int(port_hex, 16)
        except (IndexError, ValueError):
            continue
        # Host forwarding can reach wildcard or TAP-interface listeners. A
        # guest-loopback-only listener stays private to the Fedora namespace.
        wildcard = not local_address.strip("0")
        interface_bound = False
        if len(local_address) == 8:
            try:
                decoded = ipaddress.ip_address(bytes.fromhex(local_address)[::-1])
                interface_bound = str(decoded) == guest_ip
            except ValueError:
                pass
        if (
            _MIN_AUTOMATIC_PORT <= port <= 65535
            and port not in _NON_APPLICATION_PORTS
            and (wildcard or interface_bound)
        ):
            ports.add(port)
    return ports


def _host_forwardings(container_name: str = CONTAINER_NAME) -> list[dict[str, object]]:
    result = slirp_network.api_request({"execute": "list_hostfwd"}, container_name=container_name)
    response = result.get("return")
    if not isinstance(response, dict):
        response = result
    entries = response.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("slirp4netns returned an invalid forwarded-port list.")
    return [entry for entry in entries if isinstance(entry, dict) and entry.get("proto") == "tcp"]


def _remove_forwarding(entry: dict[str, object], container_name: str = CONTAINER_NAME) -> None:
    forwarding_id = entry.get("id")
    if isinstance(forwarding_id, bool) or not isinstance(forwarding_id, int):
        raise RuntimeError("slirp4netns returned a forwarded port without a valid ID.")
    slirp_network.api_request(
        {"execute": "remove_hostfwd", "arguments": {"id": forwarding_id}},
        container_name=container_name,
    )


def _add_forwarding(port: int, host_address: str, container_name: str = CONTAINER_NAME) -> None:
    slirp_network.api_request(
        {
            "execute": "add_hostfwd",
            "arguments": {
                "proto": "tcp",
                "host_addr": host_address,
                "host_port": port,
                "guest_addr": _SLIRP_GUEST_IPV4,
                "guest_port": port,
            },
        },
        container_name=container_name,
    )


class PortForwardingMonitor:
    """Synchronize detected guest listeners with slirp4netns host forwards."""

    def __init__(self, container_name: str = CONTAINER_NAME) -> None:
        if container_name not in CONTAINER_NAMES:
            raise VShellError("Unknown Linux environment.")
        self.container_name = container_name
        self.container_label = "Runtime" if container_name == CONTAINER_NAME else "Fedora"
        self._errors: dict[int, str] = {}

    def refresh(self) -> None:
        try:
            running = _container_running(lambda _message: None, self.container_name)
        except (OSError, subprocess.TimeoutExpired, VShellError):
            running = False

        self._errors = {}
        if not running:
            try:
                slirp_network.stop(self.container_name)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                pass
            _write_state([], self.container_name)
            return

        network_error = ""
        try:
            _ensure_slirp_network(lambda _message: None, self.container_name)
        except (OSError, RuntimeError, subprocess.TimeoutExpired, VShellError) as error:
            network_error = f"Could not connect {self.container_label} to its user-mode network: {error}"

        try:
            guest_ports = _listening_tcp_ports(_SLIRP_GUEST_IPV4, self.container_name)
        except (OSError, subprocess.TimeoutExpired) as error:
            self._errors = {-1: f"Could not inspect {self.container_label}'s listening ports: {error}"}
            return
        try:
            public_ports = _read_public_ports(self.container_name)
        except VShellError as error:
            public_ports = set()
            settings_error = str(error)
        else:
            settings_error = ""

        desired = {
            port: "0.0.0.0" if port in public_ports else "127.0.0.1"
            for port in guest_ports
        }

        if network_error:
            self._errors = {port: network_error for port in desired}
            self._publish(desired)
            return

        try:
            entries = _host_forwardings(self.container_name)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            message = str(error)
            self._errors = {port: message for port in desired}
            self._publish(desired)
            return

        retained: dict[int, dict[str, object]] = {}
        for entry in entries:
            port = entry.get("host_port")
            address = entry.get("host_addr", "0.0.0.0")
            if isinstance(port, bool) or not isinstance(port, int):
                try:
                    _remove_forwarding(entry, self.container_name)
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    pass
                continue
            if desired.get(port) != address or port in retained:
                try:
                    _remove_forwarding(entry, self.container_name)
                except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                    self._errors[port] = str(error)
                continue
            retained[port] = entry

        for port, address in desired.items():
            if port in retained:
                continue
            try:
                _add_forwarding(port, address, self.container_name)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                self._errors[port] = str(error)

        if settings_error:
            for port in desired:
                self._errors.setdefault(port, settings_error)

        self._publish(desired)

    def _publish(self, desired: dict[int, str]) -> None:
        rows: list[dict[str, object]] = []
        for port, address in sorted(desired.items()):
            row: dict[str, object] = {
                "port": port,
                "protocol": "TCP",
                "hostAddress": f"localhost:{port}",
                "publicAccess": address == "0.0.0.0",
                "status": "Unavailable" if port in self._errors else "Forwarding",
                "error": self._errors.get(port, ""),
            }
            rows.append(row)
        _write_state(rows, self.container_name)

    def close(self) -> None:
        # slirp4netns owns the forwards and is stopped with the LXC container.
        _write_state([], self.container_name)
