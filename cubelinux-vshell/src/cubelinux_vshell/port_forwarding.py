"""Discover Fedora TCP listeners and proxy selected ports on the host."""

from __future__ import annotations

import ipaddress
import json
import os
import select
import socket
import socketserver
import subprocess
import threading
import time
from pathlib import Path

from .lxc_backend import CONTAINER_NAME, VShellError, _container_running, _lxc_path

_MIN_AUTOMATIC_PORT = 1024
_STATE_MAX_AGE = 15


def _data_dir() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return data_home / "vshell"


def _settings_path() -> Path:
    return _data_dir() / "port-forwarding.json"


def _state_path() -> Path | None:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime_dir:
        return None
    path = Path(runtime_dir)
    return path / "cubelinux-vshell-port-forwarding.json" if path.is_dir() else None


def _read_public_ports() -> set[int]:
    path = _settings_path()
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


def _write_public_ports(ports: set[int]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(sorted(ports), indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def set_public_access(port: int, enabled: bool) -> None:
    """Save the network exposure choice for one discovered guest port."""
    if isinstance(port, bool) or not isinstance(port, int) or not _MIN_AUTOMATIC_PORT <= port <= 65535:
        raise VShellError("Only automatically forwarded ports (1024 and above) can be exposed.")
    if not isinstance(enabled, bool):
        raise VShellError("The public access setting must be enabled or disabled.")
    ports = _read_public_ports()
    if enabled:
        ports.add(port)
    else:
        ports.discard(port)
    try:
        _write_public_ports(ports)
    except OSError as error:
        raise VShellError(f"Could not save port-forwarding settings: {error}") from error


def clear_port_forwarding_settings() -> None:
    """Clear per-port exposure choices when the Fedora environment is destroyed."""
    _settings_path().unlink(missing_ok=True)


def list_forwarded_ports() -> list[dict[str, object]]:
    """Read the fresh status snapshot published by the desktop watcher."""
    path = _state_path()
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
        public_ports = _read_public_ports()
    except VShellError:
        public_ports = set()
    result: list[dict[str, object]] = []
    for item in ports:
        if not isinstance(item, dict):
            continue
        port = item.get("port")
        result.append({**item, "publicAccess": port in public_ports})
    return result


def _write_state(ports: list[dict[str, object]]) -> None:
    path = _state_path()
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


def _container_ipv4() -> str | None:
    result = subprocess.run(
        ["lxc-info", "--name", CONTAINER_NAME, "--lxcpath", str(_lxc_path()), "--ips"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode:
        return None
    for value in result.stdout.split():
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv4Address) and not (address.is_loopback or address.is_unspecified):
            return str(address)
    return None


def _listening_tcp_ports(guest_ip: str) -> set[int]:
    command = [
        "lxc-attach", "--name", CONTAINER_NAME, "--lxcpath", str(_lxc_path()),
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
        # Host-side forwarding can reach wildcard or container-interface
        # listeners. A guest-loopback-only listener is isolated from this proxy.
        wildcard = not local_address.strip("0")
        interface_bound = False
        if len(local_address) == 8:
            try:
                decoded = ipaddress.ip_address(bytes.fromhex(local_address)[::-1])
                interface_bound = str(decoded) == guest_ip
            except ValueError:
                pass
        if _MIN_AUTOMATIC_PORT <= port <= 65535 and (wildcard or interface_bound):
            ports.add(port)
    return ports


class _ForwardingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False

    def __init__(self, bind_address: str, port: int, target: tuple[str, int]) -> None:
        self.target = target
        self._connection_limit = threading.BoundedSemaphore(64)
        super().__init__((bind_address, port), _ForwardingHandler, bind_and_activate=True)

    def process_request(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        if not self._connection_limit.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connection_limit.release()
            raise

    def process_request_thread(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connection_limit.release()


class _ForwardingHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            guest = socket.create_connection(self.server.target, timeout=4)
        except OSError:
            return
        client = self.request
        client.setblocking(False)
        guest.setblocking(False)
        peers = {client: guest, guest: client}
        open_reads = {client, guest}
        last_activity = time.monotonic()
        try:
            while open_reads:
                timeout = max(0, 120 - (time.monotonic() - last_activity))
                readable, _, _ = select.select(list(open_reads), [], [], timeout)
                if not readable:
                    return
                for source in readable:
                    destination = peers[source]
                    try:
                        payload = source.recv(65536)
                    except OSError:
                        payload = b""
                    if not payload:
                        open_reads.discard(source)
                        try:
                            destination.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        continue
                    last_activity = time.monotonic()
                    view = memoryview(payload)
                    while view:
                        try:
                            sent = destination.send(view)
                        except (BlockingIOError, InterruptedError):
                            _, writable, _ = select.select([], [destination], [], 5)
                            if not writable:
                                return
                            continue
                        except OSError:
                            return
                        view = view[sent:]
        finally:
            guest.close()


class PortForwardingMonitor:
    """Keep local TCP listeners synchronized with Fedora's active services."""

    def __init__(self) -> None:
        self._servers: dict[int, tuple[str, str, _ForwardingServer, threading.Thread]] = {}
        self._errors: dict[int, tuple[str, str, str]] = {}

    @staticmethod
    def _stop(server: _ForwardingServer, thread: threading.Thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    def refresh(self) -> None:
        try:
            running = _container_running(lambda _message: None)
            guest_ip = _container_ipv4() if running else None
            guest_ports = _listening_tcp_ports(guest_ip) if running and guest_ip else set()
            public_ports = _read_public_ports()
        except (OSError, subprocess.TimeoutExpired, VShellError):
            running, guest_ip, guest_ports, public_ports = False, None, set(), set()

        desired = {
            port: (guest_ip or "", "0.0.0.0" if port in public_ports else "127.0.0.1")
            for port in guest_ports
        }
        for port, (target_ip, bind_ip, server, thread) in list(self._servers.items()):
            if desired.get(port) != (target_ip, bind_ip):
                self._stop(server, thread)
                del self._servers[port]
        self._errors = {port: error for port, error in self._errors.items() if desired.get(port) == error[:2]}

        for port, (target_ip, bind_ip) in desired.items():
            if port in self._servers:
                continue
            try:
                server = _ForwardingServer(bind_ip, port, (target_ip, port))
            except OSError as error:
                self._errors[port] = (target_ip, bind_ip, str(error))
                continue
            thread = threading.Thread(target=server.serve_forever, name=f"vshell-port-{port}", daemon=True)
            thread.start()
            self._servers[port] = (target_ip, bind_ip, server, thread)

        rows: list[dict[str, object]] = []
        for port, (_target_ip, bind_ip) in sorted(desired.items()):
            row: dict[str, object] = {
                "port": port,
                "protocol": "TCP",
                "hostAddress": f"localhost:{port}",
                "publicAccess": bind_ip == "0.0.0.0",
                "status": "Forwarding",
                "error": "",
            }
            if port in self._errors:
                row["status"] = "Unavailable"
                row["error"] = self._errors[port][2]
            rows.append(row)
        _write_state(rows)

    def close(self) -> None:
        for _target, _bind, server, thread in self._servers.values():
            self._stop(server, thread)
        self._servers.clear()
        _write_state([])
