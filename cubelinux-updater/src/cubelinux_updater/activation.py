"""Single-instance activation over a per-user local socket."""

import os
from enum import Enum, auto

from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .diagnostics import LOGGER

SESSION_ID = str(os.getuid()) if hasattr(os, "getuid") else os.environ.get("USERNAME", "preview")
SERVER_NAME = f"cubelinux-updater-session-{SESSION_ID}"


class ActivationResult(Enum):
    ACTIVATED = auto()
    NO_SERVER = auto()
    UNRESPONSIVE = auto()


def activate_existing_instance(show_window: bool = True) -> ActivationResult:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(250):
        return ActivationResult.NO_SERVER

    command = (b"show" if show_window else b"background") + b"\n"
    if socket.write(command) != len(command) or not socket.waitForBytesWritten(1000):
        LOGGER.warning("Could not send the activation request to the running updater")
        return ActivationResult.UNRESPONSIVE
    if not socket.waitForReadyRead(5000):
        LOGGER.warning("The running updater did not acknowledge the activation request")
        return ActivationResult.UNRESPONSIVE
    if bytes(socket.readAll()).strip() != b"ok":
        LOGGER.warning("The running updater returned an invalid activation response")
        return ActivationResult.UNRESPONSIVE
    socket.disconnectFromServer()
    return ActivationResult.ACTIVATED


def connect_activation_server(server: QLocalServer, show_window) -> None:
    """Handle requests from subsequent launches of the updater."""
    def handle_connections() -> None:
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)

            def read_command(current=connection) -> None:
                if current.property("cubelinuxActivationHandled"):
                    return
                request = bytes(current.property("cubelinuxActivationBuffer") or b"")
                request += bytes(current.readAll())
                if b"\n" not in request:
                    current.setProperty("cubelinuxActivationBuffer", request)
                    return
                command = request.split(b"\n", 1)[0]
                current.setProperty("cubelinuxActivationHandled", True)
                if command == b"show":
                    show_window()
                elif command != b"background":
                    LOGGER.warning("Ignoring an invalid updater activation request")
                    current.write(b"error")
                    current.disconnectFromServer()
                    return

                current.write(b"ok\n")
                current.flush()
                current.disconnectFromServer()

            connection.readyRead.connect(read_command)
            if connection.bytesAvailable():
                read_command()

    server.newConnection.connect(handle_connections)
    # Handle a request that arrived before the signal was connected.
    handle_connections()
