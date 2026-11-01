"""Updater scheduling and preview constants."""

AUTO_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
AUTO_CHECK_RETRY_SECONDS = 60 * 60
AUTO_CHECK_STARTUP_DELAY_MS = 90_000
AUTO_DOWNLOAD_RETRY_MS = 30 * 60 * 1000
PREVIEW_STATES = (
    "ready",
    "up-to-date",
    "available",
    "staged",
    "checking",
    "downloading",
    "preparing",
    "error",
)
