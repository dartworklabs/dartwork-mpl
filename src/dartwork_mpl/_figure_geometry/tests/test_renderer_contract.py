"""Pin ``get_renderer``'s contract on every kind of canvas it meets.

Live Agg canvases hand back their own renderer without drawing. Every other
canvas (a plain ``Figure``, PDF/SVG/PS canvases, a Figure that pyplot closed)
is drawn once, without output, by a temporary Agg canvas at the Figure DPI:
artist positions are then current, nothing is painted into the renderer's
buffer, the caller's canvas is back in place, an artist's error reaches the
caller, and no file is written. Measured while the figure is being saved,
the temporary canvas does not take over the saving state
(``canvas.is_saving()`` is ``False`` in the measuring draw) and the saved
bytes do not change. A control figure on a live Agg canvas, drawn by
``canvas.draw()``, gives the expected geometry. A constrained layout engine
moves the Axes only when the figure is drawn, so the Axes position shows
whether a draw happened.
"""

import io

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.artist import Artist
from matplotlib.backends.backend_agg import FigureCanvasAgg, RendererAgg
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.backends.backend_ps import FigureCanvasPS
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import get_renderer

LIVE = ("pyplot", "agg")
DETACHED = ("plain", "pdf", "svg", "ps", "closed")
DPIS = (72, 123, 300)

_CANVASES = {
    "agg": FigureCanvasAgg,
    "pdf": FigureCanvasPdf,
    "svg": FigureCanvasSVG,
    "ps": FigureCanvasPS,
}


class _BrokenArtist(Artist):
    """An artist whose drawing fails, as a real one with bad state would."""

    def draw(self, renderer):
        """Fail while the figure is being drawn."""
        raise RuntimeError("artist draw failed")


class _SavingSpy(Artist):
    """Notes, on every draw, whether an Agg canvas draws and is saving."""

    def __init__(self):
        super().__init__()
        self.seen = []

    def draw(self, renderer):
        """Record the canvas kind and ``is_saving()``; paint nothing."""
        canvas = self.get_figure(root=True).canvas
        self.seen.append(
            (isinstance(canvas, FigureCanvasAgg), canvas.is_saving())
        )


class _MeasureWhileDrawn(Artist):
    """On its first draw, measures ``target`` with ``get_renderer``.

    Inactive, it only takes its place in the artist tree, so a figure with
    an inactive one is the same figure without the measurement.
    """

    def __init__(self, target, ax, active):
        super().__init__()
        self.target, self.ax, self.active = target, ax, active
        self.result = None

    def draw(self, renderer):
        """Measure once from inside the figure's draw; paint nothing."""
        if not self.active or self.result is not None:
            return
        self.result = {}  # the measuring draw comes back here
        fig = self.get_figure(root=True)
        outer, dpi = fig.canvas, fig.dpi
        outer_saving = outer.is_saving()
        measured = get_renderer(self.target)
        self.result = {
            "renderer": measured,
            "dpi": dpi,
            "outer_saving": outer_saving,
            "restored": fig.canvas is outer,
            "still_saving": fig.canvas.is_saving(),
            "dpi_after": fig.dpi,
            "position": self.ax.get_position().bounds,
            "extents": [
                text.get_window_extent(measured).bounds
                for text in _texts(self.ax)
            ],
        }


def _figure(kind, dpi, subfigure, constrained=True):
    """Build one labelled plot on the canvas ``kind`` names."""
    size = dm.figsize("13cm", "standard")
    if kind in ("pyplot", "closed"):
        fig = plt.figure(figsize=size, dpi=dpi)
    else:
        fig = Figure(figsize=size, dpi=dpi)
        if kind in _CANVASES:
            _CANVASES[kind](fig)
    if constrained:
        fig.set_layout_engine("constrained")
    target = fig.subfigures(1, 2)[1] if subfigure else fig
    ax = target.subplots()
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set(xlabel="Elapsed time (s)", ylabel="Signal", title="Observation")
    if kind == "closed":
        plt.close(fig)
    return fig, target, ax


def _texts(ax):
    return (ax.xaxis.label, ax.yaxis.label, ax.title)


def _control(dpi, subfigure, constrained=True):
    """Axes position and text extents of the same plot on a drawn Agg canvas."""
    fig, _, ax = _figure("agg", dpi, subfigure, constrained)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    extents = [text.get_window_extent(renderer).bounds for text in _texts(ax)]
    return ax.get_position().bounds, np.array(extents)


