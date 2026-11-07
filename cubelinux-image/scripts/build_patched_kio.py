#!/usr/bin/env python3
"""Build installed KF6 KIO RPMs with cubelinux's kiosk launch policy patch."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(*command: str, capture: bool = False) -> str:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def kio_package_names() -> set[str]:
    installed = run("rpm", "-qa", "--qf", "%{NAME}\n", capture=True).splitlines()
    return {
        name
        for name in installed
        if name == "kf6-kio" or name.startswith("kf6-kio-")
    }


def package_evr(package: Path) -> tuple[str, str, str]:
    metadata = run(
        "rpm",
        "-qp",
        "--qf",
        "%{NAME}\t%{VERSION}\t%{RELEASE}\n",
        str(package),
        capture=True,
    )
    name, version, release = metadata.split("\t")
    return name, version, release


def add_patch_to_spec(spec_path: Path, patch_name: str, release: str) -> None:
    spec = spec_path.read_text(encoding="utf-8")

    release_matches = list(re.finditer(r"(?m)^Release:.*$", spec))
    if len(release_matches) != 1:
        raise RuntimeError("expected exactly one Release tag in the KF6 KIO spec")
    spec = (
        spec[: release_matches[0].start()]
        + f"Release: {release}.cubelinux1"
        + spec[release_matches[0].end() :]
    )

    patch_tags = list(re.finditer(r"(?m)^Patch(\d*):", spec))
    patch_number = max(
        (int(match.group(1) or "0") for match in patch_tags),
        default=0,
    ) + 1
    description = re.search(r"(?m)^%description(?:\s|$)", spec)
    if description is None:
        raise RuntimeError("could not find the KF6 KIO spec description section")
    spec = (
        spec[: description.start()]
        + f"Patch{patch_number}: {patch_name}\n"
        + spec[description.start() :]
    )

    prep = re.search(
        r"(?ms)^%prep(?:[ \t]+[^\n]*)?\n(.*?)(?=^%build(?:\s|$))",
        spec,
    )
    if prep is None:
        raise RuntimeError("could not find the KF6 KIO %prep section")

    prep_lines = prep.group(1).splitlines(keepends=True)
    automatically_applied = False
    updated_lines: list[str] = []
    for line in prep_lines:
        macro = re.match(r"\s*%(autosetup|autopatch)\b", line)
        if macro is None:
            updated_lines.append(line)
            continue

        macro_name = macro.group(1)
        auto_setup_disabled = macro_name == "autosetup" and re.search(
            r"(?:^|\s)-N(?:\s|$)",
            line,
        )
        applies_patches = macro_name == "autopatch" or not auto_setup_disabled
        if applies_patches:
            max_patch = re.search(r"(?<!\S)-M(?:\s+|=)(\d+)(?=\s|$)", line)
            if max_patch is not None and int(max_patch.group(1)) < patch_number:
                line = (
                    line[: max_patch.start(1)]
                    + str(patch_number)
                    + line[max_patch.end(1) :]
                )
            minimum_patch = re.search(r"(?<!\S)-m(?:\s+|=)(\d+)(?=\s|$)", line)
            if minimum_patch is not None and int(minimum_patch.group(1)) > patch_number:
                raise RuntimeError("KF6 KIO patch range excludes the new downstream patch")
            automatically_applied = True
        updated_lines.append(line)

    if not automatically_applied:
        spec = (
            spec[: prep.end(1)]
            + f"%patch -P {patch_number} -p1\n"
            + spec[prep.end(1) :]
        )
    else:
        spec = spec[: prep.start(1)] + "".join(updated_lines) + spec[prep.end(1) :]

    spec_path.write_text(spec, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_patched_kio.py PATCH_FILE OUTPUT_DIR")

    patch_file = Path(sys.argv[1]).resolve(strict=True)
    output_dir = Path(sys.argv[2]).resolve()
    installed_packages = kio_package_names()
    if not installed_packages:
        raise RuntimeError("the image package stage has no installed KF6 KIO RPMs")

    installed_versions = {
        tuple(
            run(
                "rpm",
                "-q",
                "--qf",
                "%{VERSION}\t%{RELEASE}",
                package,
                capture=True,
            ).split("\t")
        )
        for package in sorted(installed_packages)
    }
    if len(installed_versions) != 1:
        raise RuntimeError(
            "installed KF6 KIO subpackages have different versions: "
            + ", ".join(sorted(installed_versions))
        )
    installed_version, installed_release = next(iter(installed_versions))

    work_dir = Path("/tmp/cubelinux-kf6-kio-build")
    srpm_dir = work_dir / "srpms"
    top_dir = work_dir / "rpmbuild"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    srpm_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    run(
        "dnf5",
        "install",
        "-y",
        "dnf5-plugins",
        "dnf5-command(download)",
        "rpm-build",
    )
    run("dnf5", "download", "--srpm", "--destdir", str(srpm_dir), "kf6-kio")
    matching_srpms = []
    for srpm in srpm_dir.glob("*.src.rpm"):
        name, version, release = package_evr(srpm)
        if name == "kf6-kio" and (version, release) == (
            installed_version,
            installed_release,
        ):
            matching_srpms.append(srpm)
    if len(matching_srpms) != 1:
        available = [
            f"{path.name} ({package_evr(path)[1]}-{package_evr(path)[2]})"
            for path in srpm_dir.glob("*.src.rpm")
        ]
        raise RuntimeError(
            f"could not find the KF6 KIO source RPM matching installed "
            f"version {installed_version}-{installed_release}; "
            f"found: {', '.join(available) or 'none'}"
        )
    srpm = matching_srpms[0]

    run("dnf5", "builddep", "-y", "--srpm", str(srpm))
    top_dir.mkdir(parents=True)
    for directory in (
        "BUILD",
        "BUILDROOT",
        "RPMS",
        "SOURCES",
        "SPECS",
        "SRPMS",
    ):
        (top_dir / directory).mkdir()
    run(
        "rpm",
        "-i",
        "--define",
        f"_topdir {top_dir}",
        str(srpm),
    )

    spec_files = list((top_dir / "SPECS").glob("*.spec"))
    if len(spec_files) != 1:
        raise RuntimeError("expected one KF6 KIO spec file in the source RPM")
    patch_name = "cubelinux-kf6-kio-kiosk-launch-policy.patch"
    shutil.copyfile(patch_file, top_dir / "SOURCES" / patch_name)
    add_patch_to_spec(
        spec_files[0],
        patch_name,
        installed_release,
    )

    run(
        "rpmbuild",
        "-bb",
        "--nocheck",
        "--define",
        f"_topdir {top_dir}",
        str(spec_files[0]),
    )

    built_names: set[str] = set()
    for rpm_file in (top_dir / "RPMS").rglob("*.rpm"):
        name, _, _ = package_evr(rpm_file)
        if name in installed_packages:
            shutil.copyfile(rpm_file, output_dir / rpm_file.name)
            built_names.add(name)
    missing = installed_packages - built_names
    if missing:
        raise RuntimeError(
            "the KF6 KIO build did not produce installed subpackages: "
            + ", ".join(sorted(missing))
        )

    print(
        "Built patched KF6 KIO packages: "
        + ", ".join(sorted(built_names)),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as error:
        raise SystemExit(f"KF6 KIO patch build failed: {error}") from error
