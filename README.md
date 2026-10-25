# Fedora 44 customized bootc image

This repository builds a customized Fedora 44 bootc image and pushes it to
GitHub Container Registry (GHCR). It also creates a compressed raw disk image
for each published GitHub Release.

## Container image builds

Every push to a branch builds the package list in `packages.yml` on top of
`quay.io/fedora/fedora-bootc:44`, then pushes the image to GHCR as:

```text
ghcr.io/OWNER/REPOSITORY:BRANCH
```

The branch name is lowercased and characters that are invalid in a container
tag are replaced with hyphens. The branch tag is updated on each push. Add or
remove Fedora RPM package names in `packages.yml` to customize the image.
The package list includes `dolphin`, `konsole`, `polkit`, `python3-pyside6`,
`kf6-kirigami`, `qt6-qtdeclarative`, `plasma-setup`, `plasma-nm`, `plasma-pa`,
`plasma-firewall`, `kscreen`, `NetworkManager-wifi`, `pipewire`, and
`pipewire-alsa`, plus `sddm`, `sddm-breeze`, and `sddm-wayland-plasma`. DNF
installs required dependencies, including `plasma-desktop`, `NetworkManager`,
`pipewire-pulseaudio`, WirePlumber, and the Plasma Firewall Firewalld backend.
System image updates can be staged from Konsole with `sudo bootc upgrade`;
they take effect after a reboot. Discover and its PackageKit, Flatpak, and
rpm-ostree backends are excluded. Add RPM packages to the image's package list
so they are included in the bootc image.
The image build installs `bootc-updater/` directly, along with its Python/QML
runtime dependencies. Its KDE launcher and session autostart entry make the
updater available from the app menu and system tray after login. The SDDM
Breeze theme is selected in `sddm-theme.conf`. The image enables
NetworkManager, Firewalld, SDDM and Plasma Setup and sets
`graphical.target` as the default. Plasma Setup runs before the login manager
on the first boot so you can create the initial user. After setup completes,
SDDM provides the login screen on later boots.

## Release disk image

Publish a GitHub Release for a version tag such as `v1.0.0`. The workflow
builds the customized image with the `v1.0.0` tag, then creates a raw disk from
that image. The raw disk is configured to check the moving `:main` image
tag for subsequent `bootc update` operations. The disk is compressed as
`.raw.zst` and attached with its SHA-256 checksum. Decompress it with:

```sh
zstd -d fedora-bootc-v1.0.0.raw.zst
```

GitHub Actions needs permission to write packages and release assets. The
workflow requests `packages: write` and `contents: write`; an organization
policy may also need to allow these permissions. Make the GHCR package public
if deployed machines should fetch updates without registry credentials.
