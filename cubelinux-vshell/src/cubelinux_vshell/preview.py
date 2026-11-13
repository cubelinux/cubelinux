"""Open the setup wizard QML with a harmless in-memory controller."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication


class PreviewController(QObject):
    """Small static stand-in for the real LXC and network controller."""

    @Property(bool, constant=True)
    def busy(self) -> bool:
        return False

    @Property(bool, constant=True)
    def ready(self) -> bool:
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

    @Slot()
    def checkInternet(self) -> None:
        """Keep the preview offline from application services."""


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
