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
    """Close figures and reset rcParams between tests.

    Yields control to the test, then performs cleanup unconditionally.
    """
    yield
    # Close all figures created during the test to prevent leaks.
    plt.close("all")
    # Restore matplotlib's compiled-in defaults so style mutations from
    # one test don't bleed into the next.
    mpl.rcdefaults()
