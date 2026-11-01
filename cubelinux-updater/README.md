# cubelinux Updater

The cubelinux Updater checks for and installs operating system updates built
from the cubelinux bootc image.

## Python and KDE stack

The application is written in Python with **PySide6**, Qt 6 Quick/QML, and KDE
Kirigami. PySide6 is Qt's official Python binding. KDE documents PySide6 and
Kirigami as a supported way to build Python applications. The tray uses KDE's
official **KStatusNotifierItem** Python binding, packaged as
`python3-kf6-kstatusnotifieritem` on Fedora. KDE also maintains Python
bindings for selected other Frameworks; these are not available for every
Framework and must match the Qt version provided by the distribution.

Use PySide6 for Qt APIs and Kirigami/QML for the interface. When application
logic needs a KDE Framework API, prefer its KDE-supported Python binding if
that binding exists and is packaged for the target system. Do not assume all
Framework APIs have Python bindings.

## Design direction

The interface should follow KDE's [Human Interface Guidelines](https://develop.kde.org/hig/)
strongly while keeping cubelinux's own identity. Prefer Kirigami and standard
Qt/KDE controls, familiar action placement, clear status and error messages,
keyboard access, accessible labels, and translatable user-facing text. Adapt
layouts to the window instead of relying on fixed positioning. Use cubelinux
names and visual assets; do not imply that the app is an official KDE product.

## Update flow

The updater starts in the background with the KDE session. After the desktop
has settled, it checks for updates and repeats the check daily. It also checks
after each login. The check only fetches image metadata. When an update is
available, the updater downloads and stages it automatically on a connection
that NetworkManager identifies as unmetered. On a metered or unknown
connection, it waits and shows the update in the Updater app; selecting
**Download update** starts the download immediately. A failed download leaves
the current system running and can be retried from the app.

When staging finishes, a desktop notification and a system-tray update
indicator offer a way to open Updater. The tray indicator is hidden
when no update needs attention. Select **Restart now** in Updater and confirm
to boot into the staged image; the updater never restarts the PC by itself.
It verifies the current image on the next login. The app shows plain-language
progress and errors, a download percentage when bootc reports byte totals, and
image version and build-date details when available. The release-notes link
opens the cubelinux image releases page.

## Security and session behavior

The desktop application requests only three fixed operations from the
root-owned helper: check for an update, download the current update, and apply
the staged update while restarting. Other bootc commands and extra arguments
are rejected. Polkit authorizes these operations for an active local session
whose user belongs to the `wheel` administrator group; other bootc operations
are not authorized by this app.

The updater process stays in the KDE session to perform scheduled checks.
Its system-tray item is passive while current and appears when an update needs
attention. Closing its window hides it; the application menu can reopen it.
Diagnostics are written to
`~/.local/state/cubelinux-updater/cubelinux-updater.log`.

The right-side application menu opens **About Updater**, which shows project
links and app, Qt, PySide6, KDE Frameworks/Kirigami, Plasma, Python, operating
system, kernel, and architecture versions.

## Development

The intended development environment is the cubelinux KDE image, which
provides PySide6, Kirigami, and the KDE Qt Quick Controls style. Run the
application from the repository with:

```sh
PYTHONPATH=src python3 -m cubelinux_updater
```

The Python package keeps application startup in `main.py`, update state and
bootc operations in `controller.py`, tray and notification behavior in
`tray.py`, session activation in `activation.py`, and preview startup in
`preview.py`. Logging and About-page system details live in `diagnostics.py`
and `system_info.py`.

The updater also has a UI-only preview with simulated update states. On
Windows, run it from the project directory with:

```powershell
python .\src\cubelinux_updater\main.py --preview
```

The preview never invokes the privileged helper or runs bootc operations. On
Windows it uses a Qt Quick Controls preview screen because the production
interface imports KDE Kirigami. The Linux preview uses the production QML.

The image installs runtime dependencies from
`cubelinux-image/config/image.toml`; component files and system integration
are declared in `component.toml`.

## Official development references

- [KDE Python application with Kirigami](https://develop.kde.org/docs/getting-started/python/python-app/)
- [KDE Python bindings for selected Frameworks](https://develop.kde.org/docs/getting-started/python/python-bindings/)
- [KDE Human Interface Guidelines](https://develop.kde.org/hig/)
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6.11/index.html)
