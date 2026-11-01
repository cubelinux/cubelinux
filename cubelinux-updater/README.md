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

Select **Check for updates** to see whether an update is available. Select
**Download update** to stage it; the PC remains usable while the image
downloads. When the download finishes, select **Restart now** and confirm to
apply it. The app shows plain-language progress and errors, a download
percentage when bootc reports byte totals, and image version and build-date
details when available. The release-notes link opens the cubelinux image
releases page.

## Security and session behavior

The desktop application requests only three fixed operations from the
root-owned helper: check for an update, download the current update, and apply
the staged update while restarting. Other bootc commands and extra arguments
are rejected. Polkit authorizes these operations for an active local session
whose user belongs to the `wheel` administrator group; other bootc operations
are not authorized by this app.

The updater stays in the KDE system tray and can start hidden with
`--background`. Closing its window hides it; the tray icon or app launcher can
reopen it. It starts with the user's KDE session. Diagnostics are written to
`~/.local/state/cubelinux-updater/cubelinux-updater.log`.

## Development

The intended development environment is the cubelinux KDE image, which
provides PySide6, Kirigami, and the KDE Qt Quick Controls style. Run the
application from the repository with:

```sh
PYTHONPATH=src python3 -m cubelinux_updater
```

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
