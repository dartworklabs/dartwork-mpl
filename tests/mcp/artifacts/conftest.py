"""Canonical, privately owned disposable input-policy fixtures, never grants."""

import os
import shutil
import stat
import tempfile
from contextlib import suppress
from pathlib import Path

import pytest


@pytest.fixture
def owned_input_root():
    """Clean a 0700 repository fixture on success/failure after ancestor checks."""
    root = Path(__file__).resolve().parents[3]
    for ancestor in (root, *root.parents):
        info = ancestor.lstat()
        assert stat.S_ISDIR(info.st_mode) and not ancestor.is_symlink()
        assert info.st_uid in {0, os.geteuid()} and not info.st_mode & 0o022
    build = root / "build"
    fixtures = build / "input-lifecycle-fixtures"
    # Parallel workers (pytest-xdist) share these two parents, and every
    # teardown below removes them once empty. Another worker's teardown can
    # therefore delete them between our mkdir and mkdtemp; recreate and retry
    # instead of failing. Each test still gets its own private folder.
    for attempt in range(20):
        try:
            build.mkdir(mode=0o700, exist_ok=True)
            fixtures.mkdir(mode=0o700, exist_ok=True)
            for path in (build, fixtures):
                info = path.lstat()
                assert stat.S_ISDIR(info.st_mode)
                assert info.st_uid == os.geteuid()
                assert not info.st_mode & 0o022
            folder = Path(tempfile.mkdtemp(prefix="task3-", dir=fixtures))
            break
        except FileNotFoundError:
            if attempt == 19:
                raise
    try:
        yield folder
    finally:
        shutil.rmtree(folder)
        for path in (fixtures, build):
            with suppress(OSError):
                path.rmdir()
