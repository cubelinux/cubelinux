"""Discover container desktop applications and publish launchers to KDE."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .lxc_backend import CONTAINER_NAMES, CONTAINER_NAME, _rootfs_path
from .port_forwarding import PortForwardingMonitor


_EXTENSIONS = (".svg", ".png", ".xpm")
_APP_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)+")


def _parse_desktop(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    in_entry = False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return values
    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_entry = line == "[Desktop Entry]"
            continue
        if in_entry and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def _display_name(values: dict[str, str]) -> str:
    language = os.environ.get("LANG", "").split(".", 1)[0].split("@", 1)[0]
    candidates = [f"Name[{language}]", f"Name[{language.split('_', 1)[0]}]", "Name"]
    return next((values[key] for key in candidates if values.get(key)), "")


def _app_sources(rootfs: Path) -> list[Path]:
    found: list[Path] = []
    for directory in (rootfs / "usr/share/applications", rootfs / "usr/local/share/applications"):
        if directory.is_dir():
            found.extend(sorted(directory.rglob("*.desktop")))
    return found


def _icon_source(rootfs: Path, icon: str, extra_roots: tuple[Path, ...] = ()) -> Path | None:
    if not icon:
        return None
    given = Path(icon)
    if given.is_absolute():
        candidates = [rootfs / str(given).lstrip("/")]
    else:
        stem = given.stem
        suffixes = (given.suffix,) if given.suffix else _EXTENSIONS
        candidates = [rootfs / "usr/share/pixmaps" / f"{stem}{suffix}" for suffix in suffixes]
        theme_roots = [rootfs / "usr/share/icons/hicolor", rootfs / "usr/share/icons/Fedora"]
        for extra_root in extra_roots:
            theme_roots.extend((extra_root / "icons/hicolor", extra_root / "icons/Fedora"))
        for theme_root in theme_roots:
            for size in ("scalable/apps", "256x256/apps", "128x128/apps", "64x64/apps", "48x48/apps", "32x32/apps", "apps"):
                candidates.extend(theme_root.glob(f"{size}/{stem}.*"))
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(rootfs.resolve())
            if resolved.suffix.lower() in _EXTENSIONS and resolved.is_file():
                return resolved
        except (OSError, ValueError):
            continue
    return None


def _copy_icon(icon: Path | None, icon_root: Path, icon_name: str) -> bool:
    if not icon:
        return False
    theme_size = "scalable" if icon.suffix.lower() == ".svg" else "256x256"
    destination = icon_root / theme_size / "apps" / f"{icon_name}{icon.suffix.lower()}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon, destination)
    return True


def _desktop_launcher(
    container_name: str, rootfs: Path, source: Path, icons: Path
) -> dict[str, object] | None:
    values = _parse_desktop(source)
    name = _display_name(values)
    if (values.get("Type") != "Application" or not name or not values.get("Exec")
            or values.get("Hidden", "false").lower() == "true"
            or values.get("NoDisplay", "false").lower() == "true"):
        return None
    relative = source.relative_to(rootfs).as_posix()
    app_id = hashlib.sha256(f"{container_name}:{relative}".encode()).hexdigest()[:20]
    icon_name = values.get("Icon", "applications-other")
    icon = _icon_source(rootfs, icon_name)
    if icon:
        icon_name = f"cubelinux-vshell-{container_name}-{app_id}"
        _copy_icon(icon, icons, icon_name)
    return {
        "container": container_name,
        "kind": "desktop",
        "path": relative,
        "has_icon": bool(icon),
        "name": name,
    }


def _flatpak_launcher(source: Path, icons: Path) -> dict[str, object] | None:
    values = _parse_desktop(source)
    name = _display_name(values)
    app_id = values.get("X-Flatpak") or source.stem
    if (values.get("Type") != "Application" or not name or not values.get("Exec")
            or values.get("Hidden", "false").lower() == "true"
            or values.get("NoDisplay", "false").lower() == "true"
            or not _APP_ID_PATTERN.fullmatch(app_id)):
        return None
    digest = hashlib.sha256(f"{CONTAINER_NAME}:flatpak:{app_id}".encode()).hexdigest()[:20]
    icon = _icon_source(
        Path("/"), values.get("Icon", "applications-other"),
        (source.parents[1],),
    )
    icon_name = f"cubelinux-vshell-{CONTAINER_NAME}-{digest}"
    has_icon = _copy_icon(icon, icons, icon_name)
    return {
        "container": CONTAINER_NAME,
        "kind": "flatpak",
        "app_id": app_id,
        "has_icon": has_icon,
        "name": name,
        "categories": values.get("Categories", ""),
    }


def _flatpak_app_sources() -> list[Path]:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    roots = (data_home / "flatpak/exports/share/applications",)
    found: list[Path] = []
    seen: set[str] = set()
    for directory in roots:
        if directory.is_dir():
            for source in sorted(directory.glob("*.desktop")):
                values = _parse_desktop(source)
                app_id = values.get("X-Flatpak") or source.stem
                if app_id in seen:
                    continue
                seen.add(app_id)
                found.append(source)
    return found


def _sync_system_launchers(launchers: list[dict[str, object]]) -> None:
    """Ask the constrained Polkit helper to publish root-owned menu wrappers."""
    pkexec = shutil.which("pkexec")
    helper = "/usr/libexec/cubelinux-vshell-launcher-sync"
    if not pkexec or not Path(helper).is_file():
        if launchers:
            print("VShell: cannot publish container application launchers; launcher sync helper is unavailable.")
        return

    request = {"launchers": launchers}
    try:
        result = subprocess.run(
            [pkexec, helper],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"VShell: could not synchronize container application launchers: {error}")
        return
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
        print(f"VShell: could not synchronize container application launchers: {detail}")


def discover_apps() -> None:
    """Refresh generated launchers from initialized container environments."""
    roots = {name: _rootfs_path(name) for name in CONTAINER_NAMES}
    icon_output = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/hicolor"
    live: list[dict[str, object]] = []
    for container_name, rootfs in roots.items():
        if not rootfs.is_dir():
            continue
        for source in _app_sources(rootfs):
            launcher = _desktop_launcher(container_name, rootfs, source, icon_output)
            if launcher:
                live.append(launcher)
    if roots[CONTAINER_NAME].is_dir():
        for source in _flatpak_app_sources():
            launcher = _flatpak_launcher(source, icon_output)
            if launcher:
                live.append(launcher)
    live_ids = set()
    for item in live:
        if item["kind"] == "flatpak":
            value = f"{item['container']}:flatpak:{item['app_id']}"
        else:
            value = f"{item['container']}:{item['path']}"
        live_ids.add(hashlib.sha256(value.encode()).hexdigest()[:20])
    if icon_output.is_dir():
        for icon_file in icon_output.rglob("cubelinux-vshell-*"):
            app_id = icon_file.stem.rsplit("-", 1)[-1]
            if app_id not in live_ids:
                icon_file.unlink(missing_ok=True)
    _sync_system_launchers(live)


def watch_apps(interval: float = 4.0) -> None:
    """Keep host launcher entries synchronized while the desktop session runs."""
    fingerprint: tuple[tuple[str, int, int], ...] | None = None
    forwarding = [PortForwardingMonitor(name) for name in CONTAINER_NAMES]
    try:
        while True:
            current: list[tuple[str, int, int]] = []
            sources: list[Path] = list(_flatpak_app_sources())
            for name in CONTAINER_NAMES:
                rootfs = _rootfs_path(name)
                if rootfs.is_dir():
                    sources.extend(_app_sources(rootfs))
            for source in sources:
                try:
                    stat = source.stat()
                except OSError:
                    continue
                current.append((str(source), stat.st_mtime_ns, stat.st_size))
            current_fingerprint = tuple(current)
            if current_fingerprint != fingerprint:
                discover_apps()
                fingerprint = current_fingerprint
            for monitor in forwarding:
                monitor.refresh()
            time.sleep(interval)
    finally:
        for monitor in forwarding:
            monitor.close()
