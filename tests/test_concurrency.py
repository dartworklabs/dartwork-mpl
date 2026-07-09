"""Concurrency stress tests for ``ensure_loaded`` / ``Style.stack``.

PR #79 (G1) introduced ``threading.Lock`` + double-checked locking to
:func:`dartwork_mpl.font.ensure_loaded` and
:func:`dartwork_mpl.style.Style.stack` to prevent races where multiple
threads would otherwise re-register the same font with matplotlib
(raising ``ValueError``) or interleave ``rcParams`` updates. Later work
applied the same pattern to icon fonts and the colors loader.

These tests exercise the locks under realistic contention by:

1. Resetting the ``_loaded`` flag back to ``False`` so every worker
   thread re-enters the slow path simultaneously (otherwise the fast
   path short-circuits before the lock is even touched).
2. Substituting the real loader functions with a counting stub so we can
   prove the loader runs exactly once even under heavy contention. This
   indirectly proves duplicate-registration races cannot recur — if the
   loader runs only once, matplotlib's registry can never be touched
   twice.
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
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl import font as font_module
from dartwork_mpl import icon as icon_module
from dartwork_mpl.colors import _loader as colors_loader_module
from dartwork_mpl.colors._loader import ensure_loaded as ensure_colors_loaded
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

# Race window held inside each counting stub. Without it the stub returns
# so fast that the first thread sets ``_loaded = True`` before any other
# thread reaches the double-check, so *even with the lock removed* the
# loader runs exactly once — i.e. the guard test would pass against an
# unlocked loader and could not detect the regression it exists to catch.
# Sleeping briefly forces several threads to pile up in the slow path, so
# an unlocked loader visibly runs more than once. It never makes the
# locked case flake: with the lock, exactly one thread ever enters.
_RACE_WINDOW_S: float = 0.02


@pytest.fixture
def _reset_icon_loaded() -> Iterator[None]:
    """Force the icon module back to its unloaded state for one test.

    Same stub-friendly pattern as the font reset; leaves
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

    Stub-friendly reset that leaves ``_loaded = True`` on teardown so
    downstream tests don't re-enter the slow path.
    """
    original_loaded = font_module._loaded
    original_loader = font_module._add_fonts
    font_module._loaded = False
    try:
        yield
    finally:
        font_module._add_fonts = original_loader  # type: ignore[assignment]
        font_module._loaded = True if original_loaded else font_module._loaded


@pytest.fixture
def _reset_colors_loaded() -> Iterator[None]:
    """Force the colours loader back to its unloaded state for one test.

    Same stub-friendly pattern as the font/icon resets; leaves
    ``_loaded = True`` on teardown so downstream tests take the fast path
    (matplotlib's named-colour mapping was already populated by an
    earlier real-loader call).
    """
    original_loaded = colors_loader_module._loaded
    original_loader = colors_loader_module._load_colors
    colors_loader_module._loaded = False
    try:
        yield
    finally:
        colors_loader_module._load_colors = original_loader  # type: ignore[assignment]
        colors_loader_module._loaded = (
            True if original_loaded else colors_loader_module._loaded
        )


def _race(fn: Callable[[], Any], submissions: int = _SUBMISSIONS) -> None:
    """Submit ``fn`` ``submissions`` times across a thread pool.

    Re-raises the first exception any worker hit so a duplicate
    matplotlib registration (``ValueError``) surfaces as a test failure.
    """
    with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
        futures = [ex.submit(fn) for _ in range(submissions)]
        for f in futures:
            f.result()


class TestIconEnsureLoadedConcurrency:
    """Stress tests for :func:`dartwork_mpl.icon.ensure_loaded`.

    icon.ensure_loaded gained the same double-checked lock as font
    (domain D, #236); without it concurrent first-use would register the
    icon fonts multiple times.
    """

    def test_concurrent_unloaded_runs_loader_exactly_once(
        self, _reset_icon_loaded: None
    ) -> None:
        call_count = {"n": 0}

        def _counting_loader() -> None:
            time.sleep(_RACE_WINDOW_S)  # widen the race window
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
        """Same pattern as the icon variant: many threads, one loader
        invocation, no duplicate ``font_manager.addfont`` calls.
        """
        call_count = {"n": 0}

        def _counting_loader() -> None:
            time.sleep(_RACE_WINDOW_S)  # widen the race window
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


class TestColorsEnsureLoadedConcurrency:
    """Stress tests for :func:`dartwork_mpl.colors._loader.ensure_loaded`.

    The colours loader was the one sibling that shipped without the
    double-checked lock that font/icon/Style got in PR #79 / #236.
    Without it, a racing first access could run ``_load_colors`` twice
    and mutate matplotlib's global named-colour mapping concurrently.
    """

    def test_concurrent_unloaded_runs_loader_exactly_once(
        self, _reset_colors_loaded: None
    ) -> None:
        call_count = {"n": 0}

        def _counting_loader() -> None:
            time.sleep(_RACE_WINDOW_S)  # widen the race window
            call_count["n"] += 1

        colors_loader_module._load_colors = _counting_loader  # type: ignore[assignment]

        _race(ensure_colors_loaded)

        assert call_count["n"] == 1, (
            f"_load_colors ran {call_count['n']} times; "
            "the lock failed to serialize threads."
        )
        assert colors_loader_module._loaded is True

    def test_fast_path_after_loaded_is_race_free(self) -> None:
        ensure_colors_loaded()
        assert colors_loader_module._loaded is True
        _race(ensure_colors_loaded)
        assert colors_loader_module._loaded is True


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

    Even though the icon and font locks are independent, both touch
    matplotlib's global state. We verify that interleaving the two
    families of calls under heavy contention is safe.
    """

    def test_icon_and_font_loaders_race_safely(self) -> None:
        """One half of the pool drives ``icon.ensure_loaded``, the other
        half drives ``font.ensure_loaded``. Both must complete without
        raising; the loaded flags must end up ``True``.

        This is the closest analogue to the real-world scenario that
        PR #79 prevented: a multi-threaded plotting workload where the
        first plot of each thread implicitly triggers both loaders.
        """
        # Pre-warm to the loaded state — the test is about the fast
        # path under simultaneous contention from two different
        # modules. (The slow-path lock behavior is covered above.)
        ensure_icons_loaded()
        ensure_fonts_loaded()

        def _worker(idx: int) -> None:
            if idx % 2 == 0:
                ensure_icons_loaded()
            else:
                ensure_fonts_loaded()

        with ThreadPoolExecutor(max_workers=_WORKERS) as ex:
            futures = [ex.submit(_worker, i) for i in range(_SUBMISSIONS)]
            for f in futures:
                f.result()

        assert icon_module._loaded is True
        assert font_module._loaded is True

    def test_style_use_implicitly_drives_font_loader(self) -> None:
        """``Style.stack`` calls ``ensure_fonts_loaded`` before mutating
        rcParams. Concurrent ``style.use`` therefore exercises the font
        and style locks together, closely mirroring real workloads where
        several threads each call ``dm.style.use(...)`` at startup.
        """

        def _apply() -> None:
            style_module.style.use("report")

        _race(_apply, submissions=_SUBMISSIONS)

        assert font_module._loaded is True
        family = plt.rcParams["font.family"]
        assert isinstance(family, list)
        assert len(family) > 0


class TestGuardEfficacy:
    """Prove the 'runs exactly once' assertions above are meaningful.

    A guard test that passes even when the thing it guards is removed is
    worthless. Here we replace the real lock with a no-op and confirm the
    widened race window makes the (unlocked) loader run more than once —
    so removing the double-checked lock would fail the guard tests, not
    slip through unnoticed.
    """

    class _NoLock:
        def __enter__(self) -> TestGuardEfficacy._NoLock:
            return self

        def __exit__(self, *_exc: object) -> bool:
            return False

    def test_removing_lock_makes_loader_run_more_than_once(
        self, _reset_font_loaded: None
    ) -> None:
        call_count = {"n": 0}

        def _counting_loader() -> None:
            time.sleep(_RACE_WINDOW_S)
            call_count["n"] += 1

        original_lock = font_module._lock
        font_module._lock = self._NoLock()  # type: ignore[assignment]
        font_module._add_fonts = _counting_loader  # type: ignore[assignment]
        try:
            _race(ensure_fonts_loaded)
        finally:
            font_module._lock = original_lock

        assert call_count["n"] > 1, (
            "with the lock removed the loader must run more than once; if "
            "it still runs exactly once the race window is too small and "
            "the guard tests above cannot detect a removed lock"
        )
