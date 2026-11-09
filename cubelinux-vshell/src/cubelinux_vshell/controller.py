"""Qt controller for the Linux Subsystem setup and workspace window."""

import re
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from .lxc_backend import (
    CONTAINER_NAME,
    FEDORA_CONTAINER_NAME,
    VShellError,
    is_initialized,
    status,
)
from .lxc_setup import create_fedora_environment, initialize, reset_environment, reset_runtime
from .port_forwarding import list_forwarded_ports, set_public_access
from .shared_folders import add_shared_folder, list_shared_folders, remove_shared_folder


class SetupWorker(QThread):
    progress = Signal(str)
    succeeded = Signal()
    failed = Signal(str)

    def __init__(
        self,
        *,
        destroy: bool = False,
        container_name: str = CONTAINER_NAME,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.destroy = destroy
        self.container_name = container_name

    def run(self) -> None:
        try:
            if self.destroy:
                if self.container_name == CONTAINER_NAME:
                    reset_runtime(self.progress.emit)
                else:
                    reset_environment(self.container_name, self.progress.emit)
            elif self.container_name == FEDORA_CONTAINER_NAME:
                create_fedora_environment(self.progress.emit)
            else:
                initialize(self.progress.emit, container_name=self.container_name)
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
    fedoraProgressChanged = Signal()
    fedoraStateChanged = Signal()
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
        self._fedora_worker: SetupWorker | None = None
        self._fedora_busy = False
        self._fedora_progress = ""
        self._fedora_setup_failed = False
        self._fedora_container_status = "not-set-up"
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
        if not is_initialized():
            self._start_worker()

    @Property(str, notify=progressChanged)
    def progress(self) -> str:
        return self._progress

    @Property(str, notify=progressChanged)
    def progressTitle(self) -> str:
        return self._progress_title or "Preparing Runtime"

    @Property(bool, notify=progressChanged)
    def setupFailed(self) -> bool:
        return self._progress_title == "Setup failed"

    @Property(bool, notify=progressChanged)
    def setupComplete(self) -> bool:
        return self._progress_title == "Setup complete"

    @Property(bool, notify=progressChanged)
    def destroyFailed(self) -> bool:
        return self._progress_title == "Reset failed"

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

    @Property(bool, notify=fedoraStateChanged)
    def fedoraReady(self) -> bool:
        return is_initialized(FEDORA_CONTAINER_NAME)

    @Property(bool, notify=fedoraStateChanged)
    def fedoraBusy(self) -> bool:
        return self._fedora_busy

    @Property(bool, notify=fedoraProgressChanged)
    def fedoraSetupFailed(self) -> bool:
        return self._fedora_setup_failed

    @Property(str, notify=fedoraProgressChanged)
    def fedoraProgress(self) -> str:
        return self._fedora_progress

    @Property(str, notify=fedoraStateChanged)
    def fedoraContainerStatus(self) -> str:
        return self._fedora_container_status

    @Slot()
    def refreshStatus(self) -> None:
        try:
            current = status()
        except (VShellError, OSError):
            current = "unknown"
        if current != self._container_status:
            self._container_status = current
            self.containerStatusChanged.emit()
        try:
            fedora_current = status(FEDORA_CONTAINER_NAME)
        except (VShellError, OSError):
            fedora_current = "unknown"
        if fedora_current != self._fedora_container_status:
            self._fedora_container_status = fedora_current
            self.fedoraStateChanged.emit()

    @Slot()
    def setup(self) -> None:
        if self.busy or self.fedoraBusy or self.folderSharingBusy or self.ready:
            return
        self._start_worker()

    @Slot()
    def createFedoraContainer(self) -> None:
        if (
            self.busy
            or self.fedoraBusy
            or self.folderSharingBusy
            or self.destroying
            or not self.ready
            or self.fedoraReady
        ):
            return
        self._busy = True
        self._fedora_busy = True
        self._fedora_setup_failed = False
        self._fedora_progress = "Getting ready…"
        self.fedoraProgressChanged.emit()
        self.stateChanged.emit()
        self.fedoraStateChanged.emit()
        self._fedora_worker = SetupWorker(
            container_name=FEDORA_CONTAINER_NAME,
            parent=self,
        )
        self._fedora_worker.progress.connect(self._set_fedora_progress)
        self._fedora_worker.succeeded.connect(self._fedora_setup_succeeded)
        self._fedora_worker.failed.connect(self._fedora_setup_failed_signal)
        self._fedora_worker.finished.connect(self._fedora_worker_finished)
        self._fedora_worker.start()

    @Slot()
    def destroyContainer(self) -> None:
        if self.busy or self.folderSharingBusy or (
            not self.ready and not (self.setupFailed or self.destroyFailed)
        ):
            return
        self._destroying = True
        self._start_worker(destroy=True)

    def _start_worker(self, *, destroy: bool = False) -> None:
        self._busy = True
        self._progress = "Resetting the Runtime environment…" if destroy else "Getting ready…"
        self._progress_title = "Resetting Runtime" if destroy else "Getting ready"
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
            "Choose a folder to share with Runtime",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.addSharedFolder(folder)

    @Slot(str)
    def removeSharedFolder(self, share_id: str) -> None:
        self._start_folder_worker("remove", share_id)

    @Slot(str, int, bool)
    def setPortPublicAccess(self, container_name: str, port: int, enabled: bool) -> None:
        try:
            set_public_access(port, enabled, container_name)
        except VShellError as error:
            self._port_forwarding_message = str(error)
            self.portForwardingChanged.emit()
            return
        self._port_forwarding_message = ""
        self._forwarded_ports = [
            {**entry, "publicAccess": enabled}
            if entry.get("container") == container_name and entry.get("port") == port
            else entry
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
        self._folder_sharing_message = "Updating Runtime folder access…"
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
    def _set_fedora_progress(self, message: str) -> None:
        self._fedora_progress = message
        self.fedoraProgressChanged.emit()

    @Slot()
    def _fedora_setup_succeeded(self) -> None:
        self._fedora_setup_failed = False
        self._fedora_progress = "Fedora environment is ready."
        self.fedoraProgressChanged.emit()
        self.refreshStatus()
        self.fedoraStateChanged.emit()

    @Slot(str)
    def _fedora_setup_failed_signal(self, message: str) -> None:
        self._fedora_setup_failed = True
        self._fedora_progress = message
        self.fedoraProgressChanged.emit()
        self.fedoraStateChanged.emit()

    @Slot()
    def _fedora_worker_finished(self) -> None:
        self._fedora_busy = False
        self._busy = False
        self._fedora_worker = None
        self.stateChanged.emit()
        self.fedoraStateChanged.emit()

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
            ("requesting one-time permission", "Preparing rootless containers"),
            ("checking your rootless container id mappings", "Preparing your account"),
            ("waiting for another runtime operation", "Waiting for Runtime setup"),
            ("creating the lxc runtime from cubelinux's bundled image", "Creating LXC Runtime"),
            ("creating the fedora container from cubelinux's bundled image", "Creating Fedora environment"),
            ("pulling the latest runtime image", "Downloading latest Runtime image"),
            ("pulling the latest fedora image", "Downloading Fedora environment"),
            ("unpacking tar rootfs", "Installing Runtime image"),
            ("starting runtime for first-time setup", "Starting Runtime"),
            ("connecting runtime to the network", "Connecting Runtime to the network"),
            ("preparing your runtime user and shell", "Preparing your Runtime account"),
            ("sharing your home folder", "Sharing your home folder"),
            ("restarting runtime", "Restarting Runtime"),
            ("read-only system", "Protecting Runtime system files"),
            ("resetting runtime's system filesystem", "Resetting Runtime"),
            ("cubelinux runtime is ready", "Runtime is ready"),
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
        self._progress_title = "Environment reset"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot(str)
    def _destroy_failed(self, message: str) -> None:
        self._destroying = False
        self._progress = message
        self._progress_title = "Reset failed"
        self._progress_percent = -1
        self.progressChanged.emit()
        self.refreshStatus()
        self.stateChanged.emit()

    @Slot()
    def openShell(self) -> None:
        if not self.busy and not self.folderSharingBusy and not self.destroying:
            QProcess.startDetached("konsole", ["--profile", "VShell"])

    @Slot()
    def openFedoraShell(self) -> None:
        if (
            self.fedoraReady
            and not self.busy
            and not self.fedoraBusy
            and not self.folderSharingBusy
            and not self.destroying
        ):
            QProcess.startDetached(
                "cubelinux-vshell",
                ["open-terminal", "--container", FEDORA_CONTAINER_NAME],
            )
