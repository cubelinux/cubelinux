# cubelinux-vshell

`cubelinux-vshell` is the command and application ID for Linux Subsystem and its
persistent Fedora LXC environment on the cubelinux Fedora bootc desktop host.

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

The Fedora environment settings show the home folder share and let you add
other host folders. Additional folders are mounted read-write under
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

The image also provides a separate Konsole Host Terminal profile for host
administration.

## Image sources

The Fedora 44 system image is downloaded from the Linux Containers image
server using LXC's `download` template. OCI application images are not used as
system images.

## Use

Open **Linux Subsystem** from the application menu and follow the short wizard.
Once setup completes, choose **Open terminal** to start a Konsole session
inside Fedora. Before setup is complete, the Konsole launcher opens Setup
Terminal directly. After setup, Konsole uses the **Terminal** profile by
default, which opens Fedora. The separate **Host Terminal** profile remains
available for host administration.

Closing Linux Subsystem while setup or destruction is running hides its window while
the operation continues. Open **Linux Subsystem** or **Konsole** to bring the
progress window back. If the operation finishes successfully while hidden,
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
Open **About Linux Subsystem** from the hamburger menu to see the application
version and project information.

## Run

The intended target is the KDE image, which includes PySide6, Kirigami, and
the KDE Qt Quick Controls style. From a development environment with those
dependencies installed:

```sh
PYTHONPATH=src python3 -m cubelinux_vshell
```
