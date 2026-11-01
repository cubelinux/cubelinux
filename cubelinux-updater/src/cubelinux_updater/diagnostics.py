"""Application logging and Qt message forwarding."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QtMsgType

LOGGER = logging.getLogger("cubelinux_updater")


def configure_logging() -> Path | None:
    """Write startup and operation diagnostics to the user's state directory."""
    try:
        log_dir = Path.home() / ".local" / "state" / "cubelinux-updater"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "cubelinux-updater.log",
            maxBytes=1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOGGER.setLevel(logging.INFO)
        LOGGER.addHandler(handler)
        LOGGER.info("Starting cubelinux-updater (arguments: %s)", sys.argv[1:])
        return log_dir / "cubelinux-updater.log"
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
