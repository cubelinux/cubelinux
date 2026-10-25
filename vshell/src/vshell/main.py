"""Launch VShell or operate its Fedora LXC environment."""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from .controller import SetupController
from .lxc_backend import VShellError, enter, initialize, status, stop


def _run_command(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="vshell")
    parser.add_argument("command", choices=("init", "enter", "stop", "status"))
    parsed = parser.parse_args(arguments)
    try:
        if parsed.command == "init":
            initialize()
            return 0
        if parsed.command == "enter":
            return enter()
        if parsed.command == "stop":
            stop()
            return 0
        print(status())
        return 0
    except (VShellError, OSError) as error:
        print(f"vshell: {error}", file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) > 1:
        return _run_command(sys.argv[1:])

    app = QGuiApplication(sys.argv)
    app.setApplicationName("vshell")
    app.setOrganizationName("vshell")

    controller = SetupController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("setupController", controller)
    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
