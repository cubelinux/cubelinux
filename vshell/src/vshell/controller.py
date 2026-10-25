"""Qt controller for setting up and opening the Virtual Shell."""

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
        self._worker: SetupWorker | None = None

    @Property(str, notify=progressChanged)
    def progress(self) -> str:
        return self._progress

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
        self.progressChanged.emit()

    @Slot()
    def _setup_succeeded(self) -> None:
        self._progress = "Fedora Virtual Shell is ready."
        self.progressChanged.emit()
        self.stateChanged.emit()

    @Slot(str)
    def _setup_failed(self, message: str) -> None:
        self._progress = message
        self.progressChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def openShell(self) -> None:
        QProcess.startDetached("konsole", ["--profile", "VShell"])
