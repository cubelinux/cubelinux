#!/bin/sh
set -eu

marker=/var/lib/cubelinux/flatpak-remotes-migrated
if [ -e "$marker" ]; then
    exit 0
fi

remote_names=$(/usr/bin/flatpak remotes --system --columns=name)
for remote in fedora fedora-testing; do
    if printf '%s\n' "$remote_names" | /usr/bin/grep -Fqx "$remote"; then
        /usr/bin/flatpak remote-modify --system --disable "$remote"
    fi
done

/usr/bin/install -D -m 0644 /dev/null "$marker"
