# cubelinux-vshell

`cubelinux-vshell` is the command and application ID for Setup Terminal and its
persistent Fedora LXC environment.

The wizard downloads a Fedora 44 LXC image, creates an unprivileged container,
and shares the signed-in user's home folder automatically. The system image
starts the LXC bridge and configures its firewall access. When Plasma Setup
creates the desktop account, a system hook allocates that account's subordinate
IDs and one LXC network interface permission, so a fresh installation does not
need another administrator password prompt in Setup Terminal. Existing accounts
without this provisioning can still use the one-time administrator setup.
Programs in the container can read and modify files in the shared home folder.

The container runs as an unprivileged user namespace. Container root maps to
subordinate host IDs; the Fedora login user maps to the desktop user's own ID
so the shared home folder remains writable. The container has a persistent
root filesystem under `~/.local/share/vshell/containers`. That existing data
location and LXC container name stay unchanged so configured environments are
preserved when the command is renamed.

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

The installed `cubelinux-vshell` command also supports these operations:

```sh
cubelinux-vshell status
cubelinux-vshell enter
cubelinux-vshell stop
```

`cubelinux-vshell enter` starts the container if needed and opens a login shell
as the mapped Fedora user. The container user has passwordless `sudo` inside
the unprivileged container only. `cubelinux-vshell stop` shuts down the
persistent container.
The setup window shows the application version at the bottom; it is currently
`0.0.0`.

## Run

The intended target is the KDE image, which includes PySide6, Kirigami, and
the KDE Qt Quick Controls style. From a development environment with those
dependencies installed:

```sh
PYTHONPATH=src python3 -m cubelinux_vshell
```
