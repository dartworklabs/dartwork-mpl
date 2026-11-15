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

import importlib
from collections import Counter
from collections.abc import Iterator
from functools import cache
from pathlib import Path

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
    # No preset is active after the reset above.
    from dartwork_mpl.style import apply as _style_apply

    _style_apply.STATE[0] = _style_apply.State()


SLICES = Path(__file__).parent / "src" / "dartwork_mpl"


@cache
def _examples() -> dict[tuple[str, str], list[str]]:
    """Edge names by their example: (``<slice>/tests/<file>``, ``[Class::]fn``)."""
    found: dict[tuple[str, str], list[str]] = {}
    for edges_file in sorted(SLICES.glob("*/edges.py")):
        slice_ = edges_file.parent.name
        module = importlib.import_module(f"dartwork_mpl.{slice_}.edges")
        for edge in module.EDGES:
            file, _, function = edge.example.partition("::")
            key = (f"{slice_}/tests/{file}", function)
            found.setdefault(key, []).append(edge.name)
    return found


@pytest.fixture(autouse=True)
def _example_fires_its_edge(request: pytest.FixtureRequest) -> Iterator[None]:
    """An edge case's example test must make it fire (``EdgeCase.example``).

    The architecture rule checks the example exists, names the edge and
    asserts; this checks, while it runs, that ``settle`` applied the edge.
    """
    path = Path(str(request.node.path)).as_posix()
    cls = request.node.cls
    function = getattr(request.node, "originalname", request.node.name)
    if cls is not None:
        function = f"{cls.__name__}::{function}"
    names = next(
        (
            names
            for (file, fn), names in _examples().items()
            if fn == function and path.endswith(file)
        ),
        None,
    )
    if names is None:
        yield
        return
    import dartwork_mpl.edgecase as edgecase

    before, edgecase.tally = edgecase.tally, Counter()
    try:
        yield
        fired = edgecase.tally
    finally:
        edgecase.tally = before
    missing = [n for n in names if not fired[n]]
    assert not missing, f"{request.node.nodeid} did not fire {missing}"
