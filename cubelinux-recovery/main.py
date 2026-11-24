#!/usr/bin/python3
"""Launch the cubelinux Recovery interface."""

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class RecoveryController(QObject):
    @Property(bool, constant=True)
    def preview(self) -> bool:
        return False


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("cubelinux Recovery")
    engine = QQmlApplicationEngine()
    controller = RecoveryController()
    engine.rootContext().setContextProperty("recoveryController", controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
