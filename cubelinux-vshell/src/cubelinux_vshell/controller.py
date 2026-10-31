"""Qt controller for the Linux Subsystem setup and workspace window."""

import re
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from .lxc_backend import VShellError, is_initialized, status
from .lxc_setup import destroy_container, initialize
from .port_forwarding import list_forwarded_ports, set_public_access
from .shared_folders import add_shared_folder, list_shared_folders, remove_shared_folder


class SetupWorker(QThread):
    progress = Signal(str)
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, *, destroy: bool = False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.destroy = destroy

    def run(self) -> None:
        try:
            if self.destroy:
                destroy_container(self.progress.emit)
            else:
                initialize(self.progress.emit)
        except (VShellError, OSError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # Present unexpected failures instead of leaving the UI stuck.
            self.failed.emit(f"Unexpected setup error: {error}")
        else:
            self.succeeded.emit()


class SharedFolderWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, action: str, value: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.action = action
        self.value = value

    def run(self) -> None:
        try:
            if self.action == "add":
                folders = add_shared_folder(self.value, self.progress.emit)
            else:
                folders = remove_shared_folder(self.value, self.progress.emit)
        except (VShellError, OSError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # Keep a folder operation failure visible in the UI.
            self.failed.emit(f"Unexpected folder sharing error: {error}")
        else:
            self.succeeded.emit(folders)


class SetupController(QObject):
    progressChanged = Signal()
    stateChanged = Signal()
    containerStatusChanged = Signal()
    sharedFoldersChanged = Signal()
    folderSharingChanged = Signal()
    forwardedPortsChanged = Signal()
    portForwardingChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._progress = ""
        self._progress_title = ""
        self._progress_percent = -1
        self._worker: SetupWorker | None = None
        self._folder_worker: SharedFolderWorker | None = None
        self._folder_sharing_busy = False
        self._folder_sharing_message = ""
        self._folder_sharing_error = False
        try:
            self._shared_folders = list_shared_folders()
        except VShellError as error:
            self._shared_folders = []
            self._folder_sharing_message = str(error)
            self._folder_sharing_error = True
        self._forwarded_ports = list_forwarded_ports()
        self._port_forwarding_message = ""
        self._busy = False
        self._destroying = False
        self._container_status = "not-set-up"
        self._port_timer = QTimer(self)
        self._port_timer.setInterval(2000)
        self._port_timer.timeout.connect(self._refresh_forwarded_ports)
        self._port_timer.start()
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
        return self._busy

    @Property(bool, notify=stateChanged)
    def ready(self) -> bool:
        return self._destroying or is_initialized()

    @Property(bool, notify=stateChanged)
    def destroying(self) -> bool:
        return self._destroying

    @Property(list, notify=sharedFoldersChanged)
    def sharedFolders(self) -> list[dict[str, str]]:
        return self._shared_folders

    @Property(list, notify=forwardedPortsChanged)
    def forwardedPorts(self) -> list[dict[str, object]]:
        return self._forwarded_ports

    @Property(str, notify=portForwardingChanged)
    def portForwardingMessage(self) -> str:
        return self._port_forwarding_message

    @Property(str, constant=True)
    def sharedHomePath(self) -> str:
        return f"/home/{Path.home().name}"

    @Property(bool, notify=folderSharingChanged)
    def folderSharingBusy(self) -> bool:
        return self._folder_sharing_busy

    @Property(str, notify=folderSharingChanged)
    def folderSharingMessage(self) -> str:
        return self._folder_sharing_message

    @Property(bool, notify=folderSharingChanged)
    def folderSharingError(self) -> bool:
        return self._folder_sharing_error

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
        if self.busy or self.folderSharingBusy or self.ready:
            return
        self._start_worker()

    @Slot()
    def destroyContainer(self) -> None:
        if self.busy or self.folderSharingBusy or (not self.ready and self._progress_title != "Destroy failed"):
            return
        self._destroying = True
        self._start_worker(destroy=True)

    def _start_worker(self, *, destroy: bool = False) -> None:
        self._busy = True
        self._progress = "Destroying the Fedora environment…" if destroy else "Getting ready…"
        self._progress_title = "Destroying Fedora" if destroy else "Getting ready"
        self._progress_percent = -1
        self.progressChanged.emit()
        self._worker = SetupWorker(destroy=destroy, parent=self)
        self._worker.progress.connect(self._set_progress)
        if destroy:
            self._worker.succeeded.connect(self._destroy_succeeded)
            self._worker.failed.connect(self._destroy_failed)
        else:
            self._worker.succeeded.connect(self._setup_succeeded)
            self._worker.failed.connect(self._setup_failed)
        self._worker.finished.connect(self._worker_finished)
        self.stateChanged.emit()
        self._worker.start()

    @Slot(str)
    def addSharedFolder(self, folder: str) -> None:
        self._start_folder_worker("add", folder)

    @Slot()
    def chooseSharedFolder(self) -> None:
        if self.busy or self.folderSharingBusy or self.destroying or not self.ready:
            return
        folder = QFileDialog.getExistingDirectory(
            None,
            "Choose a folder to share with Fedora",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.addSharedFolder(folder)

    @Slot(str)
    def removeSharedFolder(self, share_id: str) -> None:
        self._start_folder_worker("remove", share_id)

    @Slot(int, bool)
    def setPortPublicAccess(self, port: int, enabled: bool) -> None:
        try:
            set_public_access(port, enabled)
        except VShellError as error:
            self._port_forwarding_message = str(error)
            self.portForwardingChanged.emit()
            return
        self._port_forwarding_message = ""
        self._forwarded_ports = [
            {**entry, "publicAccess": enabled} if entry.get("port") == port else entry
            for entry in self._forwarded_ports
        ]
        self.forwardedPortsChanged.emit()
        self.portForwardingChanged.emit()

    @Slot()
    def _refresh_forwarded_ports(self) -> None:
        ports = list_forwarded_ports()
        if ports != self._forwarded_ports:
            self._forwarded_ports = ports
            self.forwardedPortsChanged.emit()

    def _start_folder_worker(self, action: str, value: str) -> None:
        if self.busy or self.folderSharingBusy or self.destroying or not self.ready:
            return
        self._folder_sharing_busy = True
        self._folder_sharing_error = False
        self._folder_sharing_message = "Updating Fedora folder access…"
        self.folderSharingChanged.emit()
        self._folder_worker = SharedFolderWorker(action, value, parent=self)
        self._folder_worker.progress.connect(self._set_folder_progress)
        self._folder_worker.succeeded.connect(self._folder_share_succeeded)
        self._folder_worker.failed.connect(self._folder_share_failed)
        self._folder_worker.finished.connect(self._folder_worker_finished)
        self._folder_worker.start()

    @Slot(str)
    def _set_folder_progress(self, message: str) -> None:
        self._folder_sharing_message = message
        self.folderSharingChanged.emit()

    @Slot(object)
    def _folder_share_succeeded(self, folders: list[dict[str, str]]) -> None:
        self._shared_folders = folders
        self._folder_sharing_error = False
        self._folder_sharing_message = ""
        self.sharedFoldersChanged.emit()
        self.folderSharingChanged.emit()
        self.refreshStatus()

    @Slot(str)
    def _folder_share_failed(self, message: str) -> None:
        self._folder_sharing_error = True
        self._folder_sharing_message = message
        self.folderSharingChanged.emit()
        self.refreshStatus()

    @Slot()
    def _folder_worker_finished(self) -> None:
        self._folder_sharing_busy = False
        self._folder_worker = None
        self.folderSharingChanged.emit()

    @Slot()
    def _worker_finished(self) -> None:
        self._busy = False
        self.stateChanged.emit()

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
            ("destroying the fedora container", "Destroying Fedora"),
            ("fedora virtual shell is ready", "Setup complete"),
        )
        for marker, title in steps:
            if marker in message:
                return title
        return ""

    @Slot()
    def _setup_succeeded(self) -> None:
        self._progress = "Linux Subsystem is ready."
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
    def _destroy_succeeded(self) -> None:
        self._destroying = False
        self._progress = ""
        self._progress_title = "Environment destroyed"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot(str)
    def _destroy_failed(self, message: str) -> None:
        self._destroying = False
        self._progress = message
        self._progress_title = "Destroy failed"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot()
    def openShell(self) -> None:
        if not self.busy and not self.folderSharingBusy and not self.destroying:
            QProcess.startDetached("konsole", ["--profile", "VShell"])
