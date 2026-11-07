<p align="center">
  <img src="https://pub-eb590fbfc3074776ad4199c13b93d722.r2.dev/logo/icon.svg" alt="cubelinux logo" width="240">
</p>

<h1 align="center">cubelinux</h1>

<p align="center">A KDE Plasma desktop built for everyday computing.</p>

[![Build and publish bootc image](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml/badge.svg)](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml)

> [!WARNING]
>
> **Experimental project.** cubelinux is a study project and case study in
> AI-assisted (“vibe-coded”) operating-system development. It is intended for
> learning and evaluation, not production. AI-assisted changes may be
> incomplete or incorrect.
>
> **No warranty.** The project is made available in the hope that it will be
> useful, but is provided “as is,” without warranties of any kind, express or
> implied, including merchantability or fitness for a particular purpose. See
> [LICENSE](LICENSE) for the full terms.
>
> **Operational risks.** Components may be incomplete, unstable, or
> insufficiently validated. System behavior, image formats, update mechanisms,
> and configuration interfaces may change without backward compatibility.
> Failures may make the system unavailable or cause data loss. Use only where
> you can recover or reinstall the system and keep independent backups.
> cubelinux is not suitable for production or safety-critical workloads.

## About cubelinux

cubelinux brings a complete desktop experience together in one operating
system. It starts with a first boot setup to create your user, then opens into
the restricted KDE Plasma desktop.

This kiosk study removes Flatpak, KDE Discover, and Dolphin from the host
image. KDE Kiosk disables shell access and Run Command, locks desktop
customization, and restricts user-defined application launchers and autostart
entries. A dedicated Konsole launcher opens the locked Fedora Virtual Shell
profile; KDE hides Konsole's stock launcher, and the image adds no separate
host-shell profile. These settings guide the desktop interface; they do not
confine commands run by an allowed application.

The system includes an updater for checking and downloading cubelinux image
updates. When an update is ready, restart to complete the installation.

Virtual Shell provides a separate Fedora environment for running command-line
tools and graphical applications.

## Published system image

The bootc system image is published to GitHub Container Registry as
[`ghcr.io/cubelinux/cubelinux`](https://github.com/cubelinux/cubelinux/pkgs/container/cubelinux).
Pull the moving `latest` tag with:

```sh
podman pull ghcr.io/cubelinux/cubelinux:latest
```

The image workflow publishes these tags:

- `:latest` is updated on every successful image workflow run, including builds
  from any branch or tag, so it may contain experimental changes.
- Branch or Git ref tags, such as `:main`.
- Full and short commit tags, such as `:sha-<full-commit>` and
  `:sha-<short-commit>`.
- A semantic version tag such as `v1.2.3` publishes `:v1.2.3` plus `:1.2.3`,
  `:1.2`, and `:1`.

## Monorepo layout

The cubelinux monorepo contains the bootc image builder, updater, and VShell.
Each project keeps its own source and component manifest in a top-level folder.

```text
cubelinux/
|-- cubelinux-image/
|-- cubelinux-updater/
`-- cubelinux-vshell/
```

The GitHub Actions image workflow runs when any of these project folders
changes. It stages updater and VShell files from the local component folders,
builds and verifies the image, rechunks it by RPM content, and publishes the
final OCI image to GHCR.

See [the image-builder README](cubelinux-image/README.md),
[the updater README](cubelinux-updater/README.md), and
[the VShell README](cubelinux-vshell/README.md) for project-specific details.

## License

Original cubelinux source code and image-builder materials are licensed under
GPL-3.0-or-later; see [LICENSE](LICENSE) and [COPYRIGHT](COPYRIGHT). The built image includes Fedora
and other third-party software that retains its own license. This repository's
license does not relicense those components.
