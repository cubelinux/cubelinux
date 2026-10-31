import json
import os
import struct
import stat
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import configure_distro  # noqa: E402
import prepare_image  # noqa: E402


class ConfigureDistroTests(unittest.TestCase):
    def test_replaces_os_release_and_renders_logo_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "distro.json"
            config_path.write_text(
                json.dumps(
                    {
                        "os_release": {
                            "NAME": "cubelinux",
                            "ID": "cubelinux",
                            "PRETTY_NAME": "cubelinux desktop",
                            "VERSION_ID": "44",
                            "HOME_URL": "https://cubelinux.github.io",
                            "LOGO": "cubelinux-logo",
                            "DESCRIPTION": 'cubelinux "desktop"',
                        },
                        "logo": {"url": "https://assets.example.test/icon.svg"},
                    }
                ),
                encoding="utf-8",
            )
            os_release = root / "usr/lib/os-release"
            os_release.parent.mkdir(parents=True)
            os_release.write_text('OLD_NAME="old image"\n', encoding="utf-8")
            svg = (
                b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
                b'<g style="--logo-color: #2d9bd2"><path fill="var(--logo-color)" />'
                b"</g></svg>"
            )

            def fake_rsvg_convert(command, check):
                source = Path(command[-1])
                converted = ET.parse(source).getroot()[0][0]
                self.assertEqual(converted.get("fill"), "#2d9bd2")
                size = int(command[command.index("--width") + 1])
                output = Path(command[command.index("--output") + 1])
                output.write_bytes(
                    b"\x89PNG\r\n\x1a\n"
                    + struct.pack("!IIBBBBB", size, size, 8, 6, 0, 0, 0)
                )

            with patch.object(configure_distro.subprocess, "run", side_effect=fake_rsvg_convert):
                configure_distro.configure(config_path, root, logo_data=svg)

            self.assertEqual(
                os_release.read_text(encoding="utf-8"),
                'NAME="cubelinux"\n'
                'ID="cubelinux"\n'
                'PRETTY_NAME="cubelinux desktop"\n'
                'VERSION_ID="44"\n'
                'HOME_URL="https://cubelinux.github.io"\n'
                'LOGO="cubelinux-logo"\n'
                'DESCRIPTION="cubelinux \\"desktop\\""\n',
            )
            logo = root / "usr/share/icons/hicolor/256x256/apps/cubelinux-logo.png"
            small_logo = root / "usr/share/icons/hicolor/64x64/apps/cubelinux-logo.png"
            self.assertTrue(logo.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertTrue(small_logo.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            about = root / "etc/xdg/kcm-about-distrorc"
            self.assertEqual(
                about.read_text(encoding="utf-8"),
                "[General]\n"
                f"LogoPath={logo}\n"
                "Website=https://cubelinux.github.io\n",
            )

    def test_rejects_non_svg_logo(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "distro.json"
            config_path.write_text(
                json.dumps(
                    {
                        "os_release": {
                            "NAME": "cubelinux",
                            "ID": "cubelinux",
                            "PRETTY_NAME": "cubelinux 44",
                            "VERSION_ID": "44",
                            "HOME_URL": "https://cubelinux.github.io",
                            "LOGO": "cubelinux-logo",
                        },
                        "logo": {"url": "https://assets.example.test/icon.svg"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ET.ParseError):
                configure_distro.configure(config_path, root, logo_data=b"not svg")


class ComponentStagingTests(unittest.TestCase):
    def test_stages_component_files_packages_services_and_modes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            component_root = root / "component"
            output = root / "output"
            (component_root / "app/assets").mkdir(parents=True)
            (component_root / "bin").mkdir()
            (component_root / "app/main.py").write_text("print('app')\n", encoding="utf-8")
            (component_root / "app/assets/icon.svg").write_text("<svg />\n", encoding="utf-8")
            (component_root / "bin/demo").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (component_root / "component.toml").write_text(
                'id = "demo"\n'
                'packages = ["demo-runtime"]\n'
                'services = ["demo.service"]\n'
                '\n[[files]]\n'
                'source = "app"\n'
                'destination = "/usr/lib/demo"\n'
                '\n[[files]]\n'
                'source = "bin/demo"\n'
                'destination = "/usr/bin/demo"\n'
                'mode = "0755"\n',
                encoding="utf-8",
            )
            component = {
                "id": "demo",
                "path": "component",
            }

            packages, services = prepare_image.stage_components(
                [component],
                output,
                ["base-package"],
                component_base=root,
            )

            self.assertEqual(packages, ["base-package", "demo-runtime"])
            self.assertEqual(services, {"demo.service"})
            self.assertEqual(
                (output / "rootfs/usr/lib/demo/assets/icon.svg").read_text(encoding="utf-8"),
                "<svg />\n",
            )
            executable = output / "rootfs/usr/bin/demo"
            if os.name != "nt":
                self.assertTrue(stat.S_IMODE(executable.stat().st_mode) & 0o111)

    def test_omitted_component_stages_no_component_assets_or_services(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            packages, services = prepare_image.stage_components(
                [],
                output,
                ["base-package"],
            )

            self.assertEqual(packages, ["base-package"])
            self.assertEqual(services, set())
            self.assertFalse((output / "rootfs").exists())

    def test_rejects_component_destination_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "asset.txt").write_text("asset", encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare_image.copy_entry(
                    root,
                    {"source": "asset.txt", "destination": "/usr/../etc/asset.txt"},
                    "demo",
                    set(),
                    root / "output",
                )


if __name__ == "__main__":
    unittest.main()
