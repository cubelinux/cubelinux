# Fedora 44 customized bootc image

This repository builds a customized Fedora 44 bootc image and pushes it to
GitHub Container Registry (GHCR).

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
`plasma-firewall`, `kscreen`, `kinfocenter`, `NetworkManager-wifi`, `pipewire`, and
`pipewire-alsa`, plus `sddm`, `sddm-breeze`, and `sddm-wayland-plasma`. DNF
installs required dependencies, including `plasma-desktop`, `NetworkManager`,
`pipewire-pulseaudio`, WirePlumber, and the Plasma Firewall Firewalld backend.
The bootc-updater can check for updates, stage a download-only deployment, and
apply it after a confirmed reboot; updates can also be staged from Konsole with
`sudo bootc upgrade`. Discover and its PackageKit, Flatpak, and
rpm-ostree backends are excluded. Add RPM packages to the image's package list
so they are included in the bootc image.
The image build installs `bootc-updater/` directly, along with its Python/QML
runtime dependencies. Its KDE launcher and session autostart entry make the
updater available from the app menu and system tray after login. The image
workflow labels published images with their build date and short commit ID, so
the updater can show the available image version and date. The SDDM Breeze
theme is selected in `sddm-theme.conf`. The image enables
NetworkManager, Firewalld, SDDM and Plasma Setup and sets
`graphical.target` as the default. Plasma Setup runs before the login manager
on the first boot so you can create the initial user. After setup completes,
SDDM provides the login screen on later boots.

GitHub Actions needs permission to write packages. Make the GHCR package public
if deployed machines should fetch updates without registry credentials.
