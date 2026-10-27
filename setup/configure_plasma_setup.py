#!/usr/bin/env python3
"""Apply the cubelinux Plasma Setup QML override and test account policy."""

import json
import shutil
from pathlib import Path


ROOT = Path("/usr/share/plasma/packages")
ACCOUNT = ROOT / "org.kde.plasmasetup.account"
WIFI = ROOT / "org.kde.plasmasetup.wifi"
ACCOUNT_QML = ACCOUNT / "contents/ui/main.qml"
ACCOUNT_METADATA = ACCOUNT / "metadata.json"
WIFI_METADATA = WIFI / "metadata.json"
WIFI_QML = WIFI / "contents/ui/main.qml"
SOURCE_QML = Path("/tmp/cubelinux-setup/account-main.qml")
SETUP_CONFIG = Path("/etc/xdg/plasma-setup.conf")


def set_weight(path: Path, expected_id: str, weight: int) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    plugin = data.get("KPlugin", {})
    if plugin.get("Id") != expected_id:
        raise RuntimeError(f"Unexpected Plasma Setup module in {path}: {plugin.get('Id')!r}")
    data["X-KDE-Weight"] = weight
    path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")


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
    for path in (ACCOUNT_QML, ACCOUNT_METADATA, WIFI_METADATA, WIFI_QML):
        if not path.is_file():
            raise RuntimeError(f"Required Plasma Setup package file is missing: {path}")

    account_metadata = json.loads(ACCOUNT_METADATA.read_text(encoding="utf-8"))
    if account_metadata.get("KPlugin", {}).get("Id") != "org.kde.plasmasetup.account":
        raise RuntimeError("Installed Plasma Setup account package is not the expected KDE module")

    shutil.copyfile(SOURCE_QML, ACCOUNT_QML)
    set_weight(WIFI_METADATA, "org.kde.plasmasetup.wifi", -10)
    add_wifi_guidance_and_refresh()

    SETUP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SETUP_CONFIG.write_text("[Accounts]\nUserGroups=wheel\n", encoding="utf-8")


if __name__ == "__main__":
    main()
