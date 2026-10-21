"""Real-file contracts for the viewer's startup roots and capability detection."""

import hashlib
import os
from dataclasses import replace
from pathlib import Path

import pytest

from dartwork_mpl.ui.platform import fs


def snapshot(root: Path) -> dict[str, str]:
    """Hash the complete tree without following links, including empty folders."""
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = "link:" + os.readlink(path)
        elif path.is_dir():
            result[relative] = "directory"
        else:
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def test_unsupported_capability_creates_nothing(tmp_path: Path) -> None:
    """An unavailable required primitive fails before even configured roots exist."""
    unavailable = replace(fs.detect_capabilities(), dir_fd_rename=False)
    before = snapshot(tmp_path)
    result = fs.open_roots(
        tmp_path / "primary", "copy", cwd=tmp_path, capabilities=unavailable
    )
    assert isinstance(result, fs.UnsupportedFilesystem)
    assert snapshot(tmp_path) == before


def test_bad_second_root_refuses_before_root_creation(tmp_path: Path) -> None:
    """A configured file cannot be a directory root or cause partial startup creation."""
    copy = tmp_path / "copy"
    copy.write_bytes(b"keep")
    before = snapshot(tmp_path)
    result = fs.open_roots(tmp_path / "primary", copy, cwd=tmp_path)
    assert isinstance(result, fs.TargetConflict)
    assert snapshot(tmp_path) == before


def test_capability_detection_uses_supported_rename() -> None:
    """macOS supports dir-fd rename although replace is absent from the support set."""
    capabilities = fs.detect_capabilities()
    assert capabilities.dir_fd_rename == (os.rename in os.supports_dir_fd)
    assert capabilities.supported


def test_partial_startup_closes_opened_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure at a later configured root releases all previously acquired fds."""
    open_root = fs._open_root
    observed = []

    def fail_second(path: Path) -> int:
        """Capture the primary's real descriptor then fail a later root."""
        if observed:
            raise OSError("controlled startup failure")
        fd = open_root(path)
        observed.append(fd)
        return fd

    monkeypatch.setattr(fs, "_open_root", fail_second)
    result = fs.open_roots(tmp_path / "primary", "copy", cwd=tmp_path)
    assert isinstance(result, fs.FileIOFailure)
    for fd in observed:
        with pytest.raises(OSError):
            os.fstat(fd)
