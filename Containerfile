FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install ${PACKAGES} && dnf clean all

COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
