"""Runtime component information shown in the About page."""

import json
import platform
import subprocess

import PySide6
from PySide6.QtCore import __version__ as qt_build_version, qVersion


def _about_components_json() -> str:
    """Return installed framework and host versions for the About page."""
    try:
        os_release = platform.freedesktop_os_release()
    except (AttributeError, OSError):
        os_release = {}

    def package_version(package: str) -> str:
        try:
            result = subprocess.run(
                ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package],
                capture_output=True,
                check=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip()

    components = [
        {
            "name": "PySide6",
            "description": "Qt for Python binding",
            "version": PySide6.__version__,
        },
        {
            "name": "Qt (build)",
            "description": "Qt version used to build PySide6",
            "version": qt_build_version,
        },
        {
            "name": "Qt (runtime)",
            "description": "Qt library version in use",
            "version": qVersion(),
        },
        {
            "name": "KDE Frameworks (Kirigami)",
            "description": "Installed Kirigami package",
            "version": package_version("kf6-kirigami"),
        },
        {
            "name": "KDE Plasma",
            "description": "Installed Plasma workspace package",
            "version": package_version("plasma-workspace"),
        },
        {
            "name": "Python",
            "description": "Python runtime",
            "version": platform.python_version(),
        },
        {
            "name": "Operating system",
            "description": os_release.get("PRETTY_NAME", os_release.get("NAME", "Linux")),
            "version": os_release.get("VERSION_ID", ""),
        },
        {"name": "Kernel", "description": "Linux kernel", "version": platform.release()},
        {
            "name": "Architecture",
            "description": "System architecture",
            "version": platform.machine(),
        },
    ]
    available_components = [component for component in components if component["version"]]
    return json.dumps(available_components, ensure_ascii=False)
