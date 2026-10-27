#!/usr/bin/python3
"""Set the cubelinux logo on the Plasma launcher once per user."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage


LOGO = Path("/usr/share/icons/hicolor/scalable/apps/cubelinux-logo.svg")
ICON_URL = f"file://{LOGO}"
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
MARKER = CONFIG_HOME / "cubelinux" / "kickoff-logo-configured"
PLASMASHELL = "org.kde.plasmashell"
SCRIPT = f'''\
var logoName = "cubelinux-logo";
var logoPath = "{ICON_URL}";
var changed = 0;
var currentPanels = panels();
for (var panelIndex = 0; panelIndex < currentPanels.length; panelIndex++) {{
    var widgets = currentPanels[panelIndex].widgets();
    for (var widgetIndex = 0; widgetIndex < widgets.length; widgetIndex++) {{
        var applet = widgets[widgetIndex];
        var pluginName = applet.pluginName || applet.type;
        if (["org.kde.plasma.kickoff", "org.kde.plasma.kicker", "org.kde.plasma.simplemenu"].indexOf(pluginName) === -1) {{
            continue;
        }}
        applet.currentConfigGroup = ["Configuration", "General"];
        applet.writeConfig("icon", logoName);
        applet.writeConfig("useCustomButtonImage", true);
        applet.writeConfig("customButtonImage", logoPath);
        changed++;
    }}
}}
changed.toString();
'''


class LauncherBranding:
    def __init__(self) -> None:
        self.app = QCoreApplication(sys.argv)
        self.bus = QDBusConnection.sessionBus()
        self.attempts = 0
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.apply)

    def run(self) -> int:
        if MARKER.exists() or not LOGO.is_file() or not self.bus.isConnected():
            return 0
        self.timer.start()
        QTimer.singleShot(0, self.apply)
        return self.app.exec()

    def apply(self) -> None:
        self.attempts += 1
        if self.attempts > 60:
            self.app.quit()
            return

        if not self.bus.interface().isServiceRegistered(PLASMASHELL):
            return

        message = QDBusMessage.createMethodCall(
            PLASMASHELL,
            "/PlasmaShell",
            "org.kde.PlasmaShell",
            "evaluateScript",
        )
        message.setArguments([SCRIPT])
        reply = self.bus.call(message, QDBus.Block, 3000)
        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            return

        result = reply.arguments()
        if result and str(result[0]).strip() not in ("", "0", "undefined", "null"):
            MARKER.parent.mkdir(parents=True, exist_ok=True)
            MARKER.write_text("cubelinux launcher icon configured\n", encoding="utf-8")
            self.timer.stop()
            self.app.quit()


if __name__ == "__main__":
    raise SystemExit(LauncherBranding().run())
