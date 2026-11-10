# cubelinux-vshell

`cubelinux-vshell` is the command and application ID for Linux Subsystem and its
container environments on the cubelinux Fedora bootc desktop host.

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

After Plasma Setup, VShell automatically prepares the Runtime on the user's
first KDE login and starts it on later logins. See **Image source** for image
pull and reset behavior.
slirp4netns gives the container outbound
connectivity without a host bridge, DHCP server, or veth permission. When Plasma
Setup creates the desktop account, a system hook
allocates that account's subordinate IDs, so a fresh installation does not
need another administrator password prompt in Linux Subsystem. Existing accounts
without this provisioning can use the one-time administrator setup for those IDs.
The `lxc-net` bridge service is disabled. Networking uses slirp4netns.
After initial account setup, the LXC instance's system files are mounted
read-only. `/tmp` and `/var` are temporary writable filesystems. The shared
`/home/<user>` is the only default persistent writable mount. VShell configures
Flathub as a user-scoped remote, and Flatpak user installs persist in the shared
home across Runtime resets; there is no persistent system Flatpak store.
Runtime also mounts a separate read-only procfs at
`/var/lib/cubelinux-vshell/proc`, allowing Flatpak's bubblewrap sandbox to
create its own procfs without relaxing the outer LXC security policy.
RPM/DNF changes to the guest system do not persist; use Flatpak for applications.
Programs in the container can read and modify files in the shared home folder.
The host user's runtime directory and X11 socket directory are also mounted so
terminal-launched applications can connect to the host's Wayland/XWayland,
D-Bus, and PipeWire/PulseAudio session. The host X11 directory is mounted outside
the guest's `/tmp` and linked back after Runtime mounts its temporary
filesystem there. The container user is mapped to the desktop user's host ID,
so those sockets accept connections as that user.

The optional Fedora environment is pulled from LXC's Fedora 44 image server when
the user selects **Create Fedora container**. It uses the LXC name `fedora` and
is stored under `~/.local/share/vshell/containers/fedora/`. Fedora's root
filesystem remains writable and persistent between starts, so DNF-installed
packages and system changes remain available until reset. It uses slirp4netns
for networking and shares the signed-in user's home, host desktop sockets, and
any additional folders selected in Fedora's environment settings. Fedora apps
are discovered for KDE launchers, and its TCP services use the same automatic
port forwarding and optional public exposure controls as Runtime.

**Reset Fedora** removes that container and immediately downloads a fresh Fedora
image from the LXC image server. DNF packages, system changes, additional
shared-folder settings, and public port choices are cleared; the host home and
its files remain.

Open an environment card's menu and choose **Environment settings** to view the
home folder share, add other host folders, and manage forwarded ports.
Additional folders are mounted read-write under
`/var/lib/vshell-shares/` inside that environment, subject to the host folder's
permissions. Changing folder shares restarts the selected environment when it
is running so LXC can apply the updated mounts. Resetting Runtime or Fedora
also removes that environment's additional folder-share settings.

Install graphical applications in Runtime with Discover's Flatpak backend. User
Flatpak installs live in the shared home, so they remain available when Runtime
is reset. Discover is available inside Runtime, and its Flatpak backend does not
change the read-only system image. VShell watches the Flatpak export directory
in the shared home and publishes root-owned KDE launcher wrappers alongside
the installed RPM application wrappers. A narrowly scoped Polkit helper
publishes these entries under `/usr/local/share/applications/cubelinux` so KDE
Kiosk can keep user-created application entries out of Kickoff while VShell
entries remain available. The host image bind-mounts that directory from
`/var/lib/cubelinux-vshell/applications`, since the bootc root filesystem is
read-only. Each launcher starts its app inside the environment that owns it, with the host
display/audio sockets and session environment. Flatpak launchers run the
selected app from the user's Flatpak installation; native launchers run the
matching desktop entry in that environment. Terminal-launched programs continue to work
as before.

