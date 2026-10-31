#!/usr/bin/env python3
"""Fetch pinned image components and assemble their declared build inputs."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "image.toml"
OUTPUT = ROOT / ".image-build"
PACKAGE_RE = re.compile(r"[A-Za-z0-9_.+-]+\Z")
COMPONENT_RE = re.compile(r"[a-z][a-z0-9-]*\Z")
SERVICE_RE = re.compile(r"[A-Za-z0-9_.@:-]+\Z")


def fail(message: str) -> None:
    raise ValueError(message)


def validate_package_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not PACKAGE_RE.fullmatch(item) for item in value
    ):
        fail(f"{label} must be a list of valid package names")
    return value


def safe_destination(value: object, component_id: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.startswith("/"):
        fail(f"{component_id}: file destinations must be absolute paths")
    destination = PurePosixPath(value)
    if any(part in (".", "..") for part in destination.parts):
        fail(f"{component_id}: unsafe destination path {value!r}")
    if value == "/" or not value.startswith("/usr/") and not value.startswith("/etc/"):
        fail(f"{component_id}: destination must be under /usr or /etc")
    return destination


def copy_entry(
    source_root: Path,
    entry: object,
    component_id: str,
    targets: set[str],
    output_dir: Path = OUTPUT,
) -> None:
    if not isinstance(entry, dict):
        fail(f"{component_id}: each files entry must be a table")
    source_text = entry.get("source")
    if not isinstance(source_text, str) or source_text.startswith("/"):
        fail(f"{component_id}: source must be a relative path")
    source_path = PurePosixPath(source_text)
    if not source_path.parts or any(part in (".", "..") for part in source_path.parts):
        fail(f"{component_id}: unsafe source path {source_text!r}")
    candidate = source_root.joinpath(*source_path.parts)
    current = source_root
    for part in source_path.parts:
        current = current / part
        if current.is_symlink():
            fail(f"{component_id}: symlinks are not allowed in component files")
    source = candidate.resolve(strict=True)
    if not source.is_relative_to(source_root.resolve()):
        fail(f"{component_id}: source escapes the component checkout")
    destination = safe_destination(entry.get("destination"), component_id)
    mode_value = entry.get("mode", "0644")
    if not isinstance(mode_value, str) or not re.fullmatch(r"0[0-7]{3}", mode_value):
        fail(f"{component_id}: mode must be a four-digit octal string")
    mode = int(mode_value, 8)
    if source.is_dir():
        for child in sorted(source.rglob("*")):
            if child.is_symlink():
                fail(f"{component_id}: symlinks are not allowed in component files")
            if child.is_file():
                relative = child.relative_to(source)
                target = destination / PurePosixPath(relative.as_posix())
                copy_file(child, target, mode, component_id, targets, output_dir)
    elif source.is_file():
        copy_file(source, destination, mode, component_id, targets, output_dir)
    else:
        fail(f"{component_id}: source must be a file or directory")


def copy_file(
    source: Path,
    destination: PurePosixPath,
    mode: int,
    component_id: str,
    targets: set[str],
    output_dir: Path = OUTPUT,
) -> None:
    target_text = destination.as_posix()
    if target_text in targets or any(
        target_text.startswith(f"{previous}/") or previous.startswith(f"{target_text}/")
        for previous in targets
    ):
        fail(f"component files overlap at {target_text}")
    targets.add(target_text)
    target = output_dir / "rootfs" / target_text.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(mode)


def local_component_path(component_id: str, value: object, component_base: Path) -> Path:
    if not isinstance(value, str) or not value:
        fail(f"{component_id}: path must name a component directory")
    relative = Path(value)
    if relative.is_absolute() or any(part in (".", "..") for part in relative.parts):
        fail(f"{component_id}: component path must be a safe relative path")
    base = component_base.resolve()
    try:
        component = (base / relative).resolve(strict=True)
    except OSError as error:
        fail(f"{component_id}: component directory is unavailable: {error}")
    if component == base or not component.is_relative_to(base) or not component.is_dir():
        fail(f"{component_id}: component path must stay inside the monorepo")
    return component


def stage_components(
    components: object,
    output_dir: Path,
    component_packages: list[str] | None = None,
    component_base: Path = ROOT.parent,
) -> tuple[list[str], set[str]]:
    if not isinstance(components, list):
        fail("components must be an array of tables")
    packages = list(component_packages or [])
    ids: set[str] = set()
    services: set[str] = set()
    targets: set[str] = set()

    for component in components:
        if not isinstance(component, dict):
            fail("each component must be a table")
        component_id = component.get("id")
        component_path = component.get("path")
        if not isinstance(component_id, str) or not COMPONENT_RE.fullmatch(component_id):
            fail("component id must use lowercase letters, digits, and hyphens")
        if component_id in ids:
            fail(f"duplicate component id {component_id}")
        ids.add(component_id)
        checkout = local_component_path(component_id, component_path, component_base)
        print(f"Staging component {component_id} from {component_path}")
        manifest_path = checkout / "component.toml"
        if not manifest_path.is_file():
            fail(f"{component_id}: missing component.toml")
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("id") != component_id:
            fail(f"{component_id}: manifest id does not match image configuration")
        packages.extend(validate_package_list(manifest.get("packages", []), f"{component_id}.packages"))
        component_services = manifest.get("services", [])
        if not isinstance(component_services, list) or any(
            not isinstance(service, str) or not SERVICE_RE.fullmatch(service)
            for service in component_services
        ):
            fail(f"{component_id}.services must contain valid systemd unit names")
        services.update(component_services)
        files = manifest.get("files", [])
        if not isinstance(files, list):
            fail(f"{component_id}.files must be an array of tables")
        for entry in files:
            copy_entry(checkout, entry, component_id, targets, output_dir)

    return packages, services


def main() -> None:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    base_image = config.get("base_image")
    if not isinstance(base_image, str) or not re.fullmatch(r"[A-Za-z0-9./:_-]+", base_image):
        fail("base_image must be a valid image reference")

    package_config = config.get("packages", {})
    if not isinstance(package_config, dict):
        fail("packages must be a table")
    packages = validate_package_list(package_config.get("base", []), "packages.base")

    distro = config.get("distro")
    if not isinstance(distro, dict) or not isinstance(distro.get("os_release"), dict):
        fail("distro.os_release must be a table")
    logo_url = distro.get("logo", {}).get("url") if isinstance(distro.get("logo"), dict) else None
    if not isinstance(logo_url, str) or not logo_url.startswith("https://"):
        fail("distro.logo.url must be an HTTPS URL")
    plymouth_logo = distro.get("plymouth_logo")
    if plymouth_logo is not None:
        plymouth_logo_url = (
            plymouth_logo.get("url") if isinstance(plymouth_logo, dict) else None
        )
        if not isinstance(plymouth_logo_url, str) or not plymouth_logo_url.startswith("https://"):
            fail("distro.plymouth_logo.url must be an HTTPS URL")

    if OUTPUT.is_symlink():
        fail("refusing to write through a symlink at .image-build")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "rootfs").mkdir(parents=True)

    packages, services = stage_components(
        config.get("components", []), OUTPUT, packages, component_base=ROOT.parent
    )

    distro_json = OUTPUT / "distro.json"
    distro_json.write_text(json.dumps(distro), encoding="utf-8")
    (OUTPUT / "services.txt").write_text("".join(f"{unit}\n" for unit in sorted(services)), encoding="utf-8")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"base_image={base_image}\n")
            output.write(f"packages={' '.join(dict.fromkeys(packages))}\n")
    else:
        print(
            f"Prepared {len(config.get('components', []))} components; "
            f"packages: {' '.join(dict.fromkeys(packages))}"
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        print(f"Image preparation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
