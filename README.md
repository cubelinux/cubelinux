# cubelinux-vshell

`cubelinux-vshell` is the command and application ID for Setup Terminal and its
persistent Fedora LXC environment on the cubelinux Fedora bootc desktop host.

The wizard downloads a Fedora 44 LXC image, creates an unprivileged container,
and shares the signed-in user's home folder automatically. The system image
starts the LXC bridge and configures its firewall access. When Plasma Setup
creates the desktop account, a system hook allocates that account's subordinate
IDs and one LXC network interface permission, so a fresh installation does not
need another administrator password prompt in Setup Terminal. Existing accounts
without this provisioning can still use the one-time administrator setup.
Programs in the container can read and modify files in the shared home folder.
The host user's runtime directory and X11 socket directory are also mounted so
terminal-launched applications can connect to the host's Wayland/XWayland,
D-Bus, and PipeWire/PulseAudio session. The host X11 directory is mounted outside
the guest's `/tmp` and linked back after the Fedora guest mounts its temporary
filesystem there. The container user is mapped to the desktop user's host ID,
so those sockets accept connections as that user.

Install graphical applications inside Fedora with DNF, then start them from the
VShell terminal. For example, install `vlc` and run `vlc`. The app and its
toolkit libraries come from the container's Fedora repositories; VShell passes
the host display/audio sockets and the session environment needed to use them.
Applications are not automatically exported to the host application menu yet.
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

Open **Setup Terminal** from the application menu and follow the short wizard.
Once setup completes, choose **Open terminal** to start a Konsole session
inside Fedora. Before setup is complete, the Konsole launcher opens Setup
Terminal directly. After setup, Konsole uses the **Terminal** profile by
default, which opens Fedora. The separate **Host Terminal** profile remains
available for host administration.

Closing Setup Terminal while setup or reset is running hides its window while
the operation continues. Open **Setup Terminal** or **Konsole** to bring the
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
persistent container. Use **Reset Fedora environment** in Setup Terminal to
delete and recreate the container. Reset permanently removes installed
packages, container settings, and files in the container filesystem. The shared
host home folder remains untouched. During reset, VShell asks LXC to check for
a newer Fedora 44 image and reuse the cached image if it is still current. If an
update check fails, it retries with the cached image. When a newer image is
downloaded, LXC replaces the previous cached image.
Open **About Setup Terminal** from the hamburger menu to see the application
version and project information.

## Run

The intended target is the KDE image, which includes PySide6, Kirigami, and
the KDE Qt Quick Controls style. From a development environment with those
dependencies installed:

```sh
PYTHONPATH=src python3 -m cubelinux_vshell
```
