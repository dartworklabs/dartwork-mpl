"""Tests for module-level monkey patches applied by dartwork_mpl.__init__.

Currently covers the ``Axes.twinx`` reentrance guard: reloading
``dartwork_mpl`` must not produce a self-wrapping infinite loop in
``ax.twinx()``.
"""

from __future__ import annotations

import importlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.axes  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


class TestTwinxPatchReentranceGuard:
    """The patched ``twinx`` is tagged with ``__dm_patched__`` so a reload
    of dartwork_mpl does not capture the already-wrapped callable as the
    "original", which would otherwise recurse forever on the next
    ``ax.twinx()`` call.
    """

    def test_patched_twinx_is_marked(self) -> None:
        import dartwork_mpl  # noqa: F401  (ensures patch applied)

        assert (
            getattr(matplotlib.axes.Axes.twinx, "__dm_patched__", False) is True
        )

    def test_reload_does_not_recurse(self) -> None:
        """Reloading dartwork_mpl + invoking twinx must not RecursionError."""
        import dartwork_mpl

        importlib.reload(dartwork_mpl)
        importlib.reload(dartwork_mpl)
        # Should still be a single layer of wrapping.
        assert (
            getattr(matplotlib.axes.Axes.twinx, "__dm_patched__", False) is True
        )

        fig, ax = plt.subplots()
        try:
            ax2 = ax.twinx()
            # Right spine visible (the patch's whole purpose).
            assert ax2.spines["right"].get_visible() is True
        finally:
            plt.close(fig)
