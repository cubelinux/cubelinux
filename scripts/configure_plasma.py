#!/usr/bin/env python3
"""Set image-wide KDE defaults and customize the Plasma Setup pages."""

import json
import shutil
from configparser import ConfigParser
from pathlib import Path


ROOT = Path("/usr/share/plasma/packages")
ACCOUNT = ROOT / "org.kde.plasmasetup.account"
WIFI = ROOT / "org.kde.plasmasetup.wifi"
ACCOUNT_QML = ACCOUNT / "contents/ui/main.qml"
ACCOUNT_METADATA = ACCOUNT / "metadata.json"
WIFI_METADATA = WIFI / "metadata.json"
WIFI_QML = WIFI / "contents/ui/main.qml"
SOURCE_QML = Path("/tmp/cubelinux-setup/account-main.qml")
PLASMA_CONFIG = Path("/tmp/cubelinux-plasma")
BREEZE_GLOBALS_SOURCE = PLASMA_CONFIG / "kdeglobals"
BRANDING_SOURCE = PLASMA_CONFIG / "cubelinux-kickoff-branding.py"
AUTOSTART_SOURCE = PLASMA_CONFIG / "cubelinux-kickoff-branding.desktop"
SETUP_CONFIG = Path("/etc/xdg/plasmasetuprc")
KDE_GLOBALS = Path("/etc/xdg/kdeglobals")
FEDORA_KDE_PROFILE_GLOBALS = Path(
    "/usr/share/kde-settings/kde-profile/default/xdg/kdeglobals"
)
BRANDING_TARGET = Path("/usr/libexec/cubelinux-kickoff-branding.py")
AUTOSTART_TARGET = Path("/etc/xdg/autostart/cubelinux-kickoff-branding.desktop")


def set_weight(path: Path, expected_id: str, weight: int) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    plugin = data.get("KPlugin", {})
    if plugin.get("Id") != expected_id:
        raise RuntimeError(f"Unexpected Plasma Setup module in {path}: {plugin.get('Id')!r}")
    data["X-KDE-Weight"] = weight
    path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


def set_ini_value(path: Path, section: str, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
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


def add_wifi_guidance_and_refresh() -> None:
    qml = WIFI_QML.read_text(encoding="utf-8")
    available_marker = "available: availableDevices.wirelessDeviceAvailable"
    body_marker = """        ColumnLayout {
            Layout.alignment: Qt.AlignCenter

            Label {
                id: titleLabel"""
    replacement = """        ColumnLayout {
            Layout.alignment: Qt.AlignCenter

            Label {
                Layout.leftMargin: Kirigami.Units.gridUnit
                Layout.rightMargin: Kirigami.Units.gridUnit
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                color: Kirigami.Theme.disabledTextColor
                text: availableDevices.wirelessDeviceAvailable
                    ? i18n(\"Can't find your network? Refresh the list, connect Ethernet, or continue offline.\")
                    : i18n(\"Wi-Fi isn't available on this device. Connect Ethernet or continue offline.\")
            }

            Button {
                Layout.alignment: Qt.AlignHCenter
                text: i18n(\"Refresh Wi-Fi networks\")
                enabled: availableDevices.wirelessDeviceAvailable
                onClicked: handler.requestScan()
            }

            Label {
                id: titleLabel"""
    if available_marker in qml and body_marker in qml:
        qml = qml.replace(available_marker, "available: true", 1)
        qml = qml.replace(body_marker, replacement, 1)
    elif "Refresh Wi-Fi networks" not in qml:
        raise RuntimeError("Installed Plasma Setup Wi-Fi page has an unexpected QML layout")
    WIFI_QML.write_text(qml, encoding="utf-8")


def main() -> None:
    for path in (
        ACCOUNT_QML,
        ACCOUNT_METADATA,
        WIFI_METADATA,
        WIFI_QML,
        SOURCE_QML,
        BREEZE_GLOBALS_SOURCE,
        BRANDING_SOURCE,
        AUTOSTART_SOURCE,
    ):
        if not path.is_file():
            raise RuntimeError(f"Required Plasma Setup package file is missing: {path}")

    account_metadata = json.loads(ACCOUNT_METADATA.read_text(encoding="utf-8"))
    if account_metadata.get("KPlugin", {}).get("Id") != "org.kde.plasmasetup.account":
        raise RuntimeError("Installed Plasma Setup account package is not the expected KDE module")

    shutil.copyfile(SOURCE_QML, ACCOUNT_QML)
    set_weight(WIFI_METADATA, "org.kde.plasmasetup.wifi", -10)
    add_wifi_guidance_and_refresh()

    BRANDING_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BRANDING_SOURCE, BRANDING_TARGET)
    BRANDING_TARGET.chmod(0o755)
    AUTOSTART_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(AUTOSTART_SOURCE, AUTOSTART_TARGET)

    set_breeze_default()

    SETUP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SETUP_CONFIG.write_text("[Accounts]\nUserGroups=wheel\n", encoding="utf-8")


if __name__ == "__main__":
    main()
