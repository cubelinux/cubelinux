<p align="center">
  <img src="https://pub-eb590fbfc3074776ad4199c13b93d722.r2.dev/logo/icon.svg" alt="cubelinux logo" width="240">
</p>

<h1 align="center">cubelinux</h1>

<p align="center">A KDE Plasma desktop built for everyday computing.</p>

[![Build and publish bootc image](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml/badge.svg)](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml)

> [!WARNING]
> **Experimental software disclaimer:** cubelinux is pre-release software and is provided for evaluation and development. Components may be incomplete, unstable, or insufficiently validated. System behavior, image formats, update mechanisms, and configuration interfaces may change without backward compatibility. Failures may result in system unavailability or data loss. Deploy only in environments where you can recover or reinstall the system, maintain independent backups, and accept these risks. Use is at your own risk; the software is not suitable for production or safety-critical workloads.

## About cubelinux

cubelinux brings a complete desktop experience together in one operating
system. It starts with a first boot setup to create your user, then opens into
the KDE Plasma desktop with familiar tools like Dolphin.

The system includes an updater for checking and downloading cubelinux image
updates. When an update is ready, restart to complete the installation.

Virtual Shell provides a separate Fedora environment for running command-line
tools and graphical applications.

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
