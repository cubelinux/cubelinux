# vshell

`vshell` is a KDE application for setting up and opening a persistent Fedora
environment managed with LXC.

The initial setup is intentionally simple: Fedora is the only image choice,
and the signed-in user's home folder is shared automatically. Users do not
need to choose a distribution or enter a folder path.

The current version is still a UI prototype. It does not create or start
containers yet. The setup button remains disabled until the LXC backend and
Fedora unprivileged-user setup are ready.

The image also provides a separate Konsole Host Terminal profile for host
administration. Konsole's default profile will be redirected to VShell after
the container startup backend is working.

## Image sources

The planned first supported source is an LXC system image (for example, a
Fedora image from the Linux Containers image server). LXC does not directly
launch a registry OCI image as a system container. An OCI image can be
converted/unpacked into a root filesystem and supplied with LXC configuration,
but that conversion must account for image layers, metadata, entrypoint, users,
and container init behavior.

Incus, a system-container manager built on LXC, can launch OCI registry images
as **application containers**. That runs the image's application entrypoint;
it is different from a full distribution environment intended to provide an
interactive Linux shell. Incus can also launch system containers from its own
Linux distribution images. For the initial vshell workflow, use an
LXC-compatible distro root filesystem. OCI system-image import/conversion can
be designed as a later feature.

## UI prototype

The Qt Quick/Kirigami screen guides the user through a short setup wizard:

- welcome and explain the container environment;
- show Fedora and automatic home-folder sharing as fixed defaults;
- review the setup before continuing;
- finish setup (currently disabled until the backend is ready).

## Run

The intended target is the KDE image, which already includes PySide6 and
Kirigami. From a development environment with those dependencies installed:

```sh
PYTHONPATH=src python3 -m vshell
```
