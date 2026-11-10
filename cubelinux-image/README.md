<p align="center">
  <img src="https://pub-eb590fbfc3074776ad4199c13b93d722.r2.dev/logo/icon.svg" alt="cubelinux logo" width="240">
</p>

<h1 align="center">cubelinux</h1>

<p align="center">A KDE Plasma desktop built for everyday computing.</p>

[![Build and publish bootc image](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml/badge.svg)](https://github.com/cubelinux/cubelinux/actions/workflows/image-and-release.yml)

## About cubelinux

cubelinux brings a complete desktop experience together in one operating
system. It starts with a first boot setup to create your user, then opens into
the restricted KDE Plasma desktop.

The system includes an updater for checking and downloading cubelinux image
updates. When an update is ready, restart to complete the installation.

This kiosk experiment removes Flatpak and KDE Discover from the host image and
includes Dolphin for file management, pinned to the taskbar for new Plasma
profiles. KDE Kiosk disables shell access and Run Command, locks desktop
customization, and restricts user-defined application
launchers and autostart entries. Patched KIO blocks launching executable files
and user-created desktop launchers. Dolphin's terminal actions stay unavailable
while shell access is disabled. A dedicated Konsole launcher opens the locked
Fedora Virtual Shell profile; KDE hides Konsole's stock launcher, and the image
adds no separate host-shell profile. These are exploratory desktop
restrictions, not an operating-system security boundary.

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
|   |-- patches/                       # Downstream patches for image packages
|   |-- scripts/                       # Prepare, build, and verify image contents
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
- **`cubelinux-image/config/plasma/`** holds shared Plasma defaults. The Breeze
  applet setup defaults brand Kickoff and remove the Discover taskbar pin while
  pinning Dolphin as Plasma creates the initial panel for a new profile. They
  do not rewrite existing user profiles. Keep the selected global theme in
  `kdeglobals`.
- **`cubelinux-updater/component.toml`** and
  **`cubelinux-vshell/component.toml`** describe each app's image contribution:
  packages it needs, systemd services to enable, and files to install with
  their source path, destination, and mode. Components can also declare
  HTTPS downloads for assets that should only enter the image during builds.
  Keep each app's code and local assets in its own top-level folder.
- **`cubelinux-image/Containerfile`** contains shared image build operations.
  Do not add component-specific `COPY` statements or package lists here;
  declare those in the component manifest. It builds the installed KF6 KIO
  subpackages from the matching Fedora source RPM with the cubelinux kiosk
  launch policy patch in an intermediate stage, then installs those patched
  RPMs into the image.
- **`cubelinux-image/scripts/prepare_image.py`** validates configuration and
  manifests and creates `.image-build/`. That directory is generated and ignored
  by Git; do not edit or commit it.
- **`cubelinux-image/scripts/configure_distro.py`** applies the configured
  operating-system identity and logo. Keep distro branding values in
  `cubelinux-image/config/image.toml`.
- **`cubelinux-image/scripts/configure_plasma.py`** merges checked-in KDE
  defaults into the image during the build and applies the experimental Kiosk
  restrictions while preserving Fedora's other profile settings. The image's
  KF6 KIO patch permits root-owned desktop entries from system application
  directories while `run_desktop_files` is disabled, so user-created launchers
  remain blocked. It also blocks launching executable binaries such as AppImages
  and executable scripts through KIO's file-opening path.
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

The GitHub image workflow verifies the completed filesystem during the
BuildKit build, then rechunks the image by RPM content before publishing the
final OCI image to GHCR. Stable package layers can be reused by bootc clients
when another package changes. The published layers use standard OCI zstd
compression; the workflow does not enable the separate `zstd:chunked` format,
which is not currently supported by every bootc storage backend. The workflow
checks
`/usr/lib/os-release`, the configured logo, KDE's distro settings, and all
staged component files against the build inputs. The image is never started,
so its desktop services do not run during verification.

To inspect a locally built image, first run image preparation and build it with
Docker, then run:

```sh
python3 scripts/verify_image.py --image cubelinux:test
```

## Learn more

Visit [cubelinux.github.io](https://cubelinux.github.io) for more information.

## License

Original cubelinux image-builder source and configuration are licensed under
GPL-3.0-or-later; see the repository's [LICENSE](../LICENSE) and
[COPYRIGHT](../COPYRIGHT). Software included in a built image is distributed
under the license applicable to each component; this project license does not
change those terms.
