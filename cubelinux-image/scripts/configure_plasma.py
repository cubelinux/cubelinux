#!/usr/bin/env python3
"""Set image-wide KDE defaults and cubelinux launcher branding."""

import shutil
from configparser import ConfigParser
from pathlib import Path


PLASMA_CONFIG = Path("/tmp/cubelinux-plasma")
BREEZE_GLOBALS_SOURCE = PLASMA_CONFIG / "kdeglobals"
BRANDING_SOURCE = PLASMA_CONFIG / "cubelinux-kickoff-branding.py"
AUTOSTART_SOURCE = PLASMA_CONFIG / "cubelinux-kickoff-branding.desktop"
KDE_GLOBALS = Path("/etc/xdg/kdeglobals")
FEDORA_KDE_PROFILE_GLOBALS = Path(
    "/usr/share/kde-settings/kde-profile/default/xdg/kdeglobals"
)
BRANDING_TARGET = Path("/usr/libexec/cubelinux-kickoff-branding.py")
# Keep this image-owned service in KDE's system autostart resource path so the
# kiosk can block user autostart entries without blocking launcher branding.
AUTOSTART_TARGET = Path("/usr/share/autostart/cubelinux-kickoff-branding.desktop")


def set_ini_value(path: Path, section: str, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    section_header = f"[{section}]"
    section_start = next(
        (index for index, line in enumerate(lines) if line.strip() == section_header),
        None,
    )

    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend((section_header, f"{key}={value}"))
    else:
        section_end = next(
            (
                index
                for index in range(section_start + 1, len(lines))
                if lines[index].lstrip().startswith("[")
            ),
            len(lines),
        )
        key_index = next(
            (
                index
                for index in range(section_start + 1, section_end)
                if lines[index].partition("=")[0].strip() == key
            ),
            None,
        )
        if key_index is None:
            lines.insert(section_end, f"{key}={value}")
        else:
            lines[key_index] = f"{key}={value}"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_breeze_default() -> None:
    defaults = ConfigParser(interpolation=None)
    defaults.read(BREEZE_GLOBALS_SOURCE, encoding="utf-8")
    look_and_feel = defaults.get("KDE", "LookAndFeelPackage")

    # Fedora's KDE profile supplies the default copied into new user accounts.
    # /etc/xdg provides the same selection for systems without that profile.
    set_ini_value(
        FEDORA_KDE_PROFILE_GLOBALS,
        "KDE",
        "LookAndFeelPackage",
        look_and_feel,
    )
    set_ini_value(
        KDE_GLOBALS,
        "KDE",
        "LookAndFeelPackage",
        look_and_feel,
    )
    # Keep KAccounts installed for Plasma dependencies, but hide and restrict
    # its Online Accounts module in System Settings until cubelinux enables it.
    set_ini_value(
        KDE_GLOBALS,
        "KDE Control Module Restrictions][$i",
        "kcm_kaccounts",
        "false",
    )


def set_kiosk_restrictions() -> None:
    # The cubelinux KIO build allows only trusted system application entries
    # through this restriction; user-created desktop files remain blocked.
    restrictions = (
        "shell_access",
        "run_command",
        "action/run_command",
        "run_desktop_files",
        "run_executables",
        "plasma-desktop/scripting_console",
        "plasma/plasmashell/unlockedDesktop",
    )
    for restriction in restrictions:
        set_ini_value(
            KDE_GLOBALS,
            "KDE Action Restrictions][$i",
            restriction,
            "false",
        )


def set_kiosk_resource_restrictions() -> None:
    restrictions = (
        "appdata_kdesktop",
        "apps",
        "autostart",
        "data_konsole",
        "services",
        "xdgdata-apps",
    )
    for restriction in restrictions:
        set_ini_value(
            KDE_GLOBALS,
            "KDE Resource Restrictions][$i",
            restriction,
            "false",
        )


def main() -> None:
    for path in (BREEZE_GLOBALS_SOURCE, BRANDING_SOURCE, AUTOSTART_SOURCE):
        if not path.is_file():
            raise RuntimeError(f"Required Plasma branding file is missing: {path}")

    BRANDING_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BRANDING_SOURCE, BRANDING_TARGET)
    BRANDING_TARGET.chmod(0o755)
    AUTOSTART_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(AUTOSTART_SOURCE, AUTOSTART_TARGET)

    set_breeze_default()
    set_kiosk_restrictions()
    set_kiosk_resource_restrictions()


if __name__ == "__main__":
    main()
