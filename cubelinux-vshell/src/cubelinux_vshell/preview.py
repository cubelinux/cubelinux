"""Open the setup wizard QML with a harmless in-memory controller."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication


class PreviewController(QObject):
    """Small static stand-in for the real LXC and network controller."""

    previewActionRequested = Signal(str)

    @Property(bool, constant=True)
    def busy(self) -> bool:
        return False

    @Property(bool, constant=True)
    def ready(self) -> bool:
        return False

    @Property(bool, constant=True)
    def destroying(self) -> bool:
        return False

    @Property(bool, constant=True)
    def folderSharingBusy(self) -> bool:
        return False

    @Property(bool, constant=True)
    def folderSharingError(self) -> bool:
        return False

    @Property(str, constant=True)
    def folderSharingMessage(self) -> str:
        return ""

    @Property(str, constant=True)
    def portForwardingMessage(self) -> str:
        return ""

    @Property(str, constant=True)
    def containerStatus(self) -> str:
        return "running"

    @Property(str, constant=True)
    def progress(self) -> str:
        return ""

    @Property(bool, constant=True)
    def setupFailed(self) -> bool:
        return False

    @Property(bool, constant=True)
    def destroyFailed(self) -> bool:
        return False

    @Property(str, constant=True)
    def connectivityStatus(self) -> str:
        return "online"

    @Property(str, constant=True)
    def connectivityError(self) -> str:
        return ""

    @Property(str, constant=True)
    def sharedHomePath(self) -> str:
        return f"/home/{Path.home().name}"

    @Property(list, constant=True)
    def sharedFolders(self) -> list[dict[str, str]]:
        project_folder = Path.home() / "Projects"
        return [{
            "id": "preview-projects",
            "name": "Projects",
            "path": str(project_folder),
            "mountPath": "/mnt/vshell-shares/projects",
            "available": "true",
        }]

    @Property(list, constant=True)
    def forwardedPorts(self) -> list[dict[str, object]]:
        return [{
            "port": 3000,
            "status": "Forwarding",
            "hostAddress": "127.0.0.1:3000",
            "error": "",
            "publicAccess": False,
        }]

    @Slot()
    def checkInternet(self) -> None:
        """Keep the preview offline from application services."""

    @Slot()
    def openShell(self) -> None:
        self.previewActionRequested.emit("Open terminal")

    @Slot()
    def chooseSharedFolder(self) -> None:
        self.previewActionRequested.emit("Add folder")

    @Slot(str)
    def removeSharedFolder(self, folder_id: str) -> None:
        self.previewActionRequested.emit("Remove shared folder")

    @Slot(int, bool)
    def setPortPublicAccess(self, port: int, enabled: bool) -> None:
        self.previewActionRequested.emit("Change port exposure")


def _preview_icon_url() -> str:
    module_dir = Path(__file__).resolve().parent
    candidates = [module_dir / "qml" / "cubelinux-icon.png"]
    candidates.extend(
        parent / "cubelinux-branding-assets" / "png" / "icon-512.png"
        for parent in Path(__file__).resolve().parents
    )

    for candidate in candidates:
        if candidate.is_file():
            return QUrl.fromLocalFile(str(candidate)).toString()

    return ""


def _has_kirigami(engine: QQmlApplicationEngine) -> bool:
    return any(
        (Path(import_path) / "org" / "kde" / "kirigami" / "qmldir").is_file()
        for import_path in engine.importPathList()
    )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("cubelinux-vshell-preview")
    app.setOrganizationName("cubelinux")
    app.setQuitOnLastWindowClosed(True)

    controller = PreviewController()
    engine = QQmlApplicationEngine()
    use_kirigami = _has_kirigami(engine)
    if use_kirigami and not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("org.kde.desktop")

    context = engine.rootContext()
    context.setContextProperty("previewController", controller)
    context.setContextProperty("previewIconUrl", _preview_icon_url())
    qml_name = "PreviewMain.qml" if use_kirigami else "PreviewQtMain.qml"
    if not use_kirigami:
        print("KDE Kirigami was not found; opening the Qt Quick Controls preview.")
    qml_file = Path(__file__).parent / "qml" / qml_name
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        return 1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
