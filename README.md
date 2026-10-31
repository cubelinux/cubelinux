<p align="center">
  <img src="https://pub-eb590fbfc3074776ad4199c13b93d722.r2.dev/logo/icon.svg" alt="cubelinux logo" width="240">
</p>

<h1 align="center">cubelinux</h1>

<p align="center">A KDE Plasma desktop built for everyday computing.</p>

[![Build and publish bootc image](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml/badge.svg)](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml)

## About cubelinux

cubelinux brings a complete desktop experience together in one operating
system. It starts with a first boot setup to create your user, then opens into
the KDE Plasma desktop with familiar tools like Dolphin and Konsole.

The system includes an updater for checking and downloading cubelinux image
updates. When an update is ready, restart to complete the installation. A
separate host terminal profile is available for system administration.

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
builds the image, verifies the result, and publishes it to GHCR.

See [the image-builder README](cubelinux-image/README.md),
[the updater README](cubelinux-updater/README.md), and
[the VShell README](cubelinux-vshell/README.md) for project-specific details.
