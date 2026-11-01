#!/usr/bin/env python3
"""Configure Flathub and limit KDE Discover to Flatpak applications."""

from __future__ import annotations

import configparser
from pathlib import Path
from urllib.request import Request, urlopen


FLATHUB_REPO_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"
MAX_REMOTE_SIZE = 128 * 1024
REMOTE_PATH = Path("/etc/flatpak/remotes.d/flathub.flatpakrepo")
WRAPPER_PATH = Path("/usr/local/bin/plasma-discover")
APPLICATION_PATHS = (
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
)


def download_flathub_remote() -> bytes:
    request = Request(FLATHUB_REPO_URL, headers={"User-Agent": "cubelinux-image-builder"})
    with urlopen(request, timeout=30) as response:
        contents = response.read(MAX_REMOTE_SIZE + 1)
    if len(contents) > MAX_REMOTE_SIZE:
        raise ValueError("Flathub remote configuration exceeds the size limit")

    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        parser.read_string(contents.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error) as error:
        raise ValueError(f"Flathub returned an invalid remote configuration: {error}") from error

    if not parser.has_section("Flatpak Repo"):
        raise ValueError("Flathub remote configuration is missing its Flatpak Repo section")
    remote = parser["Flatpak Repo"]
    if remote.get("title") != "Flathub":
        raise ValueError("Downloaded Flatpak remote is not titled Flathub")
    if remote.get("url") != "https://dl.flathub.org/repo/":
        raise ValueError("Downloaded Flathub remote has an unexpected repository URL")
    if not remote.get("gpgkey") and not remote.get("gpgkeysurl"):
        raise ValueError("Flathub remote configuration does not provide a signing key")
    return contents


def configure_discover() -> None:
    WRAPPER_PATH.parent.mkdir(parents=True, exist_ok=True)
    WRAPPER_PATH.write_text(
        "#!/bin/sh\n"
        'exec /usr/bin/plasma-discover "$@" --backends=flatpak\n',
        encoding="utf-8",
    )
    WRAPPER_PATH.chmod(0o755)

    local_applications = APPLICATION_PATHS[1]
    local_applications.mkdir(parents=True, exist_ok=True)
    for application_directory in APPLICATION_PATHS:
        if not application_directory.is_dir():
            continue
        for desktop_file in application_directory.glob("*.desktop"):
            contents = desktop_file.read_text(encoding="utf-8")
            updated_lines = []
            changed = False
            for line in contents.splitlines():
                if line.startswith("Exec="):
                    command = line[len("Exec="):]
                    if command.startswith("plasma-discover ") or command == "plasma-discover":
                        arguments = command[len("plasma-discover"):]
                        line = f"Exec={WRAPPER_PATH}{arguments}"
                        changed = True
                updated_lines.append(line)
            if changed and desktop_file.parent != local_applications:
                (local_applications / desktop_file.name).write_text(
                    "\n".join(updated_lines) + "\n", encoding="utf-8"
                )


def main() -> None:
    REMOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REMOTE_PATH.write_bytes(download_flathub_remote())
    REMOTE_PATH.chmod(0o644)
    configure_discover()


if __name__ == "__main__":
    main()
