#!/usr/bin/env python3
"""Apply distro identity and icon data generated from image.toml."""

import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def render_os_release(fields: object) -> str:
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
    return "\n".join(lines) + "\n"


def resolve_svg_color_variables(root: ET.Element) -> None:
    variables: dict[str, str] = {}
    variable_pattern = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*\)")

    for element in root.iter():
        for declaration in element.get("style", "").split(";"):
            name, separator, value = declaration.partition(":")
            name = name.strip()
            if separator and name.startswith("--"):
                variables[name] = value.strip()

    for element in root.iter():
        for attribute, original in element.attrib.items():
            if "var(" not in original:
                continue

            def replace_variable(match: re.Match[str]) -> str:
                name = match.group(1)
                if name not in variables:
                    raise ValueError(f"SVG references undefined color variable {name}")
                return variables[name]

            resolved = variable_pattern.sub(replace_variable, original)
            if "var(" in resolved:
                raise ValueError(f"unsupported CSS variable syntax in SVG attribute {attribute}")
            element.set(attribute, resolved)


def render_logo_pngs(root: ET.Element, logo_name: str, root_dir: Path) -> dict[int, Path]:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    resolve_svg_color_variables(root)

    outputs = {
        size: root_dir
        / "usr/share/icons/hicolor"
        / f"{size}x{size}"
        / "apps"
        / f"{logo_name}.png"
        for size in (64, 256)
    }
    with tempfile.TemporaryDirectory(prefix="cubelinux-logo-") as temporary:
        source = Path(temporary) / "logo.svg"
        source.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
        for size, output in outputs.items():
            output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "rsvg-convert",
                    "--width",
                    str(size),
                    "--height",
                    str(size),
                    "--keep-aspect-ratio",
                    "--output",
                    str(output),
                    str(source),
                ],
                check=True,
            )
            if not output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError(f"rsvg-convert did not create a valid PNG at {output}")
    return outputs


def configure(
    config_path: Path,
    root_dir: Path = Path("/"),
    logo_data: bytes | None = None,
) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    fields = config.get("os_release")
    os_release = render_os_release(fields)

    logo_name = fields["LOGO"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", logo_name):
        raise ValueError("LOGO must be a simple icon name")

    logo = config.get("logo")
    logo_url = logo.get("url") if isinstance(logo, dict) else None
    if not isinstance(logo_url, str) or not logo_url.startswith("https://"):
        raise ValueError("distro config must provide an HTTPS URL in logo.url")

    if logo_data is None:
        request = urllib.request.Request(
            logo_url,
            headers={"User-Agent": "cubelinux-image-builder"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            icon_data = response.read(5 * 1024 * 1024 + 1)
    else:
        icon_data = logo_data
    if len(icon_data) > 5 * 1024 * 1024:
        raise ValueError("logo SVG exceeds the 5 MiB limit")
    root = ET.fromstring(icon_data)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("logo URL did not return an SVG document")
    icon_paths = render_logo_pngs(root, logo_name, root_dir)

    os_release_path = root_dir / "usr/lib/os-release"
    os_release_path.parent.mkdir(parents=True, exist_ok=True)
    os_release_path.write_text(os_release, encoding="utf-8")
    about_distro = root_dir / "etc/xdg/kcm-about-distrorc"
    about_distro.parent.mkdir(parents=True, exist_ok=True)
    about_distro.write_text(
        "[General]\n"
        f"LogoPath={icon_paths[256]}\n"
        f"Website={fields['HOME_URL']}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    configure(Path(sys.argv[1]))
