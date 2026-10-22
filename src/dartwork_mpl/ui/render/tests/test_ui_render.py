"""Rendering to bytes never leaks the callback's figure, on success or failure."""

from __future__ import annotations

import pytest


class TestFigureNotLeaked:
    """render/export must not leak matplotlib figures when rendering fails."""

    def test_figure_closed_on_savefig_error(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from dartwork_mpl.ui.render._figure import _figure_to_bytes

        before = set(plt.get_fignums())

        def figure_fn(_model: object) -> plt.Figure:
            return plt.figure()

        # matplotlib raises ValueError for an unsupported savefig format.
        with pytest.raises(ValueError):
            _figure_to_bytes(figure_fn, None, "not-a-real-format")

        assert set(plt.get_fignums()) == before

    def test_figure_closed_on_success(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from dartwork_mpl.ui.render._figure import _figure_to_bytes

        before = set(plt.get_fignums())

        def figure_fn(_model: object) -> plt.Figure:
            fig = plt.figure()
            fig.add_subplot().plot([0, 1], [0, 1])
            return fig

        data = _figure_to_bytes(figure_fn, None, "png")
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert set(plt.get_fignums()) == before
