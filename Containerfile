FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install \
        --exclude='plasma-discover*' \
        --exclude=PackageKit \
        ${PACKAGES} && \
    dnf clean all

COPY distro.json /tmp/distro.json
COPY scripts/configure-distro.py /tmp/configure-distro.py
RUN python3 /tmp/configure-distro.py /tmp/distro.json && \
    rm -f /tmp/configure-distro.py /tmp/distro.json

# Plymouth must be present in the initramfs, which is shipped with the bootc image.
RUN set -eux; \
    kver="$(ls /usr/lib/modules)"; \
    env DRACUT_NO_XATTR=1 dracut -vf "/usr/lib/modules/${kver}/initramfs.img" "${kver}"; \
    bootc container lint

COPY bootc-updater/src/bootc_updater /usr/lib/bootc-updater/bootc_updater
COPY bootc-updater/bin/bootc-updater /usr/bin/bootc-updater
COPY bootc-updater/bin/bootc-updater-helper /usr/libexec/bootc-updater-helper
COPY bootc-updater/data/org.bootc.Updater.desktop /usr/share/applications/org.bootc.Updater.desktop
COPY vshell/src/vshell /usr/lib/vshell/vshell
COPY vshell/bin/vshell /usr/bin/vshell
COPY vshell/bin/vshell-host-setup /usr/libexec/vshell-host-setup
COPY vshell/data/org.vshell.desktop /usr/share/applications/org.vshell.desktop
COPY vshell/data/org.vshell.HostTerminal.desktop /usr/share/applications/org.vshell.HostTerminal.desktop
COPY vshell/data/VShell.profile /usr/share/konsole/VShell.profile
COPY vshell/data/HostTerminal.profile /usr/share/konsole/HostTerminal.profile
COPY vshell/data/lxc-sysconfig /etc/sysconfig/lxc
COPY vshell/data/org.vshell.LxcSetup.policy /usr/share/polkit-1/actions/org.vshell.LxcSetup.policy
COPY bootc-updater/data/bootc-updater-autostart.desktop /etc/xdg/autostart/bootc-updater-autostart.desktop
COPY bootc-updater/data/org.bootc.Updater.policy /usr/share/polkit-1/actions/org.bootc.Updater.policy
COPY bootc-updater/data/50-bootc-updater.rules /usr/share/polkit-1/rules.d/50-bootc-updater.rules

RUN chmod 0755 /usr/bin/bootc-updater /usr/libexec/bootc-updater-helper /usr/bin/vshell /usr/libexec/vshell-host-setup

COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf
COPY bootc/kargs.d/10-quiet-boot.toml /usr/lib/bootc/kargs.d/10-quiet-boot.toml

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable lxc-net.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
