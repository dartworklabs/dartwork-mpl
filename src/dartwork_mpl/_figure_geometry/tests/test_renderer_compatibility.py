"""Renderer measurement survives canvas detachment without changing figures."""

import datetime
import random

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.artist import Artist
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from matplotlib.image import imread

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import get_renderer


def _figure(kind, dpi, subfigure=False):
    """Build the same labeled plot with a live, missing or vector renderer."""
    if kind == "closed":
        fig = plt.figure(figsize=dm.figsize("13cm", "standard"), dpi=dpi)
    else:
        fig = Figure(figsize=dm.figsize("13cm", "standard"), dpi=dpi)
        canvas_type = {
            "agg": FigureCanvasAgg,
            "pdf": FigureCanvasPdf,
            "svg": FigureCanvasSVG,
        }.get(kind)
        if canvas_type is not None:
            canvas_type(fig)
    target = fig.subfigures() if subfigure else fig
    ax = target.subplots()
    ax.plot([0, 1, 2], [1, 3, 2], label="Measured")
    ax.set(xlabel="Elapsed time (s)", ylabel="Signal", title="Observation")
    if kind == "closed":
        plt.close(fig)
    return fig, target, ax


def _state(fig):
    """Capture caller-owned canvas, dimensions and process plotting state."""
    return (
        fig.canvas,
        fig.canvas.manager,
        fig.dpi,
        tuple(fig.get_size_inches()),
        mpl.get_backend(),
        tuple(plt.get_fignums()),
        dict(mpl.rcParams),
    )


@pytest.mark.parametrize("kind", ["closed", "native", "pdf", "svg"])
@pytest.mark.parametrize("subfigure", [False, True])
@pytest.mark.parametrize("dpi", [83, 147])
def test_measurement_matches_agg_and_preserves_state(kind, subfigure, dpi):
    """Fallback text extents use current DPI and leave canvas ownership intact."""
    dm.style.use("report")
    control, control_target, control_ax = _figure("agg", dpi, subfigure)
    control.canvas.draw()
    expected = np.array(
        [
            artist.get_window_extent(get_renderer(control_target)).bounds
            for artist in (control_ax.xaxis.label, control_ax.yaxis.label)
        ]
    )
    fig, target, ax = _figure(kind, dpi, subfigure)
    if hasattr(fig.canvas, "get_renderer"):
        fig.canvas.draw()
    before = _state(fig)
    child_canvas = target.canvas
    renderer = get_renderer(target)
    actual = np.array(
        [
            artist.get_window_extent(renderer).bounds
            for artist in (ax.xaxis.label, ax.yaxis.label)
        ]
    )
    np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=0)
    assert _state(fig) == before
    assert target.canvas is child_canvas
    assert ax.get_figure(root=True) is fig


@pytest.mark.parametrize("kind", ["closed", "native"])
@pytest.mark.parametrize("subfigure", [False, True])
def test_layout_validation_and_exports_match_open_control(
    kind, subfigure, tmp_path
):
    """Real layout, warnings and PNG/PDF output survive absent canvas renderers."""
    dm.style.use("report")
    results = []
    for current in ("agg", kind):
        fig, _, ax = _figure(current, 123, subfigure)
        before = _state(fig)
        ax.xaxis.label.set_fontsize(12)
        ax.yaxis.label.set_fontsize(12)
        dm.simple_layout(fig)
        assert not dm.validate_figure(
            fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
        )
        stem = tmp_path / current
        dm.save_formats(fig, str(stem), validate=True, validate_quiet=True)
        assert stem.with_suffix(".pdf").read_bytes().startswith(b"%PDF-")
        results.append(
            (ax.get_position().bounds, imread(stem.with_suffix(".png")))
        )
        assert _state(fig) == before
    np.testing.assert_allclose(results[1][0], results[0][0], atol=1e-12, rtol=0)
    np.testing.assert_array_equal(results[1][1], results[0][1])


def test_live_agg_renderer_is_retained_across_repeated_measurements():
    """The supported live-canvas path keeps its renderer and geometry at each DPI."""
    rng = random.Random(41793)
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel("Elapsed time (s)")
    assert fig.canvas.manager is not None
    for _ in range(5):
        fig.set_dpi(rng.randrange(72, 190))
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        before = _state(fig)
        assert get_renderer(fig) is renderer
        assert ax.xaxis.label.get_window_extent(renderer).width > 0
        assert _state(fig) == before


@pytest.mark.parametrize("kind", ["closed", "native"])
@pytest.mark.parametrize("subfigure", [False, True])
def test_explicit_tick_overlap_edit_matches_live_canvas(kind, subfigure):
    """Direct tick thinning and rotation keep their effect on detached canvases."""
    dm.style.use("report")
    results = []
    for current in ("agg", kind):
        fig, _, ax = _figure(current, 123, subfigure)
        ax.set_xticks(range(9), [f"Observation number {i}" for i in range(9)])
        before = _state(fig)
        dm.avoid_tick_overlap(ax, max_visible=4, rotation=35)
        labels = ax.get_xticklabels()
        results.append(
            [(label.get_text(), label.get_rotation()) for label in labels]
        )
        assert _state(fig) == before
    assert len(results[1]) == 4
    assert all(rotation == 35 for _, rotation in results[1])
    assert results[1] == results[0]


@pytest.mark.parametrize("kind", ["closed", "native"])
def test_concise_date_thinning_matches_live_canvas(kind):
    """Automatic date tick density uses current renderer extents after close."""
    dm.style.use("report")
    results = []
    for current in ("agg", kind):
        fig, _, ax = _figure(current, 123)
        fig.set_size_inches(*dm.figsize("9cm", "standard"))
        ax.clear()
        days = [
            datetime.date(2025, 1, 1) + datetime.timedelta(days=30 * i)
            for i in range(24)
        ]
        ax.plot(days, range(24))
        dm.simple_layout(fig)
        results.append(
            (
                ax.get_xticks(),
                [label.get_text() for label in ax.get_xticklabels()],
            )
        )
    np.testing.assert_array_equal(results[1][0], results[0][0])
    assert results[1][1] == results[0][1]


class _BrokenArtist(Artist):
    """A real artist exposes failed drawing without mocking backend internals."""

    def draw(self, renderer):
        """Fail while the temporary canvas and renderer are active."""
        raise RuntimeError("artist draw failed")


def test_failed_measurement_restores_canvas_and_propagates_draw_error():
    """Fallback rendering never hides artist failures or strands a temporary canvas."""
    fig, _, _ = _figure("native", 123)
    fig.add_artist(_BrokenArtist())
    before = _state(fig)
    with pytest.raises(RuntimeError, match="artist draw failed"):
        get_renderer(fig)
    assert _state(fig) == before
