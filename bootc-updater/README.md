# bootc-updater

A small KDE Plasma application for checking and staging Fedora bootc image
updates.

## UI stack

- Qt 6 Quick and QML for the interface
- KDE Kirigami for Plasma-native controls and adaptive layouts
- Python with PySide6 for application logic and the interface to bootc
- `pyproject.toml` and setuptools for Python packaging

KDE recommends Qt Quick and Kirigami for new KDE applications. Kirigami uses
QML and Qt Quick Controls, while keeping application logic separate from the
visual interface. KDE also provides a PySide6 setup path for Kirigami apps.

## Planned screen

Show the installed image and update status, with a clear action to stage an
available update. After staging, show that a reboot is needed to boot into the
updated image. Include progress and actionable error messages while checking or
staging updates.

## Development notes

Keep privileged bootc operations out of the UI process. The implementation
should use a narrowly scoped authorization mechanism and report operation
progress and errors to the interface.

## Run the prototype

Install PySide6 and the Kirigami QML runtime module from your distribution,
then install the project with `python -m pip install --no-deps -e .` and launch
it with `bootc-updater`.

The current screen is a UI prototype. Bootc status checks and update staging
are not connected yet. The app stays in the KDE system tray, can start hidden
with `--background`, and opens its window from the tray icon or KDE app
launcher. Closing the window hides it; the tray menu has no quit action, so the
process stays active until ended externally or the user session stops.
`data/bootc-updater-autostart.desktop` is intended for the system autostart
directory so it starts when the user's KDE session begins. Update notifications
will be connected when the update backend is implemented.

The Containerfile copies the Python/QML application, launcher, desktop entry,
and KDE session autostart entry directly into the image. Runtime dependencies
are listed in the root `packages.yml` manifest.
