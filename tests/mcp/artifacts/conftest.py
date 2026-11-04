"""Canonical, privately owned disposable input-policy fixtures, never grants."""

import os
import stat
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def owned_input_root():
    """Clean a unique 0700 fixture under verified user-owned home ancestry."""
    # A self-hosted checkout may have group-writable runner ancestors. Keep
    # real input-policy tests outside it rather than relaxing their admission.
    root = Path.home().resolve(strict=True)
    assert root.stat().st_uid == os.geteuid()
    for ancestor in (root, *root.parents):
        info = ancestor.lstat()
        assert stat.S_ISDIR(info.st_mode) and not ancestor.is_symlink()
        assert info.st_uid in {0, os.geteuid()} and not info.st_mode & 0o022
    # Each worker owns only this leaf; no shared parent is created or removed.
    with tempfile.TemporaryDirectory(
        prefix="dmpl-input-test-", dir=root
    ) as folder:
        yield Path(folder)
