"""Pytest setup shared by both test trees: ``tests/`` and ``src/dartwork_mpl/**/tests/``.

Loaded as a plugin (``-p tests.fixtures`` in ``pyproject.toml``), so it applies
to both trees without a ``conftest.py`` at the repository root. After each
test it closes figures, resets ``rcParams`` and the active preset, and restores
``dm.config``, so one test's style cannot leak into the next. It also checks
that an edge case's example test really makes that edge fire.
"""

from __future__ import annotations

from collections.abc import Iterator

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest


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
    # No preset is active after the reset above.
    from dartwork_mpl.style import apply as _style_apply

    _style_apply.STATE[0] = _style_apply.State()
