#!/usr/bin/python3

"""Remove Discover from Plasma's system-provided launcher defaults."""

import re
from pathlib import Path


ROOTS = (
    Path("/usr/share/plasma/look-and-feel"),
    Path("/usr/share/plasma/layout-templates"),
    Path("/usr/share/plasma/shells/org.kde.plasma.desktop"),
    Path("/usr/share/plasma/plasmoids/org.kde.plasma.kicker"),
    Path("/usr/share/plasma/plasmoids/org.kde.plasma.kickoff"),
    Path("/usr/share/plasma/plasmoids/org.kde.plasma.kickerdash"),
    Path("/usr/share/kde-settings/kde-profile/default/share/config"),
)
TEXT_SUFFIXES = {".conf", ".js", ".rc", ".xml"}
APP_ID = r"(?:applications:)?org\.kde\.discover\.desktop"
ENTRY = rf"(?:\"{APP_ID}\"|'{APP_ID}'|{APP_ID})"


def without_entry(text: str) -> str:
    # Handle JS arrays and comma-separated KConfig favorites/launcher values.
    text = re.sub(rf"(?P<open>[\[,])\s*{ENTRY}\s*,", r"\g<open>", text)
    text = re.sub(rf"(?P<open>[\"'])\s*{APP_ID}\s*,", r"\g<open>", text)
    text = re.sub(rf",\s*{ENTRY}(?=\s*[\]\)\"'<])", "", text)
    return re.sub(ENTRY, "", text)


for root in ROOTS:
    if not root.exists():
        continue
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        updated = without_entry(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(f"Removed Discover launcher reference from {path}")
