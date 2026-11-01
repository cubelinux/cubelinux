"""UI-only preview launcher for updater development."""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

from .constants import PREVIEW_STATES
from .controller import UpdateController
from .diagnostics import LOGGER, _qt_message_handler
from .version import __version__


def _preview_state_from_arguments(arguments: list[str]) -> str | None:
    for argument in arguments:
        if argument == "--preview":
            return "available"
        if argument.startswith("--preview="):
            return argument.partition("=")[2] or "available"
    return None


def run_preview(preview_state: str, arguments: list[str]) -> int:
    """Run the QML interface with simulated data and no system operations."""
    logging.basicConfig(level=logging.INFO)
    LOGGER.info("Starting UI-only preview in the %s state", preview_state)
    qInstallMessageHandler(_qt_message_handler)

    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        style = "Fusion" if sys.platform == "win32" else "org.kde.desktop"
        QQuickStyle.setStyle(style)

    app = QApplication(arguments)
    app.setApplicationName("cubelinux-updater-preview")
    app.setOrganizationName("cubelinux")

    engine = QQmlApplicationEngine()

    def log_qml_warnings(warnings) -> None:
        for warning in warnings:
            LOGGER.error("QML: %s", warning.toString())

    engine.warnings.connect(log_qml_warnings)
    update_controller = UpdateController(preview_state=preview_state)
    update_controller.setParent(app)
    engine.rootContext().setContextProperty("updateController", update_controller)
    engine.rootContext().setContextProperty("softwareVersion", __version__)
    engine.rootContext().setContextProperty("previewMode", True)
    qml_name = "Preview.qml" if sys.platform == "win32" else "Main.qml"
    qml_file = Path(__file__).parent / "qml" / qml_name
    engine.load(str(qml_file))
    if not engine.rootObjects():
        QMessageBox.critical(
            None,
            "Updater preview could not start",
            "The QML interface failed to load. Confirm that the Qt Quick and KDE Kirigami QML modules are installed.",
        )
        return 1

    window = engine.rootObjects()[0]
    window.show()
    return app.exec()
