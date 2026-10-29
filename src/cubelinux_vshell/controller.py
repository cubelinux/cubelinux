"""Qt controller for setting up and opening Setup Terminal."""

import re

from PySide6.QtCore import Property, QObject, QProcess, QThread, Signal, Slot

from .lxc_backend import VShellError, initialize, is_initialized, reset_container, status


class SetupWorker(QThread):
    progress = Signal(str)
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, *, reset: bool = False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.reset = reset

    def run(self) -> None:
        try:
            if self.reset:
                reset_container(self.progress.emit)
            else:
                initialize(self.progress.emit)
        except (VShellError, OSError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # Present unexpected failures instead of leaving the UI stuck.
            self.failed.emit(f"Unexpected setup error: {error}")
        else:
            self.succeeded.emit()


class SetupController(QObject):
    progressChanged = Signal()
    stateChanged = Signal()
    containerStatusChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._progress = ""
        self._progress_title = ""
        self._progress_percent = -1
        self._worker: SetupWorker | None = None
        self._resetting = False
        self._container_status = "not-set-up"
        self.refreshStatus()

    @Property(str, notify=progressChanged)
    def progress(self) -> str:
        return self._progress

    @Property(str, notify=progressChanged)
    def progressTitle(self) -> str:
        return self._progress_title or "Setting up Fedora"

    @Property(int, notify=progressChanged)
    def progressPercent(self) -> int:
        return self._progress_percent

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    @Property(bool, notify=stateChanged)
    def ready(self) -> bool:
        return self._resetting or is_initialized()

    @Property(str, notify=containerStatusChanged)
    def containerStatus(self) -> str:
        return self._container_status

    @Slot()
    def refreshStatus(self) -> None:
        try:
            current = status()
        except (VShellError, OSError):
            current = "unknown"
        if current != self._container_status:
            self._container_status = current
            self.containerStatusChanged.emit()

    @Slot()
    def setup(self) -> None:
        if self.busy or self.ready:
            return
        self._start_worker(reset=False)

    @Slot()
    def resetContainer(self) -> None:
        if self.busy or not self.ready:
            return
        self._resetting = True
        self.stateChanged.emit()
        self._start_worker(reset=True)

    def _start_worker(self, *, reset: bool) -> None:
        self._progress = "Getting ready…"
        self._progress_title = "Resetting Fedora" if reset else "Getting ready"
        self._progress_percent = -1
        self.progressChanged.emit()
        self._worker = SetupWorker(reset=reset, parent=self)
        self._worker.progress.connect(self._set_progress)
        if reset:
            self._worker.succeeded.connect(self._reset_succeeded)
            self._worker.failed.connect(self._reset_failed)
        else:
            self._worker.succeeded.connect(self._setup_succeeded)
            self._worker.failed.connect(self._setup_failed)
        self._worker.finished.connect(self.stateChanged.emit)
        self.stateChanged.emit()
        self._worker.start()

    @Slot(str)
    def _set_progress(self, message: str) -> None:
        self._progress = message
        title = self._title_for_progress(message.lower())
        if title and title != self._progress_title:
            self._progress_title = title
            self._progress_percent = -1

        percentage = re.search(r"(?<!\d)(100|[1-9]?\d)%", message)
        if percentage:
            self._progress_percent = int(percentage.group(1))
        self.progressChanged.emit()

    @staticmethod
    def _title_for_progress(message: str) -> str:
        steps = (
            ("requesting one-time permission", "Preparing container networking"),
            ("checking your rootless container id mappings", "Preparing your account"),
            ("downloading the fedora environment", "Downloading Fedora image"),
            ("checking for fedora template updates", "Checking for Fedora image updates"),
            ("template update check failed", "Using cached Fedora image"),
            ("downloading the image index", "Checking the Fedora image"),
            ("downloading the rootfs", "Downloading Fedora filesystem"),
            ("downloading the metadata", "Downloading image metadata"),
            ("unpacking the rootfs", "Extracting Fedora filesystem"),
            ("starting fedora for first-time setup", "Starting Fedora"),
            ("connecting fedora to the network", "Connecting Fedora to the network"),
            ("preparing your fedora user and shell", "Preparing your Fedora account"),
            ("sharing your home folder", "Sharing your home folder"),
            ("restarting fedora", "Restarting Fedora"),
            ("fedora virtual shell is ready", "Setup complete"),
        )
        for marker, title in steps:
            if marker in message:
                return title
        return ""

    @Slot()
    def _setup_succeeded(self) -> None:
        self._progress = "Setup Terminal is ready."
        self._progress_title = "Setup complete"
        self._progress_percent = 100
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot(str)
    def _setup_failed(self, message: str) -> None:
        self._progress = message
        self._progress_title = "Setup failed"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def _reset_succeeded(self) -> None:
        self._resetting = False
        self._progress = "Fedora has been reset with a fresh environment."
        self._progress_title = "Reset complete"
        self._progress_percent = 100
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot(str)
    def _reset_failed(self, message: str) -> None:
        self._resetting = False
        self._progress = message
        self._progress_title = "Reset failed"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot()
    def openShell(self) -> None:
        QProcess.startDetached("konsole", ["--profile", "VShell"])
