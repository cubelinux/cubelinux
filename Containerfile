FROM quay.io/fedora/fedora-bootc:44

ARG PACKAGES

RUN dnf -y install \
        --exclude='plasma-discover*' \
        --exclude=PackageKit \
        ${PACKAGES} && dnf clean all

RUN find /usr/share/plasma /usr/share/kde-settings /etc/xdg /etc/skel \
        -type f \( -name '*.conf' -o -name '*.js' -o -name '*.json' -o -name '*.rc' -o -name '*.xml' \) \
        -exec sed -i -E \
            -e "s/[\"']?(applications:)?org\\.kde\\.discover\\.desktop[\"']?,[[:space:]]*//g" \
            -e "s/,[[:space:]]*[\"']?(applications:)?org\\.kde\\.discover\\.desktop[\"']?//g" \
            -e 's/(applications:)?org\.kde\.discover\.desktop//g' {} +

COPY remove-discover-shortcut.service /etc/systemd/system/remove-discover-shortcut.service

RUN systemctl --root=/ enable remove-discover-shortcut.service

COPY sddm-theme.conf /etc/sddm.conf.d/10-theme.conf

RUN systemctl --root=/ enable NetworkManager.service && \
    systemctl --root=/ enable firewalld.service && \
    systemctl --root=/ enable --force sddm.service && \
    systemctl --root=/ enable plasma-setup.service && \
    systemctl --root=/ set-default graphical.target
