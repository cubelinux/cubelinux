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

### Image repository layout

Keep image assembly files in this repository and application code in the
companion repositories. The image workflow fetches the pinned components and
stages only what their manifests declare.

```text
cubelinux/
|-- .github/workflows/
|   `-- image-and-release.yml   # Build and publish the bootc image
|-- bootc/
|   `-- kargs.d/                # Shared bootc kernel arguments
|-- config/
|   |-- image.toml              # Image defaults, shared packages, components
|   |-- sddm-theme.conf         # Shared display-manager theme
|   `-- plasma/                 # Shared KDE defaults and first-login branding
|       |-- kdeglobals          # Default Breeze global theme
|       |-- cubelinux-kickoff-branding.py
|       `-- cubelinux-kickoff-branding.desktop
|-- scripts/
|   |-- configure_distro.py     # Apply distro identity and logo in the image
|   |-- configure_plasma.py     # Set Plasma defaults during image build
|   |-- prepare_image.py        # Fetch, validate, and stage components
|   `-- verify_image.py        # Inspect files in a built image
|-- tests/
|   `-- test_image_builder.py   # Offline tests for image preparation behavior
|-- Containerfile               # Image build steps; no component-specific paths
`-- README.md
```

The updater and VShell remain separate repositories. Each has a root-level
`component.toml` alongside its application files:

```text
cubelinux-updater/ or cubelinux-vshell/
|-- component.toml
|-- src/
|-- bin/
`-- data/
```

### What belongs where

- **`config/image.toml`** is the source of truth for the Fedora base image,
  shared packages, distro branding, and included component revisions. The
  image build renders `distro.logo.url` as a 64px launcher icon and a 256px
  About page icon. It downloads `distro.plymouth_logo.url` and converts that
  SVG into the PNG watermark included in the initramfs. Use `main` to follow a
  component's latest main branch or a full commit hash to pin an exact
  revision. The builder logs the commit it fetched for each component.
- **`config/plasma/`** holds shared Plasma defaults and first-login appearance
  assets. Keep the selected global theme in `kdeglobals`; the launcher helper
  only updates the panel button after Plasma creates the user's panel.
- **`component.toml`** describes one companion app's image contribution:
  packages it needs, systemd services to enable, and files to install with
  their source path, destination, and mode. Keep application logic and its
  desktop assets in that component's own repository.
- **`Containerfile`** contains shared image build operations. Do not add
  component-specific `COPY` statements or package lists here; declare those in
  the component manifest.
- **`scripts/prepare_image.py`** validates configuration and manifests and
  creates `.image-build/`. That directory is generated and ignored by Git; do
  not edit or commit it.
- **`scripts/configure_distro.py`** applies the configured operating-system
  identity and logo. Keep distro branding values in `config/image.toml`.
- **`scripts/configure_plasma.py`** merges the checked-in KDE defaults into the
  image during the build, preserving Fedora's other profile settings.
- **`bootc/` and `config/`** hold settings shared by the base system and
  desktop, not files owned by one optional component.

Component manifests currently support files under `/usr` or `/etc`, package
names, and systemd unit names. Sources must be relative to the component repo.
Use explicit entries and avoid adding installer scripts or arbitrary commands
to the image configuration.

### Adding or updating a component

1. Add or update the component's `component.toml` in its own repository.
2. Commit and publish that component change.
3. Add a `[[components]]` entry to `config/image.toml`, or update its `revision`
   to `"main"` to track the latest main branch or to a full commit hash to pin
   an exact version. The component ID must match the repository suffix: for
   example, `id = "updater"` maps to `cubelinux/cubelinux-updater`.
4. To exclude a component from an image, remove its `[[components]]` entry.
   The workflow discovers components from this config; it needs no separate
   checkout or `COPY` edits.

Publish component changes before building the image so a `main` revision can
fetch them. Builds that follow `main` can change when component repositories
change; use commit hashes when you need reproducible image inputs.

### Run image-builder tests

The unit tests use Python's standard library and do not build the Fedora image
or require network access:

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
