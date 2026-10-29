# cubelinux-updater

The KDE Plasma **Updater** app checks for and installs cubelinux system updates.

## UI stack

- Qt 6 Quick and QML for the interface
- KDE Kirigami for Plasma-native controls and adaptive layouts
- Python with PySide6 for application logic and the interface to bootc
- `pyproject.toml` and setuptools for Python packaging

KDE recommends Qt Quick and Kirigami for new KDE applications. Kirigami uses
QML and Qt Quick Controls, while keeping application logic separate from the
visual interface. KDE also provides a PySide6 setup path for Kirigami apps.

## Update flow

Select **Check for updates** to see whether an update is available. Select
**Update now** to download it; you can keep using your PC while it downloads.
When the download finishes, select **Restart now** and confirm to finish
installing the update. The app shows plain-language progress and error
messages, and shows a download percentage when bootc provides byte totals.
Preparing the update after download may take additional time, so that phase
uses an activity indicator. The tray icon animates while an operation is
running. Available or installed image version and build date are shown when
the image includes that metadata. Images built by this repository use
`YYYY-MM-DD+SHORTSHA` as the image version.

## Development notes

Keep privileged bootc operations out of the UI process. The implementation
should use a narrowly scoped authorization mechanism and report operation
progress and errors to the interface.

## Run the prototype

Install PySide6, the Kirigami QML runtime module, and the KDE Qt Quick Controls
desktop style from your distribution, then install the project with
`python -m pip install --no-deps -e .` and launch it with `cubelinux-updater`.

The app uses a root-owned helper with three fixed operations: check for system
updates, download the current update, and apply the downloaded update while
restarting. Other bootc commands and extra arguments are rejected. KDE may ask
you to authenticate unless the request comes from an active local session for
a user in the `wheel` administrator group. Those three operations are
authorized without a password for that session. Other bootc commands are not
authorized.
The app stays in the KDE system tray, can start hidden with `--background`, and
opens its window from the tray icon or KDE app launcher. Closing the window
hides it; the tray menu has no quit action, so the process stays active until
ended externally or the user session stops.
The updater window shows its software version at the bottom; it is currently
`0.0.0`.
Startup, QML, and update-operation diagnostics are written to
`~/.local/state/cubelinux-updater/cubelinux-updater.log` so failures from the hidden
autostart can be inspected after login.
`data/cubelinux-updater-autostart.desktop` is intended for the system autostart
directory so it starts when the user's KDE session begins. Update notifications
are not implemented yet.

### UI-only preview on Windows

The preview uses simulated update data. It does not start the tray, ask for
authorization, or call the Linux update helper. Install Python and PySide6,
then run this from the repository root in PowerShell:

```powershell
python .\main.py --preview
```

The root launcher adds `src` to Python's import path, so an editable project
install is not needed. On Windows, the preview uses a Qt Quick Controls screen
with the same layout because the production QML depends on KDE Kirigami. The
preview uses Qt's Fusion style; the regular Linux updater keeps the KDE desktop
style.

Available states are `ready`, `up-to-date`, `available`, `staged`, `checking`,
`downloading`, `preparing`, and `error`. The buttons simulate the flow: checking
shows an available update, downloading stages it, and restarting returns to the
up-to-date state.

The Containerfile copies the Python/QML application, launcher, desktop entry,
and KDE session autostart entry directly into the image. Runtime dependencies
are listed in the root `packages.yml` manifest.
