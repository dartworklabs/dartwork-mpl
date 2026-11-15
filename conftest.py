"""Repository-wide pytest setup for both test locations: ``tests/`` and the slices' ``src/dartwork_mpl/**/tests/``.

pytest applies a ``conftest.py`` only to the directories under it. Tests live
in two trees (cross-cutting suites in ``tests/``, slice-owned tests next to
their code, ADR 0005), so the setup every test needs sits here: an ``autouse``
fixture that, after each test, closes figures, resets ``rcParams`` and preset
ownership, and restores ``dm.config``. Without it, style and config mutations
leak across tests ("works alone, fails in suite").

Tests that *intentionally* depend on a specific style should call
``dm.style.use(...)`` themselves; the reset only happens between tests.
"""

from __future__ import annotations

from collections.abc import Iterator

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest


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
