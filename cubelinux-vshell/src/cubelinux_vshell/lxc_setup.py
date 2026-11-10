"""Create, configure, and reset the persistent cubelinux Runtime environment."""

from __future__ import annotations

import fcntl
import ipaddress
import os
import pwd
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from .lxc_backend import (
    CONTAINER_NAME, FEDORA_CONTAINER_NAME, FEDORA_RELEASE, GUEST_ID, ID_COUNT,
    VShellError, _arch, _account, _attach, _container_running, _config_path,
    _ensure_guest_x11_socket_path, _ensure_host_desktop_mounts,
    _ensure_slirp_network, _escape_mount_path, _home,
    _lxc_path, _report, _rootfs_path, _rootless_scope, _run, _start_container,
    _stop_container, _wait_for_network, is_initialized,
)
from .shared_folders import (
    clear_shared_folders,
    sync_saved_shared_folders,
)
from .port_forwarding import clear_port_forwarding_settings

Progress = Callable[[str], None]
REMOTE_RUNTIME_OCI_IMAGE = "docker://ghcr.io/cubelinux/cubelinux-vshell-runtime:main"
_NESTED_PROC_TARGET = "var/lib/cubelinux-vshell/proc"
_NESTED_PROC_ENTRY = (
    "lxc.mount.entry = proc "
    f"{_NESTED_PROC_TARGET} proc ro,nosuid,nodev,noexec,relatime,create=dir 0 0"
)


