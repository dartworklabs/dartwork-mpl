"""UI security hardening (#228).

Covers the local Host/source policy, typed output-name language, figure cleanup
and HTML escaping in the rendered template.
"""

from __future__ import annotations

import pytest

# The viewer lives behind the optional ``ui`` extra (fastapi/uvicorn).
pytest.importorskip("fastapi")

from dartwork_mpl.ui._boundary import InputFailure, parse_output


class TestOutputLanguage:
    """Only typed safe relative output paths reach the confined filesystem owner."""

    @pytest.mark.parametrize("name", ["figure.png", "sub/figure.png"])
    def test_safe_relative_name_allowed(self, name: str) -> None:
        """Relative files and safe subdirectories retain their accepted spelling."""
        result = parse_output(name)
        assert not isinstance(result, InputFailure)
        assert result.filename == name

    @pytest.mark.parametrize("name", ["../../etc/passwd", "/etc/passwd", "   "])
    def test_unsafe_name_rejected(self, name: str) -> None:
        """Absolute, parent traversal and blank names never become output capabilities."""
        assert isinstance(parse_output(name), InputFailure)


class TestFigureNotLeaked:
    """render/export must not leak matplotlib figures when rendering fails."""

    def test_figure_closed_on_savefig_error(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from dartwork_mpl.ui.ui import _figure_to_bytes

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

        from dartwork_mpl.ui.ui import _figure_to_bytes

        before = set(plt.get_fignums())

        def figure_fn(_model: object) -> plt.Figure:
            fig = plt.figure()
            fig.add_subplot().plot([0, 1], [0, 1])
            return fig

        data = _figure_to_bytes(figure_fn, None, "png")
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert set(plt.get_fignums()) == before
