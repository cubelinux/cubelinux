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
tools. It is under active development while its unprivileged container setup
and networking are completed.

## System foundation

cubelinux is based on Fedora and built with bootc. The operating system is
delivered and updated as a complete system image.

### Monorepo layout

Image assembly, the updater, and VShell live in one repository. Component
sources stay in their own top-level directories, and the image builder stages
only the files declared by each component manifest.

```text
cubelinux/
|-- .github/workflows/image-and-release.yml
|-- cubelinux-image/
|   |-- bootc/kargs.d/                 # Shared bootc kernel arguments
|   |-- config/                        # Base image, packages, Plasma defaults
|   |-- scripts/                       # Prepare and verify image contents
|   |-- tests/                         # Image-builder unit tests
|   |-- Containerfile
|   `-- README.md
|-- cubelinux-updater/                 # Updater source and component.toml
`-- cubelinux-vshell/                  # VShell source and component.toml
```

### What belongs where

- **`cubelinux-image/config/image.toml`** is the source of truth for the Fedora
  base image, shared packages, distro branding, and included local components.
  The image build renders `distro.logo.url` as a 64px launcher icon and a 256px
  About page icon. It downloads `distro.plymouth_logo.url` and converts that
  SVG into the PNG watermark included in the initramfs.
- **`cubelinux-image/config/plasma/`** holds shared Plasma defaults and
  first-login appearance assets. Keep the selected global theme in `kdeglobals`;
  the launcher helper only updates the panel button after Plasma creates the
  user's panel.
- **`cubelinux-updater/component.toml`** and
  **`cubelinux-vshell/component.toml`** describe each app's image contribution:
  packages it needs, systemd services to enable, and files to install with
  their source path, destination, and mode. Keep each app's code and assets in
  its own top-level folder.
- **`cubelinux-image/Containerfile`** contains shared image build operations.
  Do not add component-specific `COPY` statements or package lists here;
  declare those in the component manifest.
- **`cubelinux-image/scripts/prepare_image.py`** validates configuration and
  manifests and creates `.image-build/`. That directory is generated and ignored
  by Git; do not edit or commit it.
- **`cubelinux-image/scripts/configure_distro.py`** applies the configured
  operating-system identity and logo. Keep distro branding values in
  `cubelinux-image/config/image.toml`.
- **`cubelinux-image/scripts/configure_plasma.py`** merges checked-in KDE
  defaults into the image during the build, preserving Fedora's other profile
  settings.
- **`cubelinux-image/bootc/` and `cubelinux-image/config/`** hold settings
  shared by the base system and desktop, not files owned by one app.

Component manifests currently support files under `/usr` or `/etc`, package
names, and systemd unit names. Sources must be relative to the component folder.
Use explicit entries and avoid adding installer scripts or arbitrary commands
to the image configuration.

### Adding or updating a component

1. Update the app and its `component.toml` in `cubelinux-updater/` or
   `cubelinux-vshell/`.
2. The image workflow runs automatically when either component folder changes.
3. `cubelinux-image/config/image.toml` selects components by local path. Remove
   its `[[components]]` entry to exclude a component from the image.

### Run image-builder tests

Run these commands from the `cubelinux-image/` directory. The unit tests use
Python's standard library and do not build the Fedora image or require network
access:

```sh
python3 -m unittest discover -s tests -v
```

They cover component file and asset staging, executable modes, optional
component omission, safe destinations, distro `os-release` replacement, and
logo rasterization at launcher and About page sizes. These are fast unit tests
that use temporary files.

The GitHub image workflow also performs an end-to-end filesystem check. It
builds the image locally, creates a **stopped** Docker container from it, copies
out `/usr/lib/os-release`, the configured logo, KDE's distro settings, and all
staged component files, then compares their contents and modes with the build
inputs. It also checks that Plasma Setup's installed account page matches the
cubelinux source. It publishes the image only after those checks pass. The
image is never started, so its desktop services do not run during verification.

To inspect a locally built image, first run image preparation and build it with
Docker, then run:

```sh
python3 scripts/verify_image.py --image cubelinux:test
```

## Learn more

Visit [cubelinux.github.io](https://cubelinux.github.io) for more information.
