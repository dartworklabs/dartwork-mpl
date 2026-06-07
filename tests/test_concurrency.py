"""Concurrency stress tests for ``ensure_loaded`` / ``Style.stack``.

PR #79 (G1) introduced ``threading.Lock`` + double-checked locking to
:func:`dartwork_mpl.cmap.ensure_loaded`,
:func:`dartwork_mpl.font.ensure_loaded`, and
:func:`dartwork_mpl.style.Style.stack` to prevent races where multiple
threads would otherwise re-register the same colormap / font with
matplotlib (raising ``ValueError``) or interleave ``rcParams`` updates.

These tests exercise the locks under realistic contention by:

1. Resetting the ``_loaded`` flag back to ``False`` so every worker
   thread re-enters the slow path simultaneously (otherwise the fast
   path short-circuits before the lock is even touched).
2. Substituting the real ``_load_colormaps`` / ``_add_fonts`` with a
   counting stub so we can prove the loader runs exactly once even
   under heavy contention. This indirectly proves the duplicate-
   registration race that PR #79 fixed cannot recur — if the loader
   runs only once, matplotlib's registry can never be touched twice.
3. Submitting many concurrent calls via :class:`ThreadPoolExecutor`.
4. Re-raising any worker exception via ``future.result()`` so any
   accidental ``ValueError`` from matplotlib surfaces as a failure.

We deliberately avoid driving the *real* loaders concurrently after
they have already populated matplotlib's global registry — replaying
the real loader on a populated registry would itself raise
``"already registered"``, which is unrelated to the lock under test.
The counting-loader pattern isolates the lock's behavior cleanly.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl import cmap as cmap_module
from dartwork_mpl import font as font_module
from dartwork_mpl import icon as icon_module
from dartwork_mpl.cmap import ensure_loaded as ensure_cmaps_loaded
from dartwork_mpl.font import ensure_loaded as ensure_fonts_loaded
from dartwork_mpl.icon import ensure_loaded as ensure_icons_loaded

# Resolve the style submodule directly because ``dartwork_mpl.style`` is
# the singleton ``Style`` instance once the package is imported.
style_module = importlib.import_module("dartwork_mpl.style")


# Number of worker threads / total submissions used across stress tests.
# Large enough to maximize the chance that several threads observe
# ``_loaded is False`` simultaneously and race for the lock, but small
# enough to keep the test fast and deterministic on CI.
_WORKERS: int = 16
_SUBMISSIONS: int = 64


@pytest.fixture
def _reset_cmap_loaded() -> Iterator[None]:
    """Force the cmap module back to its unloaded state for one test.

    Saves and restores both ``_loaded`` and ``_load_colormaps`` so the
    test can swap in a counting stub without leaking it. Critically,
    we do *not* invoke the real loader on teardown — by this point in
    the suite, matplotlib's registry already contains the dc.* cmaps
    from earlier tests (e.g. ``test_cmap.py``), so re-running the real
    loader would raise ``"already registered"``. Setting ``_loaded =
    True`` is enough to keep the fast path working for downstream
    tests.
    """
    original_loaded = cmap_module._loaded
    original_loader = cmap_module._load_colormaps
    cmap_module._loaded = False
    try:
        yield
    finally:
        cmap_module._load_colormaps = original_loader  # type: ignore[assignment]
        # Leave the module believing cmaps are loaded so subsequent
        # tests take the fast path. Matplotlib's registry was populated
        # by an earlier real-loader call (or by this test's stub did
        # not touch it), so the flag is the only thing to restore.
        cmap_module._loaded = True if original_loaded else cmap_module._loaded


@pytest.fixture
def _reset_icon_loaded() -> Iterator[None]:
    """Force the icon module back to its unloaded state for one test.

    Same stub-friendly pattern as the cmap/font resets; leaves
    ``_loaded = True`` on teardown so downstream tests take the fast path.
    """
    original_loaded = icon_module._loaded
    original_loader = icon_module._register_icon_fonts
    icon_module._loaded = False
    try:
        yield
    finally:
        icon_module._register_icon_fonts = original_loader  # type: ignore[assignment]
        icon_module._loaded = True if original_loaded else icon_module._loaded


@pytest.fixture
def _reset_font_loaded() -> Iterator[None]:
    """Force the font module back to its unloaded state for one test.

    Same pattern as ``_reset_cmap_loaded``: stub-friendly reset that
    leaves ``_loaded = True`` on teardown so downstream tests don't
    re-enter the slow path.
    """
    original_loaded = font_module._loaded
    original_loader = font_module._add_fonts
    font_module._loaded = False
    try:
        yield
    finally:
        font_module._add_fonts = original_loader  # type: ignore[assignment]
        font_module._loaded = True if original_loaded else font_module._loaded


def _race(fn: Callable[[], Any], submissions: int = _SUBMISSIONS) -> None:
    """Submit ``fn`` ``submissions`` times across a thread pool.

    Re-raises the first exception any worker hit so a duplicate
    matplotlib registration (``ValueError``) surfaces as a test failure.
    """
    with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
        futures = [ex.submit(fn) for _ in range(submissions)]
        for f in futures:
            f.result()


class TestCmapEnsureLoadedConcurrency:
    """Stress tests for :func:`dartwork_mpl.cmap.ensure_loaded`."""

    def test_concurrent_unloaded_runs_loader_exactly_once(
        self, _reset_cmap_loaded: None
    ) -> None:
        """Reset to unloaded state and race many threads through
        ``ensure_loaded``.

        With the double-checked lock the underlying loader must execute
        exactly once and the flag must end up ``True``. Without the
        lock, multiple threads would observe ``_loaded is False`` and
        all enter ``_load_colormaps`` — which in production would crash
        on the second ``mpl.colormaps.register`` call. Here we use a
        counting stub so the test isolates the lock's behavior from
        matplotlib's global registry state.
        """
        call_count = {"n": 0}

        def _counting_loader() -> None:
            call_count["n"] += 1

        cmap_module._load_colormaps = _counting_loader  # type: ignore[assignment]

        _race(ensure_cmaps_loaded)

        assert call_count["n"] == 1, (
            f"_load_colormaps ran {call_count['n']} times; "
            "the lock failed to serialize threads."
        )
        assert cmap_module._loaded is True

    def test_fast_path_after_loaded_is_race_free(self) -> None:
        """Once loaded, every concurrent call must take the fast path
        without raising. This guards against accidentally introducing a
        write to ``_loaded`` that could be torn under contention.
        """
        # Ensure loaded once first (idempotent — likely already True).
        ensure_cmaps_loaded()
        assert cmap_module._loaded is True
        _race(ensure_cmaps_loaded)
        # Flag must remain True; a torn write would flip it back.
        assert cmap_module._loaded is True


class TestIconEnsureLoadedConcurrency:
    """Stress tests for :func:`dartwork_mpl.icon.ensure_loaded`.

    icon.ensure_loaded gained the same double-checked lock as cmap/font
    (domain D, #236); without it concurrent first-use would register the
    icon fonts multiple times.
    """

    def test_concurrent_unloaded_runs_loader_exactly_once(
        self, _reset_icon_loaded: None
    ) -> None:
        call_count = {"n": 0}

        def _counting_loader() -> None:
            call_count["n"] += 1

        icon_module._register_icon_fonts = _counting_loader  # type: ignore[assignment]

        _race(ensure_icons_loaded)

        assert call_count["n"] == 1, (
            f"_register_icon_fonts ran {call_count['n']} times; "
            "the lock failed to serialize threads."
        )
        assert icon_module._loaded is True

    def test_fast_path_after_loaded_is_race_free(self) -> None:
        ensure_icons_loaded()
        assert icon_module._loaded is True
        _race(ensure_icons_loaded)
        assert icon_module._loaded is True


class TestFontEnsureLoadedConcurrency:
    """Stress tests for :func:`dartwork_mpl.font.ensure_loaded`."""

    def test_concurrent_unloaded_runs_loader_exactly_once(
        self, _reset_font_loaded: None
    ) -> None:
        """Same pattern as the cmap variant: many threads, one loader
        invocation, no duplicate ``font_manager.addfont`` calls.
        """
        call_count = {"n": 0}

        def _counting_loader() -> None:
            call_count["n"] += 1

        font_module._add_fonts = _counting_loader  # type: ignore[assignment]

        _race(ensure_fonts_loaded)

        assert call_count["n"] == 1, (
            f"_add_fonts ran {call_count['n']} times; "
            "the lock failed to serialize threads."
        )
        assert font_module._loaded is True

    def test_fast_path_after_loaded_is_race_free(self) -> None:
        """Post-load fast path must be safe under contention."""
        ensure_fonts_loaded()
        assert font_module._loaded is True
        _race(ensure_fonts_loaded)
        assert font_module._loaded is True


class TestStyleStackConcurrency:
    """Stress tests for :meth:`dartwork_mpl.style.Style.stack`.

    ``Style.stack`` mutates ``plt.rcParams`` globally, so concurrent
    callers without a lock would interleave updates and leave rcParams
    in a half-written state. The lock serializes the
    ``rcParams.update + plt.style.use`` pair.
    """

    def test_concurrent_stack_does_not_corrupt_rcparams(self) -> None:
        """Two presets racing — both must complete without raising and
        rcParams must remain a well-formed dict-like with a usable
        ``font.family`` list at the end. A torn write would manifest
        either as an exception inside ``style.use`` or a non-list
        ``font.family``.
        """

        def _apply(idx: int) -> None:
            # Alternate between two reasonably distinct presets so we
            # exercise two different update paths.
            preset = "report" if idx % 2 == 0 else "scientific"
            style_module.style.use(preset)

        with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
            futures = [ex.submit(_apply, i) for i in range(_SUBMISSIONS)]
            for f in futures:
                f.result()

        # rcParams should still be a usable list (matplotlib normalizes
        # font.family into a list) — corruption would typically surface
        # as a None / scalar / partial state.
        family = plt.rcParams["font.family"]
        assert isinstance(family, list)
        assert len(family) > 0

    def test_concurrent_stack_via_classmethod(self) -> None:
        """Drive ``Style.stack`` directly (bypassing ``use``) from many
        threads. The ``with _style_lock:`` block in ``stack`` is the
        critical section being exercised here.
        """

        def _stack() -> None:
            # ``base`` is the lightest valid style and is guaranteed to
            # exist (covered by ``test_style.TestListStyles``).
            style_module.Style.stack(["base"])

        _race(_stack)


class TestMixedScenarioConcurrency:
    """Mixed scenarios — different ensure_loaded paths racing each other.

    Even though the cmap and font locks are independent, both touch
    matplotlib's global state. We verify that interleaving the two
    families of calls under heavy contention is safe.
    """

    def test_cmap_and_font_loaders_race_safely(self) -> None:
        """One half of the pool drives ``cmap.ensure_loaded``, the other
        half drives ``font.ensure_loaded``. Both must complete without
        raising; the loaded flags must end up ``True``.

        This is the closest analogue to the real-world scenario that
        PR #79 prevented: a multi-threaded plotting workload where the
        first plot of each thread implicitly triggers both loaders.
        """
        # Pre-warm to the loaded state — the test is about the fast
        # path under simultaneous contention from two different
        # modules. (The slow-path lock behavior is covered above.)
        ensure_cmaps_loaded()
        ensure_fonts_loaded()

        def _worker(idx: int) -> None:
            if idx % 2 == 0:
                ensure_cmaps_loaded()
            else:
                ensure_fonts_loaded()

        with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
            futures = [ex.submit(_worker, i) for i in range(_SUBMISSIONS)]
            for f in futures:
                f.result()

        assert cmap_module._loaded is True
        assert font_module._loaded is True

    def test_style_use_implicitly_drives_both_loaders(self) -> None:
        """``Style.stack`` calls ``ensure_fonts_loaded`` and
        ``ensure_cmaps_loaded`` before mutating rcParams. Concurrent
        ``style.use`` therefore exercises all three locks at once
        (cmap, font, style) — closely mirroring real workloads where
        several threads each call ``dm.style.use(...)`` at startup.
        """

        def _apply() -> None:
            style_module.style.use("report")

        _race(_apply, submissions=_SUBMISSIONS)

        assert cmap_module._loaded is True
        assert font_module._loaded is True
        family = plt.rcParams["font.family"]
        assert isinstance(family, list)
        assert len(family) > 0
