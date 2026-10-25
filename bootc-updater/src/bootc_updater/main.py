"""Application entry point."""

import sys
from pathlib import Path

from PySide6.QtCore import QLocalServer, QLocalSocket
from PySide6.QtGui import QAction, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


SERVER_NAME = "bootc-updater-session"


def activate_existing_instance() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(250):
        return False

    socket.write(b"show")
    socket.waitForBytesWritten(1000)
    socket.disconnectFromServer()
    return True


def main() -> int:
    start_in_background = "--background" in sys.argv
    arguments = [argument for argument in sys.argv if argument != "--background"]

    app = QApplication(arguments)
    app.setApplicationName("bootc-updater")
    app.setOrganizationName("bootc-updater")
    app.setQuitOnLastWindowClosed(False)

    if activate_existing_instance():
        return 0

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        return 1

    engine = QQmlApplicationEngine()
    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(qml_file)
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]

    def show_window() -> None:
        window.show()
        window.raise_()
        window.requestActivate()

    def handle_connections() -> None:
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()

            def read_command(current=connection) -> None:
                command = bytes(current.readAll())
                current.disconnectFromServer()
                current.deleteLater()
                if command == b"show":
                    show_window()

            connection.readyRead.connect(read_command)

    server.newConnection.connect(handle_connections)

    icon = QIcon.fromTheme("system-software-update")
    app.setWindowIcon(icon)
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("bootc Updater")

    menu = QMenu()
    open_action = QAction("Open bootc Updater", menu)
    open_action.triggered.connect(show_window)
    menu.addAction(open_action)
    tray.setContextMenu(menu)

    def tray_activated(reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            show_window()

    tray.activated.connect(tray_activated)
    tray.show()

    if not start_in_background or not QSystemTrayIcon.isSystemTrayAvailable():
        show_window()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