def _state(fig):
    """Caller-owned canvas, size, DPI and process plotting state."""
    return (
        fig.canvas,
        type(fig.canvas),
        fig.canvas.manager,
        fig.dpi,
        tuple(fig.get_size_inches()),
        mpl.get_backend(),
        tuple(plt.get_fignums()),
        dict(mpl.rcParams),
    )


def _draws(fig):
    """Collect the renderer of every draw of ``fig`` from now on."""
    renderers = []
    fig.canvas.mpl_connect(
        "draw_event", lambda event: renderers.append(event.renderer)
    )
    return renderers


def _assert_measures_at_figure_dpi(renderer, fig):
    assert isinstance(renderer, RendererAgg)
    assert renderer.points_to_pixels(72.0) == fig.dpi
    width, height = renderer.get_canvas_width_height()
    assert (width, height) == tuple(int(size) for size in fig.bbox.size)


def _assert_not_rasterized(renderer):
    """Nothing was painted: Agg clears to transparent, a figure paints opaque."""
    assert not np.asarray(renderer.buffer_rgba())[..., 3].any()


@pytest.mark.parametrize("kind", DETACHED)
@pytest.mark.parametrize("subfigure", [False, True])
@pytest.mark.parametrize("dpi", DPIS)
def test_detached_canvas_draws_once_at_figure_dpi(
    kind, subfigure, dpi, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    position, extents = _control(dpi, subfigure)
    fig, target, ax = _figure(kind, dpi, subfigure)
    assert not np.allclose(ax.get_position().bounds, position)
    draws = _draws(fig)
    before = _state(fig)
    child_canvas = target.canvas
    renderer = get_renderer(target)
    _assert_measures_at_figure_dpi(renderer, fig)
    _assert_not_rasterized(renderer)
    assert len(draws) == 1 and draws[0] is renderer
    np.testing.assert_allclose(
        ax.get_position().bounds, position, atol=1e-12, rtol=0
    )
    actual = [text.get_window_extent(renderer).bounds for text in _texts(ax)]
    np.testing.assert_allclose(actual, extents, atol=1e-10, rtol=0)
    assert _state(fig) == before
    assert target.canvas is child_canvas
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", LIVE)
@pytest.mark.parametrize("subfigure", [False, True])
@pytest.mark.parametrize("dpi", DPIS)
def test_live_canvas_returns_its_renderer_without_drawing(
    kind, subfigure, dpi, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    fig, target, ax = _figure(kind, dpi, subfigure)
    stale = ax.get_position().bounds
    draws = _draws(fig)
    before = _state(fig)
    renderer = get_renderer(target)
    assert renderer is fig.canvas.get_renderer()
    _assert_measures_at_figure_dpi(renderer, fig)
    assert draws == []
    assert ax.get_position().bounds == stale
    assert _state(fig) == before
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", DETACHED)
@pytest.mark.parametrize("subfigure", [False, True])
def test_artist_error_propagates_and_canvas_is_restored(
    kind, subfigure, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    fig, target, ax = _figure(kind, 123, subfigure)
    broken = target.add_artist(_BrokenArtist())
    before = _state(fig)
    with pytest.raises(RuntimeError, match="artist draw failed"):
        get_renderer(target)
    assert _state(fig) == before
    broken.remove()
    renderer = get_renderer(target)
    _assert_measures_at_figure_dpi(renderer, fig)
    _assert_not_rasterized(renderer)
    assert _state(fig) == before
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", LIVE)
def test_live_canvas_does_not_draw_a_broken_artist(kind):
    fig, target, _ = _figure(kind, 123, False)
    target.add_artist(_BrokenArtist())
    before = _state(fig)
    assert get_renderer(target) is fig.canvas.get_renderer()
    assert _state(fig) == before


@pytest.mark.parametrize("kind", LIVE + DETACHED)
@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_measurement_after_savefig_uses_restored_figure_dpi(
    kind, fmt, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    fig, target, ax = _figure(kind, 123, False)
    fig.savefig(io.BytesIO(), format=fmt, dpi=200)
    assert fig.dpi == 123
    before = _state(fig)
    renderer = get_renderer(target)
    _assert_measures_at_figure_dpi(renderer, fig)
    assert _state(fig) == before
    assert list(tmp_path.iterdir()) == []
    if kind in DETACHED:
        _assert_not_rasterized(renderer)
        position, extents = _control(123, False)
        np.testing.assert_allclose(
            ax.get_position().bounds, position, atol=1e-12, rtol=0
        )
        actual = [
            text.get_window_extent(renderer).bounds for text in _texts(ax)
        ]
        np.testing.assert_allclose(actual, extents, atol=1e-10, rtol=0)


@pytest.mark.parametrize("kind", DETACHED)
@pytest.mark.parametrize("fmt", ["pdf", "svg", "ps", "eps", "jpg"])
@pytest.mark.parametrize("subfigure", [False, True])
def test_savefig_format_does_not_pick_the_measurement_renderer(
    kind, fmt, subfigure, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    position, extents = _control(123, subfigure)
    with mpl.rc_context({"savefig.format": fmt}):
        fig, target, ax = _figure(kind, 123, subfigure)
        before = _state(fig)
        renderer = get_renderer(target)
        assert _state(fig) == before
    _assert_measures_at_figure_dpi(renderer, fig)
    _assert_not_rasterized(renderer)
    np.testing.assert_allclose(
        ax.get_position().bounds, position, atol=1e-12, rtol=0
    )
    actual = [text.get_window_extent(renderer).bounds for text in _texts(ax)]
    np.testing.assert_allclose(actual, extents, atol=1e-10, rtol=0)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", DETACHED)
def test_repeated_measurement_is_stable(kind):
    fig, target, ax = _figure(kind, 123, True)
    first = get_renderer(target)
    extents = [text.get_window_extent(first).bounds for text in _texts(ax)]
    before = _state(fig)
    second = get_renderer(target)
    _assert_not_rasterized(second)
    again = [text.get_window_extent(second).bounds for text in _texts(ax)]
    np.testing.assert_allclose(again, extents, atol=1e-10, rtol=0)
    assert _state(fig) == before


@pytest.mark.parametrize("kind", ("plain", "pdf", "closed"))
@pytest.mark.parametrize("fmt", ["pdf", "svg", "ps"])
@pytest.mark.parametrize("subfigure", [False, True])
def test_measurement_while_saving_keeps_output_and_not_the_saving_state(
    kind, fmt, subfigure, tmp_path, monkeypatch
):
    """An artist measures during a vector save, where the print canvas has no
    renderer of its own: the measurement runs at the DPI the save set, the
    print canvas stays in place and saving, the saved bytes equal a save
    without the measurement, and the temporary canvas reads not saving.

    No layout engine here: one would run again in the measuring draw with
    Agg text metrics and move the Axes in the middle of the save (the old
    private path did the same), so the bytes would differ for that reason.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    outputs, probes, spies = [], [], []
    for active in (False, True):
        mpl.rcParams["svg.hashsalt"] = "renderer-contract"
        fig, target, ax = _figure(kind, 123, subfigure, constrained=False)
        spy = fig.add_artist(_SavingSpy())
        probe = fig.add_artist(_MeasureWhileDrawn(target, ax, active))
        before = _state(fig)
        buffer = io.BytesIO()
        fig.savefig(buffer, format=fmt)
        assert _state(fig) == before
        outputs.append(buffer.getvalue())
        probes.append(probe)
        spies.append(spy)
    assert outputs[1] == outputs[0]
    assert probes[0].result is None
    assert [agg for agg, _ in spies[0].seen] == [False]
    result = probes[1].result
    assert result["outer_saving"] and result["still_saving"]
    assert result["restored"] and result["dpi_after"] == result["dpi"]
    renderer = result["renderer"]
    assert isinstance(renderer, RendererAgg)
    assert renderer.points_to_pixels(72.0) == result["dpi"]
    _assert_not_rasterized(renderer)
    measuring = [saving for agg, saving in spies[1].seen if agg]
    printing = [saving for agg, saving in spies[1].seen if not agg]
    assert measuring == [False]
    assert printing and all(printing)
    position, extents = _control(result["dpi"], subfigure, constrained=False)
    np.testing.assert_allclose(result["position"], position, atol=1e-12, rtol=0)
    np.testing.assert_allclose(result["extents"], extents, atol=1e-10, rtol=0)
    assert list(tmp_path.iterdir()) == []
