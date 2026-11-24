#!/usr/bin/env python3
"""Open the recovery UI in a window without touching disks."""

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

class PreviewController(QObject):
    @Property(bool, constant=True)
    def preview(self) -> bool:
        return True


app = QGuiApplication(sys.argv)
app.setApplicationName("cubelinux recovery preview")
engine = QQmlApplicationEngine()
controller = PreviewController()
engine.rootContext().setContextProperty("recoveryController", controller)
engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
if not engine.rootObjects():
    sys.exit(1)
sys.exit(app.exec())
