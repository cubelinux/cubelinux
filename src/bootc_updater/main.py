"""Application entry point."""

import json
import logging
import math
import re
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import (
    QObject,
    Property,
    QProcess,
    QTimer,
    Qt,
    QtMsgType,
    Signal,
    Slot,
    qInstallMessageHandler,
)
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from .version import __version__


SERVER_NAME = "bootc-updater-session"
LOGGER = logging.getLogger("bootc_updater")


def configure_logging() -> Path | None:
    """Write startup and operation diagnostics to the user's state directory."""
    try:
        log_dir = Path.home() / ".local" / "state" / "bootc-updater"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "bootc-updater.log",
            maxBytes=1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOGGER.setLevel(logging.INFO)
        LOGGER.addHandler(handler)
        LOGGER.info("Starting bootc-updater (arguments: %s)", sys.argv[1:])
        return log_dir / "bootc-updater.log"
    except OSError as error:
        logging.basicConfig(level=logging.INFO)
        LOGGER.warning("Could not open the updater log file: %s", error)
        return None


def _qt_message_handler(message_type, _context, message: str) -> None:
    if message_type == QtMsgType.QtDebugMsg:
        LOGGER.debug("Qt: %s", message)
    elif message_type == QtMsgType.QtInfoMsg:
        LOGGER.info("Qt: %s", message)
    elif message_type == QtMsgType.QtWarningMsg:
        LOGGER.warning("Qt: %s", message)
    elif message_type == QtMsgType.QtCriticalMsg:
        LOGGER.error("Qt: %s", message)
    else:
        LOGGER.critical("Qt: %s", message)


