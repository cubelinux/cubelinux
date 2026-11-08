#!/usr/bin/python3
"""Brand the Plasma launcher and pin Dolphin to the taskbar once per user."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage


LOGO = Path("/usr/share/icons/hicolor/64x64/apps/cubelinux-logo.png")
ICON_URL = f"file://{LOGO}"
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
MARKER_DIR = CONFIG_HOME / "cubelinux"
LOGO_MARKER = MARKER_DIR / "kickoff-logo-v2-configured"
DOLPHIN_PIN_MARKER = MARKER_DIR / "taskbar-launchers-v1-configured"
PLASMASHELL = "org.kde.plasmashell"
SCRIPT_TEMPLATE = f'''\
var logoName = "cubelinux-logo";
var logoPath = "{ICON_URL}";
var configureLogo = __CONFIGURE_LOGO__;
var logoFound = 0;
var taskManagersFound = 0;
var dolphinLauncher = "applications:org.kde.dolphin.desktop";
var currentPanels = panels();
for (var panelIndex = 0; panelIndex < currentPanels.length; panelIndex++) {{
    var widgets = currentPanels[panelIndex].widgets();
    for (var widgetIndex = 0; widgetIndex < widgets.length; widgetIndex++) {{
        var applet = widgets[widgetIndex];
        var pluginName = applet.pluginName || applet.type;
        if (configureLogo && ["org.kde.plasma.kickoff", "org.kde.plasma.kicker", "org.kde.plasma.simplemenu"].indexOf(pluginName) !== -1) {{
            applet.currentConfigGroup = ["Configuration", "General"];
            applet.writeConfig("icon", logoName);
            applet.writeConfig("useCustomButtonImage", true);
            applet.writeConfig("customButtonImage", logoPath);
            logoFound++;
        }}

        if (["org.kde.plasma.icontasks", "org.kde.plasma.taskmanager"].indexOf(pluginName) !== -1) {{
            taskManagersFound++;
            applet.currentConfigGroup = ["General"];
            var launcherText = String(applet.readConfig("launchers", ""));
            var launchers = launcherText ? launcherText.split(",") : [];
            var cleanedLaunchers = [];
            var hasDolphin = false;
            var launchersChanged = false;

            for (var launcherIndex = 0; launcherIndex < launchers.length; launcherIndex++) {{
                var launcher = launchers[launcherIndex].trim();
                if ([
                    "applications:org.kde.discover.desktop",
                    "org.kde.discover.desktop",
                    "applications:plasma-discover.desktop",
                    "plasma-discover.desktop"
                ].indexOf(launcher) !== -1) {{
                    launchersChanged = true;
                    continue;
                }}

                if (launcher === "preferred://filemanager") {{
                    cleanedLaunchers.push(dolphinLauncher);
                    hasDolphin = true;
                    launchersChanged = true;
                }} else if (launcher === dolphinLauncher) {{
                    cleanedLaunchers.push(launcher);
                    hasDolphin = true;
                }} else {{
                    cleanedLaunchers.push(launchers[launcherIndex]);
                }}
            }}

            if (!hasDolphin) {{
                cleanedLaunchers.push(dolphinLauncher);
                launchersChanged = true;
            }}

            if (launchersChanged) {{
                applet.writeConfig("launchers", cleanedLaunchers.join(","));
                applet.reloadConfig();
            }}
        }}
    }}
}}
"logo=" + logoFound + ";taskmanagers=" + taskManagersFound;
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
        if (
            (LOGO_MARKER.exists() and DOLPHIN_PIN_MARKER.exists())
            or not self.bus.isConnected()
        ):
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
        script = SCRIPT_TEMPLATE.replace(
            "__CONFIGURE_LOGO__",
            "true" if not LOGO_MARKER.exists() and LOGO.is_file() else "false",
        )
        message.setArguments([script])
        reply = self.bus.call(message, QDBus.Block, 3000)
        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            return

        result = reply.arguments()
        if not result:
            return

        status = str(result[0]).strip()
        values = dict(
            part.split("=", 1)
            for part in status.split(";")
            if "=" in part
        )
        if values.get("logo", "0") != "0" and LOGO.is_file():
            MARKER_DIR.mkdir(parents=True, exist_ok=True)
            LOGO_MARKER.write_text("cubelinux launcher icon configured\n", encoding="utf-8")
        if values.get("taskmanagers", "0") != "0":
            MARKER_DIR.mkdir(parents=True, exist_ok=True)
            DOLPHIN_PIN_MARKER.write_text("Dolphin pinned to the Plasma taskbar\n", encoding="utf-8")

        if LOGO_MARKER.exists() and DOLPHIN_PIN_MARKER.exists():
            self.timer.stop()
            self.app.quit()


if __name__ == "__main__":
    raise SystemExit(LauncherBranding().run())
