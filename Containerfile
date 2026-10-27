ARG BASE_IMAGE=quay.io/fedora/fedora-bootc:44
FROM ${BASE_IMAGE}

ARG PACKAGES

RUN dnf -y install \
        --exclude='plasma-discover*' \
        --exclude=PackageKit \
        ${PACKAGES} && \
    dnf clean all

COPY .image-build/distro.json /tmp/distro.json
COPY scripts/configure_distro.py /tmp/configure_distro.py
RUN python3 /tmp/configure_distro.py /tmp/distro.json && \
    rm -f /tmp/configure_distro.py /tmp/distro.json

# Plymouth must be present in the initramfs, which is shipped with the bootc image.
RUN set -eux; \
    kver="$(ls /usr/lib/modules)"; \
    env DRACUT_NO_XATTR=1 dracut -vf "/usr/lib/modules/${kver}/initramfs.img" "${kver}"; \
    bootc container lint

COPY .image-build/rootfs/ /

# Brand Plasma Setup's existing account page while retaining its AccountController
# and KAuth user-creation backend. Reorder the built-in Wi-Fi module to the front.
COPY setup/ /tmp/cubelinux-setup/
RUN python3 /tmp/cubelinux-setup/configure_plasma_setup.py && \
    rm -rf /tmp/cubelinux-setup

COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf
COPY bootc/kargs.d/10-quiet-boot.toml /usr/lib/bootc/kargs.d/10-quiet-boot.toml

COPY .image-build/services.txt /tmp/component-services.txt
RUN systemctl --root=/ enable NetworkManager.service firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    while IFS= read -r service; do \
        [ -z "$service" ] || systemctl --root=/ enable "$service"; \
    done < /tmp/component-services.txt && \
    systemctl --root=/ set-default graphical.target && \
    rm -f /tmp/component-services.txt
