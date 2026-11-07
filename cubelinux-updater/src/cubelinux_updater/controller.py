"""Update state, bootc operations, progress, and automatic scheduling."""

import json
import os
import re
import subprocess
import time

from PySide6.QtCore import (
    QObject, Property, QProcess, QSettings, QTimer, Signal, Slot,
)

from .constants import (
    AUTO_CHECK_INTERVAL_SECONDS, AUTO_CHECK_RETRY_SECONDS,
    AUTO_CHECK_STARTUP_DELAY_MS, AUTO_DOWNLOAD_RETRY_MS,
)
from .diagnostics import LOGGER


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
    notificationRequested = Signal(str, str, str, int)

    def __init__(self, preview_state: str | None = None) -> None:
        super().__init__()
        self._preview_mode = preview_state is not None
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
        self._download_bytes = 0
        self._download_bytes_total = 0
        self._latest_version = ""
        self._latest_updated = ""
        self._installed_version = ""
        self._tray_state = "idle"
        self._settings = QSettings()
        self._automatic_operation = False
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._read_process_output)
        self._process.readyReadStandardError.connect(self._read_process_error)
        self._process.finished.connect(self._operation_finished)
        self._process.errorOccurred.connect(self._process_error)
        self._auto_check_timer = QTimer(self)
        self._auto_check_timer.setSingleShot(True)
        self._auto_check_timer.timeout.connect(self._start_automatic_check)
        self._auto_download_timer = QTimer(self)
        self._auto_download_timer.setSingleShot(True)
        self._auto_download_timer.setInterval(AUTO_DOWNLOAD_RETRY_MS)
        self._auto_download_timer.timeout.connect(self._try_automatic_download)
        if preview_state is not None:
            self._set_preview_state(preview_state)

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

    @Property(str, notify=statusTextChanged)
    def busyPhase(self) -> str:
        if self._operation == "check":
            return "check"
        if self._operation == "stage":
            return "prepare" if self._progress_phase == "prepare" else "download"
        if self._operation == "apply":
            return "apply"
        return ""

    @Property(int, notify=progressChanged)
    def progressPercent(self) -> int:
        return self._progress_percent

    @Property(str, notify=progressChanged)
    def downloadSize(self) -> str:
        return self._format_size(self._download_bytes_total)

    @Property(str, notify=imageDetailsChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(str, notify=imageDetailsChanged)
    def latestUpdated(self) -> str:
        return self._latest_updated

    @Property(str, notify=imageDetailsChanged)
    def installedVersion(self) -> str:
        return self._installed_version

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

    def _set_download_progress(self, downloaded: int, total: int) -> None:
        downloaded = max(0, downloaded)
        total = max(0, total)
        if (self._download_bytes, self._download_bytes_total) == (downloaded, total):
            return
        self._download_bytes = downloaded
        self._download_bytes_total = total
        self.progressChanged.emit()

    @staticmethod
    def _format_size(size: int) -> str:
        if size <= 0:
            return ""
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return ""

    def _set_image_details(self, version: str, updated: str) -> None:
        if self._latest_version == version and self._latest_updated == updated:
            return
        self._latest_version = version
        self._latest_updated = updated
        self.imageDetailsChanged.emit()

    def _set_installed_version(self, version: str) -> None:
        if self._installed_version == version:
            return
        self._installed_version = version
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

    def _set_preview_state(self, state: str) -> None:
        self._operation = ""
        self._set_busy(False)
        self._set_update_available(False)
        self._set_update_staged(False)
        self._set_has_checked(False)
        self._set_error_details("")
        self._set_progress(-1)
        self._set_download_progress(0, 0)
        self._set_image_details("", "")
        self._set_installed_version("")
        self._set_tray_state("idle")

        if state == "ready":
            self._set_status_text("Check for updates to see if one is available.")
        elif state == "up-to-date":
            self._set_has_checked(True)
            self._set_image_details("2026-10-29+a5c583a", "2026-10-29")
            self._set_installed_version("2026-10-29+a5c583a")
            self._set_status_text("No updates are available right now.")
        elif state in ("available", "staged", "downloading", "preparing"):
            self._set_has_checked(True)
            self._set_image_details("2026.10", "2026-10-29")
            self._set_installed_version("2026-10-29+a5c583a")
            self._set_download_progress(0, 1_200_000_000)
            if state == "available":
                self._set_update_available(True)
                self._set_status_text("A system update is available.")
            elif state == "staged":
                self._set_update_staged(True)
                self._set_status_text("Your update is ready to finish installing.")
            else:
                self._set_update_available(True)
                self._set_busy(True)
                self._operation = "stage"
                if state == "downloading":
                    self._set_download_progress(684_000_000, 1_200_000_000)
                    self._set_progress(57)
                    self._set_status_text("Downloading the update...")
                else:
                    self._set_download_progress(1_200_000_000, 1_200_000_000)
                    self._set_progress(-1, "prepare")
                    self._set_status_text("Preparing the update...")
        elif state == "checking":
            self._set_busy(True)
            self._operation = "check"
            self._set_status_text("Checking for updates...")
        elif state == "error":
            self._set_has_checked(True)
            self._set_error_details("Sample preview error details.")
            self._set_status_text("Couldn't check for updates. Try again.")

    def _start_command(
        self,
        operation: str,
        arguments: list[str],
        message: str,
        *,
        automatic: bool = False,
    ) -> bool:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            return False
        LOGGER.info("Starting update operation: %s", operation)
        self._operation = operation
        self._automatic_operation = automatic
        self._process_output = ""
        self._stderr_output = ""
        self._stdout_diagnostics = ""
        self._set_error_details("")
        self._progress_buffer = ""
        self._set_progress(-1)
        if operation in ("check", "stage"):
            self._set_download_progress(0, 0)
        self._set_status_text(message)
        self._set_busy(True)
        self._set_tray_state("checking" if operation == "check" and automatic else "busy")
        self._process.start(
            "/usr/bin/pkexec",
            ["/usr/libexec/cubelinux-updater-helper", *arguments],
        )
        return True

    @Slot()
    def startAutomaticChecks(self) -> None:
        """Schedule a quiet update check after the desktop session settles."""
        if self._preview_mode:
            return

        now = int(time.time())
        last_success = int(self._settings.value("automatic/last-success", 0) or 0)
        last_attempt = int(self._settings.value("automatic/last-attempt", 0) or 0)

        if last_attempt > last_success and now - last_attempt < AUTO_CHECK_RETRY_SECONDS:
            delay_ms = (AUTO_CHECK_RETRY_SECONDS - (now - last_attempt)) * 1000
        else:
            delay_ms = AUTO_CHECK_STARTUP_DELAY_MS

        self._schedule_automatic_check(delay_ms)
        LOGGER.info("Scheduled automatic update check in %.1f minutes", delay_ms / 60000)

    def _schedule_automatic_check(self, delay_ms: int) -> None:
        if not self._preview_mode:
            self._auto_check_timer.start(max(1000, delay_ms))

    @Slot()
    def _start_automatic_check(self) -> None:
        if self.busy:
            self._schedule_automatic_check(15 * 60 * 1000)
            return

        self._settings.setValue("automatic/last-attempt", int(time.time()))
        self._set_tray_state("checking")
        started = self._start_command(
            "check",
            ["check"],
            "Checking for updates in the background...",
            automatic=True,
        )
        if not started:
            self._schedule_automatic_check(15 * 60 * 1000)

    def _complete_check(self, succeeded: bool, automatic: bool) -> None:
        if succeeded:
            now = int(time.time())
            self._settings.setValue("automatic/last-success", now)
            self._settings.remove("automatic/last-attempt")
            self._settings.sync()
            self._schedule_automatic_check(AUTO_CHECK_INTERVAL_SECONDS * 1000)
        elif automatic:
            self._settings.setValue("automatic/last-attempt", int(time.time()))
            self._settings.sync()
            self._schedule_automatic_check(AUTO_CHECK_RETRY_SECONDS * 1000)

    def _notify_update_once_per_day(self, summary: str, body: str, kind: str, timeout: int) -> None:
        key = f"automatic/last-notification/{kind}"
        now = int(time.time())
        last_notification = int(self._settings.value(key, 0) or 0)
        if now - last_notification < AUTO_CHECK_INTERVAL_SECONDS:
            return
        self._settings.setValue(key, now)
        self._settings.sync()
        self.notificationRequested.emit(summary, body, kind, timeout)

    @staticmethod
    def _has_unmetered_connection() -> bool:
        """Return true only when NetworkManager confirms an active unmetered link."""
        try:
            devices = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
                env={**os.environ, "LC_ALL": "C"},
            )
        except (OSError, subprocess.SubprocessError):
            LOGGER.info("Could not determine whether the connection is metered")
            return False

        network_device_types = {"wifi", "ethernet", "gsm", "cdma", "wimax", "bluetooth"}
        connected_devices = []
        for line in devices.stdout.splitlines():
            fields = line.split(":", 2)
            if len(fields) == 3:
                device, device_type, state = fields
                if (
                    device_type.strip().lower() in network_device_types
                    and state.strip().lower().startswith("connected")
                ):
                    connected_devices.append(device.strip())
        if not connected_devices:
            return False

        for device in connected_devices:
            try:
                result = subprocess.run(
                    ["nmcli", "-g", "GENERAL.METERED", "device", "show", device],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                    env={**os.environ, "LC_ALL": "C"},
                )
            except (OSError, subprocess.SubprocessError):
                LOGGER.info("Could not determine whether %s is metered", device)
                return False

            metered = result.stdout.strip().lower()
            if metered in ("yes", "guess-yes"):
                return False
            if metered not in ("no", "guess-no"):
                return False
        return True

    def _try_automatic_download(self) -> None:
        if not self._update_available or self.busy:
            return
        if not self._has_unmetered_connection():
            self._set_status_text(
                "An update is available. Automatic download is paused until an unmetered connection is available."
            )
            self._set_tray_state("available")
            self._auto_download_timer.start()
            return

        self._auto_download_timer.stop()
        if not self._start_command(
            "stage",
            ["download"],
            "Downloading the update in the background...",
            automatic=True,
        ):
            self._auto_download_timer.start(15 * 60 * 1000)

    @Slot()
    def checkForUpdates(self) -> None:
        if self._preview_mode:
            self._set_preview_state("available")
            return
        self._start_command(
            "check",
            ["check"],
            "Checking for updates...",
        )

    @Slot()
    def stageUpdate(self) -> None:
        if self._update_available:
            self._auto_download_timer.stop()
            if self._preview_mode:
                self._set_preview_state("staged")
                return
            self._start_command(
                "stage",
                ["download"],
                "Downloading the update... You can keep using your PC.",
            )

    @Slot()
    def applyAndReboot(self) -> None:
        if self._update_staged:
            if self._preview_mode:
                self._set_preview_state("up-to-date")
                return
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
                self._set_download_progress(downloaded, total)
                percent = (downloaded * 100) // total
                self._set_progress(percent)
            else:
                self._set_progress(-1)
        elif task in ("importing", "staging"):
            self._set_progress(-1, "prepare")
        else:
            return False
        return True

    def _operation_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._read_process_output()
        self._read_process_error()
        if self._operation == "stage":
            if not self._read_progress_event(self._progress_buffer):
                self._stdout_diagnostics += self._progress_buffer
            self._progress_buffer = ""
        self._set_busy(False)
        output = self._process_output.strip()
        operation = self._operation
        automatic = self._automatic_operation
        self._operation = ""
        self._automatic_operation = False
        if operation == "check":
            self._set_has_checked(True)

        check_output, marker, status_output = output.partition(
            "CUBELINUX_UPDATER_STATUS_JSON_BEGIN"
        )
        if not marker:
            check_output = output
            status_output = ""

        reboot_started = (
            operation == "apply"
            and exit_status == QProcess.ExitStatus.CrashExit
            and "staged deployment will now be applied on reboot"
            in f"{output}\n{self._stderr_output}".lower()
        )
        if reboot_started:
            # bootc initiates the reboot, which terminates this helper before
            # it can exit normally. Keep the UI in its restarting state.
            self._operation = "apply"
            self._set_busy(True)
            self._set_tray_state("rebooting")
            self._set_status_text("Your PC is restarting to finish installing the update.")
            LOGGER.info("bootc initiated the reboot; updater helper ended during shutdown")
            return

        if exit_code != 0:
            self._set_tray_state("idle" if operation == "check" and automatic else "error")
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
            if operation == "check":
                self._complete_check(False, automatic)
            elif operation == "stage" and automatic:
                self._auto_download_timer.start(6 * 60 * 60 * 1000)
                self._notify_update_once_per_day(
                    "Could not download the system update",
                    "Open Updater to review the error and try again.",
                    "download-error",
                    10000,
                )
            LOGGER.error(
                "Update operation %s failed (exit %s): %s",
                operation,
                exit_code,
                details[-2000:],
            )
            return

        if operation == "check":
            if "Update available for:" in check_output:
                installed_version, _ = self._status_image_details(status_output)
                self._set_installed_version(installed_version)
                version_match = re.search(r"^\s*Version:\s*(.+)$", check_output, re.MULTILINE)
                if version_match:
                    self._set_image_details(*self._format_image_details(version_match.group(1)))
                else:
                    self._set_image_details("", "")
                self._set_update_available(True)
                self._set_update_staged(False)
                self._set_tray_state("available")
                self._set_status_text("A system update is available. Preparing its download...")
                self._complete_check(True, automatic)
                self._notify_update_once_per_day(
                    "System update available",
                    "An update is ready. Open Updater to review its status or download it.",
                    "available",
                    10000,
                )
                QTimer.singleShot(0, self._try_automatic_download)
            elif "Staged update present, not changed" in check_output:
                installed_version, _ = self._status_image_details(status_output)
                self._set_installed_version(installed_version)
                self._set_image_details(*self._status_image_details(status_output, staged=True))
                self._set_update_available(False)
                self._set_update_staged(True)
                self._set_tray_state("staged")
                self._set_status_text("Your update is ready. Restart your PC to finish installing it.")
                self._auto_download_timer.stop()
                self._complete_check(True, automatic)
                if automatic:
                    self._notify_update_once_per_day(
                        "System update ready",
                        "Restart your PC when convenient to finish installing the update.",
                        "staged",
                        0,
                    )
            elif any(marker in check_output for marker in ("No changes in:", "No update available.")):
                self._set_image_details(*self._status_image_details(status_output))
                self._set_installed_version(self._latest_version)
                self._set_update_available(False)
                self._set_update_staged(False)
                self._set_tray_state("idle")
                self._set_status_text("You're up to date.")
                self._auto_download_timer.stop()
                self._complete_check(True, automatic)
            else:
                self._set_tray_state("error")
                details = (
                    self._stderr_output.strip()
                    or self._stdout_diagnostics.strip()
                    or check_output.strip()
                    or "The updater returned an unrecognized status."
                )
                self._set_error_details(details[-2000:])
                self._set_status_text("Couldn't tell whether an update is available. Try again.")
                self._complete_check(False, automatic)
        elif operation == "stage":
            self._set_update_available(False)
            self._set_update_staged(True)
            self._set_tray_state("staged")
            self._set_status_text("Update downloaded. Restart your PC to finish installing it.")
            self._auto_download_timer.stop()
            if automatic:
                self._notify_update_once_per_day(
                    "System update ready",
                    "Restart your PC when convenient to finish installing the update.",
                    "staged",
                    0,
                )
        elif operation == "apply":
            self._operation = "apply"
            self._set_busy(True)
            self._set_tray_state("rebooting")
            self._set_status_text("Your PC is restarting to finish installing the update.")

    def _process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.Crashed and self._operation == "apply":
            LOGGER.info("Update helper ended during apply; checking whether bootc initiated a reboot")
        else:
            LOGGER.error("Update helper process error (%s): %s", error, self._process.errorString())
        if error == QProcess.ProcessError.FailedToStart:
            operation = self._operation
            automatic = self._automatic_operation
            if self._operation == "check":
                self._set_has_checked(True)
            self._operation = ""
            self._automatic_operation = False
            self._set_busy(False)
            self._set_tray_state("idle" if operation == "check" and automatic else "error")
            self._set_error_details(self._process.errorString())
            self._set_status_text("Couldn't start the update. Check that the password prompt is available.")
            if operation == "check":
                self._complete_check(False, automatic)
            elif operation == "stage" and automatic:
                self._auto_download_timer.start(6 * 60 * 60 * 1000)
