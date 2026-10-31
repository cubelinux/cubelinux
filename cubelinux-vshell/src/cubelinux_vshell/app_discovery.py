"""Discover Fedora desktop applications and publish launchers to the host."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path

from .lxc_backend import _rootfs_path
from .port_forwarding import PortForwardingMonitor


_MARKER = "X-CubeLinux-VShell-HostLauncher=true"
_EXTENSIONS = (".svg", ".png", ".xpm")


def _applications_dir() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "applications"


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


def _icon_source(rootfs: Path, icon: str) -> Path | None:
    if not icon:
        return None
    given = Path(icon)
    if given.is_absolute():
        candidates = [rootfs / str(given).lstrip("/")]
    else:
        stem = given.stem
        suffixes = (given.suffix,) if given.suffix else _EXTENSIONS
        candidates = [rootfs / "usr/share/pixmaps" / f"{stem}{suffix}" for suffix in suffixes]
        for theme_root in (rootfs / "usr/share/icons/hicolor", rootfs / "usr/share/icons/Fedora"):
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


def _desktop_launcher(rootfs: Path, source: Path, output: Path, icons: Path) -> bool:
    values = _parse_desktop(source)
    name = _display_name(values)
    if (values.get("Type") != "Application" or not name or not values.get("Exec")
            or values.get("Hidden", "false").lower() == "true"
            or values.get("NoDisplay", "false").lower() == "true"):
        return False
    relative = source.relative_to(rootfs).as_posix()
    app_id = hashlib.sha256(relative.encode()).hexdigest()[:20]
    destination = output / f"org.cubelinux.VShell.Fedora.{app_id}.desktop"
    icon_name = values.get("Icon", "applications-other")
    icon = _icon_source(rootfs, icon_name)
    if icon:
        icons.mkdir(parents=True, exist_ok=True)
        icon_name = f"cubelinux-vshell-fedora-{app_id}"
        shutil.copy2(icon, icons / f"{icon_name}{icon.suffix.lower()}")

    # Desktop Entry Exec quoting uses double quotes and backslash escapes. Quote
    # the source path so it remains one argument even for nested app folders.
    escaped_path = relative.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    entry = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={name} (Fedora)",
        f"Exec=/usr/bin/cubelinux-vshell launch-app \"{escaped_path}\" %U",
        f"Icon={icon_name}",
        "Terminal=false",
        "DBusActivatable=false",
        f"Categories={values.get('Categories', 'Utility;')}",
        _MARKER,
    ]
    for key in ("GenericName", "Comment", "StartupWMClass", "MimeType", "Keywords"):
        if values.get(key):
            entry.append(f"{key}={values[key]}")
    output.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(entry) + "\n", encoding="utf-8")
    return True


def discover_apps() -> None:
    """Refresh generated host launchers from the Fedora root filesystem."""
    rootfs = _rootfs_path()
    output = _applications_dir()
    icon_output = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/hicolor/scalable/apps"
    live: set[Path] = set()
    for source in _app_sources(rootfs):
        values = _parse_desktop(source)
        if values.get("Type") != "Application" or not values.get("Exec"):
            continue
        relative = source.relative_to(rootfs).as_posix()
        app_id = hashlib.sha256(relative.encode()).hexdigest()[:20]
        launcher = output / f"org.cubelinux.VShell.Fedora.{app_id}.desktop"
        if _desktop_launcher(rootfs, source, output, icon_output):
            live.add(launcher)
    if output.is_dir():
        for launcher in output.glob("org.cubelinux.VShell.Fedora.*.desktop"):
            try:
                marked = _MARKER in launcher.read_text(encoding="utf-8", errors="replace")
            except OSError:
                marked = False
            if marked and launcher not in live:
                launcher.unlink(missing_ok=True)
    live_ids = {path.stem.rsplit(".", 1)[-1] for path in live}
    if icon_output.is_dir():
        for icon_file in icon_output.glob("cubelinux-vshell-fedora-*"):
            app_id = icon_file.stem.removeprefix("cubelinux-vshell-fedora-")
            if app_id not in live_ids:
                icon_file.unlink(missing_ok=True)


def watch_apps(interval: float = 4.0) -> None:
    """Keep host launcher entries synchronized while the desktop session runs."""
    fingerprint: tuple[tuple[str, int, int], ...] | None = None
    forwarding = PortForwardingMonitor()
    try:
        while True:
            rootfs = _rootfs_path()
            current: list[tuple[str, int, int]] = []
            for source in _app_sources(rootfs):
                try:
                    stat = source.stat()
                except OSError:
                    continue
                current.append((str(source), stat.st_mtime_ns, stat.st_size))
            current_fingerprint = tuple(current)
            if current_fingerprint != fingerprint:
                discover_apps()
                fingerprint = current_fingerprint
            forwarding.refresh()
            time.sleep(interval)
    finally:
        forwarding.close()
