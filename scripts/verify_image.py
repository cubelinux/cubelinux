#!/usr/bin/env python3
"""Inspect the filesystem of a built image without starting its services."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from configure_distro import render_os_release


ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".image-build"


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


def verify_image(image: str) -> None:
    distro = json.loads((BUILD / "distro.json").read_text(encoding="utf-8"))
    fields = distro["os_release"]
    component_root = BUILD / "rootfs"
    logo_name = fields["LOGO"]
    logo_image_path = f"/usr/share/icons/hicolor/scalable/apps/{logo_name}.svg"
    about_image_path = "/etc/xdg/kcm-about-distrorc"
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
            scratch = Path(temporary)

            actual_os_release = copy_from_image(
                container, "/usr/lib/os-release", scratch / "os-release"
            ).decode("utf-8")
            expected_os_release = render_os_release(fields)
            if actual_os_release != expected_os_release:
                raise ValueError("image /usr/lib/os-release does not match config/image.toml")

            logo_bytes = copy_from_image(container, logo_image_path, scratch / "logo.svg")
            logo_root = ET.fromstring(logo_bytes)
            if logo_root.tag.rsplit("}", 1)[-1] != "svg":
                raise ValueError(f"image logo at {logo_image_path} is not an SVG")

            actual_about = copy_from_image(
                container, about_image_path, scratch / "kcm-about-distrorc"
            ).decode("utf-8")
            expected_about = (
                "[General]\n"
                f"LogoPath={logo_image_path}\n"
                f"Website={fields['HOME_URL']}\n"
            )
            if actual_about != expected_about:
                raise ValueError("image KDE distro settings do not match configured logo and website")

            staged_files = sorted(path for path in component_root.rglob("*") if path.is_file())
            for index, expected_path in enumerate(staged_files):
                relative = expected_path.relative_to(component_root).as_posix()
                image_path = f"/{relative}"
                actual_path = scratch / "components" / str(index)
                actual_bytes = copy_from_image(container, image_path, actual_path)
                if actual_bytes != expected_path.read_bytes():
                    raise ValueError(f"image component file differs from staged file: {image_path}")
                if os.name != "nt":
                    expected_mode = stat.S_IMODE(expected_path.stat().st_mode)
                    actual_mode = stat.S_IMODE(actual_path.stat().st_mode)
                    if actual_mode != expected_mode:
                        raise ValueError(f"image component file has wrong mode: {image_path}")
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    print(f"Verified distro metadata, logo, and {len(staged_files)} component files in {image}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="Local Docker image name and tag")
    arguments = parser.parse_args()
    if shutil.which("docker") is None:
        raise RuntimeError("docker CLI is required to inspect the built image")
    verify_image(arguments.image)


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ET.ParseError, KeyError, ValueError, RuntimeError) as error:
        print(f"Image verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
