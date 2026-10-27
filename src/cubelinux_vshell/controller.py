"""Qt controller for setting up and opening the Virtual Shell."""

import re

from PySide6.QtCore import Property, QObject, QProcess, QThread, Signal, Slot

from .lxc_backend import VShellError, initialize, is_initialized


class SetupWorker(QThread):
    progress = Signal(str)
    succeeded = Signal()
    failed = Signal(str)

    def run(self) -> None:
        try:
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

    def __init__(self) -> None:
        super().__init__()
        self._progress = ""
        self._progress_title = ""
        self._progress_percent = -1
        self._worker: SetupWorker | None = None

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
        return is_initialized()

    @Slot()
    def setup(self) -> None:
        if self.busy or self.ready:
            return
        self._progress = "Getting ready…"
        self._progress_title = "Getting ready"
        self._progress_percent = -1
        self.progressChanged.emit()
        self._worker = SetupWorker(self)
        self._worker.progress.connect(self._set_progress)
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
        self._progress = "Fedora Virtual Shell is ready."
        self._progress_title = "Setup complete"
        self._progress_percent = 100
        self.progressChanged.emit()
        self.stateChanged.emit()

    @Slot(str)
    def _setup_failed(self, message: str) -> None:
        self._progress = message
        self._progress_title = "Setup failed"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def openShell(self) -> None:
        QProcess.startDetached("konsole", ["--profile", "VShell"])