class UpdateController(QObject):
    statusTextChanged = Signal()
    busyChanged = Signal()
    updateAvailableChanged = Signal()
    updateStagedChanged = Signal()
    hasCheckedChanged = Signal()
    progressChanged = Signal()
    imageDetailsChanged = Signal()
    errorDetailsChanged = Signal()
    trayStateChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._status_text = "Check for updates to see if one is available."
        self._busy = False
        self._update_available = False
        self._update_staged = False
        self._has_checked = False
        self._operation = ""
        self._process_output = ""
        self._stderr_output = ""
        self._stdout_diagnostics = ""
        self._error_details = ""
        self._progress_buffer = ""
        self._progress_percent = -1
        self._progress_phase = "download"
        self._latest_version = ""
        self._latest_updated = ""
        self._tray_state = "idle"
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._read_process_output)
        self._process.readyReadStandardError.connect(self._read_process_error)
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

    @Property(bool, notify=hasCheckedChanged)
    def hasChecked(self) -> bool:
        return self._has_checked

    @Property(str, notify=statusTextChanged)
    def busyText(self) -> str:
        if self._operation == "stage":
            if self._progress_phase == "prepare":
                return "Finishing update..."
            if self._progress_percent >= 0:
                return f"Downloading... {self._progress_percent}%"
            return "Downloading..."
        return {
            "check": "Checking...",
            "apply": "Restarting...",
        }.get(self._operation, "Please wait...")

    @Property(int, notify=progressChanged)
    def progressPercent(self) -> int:
        return self._progress_percent

    @Property(str, notify=imageDetailsChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(str, notify=imageDetailsChanged)
    def latestUpdated(self) -> str:
        return self._latest_updated

    @Property(str, notify=errorDetailsChanged)
    def errorDetails(self) -> str:
        return self._error_details

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

    def _set_has_checked(self, value: bool) -> None:
        if self._has_checked != value:
            self._has_checked = value
            self.hasCheckedChanged.emit()

    def _set_progress(self, percent: int, phase: str = "download") -> None:
        percent = max(-1, min(100, percent))
        if self._progress_percent == percent and self._progress_phase == phase:
            return
        self._progress_percent = percent
        self._progress_phase = phase
        self.progressChanged.emit()
        self.statusTextChanged.emit()

    def _set_image_details(self, version: str, updated: str) -> None:
        if self._latest_version == version and self._latest_updated == updated:
            return
        self._latest_version = version
        self._latest_updated = updated
        self.imageDetailsChanged.emit()

    def _set_error_details(self, value: str) -> None:
        value = value.strip()
        if self._error_details == value:
            return
        self._error_details = value
        self.errorDetailsChanged.emit()

    @staticmethod
    def _format_image_details(version: object, timestamp: object = None) -> tuple[str, str]:
        version_text = str(version).strip() if version else ""
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})\+([0-9a-f]{7,40})", version_text)
        if match:
            return version_text, match.group(1)

        updated = str(timestamp).strip()[:10] if timestamp else ""
        return version_text, updated

    @classmethod
    def _status_image_details(cls, status_output: str, staged: bool = False) -> tuple[str, str]:
        try:
            document = json.loads(status_output)
            status = document.get("status", {})
            deployment = status.get("staged") if staged else None
            deployment = deployment or status.get("booted") or {}
            image = deployment.get("image") or {}
            return cls._format_image_details(image.get("version"), image.get("timestamp"))
        except (json.JSONDecodeError, AttributeError, TypeError):
            return "", ""

    def _set_tray_state(self, value: str) -> None:
        if self._tray_state != value:
            self._tray_state = value
            self.trayStateChanged.emit(value)

    def _start_command(self, operation: str, arguments: list[str], message: str) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            return
        LOGGER.info("Starting update operation: %s", operation)
        self._operation = operation
        self._process_output = ""
        self._stderr_output = ""
        self._stdout_diagnostics = ""
        self._set_error_details("")
        self._progress_buffer = ""
        self._set_progress(-1)
        self._set_status_text(message)
        self._set_busy(True)
        self._set_tray_state("busy")
        self._process.start(
            "/usr/bin/pkexec",
            ["/usr/libexec/bootc-updater-helper", *arguments],
        )

    @Slot()
    def checkForUpdates(self) -> None:
        self._start_command(
            "check",
            ["check"],
            "Checking for updates...",
        )

    @Slot()
    def stageUpdate(self) -> None:
        if self._update_available:
            self._start_command(
                "stage",
                ["download"],
                "Downloading the update... You can keep using your PC.",
            )

    @Slot()
    def applyAndReboot(self) -> None:
        if self._update_staged:
            self._start_command(
                "apply",
                ["apply"],
                "Restarting to finish installing the update...",
            )

    def _read_process_output(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
        if chunk:
            if self._operation == "stage":
                self._progress_buffer += chunk
                lines = self._progress_buffer.split("\n")
                self._progress_buffer = lines.pop()
                for line in lines:
                    if not self._read_progress_event(line):
                        self._stdout_diagnostics += line + "\n"
            else:
                self._process_output += chunk

    def _read_process_error(self) -> None:
        chunk = bytes(self._process.readAllStandardError()).decode(errors="replace")
        if chunk:
            self._stderr_output += chunk

    def _read_progress_event(self, line: str) -> bool:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return False

        task = event.get("task")
        if task == "pulling":
            total = event.get("bytesTotal", 0)
            downloaded = event.get("bytes", 0)
            if isinstance(total, int) and isinstance(downloaded, int) and total > 0:
                percent = (downloaded * 100) // total
                self._set_progress(percent)
            else:
                self._set_progress(-1)
        elif task in ("importing", "staging"):
            self._set_progress(-1, "prepare")
        else:
            return False
        return True

    def _operation_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._read_process_output()
        self._read_process_error()
        if self._operation == "stage":
            if not self._read_progress_event(self._progress_buffer):
                self._stdout_diagnostics += self._progress_buffer
            self._progress_buffer = ""
        self._set_busy(False)
        output = self._process_output.strip()
        operation = self._operation
        self._operation = ""
        if operation == "check":
            self._set_has_checked(True)

        check_output, marker, status_output = output.partition(
            "BOOTC_UPDATER_STATUS_JSON_BEGIN"
        )
        if not marker:
            check_output = output
            status_output = ""

        if exit_code != 0:
            self._set_tray_state("error")
            details = (
                self._stderr_output.strip()
                or self._stdout_diagnostics.strip()
                or output
            )
            self._set_error_details(details[-2000:])
            failure_message = {
                "check": "Couldn't check for updates. Try again.",
                "stage": "Couldn't download the update. Try again.",
                "apply": "Couldn't finish installing the update. Try again.",
            }.get(operation, "Something went wrong. Try again.")
            self._set_status_text(failure_message)
            LOGGER.error(
                "Update operation %s failed (exit %s): %s",
                operation,
                exit_code,
                details[-2000:],
            )
            return

        if operation == "check":
            if "Update available for:" in check_output:
                version_match = re.search(r"^\s*Version:\s*(.+)$", check_output, re.MULTILINE)
                if version_match:
                    self._set_image_details(*self._format_image_details(version_match.group(1)))
                else:
                    self._set_image_details("", "")
                self._set_update_available(True)
                self._set_update_staged(False)
                self._set_tray_state("available")
                self._set_status_text("An update is available. Select Update now to download it.")
            elif "Staged update present, not changed" in check_output:
                self._set_image_details(*self._status_image_details(status_output, staged=True))
                self._set_update_available(False)
                self._set_update_staged(True)
                self._set_tray_state("staged")
                self._set_status_text("Your update is ready. Restart your PC to finish installing it.")
            elif any(marker in check_output for marker in ("No changes in:", "No update available.")):
                self._set_image_details(*self._status_image_details(status_output))
                self._set_update_available(False)
                self._set_update_staged(False)
                self._set_tray_state("idle")
                self._set_status_text("You're up to date.")
            else:
                self._set_tray_state("error")
                self._set_status_text("Couldn't tell whether an update is available. Try again.")
        elif operation == "stage":
            self._set_update_available(False)
            self._set_update_staged(True)
            self._set_tray_state("staged")
            self._set_status_text("Update downloaded. Restart your PC to finish installing it.")
        elif operation == "apply":
            self._set_update_staged(False)
            self._set_tray_state("rebooting")
            self._set_status_text("Your PC is restarting to finish installing the update.")

    def _process_error(self, error: QProcess.ProcessError) -> None:
        LOGGER.error("Update helper process error (%s): %s", error, self._process.errorString())
        if error == QProcess.ProcessError.FailedToStart:
            if self._operation == "check":
                self._set_has_checked(True)
            self._operation = ""
            self._set_busy(False)
            self._set_tray_state("error")
            self._set_error_details(self._process.errorString())
            self._set_status_text("Couldn't start the update. Check that the password prompt is available.")


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


def activate_existing_instance(show_window: bool = True) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(250):
        return False

    socket.write(b"show" if show_window else b"background")
    socket.waitForBytesWritten(1000)
    socket.disconnectFromServer()
    return True


def main() -> int:
    configure_logging()
    qInstallMessageHandler(_qt_message_handler)
    start_in_background = "--background" in sys.argv
    arguments = [argument for argument in sys.argv if argument != "--background"]

    app = QApplication(arguments)
    app.setApplicationName("bootc-updater")
    app.setOrganizationName("bootc-updater")
    app.setQuitOnLastWindowClosed(False)
    sys.excepthook = lambda exception_type, exception, traceback: LOGGER.critical(
        "Uncaught application exception",
        exc_info=(exception_type, exception, traceback),
    )

    if activate_existing_instance(show_window=not start_in_background):
        LOGGER.info("Activated the existing updater process")
        return 0

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        LOGGER.error("Could not listen on the session socket: %s", server.errorString())
        return 1

    engine = QQmlApplicationEngine()

    def log_qml_warnings(warnings) -> None:
        for warning in warnings:
            LOGGER.error("QML: %s", warning.toString())

    engine.warnings.connect(log_qml_warnings)
    update_controller = UpdateController()
    engine.rootContext().setContextProperty("updateController", update_controller)
    engine.rootContext().setContextProperty("softwareVersion", __version__)
    qml_file = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(str(qml_file))
    if not engine.rootObjects():
        LOGGER.error("QML interface failed to load from %s", qml_file)
        QMessageBox.critical(
            None,
            "bootc Updater could not start",
            "The updater interface failed to load. Check "
            "~/.local/state/bootc-updater/bootc-updater.log for details.",
        )
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
            "staged": "bootc Updater: restart to finish installing the update",
            "rebooting": "bootc Updater: restarting to finish the update",
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
    if not QSystemTrayIcon.isSystemTrayAvailable():
        LOGGER.warning("No system tray is available in this desktop session")

    if not start_in_background:
        show_window()

    LOGGER.info("Updater started successfully%s", " in background" if start_in_background else "")
    app.aboutToQuit.connect(lambda: LOGGER.info("Updater is shutting down"))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
