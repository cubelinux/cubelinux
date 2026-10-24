FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install ${PACKAGES} && dnf clean all

RUN systemctl --root=/ enable sddm.service && \
    systemctl --root=/ set-default graphical.target
