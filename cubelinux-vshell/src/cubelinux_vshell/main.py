"""Launch Linux Subsystem or operate its LXC environments."""

import argparse
import json
import os
import platform
import pwd
import shutil
import subprocess
import sys
from pathlib import Path

import PySide6
from PySide6.QtCore import (
    QLockFile,
    QStandardPaths,
    QUrl,
    __version__ as qt_build_version,
    qVersion,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from .controller import SetupController
from .lxc_backend import (
    CONTAINER_NAME,
    FEDORA_CONTAINER_NAME,
    LEGACY_CONTAINER_NAME,
    _LXC_CONTAINER_NAMES,
    VShellError,
    enter,
    install_shutdown_hook,
    is_initialized,
    status,
    stop,
)
from .lxc_apps import launch_app
from .lxc_setup import initialize
from .app_discovery import watch_apps
from .version import __version__

_USER_ID = os.getuid() if hasattr(os, "getuid") else os.getpid()
_SERVER_NAME = f"cubelinux-vshell-setup-{_USER_ID}"


def _is_plasma_setup_account() -> bool:
    """Avoid starting user-scoped VShell services in Plasma Setup's temporary session."""
    try:
        return pwd.getpwuid(os.getuid()).pw_name == "plasma-setup"
    except (KeyError, OSError):
        return False


def _about_components_json() -> str:
    """Return installed framework and host versions for the About page."""
    try:
        os_release = platform.freedesktop_os_release()
    except (AttributeError, OSError):
        os_release = {}

    def package_version(package: str) -> str:
        try:
            result = subprocess.run(
                ["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package],
                capture_output=True,
                check=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip()

    components = [
        {
            "name": "PySide6",
            "description": "Qt for Python binding",
            "version": PySide6.__version__,
        },
        {
            "name": "Qt (build)",
            "description": "Qt version used to build PySide6",
            "version": qt_build_version,
        },
        {
            "name": "Qt (runtime)",
            "description": "Qt library version in use",
            "version": qVersion(),
        },
        {
            "name": "KDE Frameworks (Kirigami)",
            "description": "Installed Kirigami package",
            "version": package_version("kf6-kirigami"),
        },
        {
            "name": "KDE Plasma",
            "description": "Installed Plasma workspace package",
            "version": package_version("plasma-workspace"),
        },
        {
            "name": "Python",
            "description": "Python runtime",
            "version": platform.python_version(),
        },
        {
            "name": "Operating system",
            "description": os_release.get("PRETTY_NAME", os_release.get("NAME", "Linux")),
            "version": os_release.get("VERSION_ID", ""),
        },
        {"name": "Kernel", "description": "Linux kernel", "version": platform.release()},
        {
            "name": "Architecture",
            "description": "System architecture",
            "version": platform.machine(),
        },
    ]
    available_components = [component for component in components if component["version"]]
    return json.dumps(available_components, ensure_ascii=False)


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


def _launch_detached(command: list[str]) -> None:
    try:
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as error:
        raise VShellError(f"Could not start {command[0]}: {error}") from error


def _open_terminal(container_name: str = CONTAINER_NAME) -> None:
    if container_name == LEGACY_CONTAINER_NAME:
        raise VShellError(
            "The previous VShell container is being migrated. Open the cubelinux Runtime terminal after setup finishes."
        )
    if not is_initialized(container_name):
        if container_name != CONTAINER_NAME:
            raise VShellError(
                "Create the Fedora environment in Linux Subsystem before opening its terminal."
            )
        executable = shutil.which("cubelinux-vshell")
        command = (
            [executable]
            if executable
            else [sys.executable, "-m", "cubelinux_vshell.main"]
        )
    else:
        executable = shutil.which("konsole")
        if not executable:
            raise VShellError("Konsole is not installed on this system.")
        profile = "VShell" if container_name == CONTAINER_NAME else "Fedora"
        command = [executable, "--profile", profile]
    _launch_detached(command)


def _run_command(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cubelinux-vshell")
    parser.add_argument(
        "command",
        choices=(
            "init",
            "enter",
            "open-terminal",
            "stop",
            "status",
            "activate-if-busy",
            "watch-apps",
            "launch-app",
        ),
    )
    parser.add_argument("--container", choices=_LXC_CONTAINER_NAMES, default=CONTAINER_NAME)
    parser.add_argument("app", nargs="?")
    parser.add_argument("files", nargs="*")
    parsed = parser.parse_args(arguments)
    try:
        if parsed.command == "init":
            if parsed.container != CONTAINER_NAME:
                raise VShellError("Only cubelinux Runtime initialization is available right now.")
            initialize()
            return 0
        if parsed.command == "enter":
            return enter(parsed.container)
        if parsed.command == "open-terminal":
            _open_terminal(parsed.container)
            return 0
        if parsed.command == "stop":
            stop(parsed.container)
            return 0
        if parsed.command == "activate-if-busy":
            return 0 if _request_setup_status() == "busy" else 1
        if parsed.command == "watch-apps":
            watch_apps()
            return 0
        if parsed.command == "launch-app":
            if not parsed.app:
                parser.error("launch-app requires a container desktop application identifier")
            return launch_app(parsed.app, parsed.files, parsed.container)
        print(status(parsed.container))
        return 0
    except (VShellError, OSError) as error:
        print(f"cubelinux-vshell: {error}", file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] in ("init", "watch-apps") and _is_plasma_setup_account():
            return 0
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

    app = QApplication(sys.argv)
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
    engine.rootContext().setContextProperty("aboutComponentsJson", _about_components_json())
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
