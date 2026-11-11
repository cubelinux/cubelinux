#!/usr/bin/env python3
"""Inspect the filesystem of a built image without starting its services."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from configure_distro import render_os_release


ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".image-build"
PLASMA_SETUP_SCRIPTS = ROOT / "config" / "plasma" / "plasmoidsetupscripts"
REQUIRED_PLASMA_SETUP_SCRIPTS = (
    "org.kde.plasma.kickoff.js",
    "org.kde.plasma.icontasks.js",
)
PLASMA_SETUP_SESSION_FILES = {
    "/usr/libexec/cubelinux-plasma-setup-hide-edit-mode": (
        ROOT / "config" / "plasma" / "plasma-setup-hide-edit-mode",
        0o755,
    ),
    "/usr/lib/systemd/user/cubelinux-plasma-setup-hide-edit-mode.service": (
        ROOT / "config" / "plasma" / "plasma-setup-hide-edit-mode.service",
        0o644,
    ),
}
PLASMA_SETUP_SESSION_WANTS = (
    "/usr/lib/systemd/user/default.target.wants/"
    "cubelinux-plasma-setup-hide-edit-mode.service"
)


def copy_from_image(container: str, image_path: str, destination: Path) -> bytes:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["docker", "cp", f"{container}:{image_path}", str(destination)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return destination.read_bytes()


def verify_rootfs(rootfs: Path, distro_path: Path, component_root: Path) -> int:
    distro = json.loads(distro_path.read_text(encoding="utf-8"))
    fields = distro["os_release"]
    logo_name = fields["LOGO"]
    logo_paths = {
        size: f"/usr/share/icons/hicolor/{size}x{size}/apps/{logo_name}.png"
        for size in (64, 256)
    }
    about_image_path = "/etc/xdg/kcm-about-distrorc"
    setup_scripts = {}
    for script_name in REQUIRED_PLASMA_SETUP_SCRIPTS:
        source = PLASMA_SETUP_SCRIPTS / script_name
        if not source.is_file():
            raise ValueError(f"missing Plasma widget default source file: {source}")
        image_path = (
            "/usr/share/plasma/look-and-feel/org.kde.breeze.desktop/contents/"
            f"plasmoidsetupscripts/{script_name}"
        )
        setup_scripts[image_path] = source.read_bytes()
    actual_os_release = (rootfs / "usr/lib/os-release").read_text(encoding="utf-8")
    expected_os_release = render_os_release(fields)
    if actual_os_release != expected_os_release:
        raise ValueError("image /usr/lib/os-release does not match config/image.toml")

    for size, logo_image_path in logo_paths.items():
        logo_bytes = (rootfs / logo_image_path.lstrip("/")).read_bytes()
        if (
            not logo_bytes.startswith(b"\x89PNG\r\n\x1a\n")
            or len(logo_bytes) < 24
            or struct.unpack(">II", logo_bytes[16:24]) != (size, size)
        ):
            raise ValueError(
                f"image logo at {logo_image_path} is not a {size}x{size} PNG"
            )

    actual_about = (rootfs / about_image_path.lstrip("/")).read_text(encoding="utf-8")
    expected_about = (
        "[General]\n"
        f"LogoPath={logo_paths[256]}\n"
        f"Website={fields['HOME_URL']}\n"
    )
    if actual_about != expected_about:
        raise ValueError("image KDE distro settings do not match configured logo and website")
    for image_path, expected_contents in setup_scripts.items():
        actual_contents = (rootfs / image_path.lstrip("/")).read_bytes()
        if actual_contents != expected_contents:
            raise ValueError(
                f"image Plasma widget defaults differ from the source file at {image_path}"
            )

    for image_path, (source, expected_mode) in PLASMA_SETUP_SESSION_FILES.items():
        actual_path = rootfs / image_path.lstrip("/")
        if not source.is_file() or not actual_path.is_file():
            raise ValueError(f"image is missing Plasma Setup session file: {image_path}")
        if actual_path.read_bytes() != source.read_bytes():
            raise ValueError(f"image Plasma Setup session file differs from source: {image_path}")
        if os.name != "nt" and stat.S_IMODE(actual_path.stat().st_mode) != expected_mode:
            raise ValueError(f"image Plasma Setup session file has wrong mode: {image_path}")

    wants_path = rootfs / PLASMA_SETUP_SESSION_WANTS.lstrip("/")
    if wants_path.is_symlink():
        if os.readlink(wants_path) != "../cubelinux-plasma-setup-hide-edit-mode.service":
            raise ValueError("Plasma Setup session service has an unexpected enablement link")
    elif not wants_path.is_file() or wants_path.read_bytes() != (
        rootfs / "usr/lib/systemd/user/cubelinux-plasma-setup-hide-edit-mode.service"
    ).read_bytes():
        raise ValueError("Plasma Setup session service is not enabled for user sessions")

    staged_files = sorted(path for path in component_root.rglob("*") if path.is_file())
    for expected_path in staged_files:
        relative = expected_path.relative_to(component_root)
        image_path = f"/{relative.as_posix()}"
        actual_path = rootfs / relative
        if (
            not actual_path.is_file()
            or actual_path.read_bytes() != expected_path.read_bytes()
        ):
            raise ValueError(f"image component file differs from staged file: {image_path}")
        if os.name != "nt":
            expected_mode = stat.S_IMODE(expected_path.stat().st_mode)
            actual_mode = stat.S_IMODE(actual_path.stat().st_mode)
            if actual_mode != expected_mode:
                raise ValueError(f"image component file has wrong mode: {image_path}")

    return len(staged_files)


def verify_image(image: str) -> None:
    distro_path = BUILD / "distro.json"
    component_root = BUILD / "rootfs"
    distro = json.loads(distro_path.read_text(encoding="utf-8"))
    logo_name = distro["os_release"]["LOGO"]
    logo_paths = {
        f"/usr/share/icons/hicolor/{size}x{size}/apps/{logo_name}.png"
        for size in (64, 256)
    }
    staged_files = sorted(path for path in component_root.rglob("*") if path.is_file())
    image_paths = {
        "/usr/lib/os-release",
        "/etc/xdg/kcm-about-distrorc",
        *(
            "/usr/share/plasma/look-and-feel/org.kde.breeze.desktop/contents/"
            f"plasmoidsetupscripts/{script_name}"
            for script_name in REQUIRED_PLASMA_SETUP_SCRIPTS
        ),
        *PLASMA_SETUP_SESSION_FILES,
        PLASMA_SETUP_SESSION_WANTS,
        *logo_paths,
        *(f"/{path.relative_to(component_root).as_posix()}" for path in staged_files),
    }
    container = f"cubelinux-image-verify-{uuid.uuid4().hex[:12]}"

    subprocess.run(
        ["docker", "create", "--name", container, image],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="cubelinux-image-verify-") as temporary:
            rootfs = Path(temporary)
            for image_path in sorted(image_paths):
                copy_from_image(container, image_path, rootfs / image_path.lstrip("/"))
            count = verify_rootfs(rootfs, distro_path, component_root)
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    print(f"Verified distro metadata, logo, and {count} component files in {image}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--image", help="Local Docker image name and tag")
    target.add_argument(
        "--rootfs", type=Path, help="Root filesystem directory to verify"
    )
    parser.add_argument("--distro", type=Path, default=BUILD / "distro.json")
    parser.add_argument("--expected-rootfs", type=Path, default=BUILD / "rootfs")
    arguments = parser.parse_args()
    if arguments.image:
        if shutil.which("docker") is None:
            raise RuntimeError("docker CLI is required to inspect the built image")
        verify_image(arguments.image)
    else:
        count = verify_rootfs(
            arguments.rootfs, arguments.distro, arguments.expected_rootfs
        )
        print(
            f"Verified distro metadata, logo, and {count} component files "
            f"in {arguments.rootfs}"
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ET.ParseError, KeyError, ValueError, RuntimeError) as error:
        print(f"Image verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
