# bootc-updater

A small KDE Plasma application for checking for and installing Fedora bootc
system updates.

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
running.

## Development notes

Keep privileged bootc operations out of the UI process. The implementation
should use a narrowly scoped authorization mechanism and report operation
progress and errors to the interface.

## Run the prototype

Install PySide6 and the Kirigami QML runtime module from your distribution,
then install the project with `python -m pip install --no-deps -e .` and launch
it with `bootc-updater`.

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
`data/bootc-updater-autostart.desktop` is intended for the system autostart
directory so it starts when the user's KDE session begins. Update notifications
are not implemented yet.

The Containerfile copies the Python/QML application, launcher, desktop entry,
and KDE session autostart entry directly into the image. Runtime dependencies
are listed in the root `packages.yml` manifest.
