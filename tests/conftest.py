"""Shared pytest fixtures for the dartwork-mpl test suite.

Why this file exists
--------------------
Many tests apply matplotlib styles via ``dm.style.use(...)`` or mutate
``plt.rcParams`` / open figures as a side effect. Without isolation,
that state leaks across tests and produces order-dependent failures
("works alone, fails in suite") or silent style cross-contamination.

This conftest adds a single ``autouse`` fixture that runs **after**
each test to:

1. Close every open figure (prevents figure-leak warnings and
   accumulated memory in long suites).
2. Reset ``rcParams`` to matplotlib's compiled-in defaults so the next
   test starts from a known baseline.

Tests that *intentionally* depend on a specific style should call
``dm.style.use(...)`` themselves; the reset only happens between tests.
"""

from __future__ import annotations

from collections.abc import Iterator

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest


@pytest.fixture(autouse=True)
def _matplotlib_state_isolation() -> Iterator[None]:
    """Close figures, reset rcParams, and restore ``dm.config``.

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
