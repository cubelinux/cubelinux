"""Launch Virtual Shell or operate its Fedora LXC environment."""

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine

from .controller import SetupController
from .lxc_backend import VShellError, enter, install_shutdown_hook, status, stop
from .lxc_apps import launch_app
from .lxc_setup import initialize
from .app_discovery import watch_apps
from .version import __version__

_USER_ID = os.getuid() if hasattr(os, "getuid") else os.getpid()
_SERVER_NAME = f"cubelinux-vshell-setup-{_USER_ID}"


def _notify_existing_setup(timeout_ms: int = 100) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(_SERVER_NAME)
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(b"show\n")
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    return True


def _request_setup_status(timeout_ms: int = 3000) -> str | None:
    socket = QLocalSocket()
    socket.connectToServer(_SERVER_NAME)
    if not socket.waitForConnected(timeout_ms):
        return None
    socket.write(b"activate-if-busy\n")
    socket.flush()
    if not socket.waitForReadyRead(timeout_ms):
        return None
    return bytes(socket.readAll()).decode("ascii", errors="replace").strip()


def _claim_setup_instance(lock: QLockFile) -> bool:
    if lock.tryLock(0):
        return True

    # The owner may still be creating its local server. Keep checking for it
    # while also taking over if that process exits during startup.
    for _ in range(20):
        if _notify_existing_setup():
            return False
        if lock.tryLock(0):
            return True
        if lock.error() != QLockFile.LockFailedError:
            raise OSError(f"could not create the setup window lock: {lock.error()}")
    return False


def _run_command(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cubelinux-vshell")
    parser.add_argument("command", choices=("init", "enter", "stop", "status", "activate-if-busy", "watch-apps", "launch-app"))
    parser.add_argument("app", nargs="?")
    parser.add_argument("files", nargs="*")
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
        if parsed.command == "activate-if-busy":
            return 0 if _request_setup_status() == "busy" else 1
        if parsed.command == "watch-apps":
            watch_apps()
            return 0
        if parsed.command == "launch-app":
            if not parsed.app:
                parser.error("launch-app requires a Fedora desktop file path")
            return launch_app(parsed.app, parsed.files)
        print(status())
        return 0
    except (VShellError, OSError) as error:
        print(f"cubelinux-vshell: {error}", file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] not in ("watch-apps", "launch-app"):
            try:
                install_shutdown_hook()
            except VShellError as error:
                print(f"cubelinux-vshell: {error}", file=sys.stderr)
        return _run_command(sys.argv[1:])

    try:
        install_shutdown_hook()
    except VShellError as error:
        print(f"cubelinux-vshell: {error}", file=sys.stderr)

    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("org.kde.desktop")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("cubelinux-vshell")
    app.setOrganizationName("cubelinux")
    app.setQuitOnLastWindowClosed(False)

    runtime_dir = QStandardPaths.writableLocation(QStandardPaths.RuntimeLocation)
    lock_path = Path(runtime_dir or QStandardPaths.writableLocation(QStandardPaths.TempLocation))
    lock = QLockFile(str(lock_path / f"{_SERVER_NAME}.lock"))
    lock.setStaleLockTime(0)
    try:
        owns_instance = _claim_setup_instance(lock)
    except OSError as error:
        print(f"cubelinux-vshell: {error}", file=sys.stderr)
        return 1
    if not owns_instance:
        return 0

    # Only the process holding the per-user lock may remove a stale socket or
    # start the setup server.
    QLocalServer.removeServer(_SERVER_NAME)
    server = QLocalServer()
    if not server.listen(_SERVER_NAME):
        print(f"cubelinux-vshell: could not create the setup window socket: {server.errorString()}", file=sys.stderr)
        return 1

    controller = SetupController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("setupController", controller)
    engine.rootContext().setContextProperty("softwareVersion", __version__)
    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]

    def activate_window() -> None:
        window.setProperty("closeAfterSetup", False)
        window.showNormal()
        window.raise_()
        window.requestActivate()

    def handle_request(connection) -> None:
        if not connection.canReadLine():
            return
        request = bytes(connection.readLine()).decode("ascii", errors="replace").strip()
        if request == "show":
            activate_window()
            response = "shown"
        elif request == "activate-if-busy":
            if controller.busy:
                activate_window()
                response = "busy"
            else:
                response = "idle"
        else:
            response = "unknown"
        connection.write(f"{response}\n".encode("ascii"))
        connection.flush()
        connection.disconnectFromServer()

    def handle_activation() -> None:
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            connection.readyRead.connect(lambda client=connection: handle_request(client))
            if connection.canReadLine():
                handle_request(connection)

    server.newConnection.connect(handle_activation)
    handle_activation()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
