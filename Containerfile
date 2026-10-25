FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install \
        --exclude='plasma-discover*' \
        --exclude=PackageKit \
        ${PACKAGES} && \
    dnf clean all

COPY bootc-updater/src/bootc_updater /usr/lib/bootc-updater/bootc_updater
COPY bootc-updater/bin/bootc-updater /usr/bin/bootc-updater
COPY bootc-updater/bin/bootc-updater-helper /usr/libexec/bootc-updater-helper
COPY bootc-updater/data/org.bootc.Updater.desktop /usr/share/applications/org.bootc.Updater.desktop
COPY bootc-updater/data/bootc-updater-autostart.desktop /etc/xdg/autostart/bootc-updater-autostart.desktop
COPY bootc-updater/data/org.bootc.Updater.policy /usr/share/polkit-1/actions/org.bootc.Updater.policy
COPY bootc-updater/data/50-bootc-updater.rules /usr/share/polkit-1/rules.d/50-bootc-updater.rules

RUN chmod 0755 /usr/bin/bootc-updater /usr/libexec/bootc-updater-helper

COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf
COPY bootc/kargs.d/10-quiet-boot.toml /usr/lib/bootc/kargs.d/10-quiet-boot.toml

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