@contextmanager
def _runtime_operation_lock(progress: Progress) -> Iterator[None]:
    """Serialize lifecycle operations for all VShell environments."""
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    lock_dir = Path(runtime_dir) if runtime_dir else Path.home() / ".local/state/cubelinux-vshell"
    if (
        not lock_dir.is_absolute()
        or not lock_dir.is_dir()
        or not _is_owned_by_current_user(lock_dir)
    ):
        lock_dir = Path.home() / ".local/state/cubelinux-vshell"
    lock_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = lock_dir / "runtime-operation.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError as error:
        raise VShellError(f"Could not lock Runtime setup operations: {error}") from error
    with os.fdopen(descriptor, "r+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            _report(progress, "Waiting for another Runtime operation to finish…")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _is_owned_by_current_user(path: Path) -> bool:
    try:
        return path.stat().st_uid == os.getuid()
    except OSError:
        return False


def _find_subid_range(
    path: Path, account: pwd.struct_passwd, identity_id: int
) -> tuple[int, int] | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split(":")
        if len(fields) != 3 or fields[0] not in (account.pw_name, str(account.pw_uid)):
            continue
        try:
            start, count = int(fields[1]), int(fields[2])
        except ValueError:
            continue
        if count >= ID_COUNT and not start <= identity_id < start + count:
            return start, count
    return None


def _id_ranges(account: pwd.struct_passwd) -> tuple[tuple[int, int], tuple[int, int]]:
    uid_range = _find_subid_range(Path("/etc/subuid"), account, account.pw_uid)
    gid_range = _find_subid_range(Path("/etc/subgid"), account, account.pw_gid)
    if not uid_range or not gid_range:
        raise VShellError(
            "Virtual Shell could not find a 65,536-ID range for your account. "
            "Run setup again and approve the one-time LXC permission request."
        )
    return uid_range, gid_range


def _host_setup_ready(account: pwd.struct_passwd) -> bool:
    try:
        _id_ranges(account)
    except VShellError:
        return False
    return True


def _host_setup(progress: Progress) -> None:
    helper = "/usr/libexec/cubelinux-vshell-host-setup"
    pkexec = shutil.which("pkexec")
    if not pkexec or not Path(helper).is_file():
        raise VShellError(
            "The LXC host setup helper is missing. Install the current cubelinux image and try again."
        )
    _report(progress, "Requesting one-time permission to prepare rootless containers…")
    _run([pkexec, helper], progress, stream=True)


def _mapping_lines(uid_start: int, gid_start: int, uid: int, gid: int) -> list[str]:
    # Keep 50000 available for VShell's guest user and map it to the host user.
    tail_count = ID_COUNT - GUEST_ID - 1
    lines = [
        f"lxc.idmap = u 0 {uid_start} {GUEST_ID}",
        f"lxc.idmap = u {GUEST_ID} {uid} 1",
        f"lxc.idmap = u {GUEST_ID + 1} {uid_start + GUEST_ID} {tail_count}",
        f"lxc.idmap = g 0 {gid_start} {GUEST_ID}",
        f"lxc.idmap = g {GUEST_ID} {gid} 1",
        f"lxc.idmap = g {GUEST_ID + 1} {gid_start + GUEST_ID} {tail_count}",
    ]
    return lines


def _remove_partial_container(root: Path, container_name: str = CONTAINER_NAME) -> None:
    """Remove only the incomplete LXC directory left by a failed create."""
    container_path = root / container_name
    if not container_path.exists():
        if container_path.is_symlink():
            raise VShellError("Refusing to remove an unexpected LXC container path.")
        return
    resolved_root = root.resolve()
    resolved_container = container_path.resolve()
    if resolved_container.parent != resolved_root or resolved_container.name != container_name:
        raise VShellError("Refusing to remove an unexpected LXC container path.")
    shutil.rmtree(resolved_container)


def _write_create_config(
    path: Path,
    account: pwd.struct_passwd,
    uid_range: tuple[int, int],
    gid_range: tuple[int, int],
    container_name: str = CONTAINER_NAME,
) -> None:
    uid_start, _ = uid_range
    gid_start, _ = gid_range
    lines = [
        "# VShell runtime rootfs",
        # The lxc-oci template adds the installed common, userns, and OCI
        # configuration files after this initial config is written.
        f"lxc.uts.name = {container_name}",
        "lxc.net.0.type = empty",
        "lxc.mount.entry = tmpfs tmp tmpfs rw,create=dir,mode=1777 0 0",
        "lxc.mount.entry = tmpfs var tmpfs rw,create=dir,mode=0755 0 0",
        # A separate, clean procfs lets Flatpak's bubblewrap mount its own proc
        # without relaxing the outer LXC security policy.
        _NESTED_PROC_ENTRY,
        *_mapping_lines(uid_start, gid_start, account.pw_uid, account.pw_gid),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_fedora_create_config(
    path: Path,
    account: pwd.struct_passwd,
    uid_range: tuple[int, int],
    gid_range: tuple[int, int],
) -> None:
    """Create a mutable Fedora container using LXC's upstream download template."""
    uid_start, _ = uid_range
    gid_start, _ = gid_range
    lines = [
        "lxc.include = /usr/share/lxc/config/common.conf",
        f"lxc.uts.name = {FEDORA_CONTAINER_NAME}",
        "lxc.net.0.type = empty",
        *_mapping_lines(uid_start, gid_start, account.pw_uid, account.pw_gid),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_nested_proc_mount(container_name: str = CONTAINER_NAME) -> bool:
    """Expose a clean procfs mountpoint for nested Flatpak bubblewrap sandboxes."""
    config = _config_path(container_name)
    original = config.read_text(encoding="utf-8")
    lines = original.splitlines()

    for index, line in enumerate(lines):
        fields = line.split()
        if (
            len(fields) >= 5
            and fields[:2] == ["lxc.mount.entry", "="]
            and fields[3] == _NESTED_PROC_TARGET
        ):
            if line == _NESTED_PROC_ENTRY:
                return False
            lines[index] = _NESTED_PROC_ENTRY
            config.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True

    var_mount_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.split()[:5] == ["lxc.mount.entry", "=", "tmpfs", "var", "tmpfs"]
        ),
        len(lines) - 1,
    )
    lines.insert(var_mount_index + 1, _NESTED_PROC_ENTRY)
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _set_rootfs_readonly(container_name: str = CONTAINER_NAME) -> bool:
    """Protect the guest OS after its account and host mounts are configured."""
    config = _config_path(container_name)
    original = config.read_text(encoding="utf-8")
    lines = original.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("lxc.rootfs.options ="):
            options = [part.strip() for part in line.split("=", 1)[1].split(",")]
            options = [part for part in options if part and part != "rw"]
            if "ro" not in options:
                options.append("ro")
            lines[index] = "lxc.rootfs.options = " + ",".join(options)
            break
    else:
        lines.append("lxc.rootfs.options = ro")
    updated = "\n".join(lines) + "\n"
    if updated == original:
        return False
    config.write_text(updated, encoding="utf-8")
    return True


def _ensure_user_flathub(
    account: pwd.struct_passwd,
    progress: Progress,
    container_name: str = CONTAINER_NAME,
) -> None:
    """Configure Flathub in the shared guest home; tolerate offline startup."""
    attach = [
        "lxc-attach", "--name", container_name, "--lxcpath", str(_lxc_path()),
        "--clear-env", "--uid", str(GUEST_ID), "--gid", str(GUEST_ID),
        "--set-var", f"HOME=/home/{account.pw_name}",
        "--set-var", f"USER={account.pw_name}",
        "--set-var", f"LOGNAME={account.pw_name}",
        "--set-var", "PATH=/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/bin:/sbin",
    ]
    list_command = [
        *attach, "--", "/usr/bin/flatpak", "remotes", "--user", "--columns=name",
    ]
    try:
        listed = subprocess.run(
            list_command, capture_output=True, text=True, errors="replace",
        check=False, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    if listed.returncode != 0 or "flathub" in listed.stdout.splitlines():
        return

    _report(progress, "Setting up your Flathub app source?")
    add_command = [
        *attach, "--", "/usr/bin/flatpak", "remote-add", "--user",
        "--if-not-exists", "flathub",
        "https://dl.flathub.org/repo/flathub.flatpakrepo",
    ]
    try:
        result = subprocess.run(
            add_command, capture_output=True, text=True, errors="replace",
            check=False, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        _report(progress, "Flathub is unavailable; VShell will retry when opened again.")
        return
    if result.returncode:
        _report(progress, "Flathub is unavailable; VShell will retry when opened again.")


def _configure_guest(
    account: pwd.struct_passwd,
    progress: Progress,
    container_name: str = CONTAINER_NAME,
) -> None:
    username = account.pw_name
    script = (
        "set -eu; "
        f"if ! getent group {GUEST_ID} >/dev/null; then "
        f"groupadd --gid {GUEST_ID} {username}; fi; "
        f"if getent passwd {GUEST_ID} >/dev/null; then "
        f"test \"$(getent passwd {GUEST_ID} | cut -d: -f1)\" = {username}; "
        "else "
        f"useradd --uid {GUEST_ID} --gid {GUEST_ID} --create-home "
        f"--home-dir /home/{username} --shell /bin/bash {username}; fi; "
        f"usermod --append --groups wheel {username}; "
        "install -d -m 0750 /etc/sudoers.d; "
        "printf '%s\\n' '%wheel ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-vshell; "
        "chmod 0440 /etc/sudoers.d/90-vshell; "
        # The resolver address belongs to this LXC network, so write it after
        # LXC starts instead of changing BuildKit's mounted /etc/resolv.conf.
        "rm -f /etc/resolv.conf; "
        "printf '%s\\n' 'nameserver 10.0.2.3' > /etc/resolv.conf; "
        "systemd-machine-id-setup"
    )
    label = "Runtime" if container_name == CONTAINER_NAME else "Fedora"
    _report(progress, f"Preparing your {label} user and shell…")
    _attach("/usr/bin/bash", "-ceu", script, progress=progress, container_name=container_name)


def _configure_fedora_guest(account: pwd.struct_passwd, progress: Progress) -> None:
    """Prepare the mapped user in the mutable Fedora template container."""
    username = account.pw_name
    script = (
        "set -eu; "
        "rm -f /etc/resolv.conf; "
        "printf '%s\\n' 'nameserver 10.0.2.3' > /etc/resolv.conf; "
        "dns_ready=0; "
        "for attempt in 1 2 3 4 5; do "
        "if getent ahostsv4 mirrors.fedoraproject.org >/dev/null; then "
        "dns_ready=1; break; fi; sleep 2; done; "
        "if [ \"$dns_ready\" -ne 1 ]; then "
        "echo 'Could not reach Fedora package servers through slirp4netns.' >&2; exit 1; fi; "
        f"if ! getent group {GUEST_ID} >/dev/null; then "
        f"groupadd --gid {GUEST_ID} {username}; fi; "
        f"if getent passwd {GUEST_ID} >/dev/null; then "
        f"test \"$(getent passwd {GUEST_ID} | cut -d: -f1)\" = {username}; "
        "else "
        f"useradd --uid {GUEST_ID} --gid {GUEST_ID} --create-home "
        f"--home-dir /home/{username} --shell /bin/bash {username}; fi; "
        f"usermod --append --groups wheel {username}; "
        "dnf -y install sudo; "
        "install -d -m 0750 /etc/sudoers.d; "
        "printf '%s\\n' '%wheel ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-vshell; "
        "chmod 0440 /etc/sudoers.d/90-vshell; "
        "systemd-machine-id-setup"
    )
    _report(progress, "Preparing your Fedora user and DNF shell…")
    _attach(
        "/usr/bin/bash", "-ceu", script,
        progress=progress, container_name=FEDORA_CONTAINER_NAME,
    )


def _bind_home(account: pwd.struct_passwd, container_name: str = CONTAINER_NAME) -> None:
    config = _config_path(container_name)
    contents = config.read_text(encoding="utf-8")
    marker = "# VShell home bind"
    mount_line = (
        f"lxc.mount.entry = {_escape_mount_path(str(_home()))} "
        f"home/{account.pw_name} none bind,create=dir 0 0"
    )
    if marker in contents or mount_line in contents.splitlines():
        return
    config.write_text(contents.rstrip() + "\n" + mount_line + "\n", encoding="utf-8")


def _mark_initialized(
    container_name: str = CONTAINER_NAME,
    *,
    immutable: bool = True,
) -> None:
    """Record readiness only after all container and desktop setup succeeds."""
    config = _config_path(container_name)
    contents = config.read_text(encoding="utf-8")
    markers = ["# VShell home bind"]
    markers.append(
        "# VShell immutable Runtime rootfs"
        if immutable
        else "# VShell mutable Fedora rootfs"
    )
    for marker in markers:
        if marker not in contents:
            contents = contents.rstrip() + "\n" + marker + "\n"
    config.write_text(contents, encoding="utf-8")


def initialize(
    progress: Progress = print,
    *,
    container_name: str = CONTAINER_NAME,
) -> None:
    """Create or start Runtime or the optional mutable Fedora environment."""
    with _runtime_operation_lock(progress):
        if container_name == CONTAINER_NAME:
            _initialize_unlocked(progress, container_name=container_name)
        elif container_name == FEDORA_CONTAINER_NAME:
            _initialize_fedora_unlocked(progress)
        else:
            raise VShellError("Only Runtime and Fedora can be initialized.")


def _initialize_unlocked(
    progress: Progress,
    *,
    container_name: str = CONTAINER_NAME,
) -> None:
    label = "Runtime" if container_name == CONTAINER_NAME else "Fedora"
    if is_initialized(container_name):
        changed = _ensure_nested_proc_mount(container_name)
        config_path = _config_path(container_name)
        config_before = config_path.read_text(encoding="utf-8")
        sync_saved_shared_folders(container_name)
        changed = config_path.read_text(encoding="utf-8") != config_before or changed
        changed = _set_rootfs_readonly(container_name) or changed
        running = _container_running(progress, container_name)
        if changed and running:
            _report(progress, f"Applying {label} mount and storage settings…")
            _stop_container(progress, container_name)
            running = False
        if not running:
            _start_container(progress, container_name)
        else:
            _ensure_slirp_network(progress, container_name)
        _ensure_guest_x11_socket_path(progress, container_name)
        _ensure_user_flathub(_account(), progress, container_name)
        _report(progress, f"{label} is already set up.")
        return
    account = _account()
    lxc_create = shutil.which("lxc-create")
    if not lxc_create:
        raise VShellError("LXC is not installed. Update to the current cubelinux image and reboot.")

    if _host_setup_ready(account):
        _report(progress, "Rootless container ID mappings are ready.")
    else:
        _host_setup(progress)
    _report(progress, "Checking your rootless container ID mappings…")
    uid_range, gid_range = _id_ranges(account)
    root = _lxc_path()
    config_path = _config_path(container_name)
    rootfs = _rootfs_path(container_name)
    root.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        _report(progress, f"Pulling the {label} image from GHCR…")
        with tempfile.TemporaryDirectory(prefix="cubelinux-vshell-") as temporary:
            create_config = Path(temporary) / "lxc.conf"
            _write_create_config(
                create_config,
                account,
                uid_range,
                gid_range,
                container_name,
            )
            try:
                _run(
                    _rootless_scope(
                        [
                            lxc_create,
                            "--name", container_name,
                            "--lxcpath", str(root),
                            "--config", str(create_config),
                            "--template", "oci",
                            "--", "--url", REMOTE_RUNTIME_OCI_IMAGE,
                        ]
                    ),
                    progress,
                    stream=True,
                )
            except VShellError as error:
                _remove_partial_container(root, container_name)
                raise VShellError(
                    f"Could not download or unpack the {label} image from GHCR. "
                    "Check your internet connection and try again. "
                    f"Details: {error}"
                ) from error
        if not (rootfs / "usr/lib/systemd/systemd").is_file():
            _remove_partial_container(root, container_name)
            raise VShellError(
                f"The {label} image did not contain systemd. "
                "The container was cleaned up; try again or report the image build issue."
            )
    elif "# VShell runtime rootfs" not in config_path.read_text(encoding="utf-8"):
        raise VShellError(
            "The existing container is incomplete or is not the cubelinux Runtime image. "
            "Reset it before creating Runtime."
        )

    container_running = _container_running(progress, container_name)
    if not container_running:
        _report(progress, f"Starting {label} for first-time setup…")
        _start_container(progress, container_name)
    else:
        _ensure_slirp_network(progress, container_name)

    _wait_for_network(progress, container_name)
    _configure_guest(account, progress, container_name)
    _report(progress, f"Sharing your home folder with {label}…")
    _bind_home(account, container_name)
    sync_saved_shared_folders(container_name)
    _report(progress, f"Connecting {label} to your desktop session...")
    _ensure_host_desktop_mounts(account, container_name)

    # Add the host-specific account and sudo policy before locking the rootfs.
    # Then restart with only the shared home retained as persistent writable data.
    _set_rootfs_readonly(container_name)
    _report(progress, f"Restarting {label} with its read-only system…")
    _stop_container(progress, container_name)
    _start_container(progress, container_name)
    _ensure_guest_x11_socket_path(progress, container_name)
    _ensure_user_flathub(account, progress, container_name)
    _mark_initialized(container_name)
    _report(progress, f"{label} is ready.")


def destroy_container(
    progress: Progress = print,
    *,
    container_name: str = CONTAINER_NAME,
) -> None:
    """Remove the guest rootfs without recreating it."""
    with _runtime_operation_lock(progress):
        _destroy_container_unlocked(progress, container_name)


def reset_runtime(progress: Progress = print) -> None:
    """Recreate Runtime from the latest registry image as one locked operation."""
    reset_environment(CONTAINER_NAME, progress)


def _set_rootfs_writable(container_name: str) -> bool:
    """Remove a read-only rootfs option from the mutable Fedora guest."""
    config = _config_path(container_name)
    original = config.read_text(encoding="utf-8")
    lines = original.splitlines()
    changed = False
    for index, line in enumerate(lines):
        if not line.strip().startswith("lxc.rootfs.options ="):
            continue
        options = [part.strip() for part in line.split("=", 1)[1].split(",")]
        writable_options = [option for option in options if option and option != "ro"]
        updated_line = "lxc.rootfs.options = " + ",".join(writable_options or ["rw"])
        if updated_line != line:
            lines[index] = updated_line
            changed = True
        break
    if changed:
        config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def _initialize_fedora_unlocked(progress: Progress) -> None:
    """Create Fedora from LXC's download template with persistent system files."""
    container_name = FEDORA_CONTAINER_NAME
    account = _account()
    config_path = _config_path(container_name)
    root = _lxc_path()

    if is_initialized(container_name):
        changed = False
        config_before = config_path.read_text(encoding="utf-8")
        sync_saved_shared_folders(container_name)
        changed = config_path.read_text(encoding="utf-8") != config_before or changed
        changed = _ensure_host_desktop_mounts(account, container_name) or changed
        changed = _set_rootfs_writable(container_name) or changed
        running = _container_running(progress, container_name)
        if changed and running:
            _report(progress, "Applying Fedora mount and desktop settings…")
            _stop_container(progress, container_name)
            running = False
        if not running:
            _start_container(progress, container_name)
        else:
            _ensure_slirp_network(progress, container_name)
        _ensure_guest_x11_socket_path(progress, container_name)
        _report(progress, "Fedora is already set up.")
        return

    container_path = root / container_name
    if container_path.exists() or container_path.is_symlink():
        _report(progress, "Cleaning up an incomplete Fedora container…")
        _destroy_container_unlocked(progress, container_name)

    lxc_create = shutil.which("lxc-create")
    if not lxc_create:
        raise VShellError("LXC is not installed. Update the cubelinux image and reboot.")

    if _host_setup_ready(account):
        _report(progress, "Rootless container ID mappings are ready.")
    else:
        _host_setup(progress)
    _report(progress, "Checking your rootless container ID mappings…")
    uid_range, gid_range = _id_ranges(account)
    root.mkdir(parents=True, exist_ok=True)

    _report(progress, f"Downloading Fedora {FEDORA_RELEASE} from the LXC image server…")
    with tempfile.TemporaryDirectory(prefix="cubelinux-fedora-") as temporary:
        create_config = Path(temporary) / "lxc.conf"
        _write_fedora_create_config(create_config, account, uid_range, gid_range)
        try:
            _run(
                _rootless_scope(
                    [
                        lxc_create,
                        "--name", container_name,
                        "--lxcpath", str(root),
                        "--config", str(create_config),
                        "--template", "download",
                        "--", "--dist", "fedora",
                        "--release", FEDORA_RELEASE,
                        "--arch", _arch(),
                        "--flush-cache",
                    ]
                ),
                progress,
                stream=True,
            )
        except VShellError as error:
            _remove_partial_container(root, container_name)
            raise VShellError(
                "Could not download Fedora from the LXC image server. "
                "Check your internet connection and try again. "
                f"Details: {error}"
            ) from error

    rootfs = _rootfs_path(container_name)
    if not (rootfs / "usr/lib/systemd/systemd").is_file():
        _remove_partial_container(root, container_name)
        raise VShellError(
            "The Fedora image did not contain systemd. The container was removed; try again."
        )

    _report(progress, "Starting Fedora for first-time setup…")
    _start_container(progress, container_name)
    _wait_for_network(progress, container_name)
    _configure_fedora_guest(account, progress)
    _report(progress, "Sharing your home folder with Fedora…")
    _bind_home(account, container_name)
    sync_saved_shared_folders(container_name)
    _report(progress, "Connecting Fedora to your desktop session…")
    _ensure_host_desktop_mounts(account, container_name)

    _report(progress, "Restarting Fedora to apply your shared folders…")
    _stop_container(progress, container_name)
    _start_container(progress, container_name)
    _ensure_guest_x11_socket_path(progress, container_name)
    _mark_initialized(container_name, immutable=False)
    _report(progress, "Fedora is ready.")


def create_fedora_environment(progress: Progress = print) -> None:
    """Create or start the Fedora environment."""
    with _runtime_operation_lock(progress):
        _initialize_fedora_unlocked(progress)


def reset_environment(container_name: str, progress: Progress = print) -> None:
    """Recreate Runtime or Fedora from its configured image source."""
    with _runtime_operation_lock(progress):
        if container_name == CONTAINER_NAME:
            _destroy_container_unlocked(progress, container_name)
            _initialize_unlocked(progress, container_name=container_name)
        elif container_name == FEDORA_CONTAINER_NAME:
            _destroy_container_unlocked(progress, container_name)
            _initialize_fedora_unlocked(progress)
        else:
            raise VShellError("Only Runtime and Fedora can be reset.")


def _destroy_container_unlocked(
    progress: Progress,
    container_name: str = CONTAINER_NAME,
) -> None:
    """Remove one guest rootfs while the lifecycle lock is held."""
    label = "Runtime" if container_name == CONTAINER_NAME else "Fedora"
    root = _lxc_path()
    if not is_initialized(container_name):
        container_path = root / container_name
        if not container_path.exists() and not container_path.is_symlink():
            _stop_container(progress, container_name)
            clear_shared_folders(container_name)
            clear_port_forwarding_settings(container_name)
            _report(progress, f"The {label} environment is already reset.")
            return
        if _container_running(progress, container_name):
            _report(progress, f"Stopping the incomplete {label} container…")
        _stop_container(progress, container_name)
        _report(progress, f"Cleaning up the incomplete {label} container…")
        _remove_partial_container(root, container_name)
        clear_shared_folders(container_name)
        clear_port_forwarding_settings(container_name)
        return

    if _container_running(progress, container_name):
        _report(progress, f"Stopping {label} before reset…")
    _stop_container(progress, container_name)

    _report(progress, f"Resetting {label}'s system filesystem…")
    _run(
        _rootless_scope(
            [
                "lxc-destroy",
                "--name",
                container_name,
                "--lxcpath",
                str(root),
                "--force",
            ]
        ),
        progress,
        stream=True,
    )
    clear_shared_folders(container_name)
    clear_port_forwarding_settings(container_name)