While the KDE desktop session is running, its VShell watcher discovers Runtime
and Fedora TCP services listening on their container network interfaces at ports 1024 and
above and forwards them to the host at `localhost:<port>` through slirp4netns.
Services bound only to an environment's loopback address are not forwarded. Each
forwarded port has its own **Expose to public** option, off by default. slirp4netns
keeps these host-forwarding rules itself; VShell does not run a separate host TCP
proxy. The guest cannot connect to services bound only to the host's loopback.
Enabling it binds that port on all host IPv4 interfaces; the host firewall
still controls incoming connections, and VShell does not change firewall
rules. Ports below 1024 are not forwarded automatically, and manual forwarding
rules are not implemented yet.

The cubelinux Runtime card uses the same cubelinux logo as the desktop start
menu, rendered from the 256-pixel icon generated by the host image build. The
optional Fedora environment uses the Fedora icon. The About page includes
Fedora trademark attribution and states that VShell and cubelinux are not
affiliated with or endorsed by the Fedora Project or Red Hat.
Fedora® and the Fedora logo are trademarks or registered trademarks of Red Hat,
Inc., or its subsidiaries in the United States and other countries.

The container runs as an unprivileged user namespace. Container root maps to
subordinate host IDs; the Runtime user maps to the desktop user's own ID
so the shared home folder remains writable. The default LXC instance is named
`cubelinux-runtime` and is created under
`~/.local/share/vshell/containers/cubelinux-runtime`; its system files are read-only after setup. `/tmp` and
`/var` are ephemeral writable mounts; the shared home is the only default
persistent writable mount. User-scoped Flatpak metadata and app data therefore
remain available after a Runtime reset.

VShell is a tightly integrated workspace, not a desktop-app sandbox. Programs
inside Runtime can access the shared home folder and the host user's display,
audio, and session-bus sockets.

## Image source

The host image does not bundle the Runtime OCI image or a user-specific LXC
instance. At the first KDE login after Plasma Setup, VShell uses LXC's OCI
template to pull `ghcr.io/cubelinux/cubelinux-vshell-runtime:main` and create
the `cubelinux-runtime` instance. On first login, its setup window waits until
KDE Welcome Center closes before it starts preparing Runtime. This first setup
needs internet access. The
`:main` tag is mutable; **Reset Runtime** pulls the version currently published
under that tag without requiring a host image update. LXC uses a local layer
cache when available to reduce repeated downloads. When the new Runtime path
is incomplete, reset it from Linux Subsystem before creating Runtime again.

## Use

Open **Linux Subsystem** from the application menu to view or manage Runtime.
Choose **Open Runtime terminal** to open the bundled
Konsole in the Linux environment. Konsole's system default is locked to VShell,
its settings menu is disabled, and no separate host-shell profile is added. The
application menu provides a dedicated **Konsole (Runtime)** entry that opens
the same profile. If Runtime is not set up yet, this entry opens Linux
Subsystem to initialize it automatically without briefly opening an empty
Konsole. If the environment exists but is stopped, Konsole starts it when
opening the profile. KDE Kiosk hides Konsole's stock launcher, which requests
general shell access.

Closing Linux Subsystem while setup or destruction is running hides its window
while the operation continues. Open **Linux Subsystem** to bring the progress
window back. If the operation finishes successfully while hidden, the app exits;
if it fails, the window reopens with the error.

The installed `cubelinux-vshell` command also supports these operations:

```sh
cubelinux-vshell status
cubelinux-vshell enter
cubelinux-vshell stop
```

`cubelinux-vshell enter` starts the container if needed and opens a login shell
as the mapped Runtime user. The container user has passwordless `sudo` inside
the unprivileged container only; the read-only root prevents system changes
from persisting. `cubelinux-vshell stop` shuts down the container. Use **Reset
Runtime** in Linux Subsystem to recreate the LXC instance by pulling the
current `:main` runtime image from GHCR. Reset needs internet access. The shared
host home and user-installed Flatpak apps remain; guest-side RPM/DNF changes
and container settings are cleared.
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

## License

VShell's original source code is licensed under GPL-3.0-or-later. See the
repository's [LICENSE](../LICENSE) and [COPYRIGHT](../COPYRIGHT). Third-party
dependencies and bundled software retain their own licenses.
