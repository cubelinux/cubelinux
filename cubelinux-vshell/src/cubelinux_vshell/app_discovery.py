"""Discover Fedora desktop applications and publish launchers to the host."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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


def _desktop_launcher(rootfs: Path, source: Path, icons: Path) -> dict[str, object] | None:
    values = _parse_desktop(source)
    name = _display_name(values)
    if (values.get("Type") != "Application" or not name or not values.get("Exec")
            or values.get("Hidden", "false").lower() == "true"
            or values.get("NoDisplay", "false").lower() == "true"):
        return None
    relative = source.relative_to(rootfs).as_posix()
    app_id = hashlib.sha256(relative.encode()).hexdigest()[:20]
    icon_name = values.get("Icon", "applications-other")
    icon = _icon_source(rootfs, icon_name)
    if icon:
        icons.mkdir(parents=True, exist_ok=True)
        icon_name = f"cubelinux-vshell-fedora-{app_id}"
        shutil.copy2(icon, icons / f"{icon_name}{icon.suffix.lower()}")
    return {"path": relative, "has_icon": bool(icon), "name": name}


def _sync_system_launchers(rootfs: Path | None, launchers: list[dict[str, object]]) -> None:
    """Ask the constrained Polkit helper to publish root-owned menu wrappers."""
    pkexec = shutil.which("pkexec")
    helper = "/usr/libexec/cubelinux-vshell-launcher-sync"
    if not pkexec or not Path(helper).is_file():
        if launchers:
            print("VShell: cannot publish Fedora application menu entries; launcher sync helper is unavailable.")
        return

    request = {
        "rootfs": str(rootfs.resolve()) if rootfs and rootfs.is_dir() else None,
        "launchers": [
            {"path": item["path"], "has_icon": item["has_icon"], "name": item["name"]}
            for item in launchers
        ],
    }
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
        print(f"VShell: could not synchronize Fedora application menu entries: {error}")
        return
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
        print(f"VShell: could not synchronize Fedora application menu entries: {detail}")
        return

    # The launchers live in a mounted subdirectory, so explicitly refresh the
    # KDE service cache after their files change instead of waiting for a watcher.
    cache_builder = shutil.which("kbuildsycoca6")
    if cache_builder:
        try:
            cache_result = subprocess.run(
                [cache_builder], capture_output=True, text=True, check=False, timeout=30
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"VShell: could not refresh the KDE application menu cache: {error}")
        else:
            if cache_result.returncode:
                detail = cache_result.stderr.strip() or cache_result.stdout.strip()
                print(f"VShell: could not refresh the KDE application menu cache: {detail}")


def discover_apps() -> None:
    """Refresh generated host launchers from the Fedora root filesystem."""
    rootfs = _rootfs_path()
    legacy_output = _applications_dir()
    icon_output = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/hicolor/scalable/apps"
    live: list[dict[str, object]] = []
    for source in _app_sources(rootfs):
        launcher = _desktop_launcher(rootfs, source, icon_output)
        if launcher:
            live.append(launcher)
    if legacy_output.is_dir():
        for launcher in legacy_output.glob("org.cubelinux.VShell.Fedora.*.desktop"):
            try:
                marked = _MARKER in launcher.read_text(encoding="utf-8", errors="replace")
            except OSError:
                marked = False
            if marked:
                launcher.unlink(missing_ok=True)
    live_ids = {
        hashlib.sha256(str(item["path"]).encode()).hexdigest()[:20]
        for item in live
    }
    if icon_output.is_dir():
        for icon_file in icon_output.glob("cubelinux-vshell-fedora-*"):
            app_id = icon_file.stem.removeprefix("cubelinux-vshell-fedora-")
            if app_id not in live_ids:
                icon_file.unlink(missing_ok=True)
    _sync_system_launchers(rootfs if rootfs.is_dir() else None, live)


def clear_apps() -> None:
    """Remove generated host launchers and icons after Fedora is destroyed."""
    legacy_output = _applications_dir()
    if legacy_output.is_dir():
        for launcher in legacy_output.glob("org.cubelinux.VShell.Fedora.*.desktop"):
            try:
                if _MARKER in launcher.read_text(encoding="utf-8", errors="replace"):
                    launcher.unlink(missing_ok=True)
            except OSError as error:
                print(f"VShell: could not remove Fedora launcher {launcher}: {error}")

    icon_output = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons/hicolor/scalable/apps"
    if icon_output.is_dir():
        for icon_file in icon_output.glob("cubelinux-vshell-fedora-*"):
            try:
                icon_file.unlink(missing_ok=True)
            except OSError as error:
                print(f"VShell: could not remove Fedora launcher icon {icon_file}: {error}")

    # The constrained helper removes only VShell launchers owned by this user.
    _sync_system_launchers(None, [])


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
