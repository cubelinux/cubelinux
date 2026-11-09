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
    BUNDLED_RUNTIME_OCI_IMAGE, CONTAINER_NAME, FEDORA_CONTAINER_NAME, GUEST_ID,
    ID_COUNT, VShellError,
    _account, _attach, _container_running, _config_path,
    _ensure_guest_x11_socket_path, _ensure_host_desktop_mounts,
    _ensure_slirp_config, _ensure_slirp_network, _escape_mount_path, _home,
    _lxc_path, _report, _rootfs_path, _rootless_scope, _run, _start_container,
    _stop_container, _wait_for_network, is_initialized,
)
from .shared_folders import clear_shared_folders, sync_saved_shared_folders
from .port_forwarding import clear_port_forwarding_settings

Progress = Callable[[str], None]
REMOTE_RUNTIME_OCI_IMAGE = "docker://ghcr.io/cubelinux/cubelinux-vshell-runtime:main"


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
        *_mapping_lines(uid_start, gid_start, account.pw_uid, account.pw_gid),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _remove_legacy_flatpak_mount(container_name: str = CONTAINER_NAME) -> bool:
    """Stop binding the old persistent system Flatpak store into Runtime."""
    config = _config_path(container_name)
    original = config.read_text(encoding="utf-8")
    kept = []
    for line in original.splitlines():
        fields = line.split()
        if (
            len(fields) >= 5
            and fields[:2] == ["lxc.mount.entry", "="]
            and fields[3] == "var/lib/flatpak"
        ):
            continue
        kept.append(line)
    updated = "\n".join(kept) + "\n"
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


def _mark_initialized(container_name: str = CONTAINER_NAME) -> None:
    """Record readiness only after all container and desktop setup succeeds."""
    config = _config_path(container_name)
    contents = config.read_text(encoding="utf-8")
    markers = ("# VShell home bind", "# VShell immutable Runtime rootfs")
    for marker in markers:
        if marker not in contents:
            contents = contents.rstrip() + "\n" + marker + "\n"
    config.write_text(contents, encoding="utf-8")


def initialize(
    progress: Progress = print,
    *,
    container_name: str = CONTAINER_NAME,
    pull_latest_runtime: bool = False,
) -> None:
    """Create or start an environment from the bundled image by default."""
    with _runtime_operation_lock(progress):
        _initialize_unlocked(
            progress,
            container_name=container_name,
            pull_latest_runtime=pull_latest_runtime,
        )


def _initialize_unlocked(
    progress: Progress,
    *,
    container_name: str = CONTAINER_NAME,
    pull_latest_runtime: bool = False,
) -> None:
    label = "Runtime" if container_name == CONTAINER_NAME else "Fedora"
    if is_initialized(container_name):
        changed = _ensure_slirp_config(container_name)
        changed = _remove_legacy_flatpak_mount(container_name) or changed
        config_path = _config_path(container_name)
        config_before = config_path.read_text(encoding="utf-8")
        sync_saved_shared_folders(container_name)
        changed = config_path.read_text(encoding="utf-8") != config_before or changed
        changed = _set_rootfs_readonly(container_name) or changed
        running = _container_running(progress, container_name)
        if changed and running:
            _report(progress, f"Applying {label} storage and network settings…")
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
    network_config_changed = _ensure_slirp_config(container_name)
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
        runtime_image = (
            REMOTE_RUNTIME_OCI_IMAGE
            if pull_latest_runtime
            else BUNDLED_RUNTIME_OCI_IMAGE
        )
        if pull_latest_runtime:
            _report(progress, f"Pulling the latest {label} image from GHCR…")
        else:
            target = "LXC Runtime" if container_name == CONTAINER_NAME else "Fedora container"
            _report(progress, f"Creating the {target} from cubelinux's bundled image…")
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
                            "--", "--url", runtime_image,
                        ]
                    ),
                    progress,
                    stream=True,
                )
            except VShellError as error:
                _remove_partial_container(root, container_name)
                if pull_latest_runtime:
                    raise VShellError(
                        f"Could not download or unpack the latest {label} image from GHCR. "
                        f"Check your internet connection and try again. Details: {error}"
                    ) from error
                raise VShellError(
                    f"Could not create {label} from the image bundled with cubelinux. "
                    "Repair or reinstall the host image, then try again. "
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
            "An incomplete older environment is present. Reset it before creating the OCI Runtime."
        )

    container_running = _container_running(progress, container_name)
    if container_running and network_config_changed:
        _report(progress, f"Updating {label}'s user-mode network…")
        _stop_container(progress, container_name)
        container_running = False
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


def create_fedora_environment(progress: Progress = print) -> None:
    """Create the optional Fedora environment from the bundled custom OCI image."""
    with _runtime_operation_lock(progress):
        container_path = _lxc_path() / FEDORA_CONTAINER_NAME
        if not is_initialized(FEDORA_CONTAINER_NAME) and (
            container_path.exists() or container_path.is_symlink()
        ):
            _report(progress, "Cleaning up the incomplete Fedora container…")
            _destroy_container_unlocked(progress, FEDORA_CONTAINER_NAME)
        # The Create action uses the same image shipped in the host image.
        # Network access is only needed for the optional Fedora user's Flathub
        # setup; container creation itself should work offline.
        _initialize_unlocked(progress, container_name=FEDORA_CONTAINER_NAME)


def reset_environment(container_name: str, progress: Progress = print) -> None:
    """Recreate one environment from the latest registry image."""
    with _runtime_operation_lock(progress):
        _destroy_container_unlocked(progress, container_name)
        _initialize_unlocked(
            progress,
            container_name=container_name,
            pull_latest_runtime=True,
        )


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
