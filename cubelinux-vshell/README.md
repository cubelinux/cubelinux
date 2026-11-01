# cubelinux-vshell

`cubelinux-vshell` is the command and application ID for Linux Subsystem and its
persistent Fedora LXC environment on the cubelinux Fedora bootc desktop host.

## Python and KDE stack

Linux Subsystem is a cubelinux application integrated with KDE Plasma. The
application is written in Python with **PySide6**, Qt 6 Quick/QML, and KDE
Kirigami. PySide6 is Qt's official Python binding, and KDE documents it as a
supported way to build Kirigami applications. KDE also maintains Python
bindings for selected KDE Frameworks; bindings are not available for every
Framework and must match the target system's Qt version.

Use PySide6 for Qt APIs and Kirigami/QML for the interface. When application
logic needs a KDE Framework API, prefer its KDE-supported Python binding if
one exists and is packaged for the target system. Do not assume all Framework
APIs have Python bindings.

## Design direction

The interface should follow KDE's [Human Interface Guidelines](https://develop.kde.org/hig/)
strongly while keeping cubelinux's own identity. Prefer Kirigami and standard
Qt/KDE controls, familiar action placement, clear status and error messages,
keyboard access, accessible labels, and translatable user-facing text. Adapt
layouts to the window instead of relying on fixed positioning. Use cubelinux
names and visual assets; do not imply that Linux Subsystem is an official KDE
product.

The wizard downloads a Fedora 44 LXC image, creates an unprivileged container,
and shares the signed-in user's home folder automatically. The system image
starts the LXC bridge and configures its firewall access. When Plasma Setup
creates the desktop account, a system hook allocates that account's subordinate
IDs and one LXC network interface permission, so a fresh installation does not
need another administrator password prompt in Linux Subsystem. Existing accounts
without this provisioning can still use the one-time administrator setup.
Programs in the container can read and modify files in the shared home folder.
The host user's runtime directory and X11 socket directory are also mounted so
terminal-launched applications can connect to the host's Wayland/XWayland,
D-Bus, and PipeWire/PulseAudio session. The host X11 directory is mounted outside
the guest's `/tmp` and linked back after the Fedora guest mounts its temporary
filesystem there. The container user is mapped to the desktop user's host ID,
so those sockets accept connections as that user.

Open the Fedora environment card's menu and choose **Environment settings** to
view the home folder share, add other host folders, and manage forwarded ports.
Additional folders are mounted read-write under
`/mnt/vshell-shares/` inside Fedora, subject to the host folder's permissions.
Changing folder shares restarts Fedora when it is running so LXC can apply the
updated mounts. Destroying Fedora also removes its additional folder-share
settings.

Install graphical applications inside Fedora with DNF. VShell discovers their
system desktop entries and adds matching launchers to the host application menu
with “(Fedora)” in the name. The KDE session watcher refreshes those entries
after packages are installed or removed, and each launcher starts the app inside
the Fedora container with the host display/audio sockets and session environment.
For example, install `vlc`; the Fedora launcher will appear in the host menu.
Terminal-launched programs continue to work as before.

While the KDE desktop session is running, its VShell watcher discovers Fedora
TCP services listening on the container network interface at ports 1024 and
above and forwards them to the host at `localhost:<port>`. Services bound only
to Fedora's loopback address are not reachable by the host proxy. Each
forwarded port has its own **Expose to public** option, off by default.
Enabling it binds that port on all host IPv4 interfaces; the host firewall
still controls incoming connections, and VShell does not change firewall
rules. Ports below 1024 are not forwarded automatically, and manual forwarding
rules are not implemented yet.

The setup card uses Fedora's SVG logo from the `fedora-logos` package already
included in the bootc image; it is available locally at runtime and is not
downloaded when VShell starts.

The container runs as an unprivileged user namespace. Container root maps to
subordinate host IDs; the Fedora login user maps to the desktop user's own ID
so the shared home folder remains writable. The container has a persistent
root filesystem under `~/.local/share/vshell/containers`. That existing data
location and LXC container name stay unchanged so configured environments are
preserved when the command is renamed.

VShell is a tightly integrated workspace, not a desktop-app sandbox. Programs
inside Fedora can access the shared home folder and the host user's display,
audio, and session-bus sockets.

## Image sources

The Fedora 44 system image is downloaded from the Linux Containers image
server using LXC's `download` template. OCI application images are not used as
system images.

## Use

Open **Linux Subsystem** from the application menu and follow the short wizard.
Once setup completes, choose **Open terminal** to open the system's configured
terminal emulator directly into Fedora. A terminal emulator must be installed
and configured on the host. For a Flatpak terminal, VShell forwards the entry
command to the host with `flatpak-spawn`, then attaches to Fedora there. The
terminal Flatpak must allow host commands; Flathub Konsole already requests
that permission. Linux Subsystem does not change the default terminal or
install terminal-emulator-specific profiles; launching a terminal from the
desktop continues to open a host shell.

Closing Linux Subsystem while setup or destruction is running hides its window while
the operation continues. Open **Linux Subsystem** to bring the progress window
back. If the operation finishes successfully while hidden,
the app exits; if it fails, the window reopens with the error.

The installed `cubelinux-vshell` command also supports these operations:

```sh
cubelinux-vshell status
cubelinux-vshell enter
cubelinux-vshell stop
```

`cubelinux-vshell enter` starts the container if needed and opens a login shell
as the mapped Fedora user. The container user has passwordless `sudo` inside
the unprivileged container only. `cubelinux-vshell stop` shuts down the
persistent container. Use **Destroy Fedora environment** in Linux Subsystem to
permanently delete the container, including installed packages, container
settings, and files stored in its filesystem. The shared host home folder and
the cached Fedora template remain untouched. After destruction, Linux
Subsystem returns to its setup wizard; use it to create a new environment when
you are ready. LXC reuses the cached template when one is available.
Open **About Linux Subsystem** from the right-side application menu to see the
app version, project links, Qt build and runtime versions, PySide6, KDE
Frameworks/Kirigami, Plasma, Python, distribution, kernel, and architecture
versions.

## Development

The intended development environment is the cubelinux KDE image, which
provides PySide6, Kirigami, and the KDE Qt Quick Controls style. Launch VShell
from a development environment with those dependencies installed:

```sh
PYTHONPATH=src python3 -m cubelinux_vshell
```

## Official development references

- [KDE Python application with Kirigami](https://develop.kde.org/docs/getting-started/python/python-app/)
- [KDE Python bindings for selected Frameworks](https://develop.kde.org/docs/getting-started/python/python-bindings/)
- [KDE Human Interface Guidelines](https://develop.kde.org/hig/)
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6.11/index.html)
