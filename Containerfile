FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install \
        --exclude='plasma-discover*' \
        --exclude=PackageKit \
        ${PACKAGES} && dnf clean all

COPY remove-discover-shortcuts.py /tmp/remove-discover-shortcuts.py

RUN python3 /tmp/remove-discover-shortcuts.py && rm -f /tmp/remove-discover-shortcuts.py

COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
