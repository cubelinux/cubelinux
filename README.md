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
The package list includes `dolphin`, `konsole`, `lxc`, `lxc-templates`, `polkit`,
`python3-pyside6`, `kf6-kirigami`, `qt6-qtdeclarative`, `plasma-setup`,
`plasma-nm`, `plasma-pa`, `plasma-firewall`, `kscreen`, `kinfocenter`,
`plymouth`, `plymouth-system-theme`, `fedora-logos`, `NetworkManager-wifi`,
`pipewire`, `pipewire-alsa`, `shadow-utils`, `sddm`, `sddm-breeze`, and
`sddm-wayland-plasma`. DNF installs required dependencies, including
`plasma-desktop`, `NetworkManager`, `pipewire-pulseaudio`, WirePlumber, and the
Plasma Firewall Firewalld backend.
LXC and its distro image templates are included for the VShell project. The
container creation backend still needs to configure and verify per-user UID/GID
mappings and networking before it can create unprivileged shells.
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

Konsole has a separate Host Terminal profile and launcher for host
administration, including commands such as `sudo bootc upgrade`. The default
Konsole shell remains unchanged until VShell can start and manage its LXC
environment.

The image adds the `rhgb` and `quiet` kernel arguments through
`/usr/lib/bootc/kargs.d/10-quiet-boot.toml` so Plymouth can show a graphical
boot splash while routine boot messages stay hidden. GRUB menu visibility is
controlled by the installer or disk-image generation configuration.

GitHub Actions needs permission to write packages. Make the GHCR package public
if deployed machines should fetch updates without registry credentials.
