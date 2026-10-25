FROM quay.io/fedora/fedora-bootc:44 AS discover-bootc-builder

RUN dnf -y install cmake gcc-c++ git kf6-ki18n-devel plasma-discover-libs qt6-qtbase-devel && dnf clean all

RUN git clone --no-checkout https://invent.kde.org/plasma/discover.git /tmp/discover && \
    git -C /tmp/discover checkout --detach fad44d8193c47f2b085a080cfcfb3b6f00fff28e

COPY discover-bootc-backend /tmp/discover-bootc-backend

RUN cmake -S /tmp/discover-bootc-backend -B /tmp/discover-bootc-backend/build \
        -DDISCOVER_SOURCE_DIR=/tmp/discover -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release && \
    cmake --build /tmp/discover-bootc-backend/build --parallel && \
    cmake --install /tmp/discover-bootc-backend/build

FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install \
        --exclude=plasma-discover-flatpak \
        --exclude=plasma-discover-packagekit \
        --exclude=plasma-discover-rpm-ostree \
        --exclude=PackageKit \
        ${PACKAGES} && dnf clean all

COPY --from=discover-bootc-builder /usr/lib64/qt6/plugins/discover/bootc-backend.so /usr/lib64/qt6/plugins/discover/bootc-backend.so
COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
