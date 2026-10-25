FROM quay.io/fedora/fedora-bootc:44 AS packagekit-bootc-builder

RUN dnf -y install gcc glib2-devel git meson ninja-build PackageKit-devel && dnf clean all

COPY packagekit-bootc.patch /tmp/packagekit-bootc.patch

RUN git clone --no-checkout https://github.com/FyraLabs/PackageKit-bootc.git /tmp/packagekit-bootc && \
    git -C /tmp/packagekit-bootc checkout --detach 7d82505b94ae5fc3388ef780520ca07dc9bdb994 && \
    git -C /tmp/packagekit-bootc submodule update --init --depth 1 && \
    git -C /tmp/packagekit-bootc apply /tmp/packagekit-bootc.patch && \
    meson setup /tmp/packagekit-bootc/builddir /tmp/packagekit-bootc --prefix=/usr --libdir=lib64 && \
    meson compile -C /tmp/packagekit-bootc/builddir && \
    meson install -C /tmp/packagekit-bootc/builddir

FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install --exclude=plasma-discover-flatpak ${PACKAGES} && dnf clean all

COPY --from=packagekit-bootc-builder /usr/lib64/packagekit-backend/libpk_backend_bootc.so /usr/lib64/packagekit-backend/libpk_backend_bootc.so
COPY --from=packagekit-bootc-builder /usr/share/PackageKit/helpers/bootc/bootcBackend.py /usr/share/PackageKit/helpers/bootc/bootcBackend.py
COPY PackageKit.conf /etc/PackageKit/PackageKit.conf
COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
