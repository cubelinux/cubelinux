"""Application entry point."""

import json
import math
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, QProcess, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


SERVER_NAME = "bootc-updater-session"


class UpdateController(QObject):
    statusTextChanged = Signal()
    busyChanged = Signal()
    updateAvailableChanged = Signal()
    updateStagedChanged = Signal()
    imageHistoryChanged = Signal()
    trayStateChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._status_text = "No update check has been run yet."
        self._busy = False
        self._update_available = False
        self._update_staged = False
        self._image_history = []
        self._operation = ""
        self._process_output = ""
        self._process_error_output = ""
        self._tray_state = "idle"
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._read_process_output)
        self._process.readyReadStandardError.connect(self._read_process_error_output)
        self._process.finished.connect(self._operation_finished)
        self._process.errorOccurred.connect(self._process_error)

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=updateAvailableChanged)
    def updateAvailable(self) -> bool:
        return self._update_available

    @Property(bool, notify=updateStagedChanged)
    def updateStaged(self) -> bool:
        return self._update_staged

    @Property("QVariantList", notify=imageHistoryChanged)
    def imageHistory(self) -> list:
        return self._image_history

    def _set_status_text(self, value: str) -> None:
        self._status_text = value
        self.statusTextChanged.emit()

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _set_update_available(self, value: bool) -> None:
        if self._update_available != value:
            self._update_available = value
            self.updateAvailableChanged.emit()

    def _set_update_staged(self, value: bool) -> None:
        if self._update_staged != value:
            self._update_staged = value
            self.updateStagedChanged.emit()

    def _set_tray_state(self, value: str) -> None:
        if self._tray_state != value:
            self._tray_state = value
            self.trayStateChanged.emit(value)

    def _start_command(self, operation: str, arguments: list[str], message: str) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            return
        self._operation = operation
        self._process_output = ""
        self._process_error_output = ""
        self._set_status_text(message)
        self._set_busy(True)
        self._set_tray_state("busy")
        self._process.start("/usr/bin/pkexec", ["/usr/bin/bootc", *arguments])

    @Slot()
    def checkForUpdates(self) -> None:
        self._start_command(
            "check",
            ["upgrade", "--check"],
            "Checking for updates... You may be asked to authenticate.",
        )

    @Slot()
    def stageUpdate(self) -> None:
        if self._update_available:
            self._start_command(
                "stage",
                ["upgrade", "--download-only"],
                "Downloading and staging the update... You may be asked to authenticate.",
            )

    @Slot()
    def applyAndReboot(self) -> None:
        if self._update_staged:
            self._start_command(
                "apply",
                ["upgrade", "--from-downloaded", "--apply"],
                "Applying the staged update and rebooting... You may be asked to authenticate.",
            )

    @Slot()
    def refreshImageHistory(self) -> None:
        self._start_command(
            "history",
            ["status", "--format=json", "--format-version=1"],
            "Loading locally tracked image deployments... You may be asked to authenticate.",
        )

    def _read_process_output(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
        if chunk:
            self._process_output += chunk
            if self._operation == "stage":
                latest_line = chunk.strip().splitlines()
                if latest_line:
                    self._set_status_text(latest_line[-1])

    def _read_process_error_output(self) -> None:
        chunk = bytes(self._process.readAllStandardError()).decode(errors="replace")
        if chunk:
            self._process_error_output += chunk

    def _operation_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._read_process_output()
        self._read_process_error_output()
        self._set_busy(False)
        error = self._process_error_output.strip()
        output = self._process_output.strip()
        operation = self._operation
        self._operation = ""

        if operation == "history":
            if exit_code != 0:
                self._set_tray_state("error")
                self._set_status_text(f"Could not load image history. {error or output}".strip())
                return
            self._load_image_history(output)
            return

        if exit_code != 0:
            self._set_tray_state("error")
            self._set_status_text(f"Operation failed (exit code {exit_code}). {error or output}".strip())
            return

        if operation == "check":
            if "Update available for:" in output:
                self._set_update_available(True)
                self._set_tray_state("available")
                self._set_status_text("An update is available. Staging downloads it but does not reboot.")
            elif "Staged update present, not changed" in output:
                self._set_update_available(False)
                self._set_update_staged(True)
                self._set_tray_state("staged")
                self._set_status_text("No newer update found. An update may already be staged.")
            elif any(marker in output for marker in ("No changes in:", "No update available.")):
                self._set_update_available(False)
                self._set_tray_state("idle")
                self._set_status_text("Your system is up to date.")
            else:
                self._set_tray_state("error")
                self._set_status_text(f"Check completed, but the result was unclear. {output}".strip())
        elif operation == "stage":
            self._set_update_available(False)
            self._set_update_staged(True)
            self._set_tray_state("staged")
            self._set_status_text("Update downloaded and staged. Apply it when you are ready to reboot.")
        elif operation == "apply":
            self._set_update_staged(False)
            self._set_tray_state("rebooting")
            self._set_status_text("The system is rebooting to apply the update.")

    def _load_image_history(self, output: str) -> None:
        try:
            document = json.loads(output)
            status = document.get("status", {})
            entries = []
            for key, label in (
                ("staged", "Staged"),
                ("booted", "Current"),
                ("rollback", "Rollback"),
                ("otherDeployments", "Other deployment"),
                ("other_deployments", "Other deployment"),
            ):
                deployments = status.get(key)
                if deployments is None:
                    continue
                if isinstance(deployments, dict):
                    deployments = [deployments]
                for deployment in deployments:
                    image_info = deployment.get("image") or {}
                    source = image_info.get("image") or {}
                    entries.append({
                        "role": label,
                        "image": source.get("image", "Unknown image"),
                        "version": image_info.get("version") or "Version unavailable",
                        "digest": image_info.get("imageDigest") or "Digest unavailable",
                    })
            self._image_history = entries
            self.imageHistoryChanged.emit()
            staged = status.get("staged")
            self._set_update_staged(staged is not None)
            if staged is not None:
                self._set_tray_state("staged")
            else:
                self._set_tray_state("available" if self._update_available else "idle")
            self._set_status_text(
                f"Loaded {len(entries)} deployment(s) tracked locally by bootc."
            )
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            self._set_status_text(f"Could not read bootc status: {exc}")

    def _process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._operation = ""
            self._set_busy(False)
            self._set_tray_state("error")
            self._set_status_text("Could not start pkexec. Check that Polkit is installed.")


def create_spinner_icons(count: int = 8) -> list[QIcon]:
    icons = []
    size = 24
    center = size / 2
    radius = 7
    for frame in range(count):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for dot in range(count):
            age = (dot - frame) % count
            alpha = int(55 + (200 * (count - age) / count))
            pen = QPen(QColor(50, 125, 220, alpha), 2.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            angle = 2 * math.pi * dot / count - math.pi / 2
            x = center + radius * math.cos(angle)
            y = center + radius * math.sin(angle)
            painter.drawPoint(int(x), int(y))
        painter.end()
        icons.append(QIcon(pixmap))
    return icons


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
    update_controller = UpdateController()
    engine.rootContext().setContextProperty("updateController", update_controller)
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

    spinner_icons = create_spinner_icons()
    tray_icons = {
        "idle": icon,
        "available": QIcon.fromTheme("software-update-available", icon),
        "staged": QIcon.fromTheme("system-reboot", icon),
        "rebooting": QIcon.fromTheme("system-reboot", icon),
        "error": QIcon.fromTheme("dialog-error", icon),
    }
    spinner_timer = QTimer(app)
    spinner_timer.setInterval(120)
    spinner_frame = 0

    def advance_spinner() -> None:
        nonlocal spinner_frame
        tray.setIcon(spinner_icons[spinner_frame])
        spinner_frame = (spinner_frame + 1) % len(spinner_icons)

    def set_tray_state(state: str) -> None:
        if state == "busy":
            tray.setToolTip("bootc Updater: working")
            spinner_timer.start()
            return

        spinner_timer.stop()
        tray.setIcon(tray_icons.get(state, icon))
        tooltip = {
            "available": "bootc Updater: update available",
            "staged": "bootc Updater: update staged; reboot to apply",
            "rebooting": "bootc Updater: rebooting to apply update",
            "error": "bootc Updater: operation failed",
            "idle": "bootc Updater",
        }
        tray.setToolTip(tooltip.get(state, "bootc Updater"))

    spinner_timer.timeout.connect(advance_spinner)
    update_controller.trayStateChanged.connect(set_tray_state)

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

    if not start_in_background:
        show_window()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
