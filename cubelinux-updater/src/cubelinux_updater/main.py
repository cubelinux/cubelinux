"""Updater application entry point."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtNetwork import QLocalServer
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMessageBox

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cubelinux_updater.activation import (
    SERVER_NAME,
    activate_existing_instance,
    connect_activation_server,
)
from cubelinux_updater.constants import PREVIEW_STATES
from cubelinux_updater.controller import UpdateController
from cubelinux_updater.diagnostics import LOGGER, _qt_message_handler, configure_logging
from cubelinux_updater.preview import _preview_state_from_arguments, run_preview
from cubelinux_updater.system_info import _about_components_json
from cubelinux_updater.tray import configure_tray
from cubelinux_updater.version import __version__


def main() -> int:
    arguments = sys.argv[1:]
    preview_state = _preview_state_from_arguments(arguments)
    if preview_state is not None:
        if preview_state not in PREVIEW_STATES:
            choices = ", ".join(PREVIEW_STATES)
            print(
                f"Unknown preview state '{preview_state}'. Choose one of: {choices}.",
                file=sys.stderr,
            )
            return 2
        qt_arguments = [
            sys.argv[0],
            *(argument for argument in arguments if not argument.startswith("--preview")),
        ]
        return run_preview(preview_state, qt_arguments)

    # KDE's Python binding for KStatusNotifierItem provides the Plasma-native
    # StatusNotifierItem protocol. Import it only for the Linux app so the
    # UI-only Windows preview remains usable without KDE libraries.
    try:
        from KStatusNotifierItem import KStatusNotifierItem
    except ImportError:
        print(
            "cubelinux-updater: KDE's python3-kf6-kstatusnotifieritem binding is required.",
            file=sys.stderr,
        )
        return 1

    configure_logging()
    LOGGER.info("Using updater activation socket %s", SERVER_NAME)
    qInstallMessageHandler(_qt_message_handler)
    start_in_background = "--background" in sys.argv
    arguments = [argument for argument in sys.argv if argument != "--background"]

    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("org.kde.desktop")

    app = QApplication(arguments)
    app.setApplicationName("cubelinux-updater")
    app.setOrganizationName("cubelinux")
    app.setQuitOnLastWindowClosed(False)
    sys.excepthook = lambda exception_type, exception, traceback: LOGGER.critical(
        "Uncaught application exception",
        exc_info=(exception_type, exception, traceback),
    )

    if activate_existing_instance(show_window=not start_in_background):
        LOGGER.info("Activated the existing updater process")
        return 0

    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        if activate_existing_instance(show_window=not start_in_background):
            LOGGER.info("Activated the updater after a simultaneous startup")
            return 0

        error = server.errorString()
        LOGGER.error("Could not listen on the session socket: %s", error)
        QMessageBox.critical(
            None,
            "Updater could not start",
            f"Another updater instance may be starting, or its session socket is unavailable.\n\n{error}\n\nCheck ~/.local/state/cubelinux-updater/cubelinux-updater.log for details.",
        )
        return 1

    engine = QQmlApplicationEngine()

    def log_qml_warnings(warnings) -> None:
        for warning in warnings:
            LOGGER.error("QML: %s", warning.toString())

    engine.warnings.connect(log_qml_warnings)
    update_controller = UpdateController()
    engine.rootContext().setContextProperty("updateController", update_controller)
    engine.rootContext().setContextProperty("softwareVersion", __version__)
    engine.rootContext().setContextProperty("aboutComponentsJson", _about_components_json())
    engine.rootContext().setContextProperty("previewMode", False)
    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(str(qml_file))
    if not engine.rootObjects():
        LOGGER.error("QML interface failed to load from %s", qml_file)
        QMessageBox.critical(
            None,
            "Updater could not start",
            "The updater interface failed to load. Check "
            "~/.local/state/cubelinux-updater/cubelinux-updater.log for details.",
        )
        return 1

    window = engine.rootObjects()[0]

    def show_window() -> None:
        window.show()
        window.raise_()
        window.requestActivate()

    connect_activation_server(server, show_window)

    configure_tray(app, update_controller, show_window, KStatusNotifierItem)

    if not start_in_background:
        show_window()

    update_controller.startAutomaticChecks()

    LOGGER.info("Updater started successfully%s", " in background" if start_in_background else "")
    app.aboutToQuit.connect(lambda: LOGGER.info("Updater is shutting down"))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
