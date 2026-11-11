"""Repository-wide pytest setup for both test locations: ``tests/`` and the slices' ``src/dartwork_mpl/**/tests/``.

Why this file lives at the repository root
------------------------------------------
pytest applies a ``conftest.py`` only to the directories under it. Tests
live in two trees (cross-cutting suites in ``tests/``, slice-owned tests
next to their code, ADR 0005), so the setup every test needs sits here:

1. A source-tree bootstrap: ``src`` and a generated ``dartwork_mpl``
   dist-info go first on ``sys.path`` and ``PYTHONPATH`` so a shared
   venv's stale editable install cannot leak another version or package
   path into tests or their subprocesses.
2. An ``autouse`` fixture that, after each test, closes figures, resets
   ``rcParams`` and preset ownership, and restores ``dm.config``. Without
   it, style and config mutations leak across tests ("works alone, fails
   in suite").

3. The font-cache guard (``tests/support/font_cache_guard.py``): the session
   fails when a test changes a matplotlib font inventory that existed before
   the session, so a test cannot quietly rewrite the developer's real cache.

Tests that *intentionally* depend on a specific style should call
``dm.style.use(...)`` themselves; the reset only happens between tests.
"""

from __future__ import annotations

import errno
import os
import re
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

pytest_plugins = ["tests.support.font_cache_guard"]

_REPO_ROOT = Path(__file__).resolve().parent
_SRC_PATH = str(_REPO_ROOT / "src")
_METADATA_ROOT = _REPO_ROOT / ".pytest_cache" / "dartwork_mpl_metadata"


def _pyproject_version() -> str:
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if match is None:
        raise RuntimeError("Could not find project.version in pyproject.toml")
    return match.group(1)


def _ensure_source_tree_metadata() -> str:
    """Publish complete metadata atomically, excluding other cached versions.

    Every xdist worker bootstraps independently. Stage the whole distribution
    before first publication so readers cannot see an empty directory; replace
    an existing metadata file atomically so a peer import cannot read it between
    truncation and writing. Version-specific search roots avoid shared deletion.
    """
    version = _pyproject_version()
    metadata_root = _METADATA_ROOT / version
    metadata_root.mkdir(parents=True, exist_ok=True)
    dist_info = metadata_root / f"dartwork_mpl-{version}.dist-info"
    with tempfile.TemporaryDirectory(
        prefix=".metadata-", dir=metadata_root
    ) as folder:
        staged = Path(folder) / dist_info.name
        staged.mkdir()
        metadata = staged / "METADATA"
        metadata.write_text(
            f"Metadata-Version: 2.1\nName: dartwork-mpl\nVersion: {version}\n",
            encoding="utf-8",
        )
        try:
            staged.rename(dist_info)
        except OSError as error:
            if error.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                raise
            metadata.replace(dist_info / "METADATA")
    return str(metadata_root)


_METADATA_PATH = _ensure_source_tree_metadata()
# Source-tree test runs use ``src`` ahead of site-packages. Mirror that for
# package metadata and subprocesses so a shared venv's stale editable install
# cannot leak a different ``dartwork-mpl`` version or package path into tests.
if _METADATA_PATH not in sys.path:
    sys.path.insert(0, _METADATA_PATH)
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)
_PYTHONPATH_PARTS = [
    part for part in os.environ.get("PYTHONPATH", "").split(os.pathsep) if part
]
for path in (_SRC_PATH, _METADATA_PATH):
    if path not in _PYTHONPATH_PARTS:
        _PYTHONPATH_PARTS.insert(0, path)
os.environ["PYTHONPATH"] = os.pathsep.join(_PYTHONPATH_PARTS)


# Fixtures whose value is a full colour-pipeline compile (~1 min). A test that
# requests one is a colour-pipeline test whether or not it says so, so it is
# marked here rather than by hand; see the ``color_pipeline`` marker in
# pyproject.toml. Subprocess build/regeneration tests carry the marker
# explicitly.
_COLOR_PIPELINE_FIXTURES = frozenset({"candidate_catalog", "comparison_report"})

# Fixtures whose value is read from an exact input in
# tests/support/approved_inputs.json. A test that requests one reads that
# input, so it is marked ``approved_input`` here; a test that calls a reader
# itself carries the marker explicitly.
_APPROVED_INPUT_FIXTURES = frozenset(
    {
        "baseline_catalog",
        "comparison_report",
        "compatibility_snapshot",
        "quality_baseline",
        "v5_ssot",
    }
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark tests by the compile and approved-input fixtures they request."""
    for item in items:
        fixtures = getattr(item, "fixturenames", ())
        if _COLOR_PIPELINE_FIXTURES.intersection(fixtures):
            item.add_marker(pytest.mark.color_pipeline)
        if _APPROVED_INPUT_FIXTURES.intersection(fixtures):
            item.add_marker(pytest.mark.approved_input)


@pytest.fixture
def report_preset() -> Iterator[None]:
    """Run one test under the ``report`` preset inside its own ``rc_context``.

    Opt in per module with ``pytestmark = pytest.mark.usefixtures(
    "report_preset")``; the preset is applied after the isolation fixture
    below has taken its snapshot and is undone before that fixture resets.

    Order: pytest sets up every autouse fixture before a ``usefixtures`` one,
    so a class-level autouse fixture (``_concise_dates`` in
    ``test_default_tick_format``, a ``dm.config`` override) now starts before
    this preset; under the per-module autouse copies it replaced,
    ``_concise_dates`` started after the preset. ``dm.style.use`` neither
    reads nor writes ``dm.config``, so
    the swap changes no result; a fixture that needs the preset in place
    must request ``report_preset`` itself.
    """
    import dartwork_mpl as dm

    with mpl.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


@pytest.fixture(autouse=True)
def _matplotlib_state_isolation() -> Iterator[None]:
    """Close figures, reset rcParams/preset ownership, and restore ``dm.config``.

    Yields control to the test, then performs cleanup unconditionally.
    """
    # Snapshot the process-global ``dm.config`` singleton so a test that
    # mutates it (directly, or forgetting ``config.override()``) can't
    # leak into later tests. Fields are re-applied onto the singleton on
    # teardown — never rebound — because consumers hold references to
    # the instance itself.
    from dataclasses import fields

    from dartwork_mpl.config import config as _dm_config

    snapshot = {f.name: getattr(_dm_config, f.name) for f in fields(_dm_config)}
    yield
    for name, value in snapshot.items():
        setattr(_dm_config, name, value)
    # Close all figures created during the test to prevent leaks.
    plt.close("all")
    # Restore matplotlib's compiled-in defaults so style mutations from
    # one test don't bleed into the next.
    mpl.rcdefaults()
    # Ownership describes the live preset values, so it cannot outlive the
    # rcdefaults reset above. Keep the private dictionary's identity stable.
    from dartwork_mpl.style import _dm_preset_values

    _dm_preset_values.clear()
