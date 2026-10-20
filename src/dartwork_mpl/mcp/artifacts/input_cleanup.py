"""FD-relative private input namespace guards and common revocation barriers.

Only this capability's fixed names are removable. Unknown/unsafe residue is
never traversed or recursively removed. The local fault seam models process
failures at actual filesystem operations, not a replacement storage backend.
"""

import os
import stat
from contextlib import suppress

PAYLOAD_NAMES = tuple(f"{index:03d}.bin" for index in range(8))
MEMBER_NAMES = frozenset((*PAYLOAD_NAMES, "inputs.json", ".revoked"))


def _fault(point: str) -> None:
    """Local injection seam immediately before a named real filesystem barrier."""


def identity(fd: int) -> tuple[int, int]:
    """Return the identity of an already-open object without reopening its name."""
    info = os.fstat(fd)
    return info.st_dev, info.st_ino


def signature(fd: int) -> tuple[int, ...]:
    """Include security and content-change indicators, excluding read access time."""
    info = os.fstat(fd)
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_uid,
        info.st_mode,
        info.st_nlink,
    )


def guard(fd: int, directory: bool = False) -> None:
    """Require an operator-owned exact private mode and single-link regular file."""
    info = os.fstat(fd)
    valid = (
        stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    )
    if (
        not valid
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
        or (not directory and info.st_nlink != 1)
    ):
        raise OSError("Unsafe private input object")


def binding(parent: int, name: str, fd: int, directory: bool = False) -> None:
    """Verify both the pinned object's guards and its current no-follow entry."""
    guard(fd, directory)
    entry = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if (entry.st_dev, entry.st_ino) != identity(fd):
        raise OSError("Input namespace changed")


def open_set(root: int, name: str) -> int:
    """Open one prevalidated namespace with no-follow and private-directory checks."""
    fd = os.open(
        name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root
    )
    try:
        binding(root, name, fd, True)
    except BaseException:
        os.close(fd)
        raise
    return fd


def open_member(folder: int, name: str, flags: int = os.O_RDONLY) -> int:
    """Open a fixed regular private member; never follow a symlink or block FIFO."""
    if name not in MEMBER_NAMES and name != ".lock":
        raise ValueError("Not a private fixed member")
    fd = os.open(
        name,
        flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY,
        0o600,
        dir_fd=folder,
    )
    try:
        binding(folder, name, fd)
    except BaseException:
        os.close(fd)
        raise
    return fd


def absent(root: int, name: str) -> bool:
    """Prove a no-follow namespace entry absent, preserving operational failures."""
    try:
        os.stat(name, dir_fd=root, follow_symlinks=False)
    except FileNotFoundError:
        return True
    return False


def write_all(fd: int, content: bytes) -> None:
    """Complete bounded metadata/marker writes or fail without partial success."""
    offset = 0
    while offset < len(content):
        written = os.pwrite(fd, content[offset:], offset)
        if written <= 0:
            raise OSError("Private metadata write failed")
        offset += written


def _mark(root: int, name: str, folder: int) -> None:
    """Atomically create or re-persist revocation before any payload unlink."""
    binding(root, name, folder, True)
    _fault("marker_create")
    try:
        marker = open_member(
            folder, ".revoked", os.O_RDWR | os.O_CREAT | os.O_EXCL
        )
    except FileExistsError:
        marker = open_member(folder, ".revoked", os.O_RDWR)
    try:
        if os.fstat(marker).st_size > 1:
            raise OSError("Unsafe revocation marker")
        _fault("marker_write")
        write_all(marker, b"1")
        _fault("marker_fsync")
        os.fsync(marker)
        binding(folder, ".revoked", marker)
        _fault("set_marked_fsync")
        os.fsync(folder)
        binding(root, name, folder, True)
    finally:
        os.close(marker)


def remove_set(root: int, name: str) -> bool:
    """Revoke/remove one owned set through every barrier; return False if absent.

    Failures preserve or best-effort re-persist a final marker where possible.
    The caller must deny the identity in this process even if persistence fails.
    Root fsync is required for absent as well as removed results.
    """
    if absent(root, name):
        _fault("root_fsync")
        os.fsync(root)
        if not absent(root, name):
            raise OSError("Input namespace changed")
        return False
    folder = open_set(root, name)
    marked = False
    try:
        _mark(root, name, folder)
        marked = True
        entries = set(os.listdir(folder))
        if not entries <= MEMBER_NAMES:
            raise OSError("Unknown input residue")
        # Validate the complete fixed namespace before removing any payload.
        pins = {}
        try:
            for entry in entries:
                pins[entry] = open_member(folder, entry)
            for entry in (*PAYLOAD_NAMES, "inputs.json"):
                binding(root, name, folder, True)
                _fault(
                    "metadata_unlink"
                    if entry == "inputs.json"
                    else f"payload_unlink:{entry}"
                )
                if entry in pins:
                    binding(folder, entry, pins[entry])
                    os.unlink(entry, dir_fd=folder)
                elif not absent(folder, entry):
                    raise OSError("Input namespace changed")
            _fault("set_empty_fsync")
            os.fsync(folder)
            binding(root, name, folder, True)
            binding(folder, ".revoked", pins[".revoked"])
            _fault("marker_unlink")
            os.unlink(".revoked", dir_fd=folder)
            binding(root, name, folder, True)
            _fault("rmdir")
            os.rmdir(name, dir_fd=root)
            _fault("root_fsync")
            os.fsync(root)
            if not absent(root, name):
                raise OSError("Input namespace changed")
            return True
        finally:
            for fd in pins.values():
                os.close(fd)
    except OSError:
        if marked:
            with suppress(OSError):
                _mark(root, name, folder)
        raise
    finally:
        os.close(folder)
