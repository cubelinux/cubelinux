# vshell

`vshell` is a KDE setup application and shell launcher for a persistent Fedora
LXC environment.

The wizard downloads a Fedora 44 LXC image, creates an unprivileged container,
and shares the signed-in user's home folder automatically. The host setup asks
for administrator authentication once to allocate subordinate IDs and enable
one LXC network interface for that user. Programs in the container can read
and modify files in the shared home folder.

The container runs as an unprivileged user namespace. Container root maps to
subordinate host IDs; the Fedora login user maps to the desktop user's own ID
so the shared home folder remains writable. The container has a persistent
root filesystem under `~/.local/share/vshell/containers`.

The image also provides a separate Konsole Host Terminal profile for host
administration. Konsole's default profile will be redirected to VShell after
the container startup backend is working.

## Image sources

The Fedora 44 system image is downloaded from the Linux Containers image
server using LXC's `download` template. OCI application images are not used as
system images.

## Use

Open **Virtual Shell** from the application menu and follow the short wizard.
Once setup completes, choose **Open Virtual Shell** to start a Konsole session
inside Fedora. Konsole also provides a **Virtual Shell** profile. The separate
**Host Terminal** profile remains available for host administration.
Opening the Virtual Shell profile before setup is complete launches the wizard.

The installed `vshell` command also supports these operations:

```sh
vshell status
vshell enter
vshell stop
```

`vshell enter` starts the container if needed and opens a login shell as the
mapped Fedora user. The container user has passwordless `sudo` inside the
unprivileged container only. `vshell stop` shuts down the persistent container.

## Run

The intended target is the KDE image, which already includes PySide6 and
Kirigami. From a development environment with those dependencies installed:

```sh
PYTHONPATH=src python3 -m vshell
```
