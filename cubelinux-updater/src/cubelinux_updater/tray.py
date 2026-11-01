"""System-tray state, progress animation, and desktop notifications."""

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu

from .diagnostics import LOGGER


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


def configure_tray(app, update_controller, show_window, status_notifier_item):
    """Create the tray item and connect it to updater state and actions."""
    KStatusNotifierItem = status_notifier_item
    notification_ids: dict[str, int] = {}
    notification_interface = None
    try:
        from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

        notification_bus = QDBusConnection.sessionBus()
        notification_interface = QDBusInterface(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications",
            notification_bus,
        )

        def notification_action_invoked(notification_id: int, action: str) -> None:
            if notification_id in notification_ids.values() and action == "default":
                show_window()

        notification_bus.connect(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications",
            "ActionInvoked",
            notification_action_invoked,
        )
    except ImportError:
        LOGGER.warning("Qt D-Bus bindings are unavailable; update notifications are disabled")

    def send_notification(summary: str, body: str, kind: str, timeout: int) -> None:
        if notification_interface is None or not notification_interface.isValid():
            LOGGER.warning("Could not show update notification: desktop notification service unavailable")
            return

        if kind == "staged" and "available" in notification_ids:
            notification_interface.call("CloseNotification", notification_ids.pop("available"))

        previous_id = notification_ids.get(kind, 0)
        reply = notification_interface.call(
            "Notify", "cubelinux Updater", previous_id, "system-software-update",
            summary, body, ["default", "Open Updater"], {}, timeout,
        )
        if reply.type() == QDBusMessage.MessageType.ErrorMessage:
            LOGGER.warning("Could not show update notification: %s", reply.errorMessage())
            return
        arguments = reply.arguments()
        if arguments:
            notification_ids[kind] = int(arguments[0])

    icon = QIcon.fromTheme("system-software-update")
    app.setWindowIcon(icon)
    tray = KStatusNotifierItem("cubelinux-updater", app)
    tray.setCategory(KStatusNotifierItem.ItemCategory.ApplicationStatus)
    tray.setStatus(KStatusNotifierItem.ItemStatus.Passive)
    tray.setTitle("Updater")
    tray.setIconByName("system-software-update")
    tray.setToolTipTitle("Updater")
    tray.setToolTipIconByName("system-software-update")

    spinner_icons = create_spinner_icons()
    spinner_timer = QTimer(app)
    spinner_timer.setInterval(120)
    spinner_frame = 0

    def advance_spinner() -> None:
        nonlocal spinner_frame
        tray.setIconByPixmap(spinner_icons[spinner_frame])
        spinner_frame = (spinner_frame + 1) % len(spinner_icons)

    def set_tray_state(state: str) -> None:
        if state == "busy":
            tray.setStatus(KStatusNotifierItem.ItemStatus.Active)
            tray.setToolTipTitle("Updater")
            tray.setToolTipSubTitle("Working on your update")
            spinner_timer.start()
            return

        spinner_timer.stop()
        if state in ("idle", "checking"):
            tray.setIconByName("system-software-update")
            tray.setStatus(KStatusNotifierItem.ItemStatus.Passive)
            tray.setToolTipTitle("Updater")
            tray.setToolTipSubTitle("No update needs attention")
            return

        icon_name = {
            "available": "software-update-available",
            "staged": "system-reboot",
            "rebooting": "system-reboot",
            "error": "dialog-error",
        }.get(state, "system-software-update")
        tray.setIconByName(icon_name)
        tray.setStatus(
            KStatusNotifierItem.ItemStatus.NeedsAttention
            if state in ("available", "staged", "error")
            else KStatusNotifierItem.ItemStatus.Active
        )
        tooltip = {
            "available": "Updater: update available",
            "staged": "Updater: restart to finish installing the update",
            "rebooting": "Updater: restarting to finish the update",
            "error": "Updater: operation failed",
            "idle": "Updater",
        }
        tray.setToolTipIconByName(icon_name)
        tray.setToolTipTitle("Updater")
        tray.setToolTipSubTitle(tooltip.get(state, "Updater"))

    spinner_timer.timeout.connect(advance_spinner)
    update_controller.trayStateChanged.connect(set_tray_state)
    set_tray_state("idle")
    update_controller.notificationRequested.connect(send_notification)

    menu = QMenu()
    open_action = QAction("Open Updater", menu)
    open_action.triggered.connect(show_window)
    menu.addAction(open_action)
    tray.setContextMenu(menu)
    tray.setStandardActionsEnabled(False)
    tray.activateRequested.connect(lambda _active, _position: show_window())
    return tray
