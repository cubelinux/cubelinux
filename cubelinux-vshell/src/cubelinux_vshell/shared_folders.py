"""Manage host folders shared with the Fedora LXC environment."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .lxc_backend import (
    CONTAINER_NAME,
    VShellError,
    _container_running,
    _config_path,
    _ensure_guest_x11_socket_path,
    _escape_mount_path,
    _lxc_path,
    _report,
    _start_container,
    _stop_container,
)

_SECTION = "# VShell additional shared folders"
_HOST_SECTION = "# VShell host desktop sockets"
_GUEST_SHARE_ROOT = Path("mnt/vshell-shares")


def _metadata_path() -> Path:
    return _lxc_path().parent / f"{CONTAINER_NAME}-shared-folders.json"


def _share_id(path: Path) -> str:
    return hashlib.sha256(os.fsencode(str(path))).hexdigest()[:16]


def _load() -> list[dict[str, str]]:
    metadata = _metadata_path()
    if not metadata.exists():
        return []
    try:
        entries: Any = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VShellError(f"Could not read shared-folder settings: {error}") from error
    if not isinstance(entries, list):
        raise VShellError("Shared-folder settings have an invalid format.")

    shares: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise VShellError("Shared-folder settings contain an invalid entry.")
        path = Path(entry["path"])
        if not path.is_absolute():
            raise VShellError("A shared-folder path is not absolute.")
        path = path.resolve(strict=False)
        if any(character in str(path) for character in ("\n", "\r", "\0")):
            raise VShellError("A shared-folder path contains unsupported characters.")
        shares.append({"id": _share_id(path), "path": str(path)})
    return sorted(shares, key=lambda entry: entry["path"].casefold())


def list_shared_folders() -> list[dict[str, str]]:
    """Return UI-safe metadata for the selected host folders."""
    result: list[dict[str, str]] = []
    for entry in _load():
        path = Path(entry["path"])
        result.append(
            {
                "id": entry["id"],
                "path": str(path),
                "name": path.name or str(path),
                "mountPath": str(_GUEST_SHARE_ROOT / entry["id"]),
                "available": str(path.is_dir()).lower(),
            }
        )
    return result


def _save(entries: list[dict[str, str]]) -> None:
    metadata = _metadata_path()
    metadata.parent.mkdir(parents=True, exist_ok=True)
    if not entries:
        metadata.unlink(missing_ok=True)
        return
    temporary = metadata.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(metadata)


def _write_config_entries(config: Path, entries: list[dict[str, str]]) -> None:
    contents = config.read_text(encoding="utf-8")
    lines = contents.rstrip().splitlines()
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index] == _SECTION:
            index += 1
            while index < len(lines) and not lines[index].startswith("# VShell "):
                index += 1
            continue
        cleaned.append(lines[index])
        index += 1

    mounts = [
        f"lxc.mount.entry = {_escape_mount_path(entry['path'])} "
        f"{(_GUEST_SHARE_ROOT / entry['id']).as_posix()} none bind,create=dir 0 0"
        for entry in entries
    ]
    if mounts:
        block = [_SECTION, *mounts]
        try:
            host_index = cleaned.index(_HOST_SECTION)
        except ValueError:
            host_index = len(cleaned)
        cleaned[host_index:host_index] = block
    config.write_text("\n".join(cleaned).rstrip() + "\n", encoding="utf-8")


def _apply(entries: list[dict[str, str]], progress) -> list[dict[str, str]]:
    config = _config_path()
    if not config.is_file():
        raise VShellError("The Fedora environment is not set up yet.")
    old_entries = _load()
    old_config = config.read_text(encoding="utf-8")
    was_running = _container_running(progress)
    if was_running:
        _report(progress, "Stopping Fedora to update shared folders…")
        _stop_container(progress)

    try:
        _save(entries)
        _write_config_entries(config, entries)
        if was_running:
            _report(progress, "Applying folder access and starting Fedora…")
            _start_container(progress)
            _ensure_guest_x11_socket_path(progress)
    except Exception as error:
        rollback_errors: list[str] = []
        try:
            _save(old_entries)
            config.write_text(old_config, encoding="utf-8")
        except OSError as rollback_error:
            rollback_errors.append(str(rollback_error))
        if was_running and not _container_running(progress):
            try:
                _start_container(progress)
                _ensure_guest_x11_socket_path(progress)
            except Exception as rollback_error:
                rollback_errors.append(str(rollback_error))
        detail = f"Could not update shared folders: {error}"
        if rollback_errors:
            detail += "; rollback also failed: " + "; ".join(rollback_errors)
        raise VShellError(detail) from error
    return list_shared_folders()


def add_shared_folder(folder: str, progress) -> list[dict[str, str]]:
    """Share a selected host folder read-write with the Fedora user."""
    try:
        path = Path(folder).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise VShellError(f"Could not open the selected folder: {error}") from error
    if not path.is_dir():
        raise VShellError("Select a folder to share with Fedora.")
    if path == Path(path.anchor):
        raise VShellError("Sharing the host filesystem root is not allowed.")
    if any(character in str(path) for character in ("\n", "\r", "\0")):
        raise VShellError("This folder path contains characters LXC cannot mount safely.")
    home = Path.home().resolve()
    try:
        path.relative_to(home)
    except ValueError:
        pass
    else:
        raise VShellError("Your home folder and its contents are already shared with Fedora.")
    entries = _load()
    if any(entry["path"] == str(path) for entry in entries):
        raise VShellError("That folder is already shared with Fedora.")
    entries.append({"id": _share_id(path), "path": str(path)})
    entries.sort(key=lambda entry: entry["path"].casefold())
    return _apply(entries, progress)


def remove_shared_folder(share_id: str, progress) -> list[dict[str, str]]:
    """Remove a selected bind mount from Fedora."""
    entries = _load()
    updated = [entry for entry in entries if entry["id"] != share_id]
    if len(updated) == len(entries):
        raise VShellError("That shared folder is no longer configured.")
    return _apply(updated, progress)


def sync_saved_shared_folders() -> None:
    """Write saved share mounts into a newly created container config."""
    _write_config_entries(_config_path(), _load())


def clear_shared_folders() -> None:
    """Forget extra folder shares when the Fedora environment is destroyed."""
    _metadata_path().unlink(missing_ok=True)
