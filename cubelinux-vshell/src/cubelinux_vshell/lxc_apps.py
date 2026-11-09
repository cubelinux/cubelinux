"""Translate host launcher requests into LXC application launches."""

from __future__ import annotations

import os
import pwd
import shlex
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

from .lxc_backend import (
    CONTAINER_NAME, CONTAINER_RUNTIME_DIR, GUEST_ID, VShellError,
    _account, _container_running, _container_runtime_value,
    _ensure_guest_x11_socket_path, _ensure_host_desktop_mounts,
    _container_name, _ensure_slirp_config, _ensure_slirp_network, _home,
    _host_runtime_dir, _lxc_path, _rootfs_path, _start_container,
    _stop_container, is_initialized,
)



def _host_argument_to_guest(value: str, account: pwd.struct_passwd) -> str:
    """Translate host file arguments under the shared home into guest paths."""
    parsed = urlparse(value)
    if parsed.scheme == "file":
        value = unquote(parsed.path)
    host_path = Path(value)
    try:
        relative = host_path.resolve(strict=False).relative_to(_home())
    except (OSError, ValueError):
        return value
    return str(Path("/home") / account.pw_name / relative)


def _desktop_exec_arguments(
    exec_value: str,
    values: list[str],
    name: str,
    desktop_file: str,
    icon: str,
    account: pwd.struct_passwd,
) -> list[str]:
    """Parse Desktop Entry Exec tokens and expand its standard field codes."""
    try:
        tokens = shlex.split(exec_value, posix=True)
    except ValueError as error:
        raise VShellError(f"The Runtime app has an invalid Exec entry: {error}") from error
    result: list[str] = []
    file_codes = {"f", "F", "u", "U"}
    for token in tokens:
        if token in ("%F", "%U"):
            result.extend(_host_argument_to_guest(value, account) for value in values)
            continue
        if token in ("%f", "%u"):
            if values:
                result.append(_host_argument_to_guest(values[0], account))
            continue
        if token == "%i":
            if icon:
                result.extend(("--icon", icon))
            continue
        output = ""
        index = 0
        while index < len(token):
            if token[index] != "%" or index + 1 >= len(token):
                output += token[index]
                index += 1
                continue
            code = token[index + 1]
            index += 2
            if code == "%":
                output += "%"
            elif code == "c":
                output += name
            elif code == "k":
                output += desktop_file
            elif code in file_codes:
                output += _host_argument_to_guest(values[0], account) if values else ""
            # Unknown/deprecated field codes are removed per the desktop-entry spec.
        if output:
            result.append(output)
    if not result:
        raise VShellError("The Runtime app's Exec entry did not contain a program.")
    return result



def launch_app(
    desktop_file: str,
    files: list[str] | None = None,
    container_name: str = CONTAINER_NAME,
) -> int:
    """Launch an approved container desktop application from the host session."""
    container_name = _container_name(container_name)
    if not is_initialized(container_name):
        raise VShellError("Virtual Shell is not set up yet. Open it from the application menu first.")
    from .app_discovery import _display_name, _parse_desktop

    account = _account()
    if desktop_file.startswith("flatpak:"):
        app_id = desktop_file.removeprefix("flatpak:")
        if not app_id or len(app_id) > 255 or not all(
            part and part[0].isalnum() and all(char.isalnum() or char in "._-" for char in part)
            for part in app_id.split(".")
        ):
            raise VShellError("Invalid Flatpak application identifier.")
        argv = ["flatpak", "run", app_id]
        argv.extend(_host_argument_to_guest(value, account) for value in files or [])
    else:
        relative = Path(desktop_file)
        if relative.is_absolute() or ".." in relative.parts:
            raise VShellError("Invalid Runtime desktop application identifier.")
        rootfs = _rootfs_path(container_name).resolve()
        source = (rootfs / relative).resolve()
        try:
            source.relative_to(rootfs)
        except ValueError as error:
            raise VShellError("Invalid Runtime desktop application identifier.") from error
        values = _parse_desktop(source)
        if values.get("Type") != "Application" or not values.get("Exec"):
            raise VShellError("The Runtime application entry is missing or cannot be launched.")
        guest_desktop_file = "/" + relative.as_posix()
        argv = _desktop_exec_arguments(
            values["Exec"], files or [], _display_name(values), guest_desktop_file,
            values.get("Icon", ""), account
        )
    network_config_changed = _ensure_slirp_config(container_name)
    mounts_changed = _ensure_host_desktop_mounts(account, container_name)
    if (mounts_changed or network_config_changed) and _container_running(print, container_name):
        _stop_container(print, container_name)
    if not _container_running(print, container_name):
        _start_container(print, container_name)
    else:
        _ensure_slirp_network(print, container_name)
    _ensure_guest_x11_socket_path(container_name=container_name)
    command = [
        "lxc-attach", "--name", container_name, "--lxcpath", str(_lxc_path()),
        "--clear-env", "--uid", str(GUEST_ID), "--gid", str(GUEST_ID),
        "--set-var", f"HOME=/home/{account.pw_name}",
        "--set-var", f"USER={account.pw_name}",
        "--set-var", f"LOGNAME={account.pw_name}",
        "--set-var", "PATH=/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/bin:/sbin",
        "--set-var", "XDG_DATA_DIRS=/usr/local/share:/usr/share",
    ]
    runtime_dir = _host_runtime_dir(account)
    if runtime_dir:
        command.extend(["--set-var", f"XDG_RUNTIME_DIR={CONTAINER_RUNTIME_DIR}"])
    for variable in (
        "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
        "PULSE_SERVER", "PIPEWIRE_REMOTE", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP",
        "QT_QPA_PLATFORM", "LANG", "LC_ALL", "LC_CTYPE",
    ):
        value = os.environ.get(variable)
        if value:
            if runtime_dir:
                value = _container_runtime_value(value, runtime_dir)
            command.extend(["--set-var", f"{variable}={value}"])
    command.extend(["--", *argv])
    return subprocess.run(command, check=False).returncode
