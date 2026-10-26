#!/usr/bin/env python3
"""Apply the distro identity and icon generated from packages.yml."""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def main(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    fields = config.get("os_release")
    if not isinstance(fields, dict):
        raise ValueError("distro config must define an os_release mapping")

    required_fields = {"NAME", "ID", "PRETTY_NAME", "VERSION_ID", "HOME_URL", "LOGO"}
    missing = required_fields - fields.keys()
    if missing:
        raise ValueError(f"missing os-release fields: {', '.join(sorted(missing))}")

    lines = []
    for key, value in fields.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"invalid os-release field name: {key!r}")
        if not isinstance(value, str) or any(char in value for char in "\r\n\0"):
            raise ValueError(f"invalid value for os-release field {key}")
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}="{escaped}"')

    logo_name = fields["LOGO"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", logo_name):
        raise ValueError("LOGO must be a simple icon name")

    logo = config.get("logo")
    logo_url = logo.get("url") if isinstance(logo, dict) else None
    if not isinstance(logo_url, str) or not logo_url.startswith("https://"):
        raise ValueError("distro config must provide an HTTPS URL in logo.url")

    request = urllib.request.Request(
        logo_url,
        headers={"User-Agent": "cubelinux-image-builder"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        icon_data = response.read(5 * 1024 * 1024 + 1)
    if len(icon_data) > 5 * 1024 * 1024:
        raise ValueError("logo SVG exceeds the 5 MiB limit")
    root = ET.fromstring(icon_data)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("logo URL did not return an SVG document")

    Path("/usr/lib/os-release").write_text("\n".join(lines) + "\n", encoding="utf-8")
    icon_path = Path("/usr/share/icons/hicolor/scalable/apps") / f"{logo_name}.svg"
    icon_path.parent.mkdir(parents=True, exist_ok=True)
    icon_path.write_bytes(icon_data)

    about_distro = Path("/etc/xdg/kcm-about-distrorc")
    about_distro.parent.mkdir(parents=True, exist_ok=True)
    about_distro.write_text(
        "[General]\n"
        f"LogoPath={icon_path}\n"
        f"Website={fields['HOME_URL']}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
