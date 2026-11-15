"""A renderer to measure a figure with, and the errors measuring may raise."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from matplotlib.backends.backend_agg import FigureCanvasAgg

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure

#: Exceptions matplotlib may raise from ``get_window_extent`` /
#: ``get_tightbbox`` on artists in degenerate states (NaN-only data,
#: zero-area fonts, renderers that refuse the call). Single source for
#: both the layout engine and the validation checks — the two used to
#: carry identical private copies.
BBOX_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    AttributeError,
)


@runtime_checkable
class _Rendering(Protocol):
    """A canvas that hands out its renderer (Agg and its subclasses)."""

    def get_renderer(self) -> RendererBase: ...


def canvas_renderer(fig: Figure | SubFigure) -> RendererBase | None:
    """The canvas's own renderer at the Figure's current size and DPI.

    ``None`` when the canvas has no ``get_renderer`` (a plain Figure, or a
    vector canvas while matplotlib saves). Unlike :func:`get_renderer` it
    never draws, so an artist may call it while the figure is drawn.
    """
    canvas = fig.canvas
    if isinstance(canvas, _Rendering):
        return canvas.get_renderer()
    return None


class _PngCanvas(FigureCanvasAgg):
    """A temporary Agg canvas whose default output is PNG.

    ``Figure.draw_without_rendering`` draws with the renderer of the
    canvas's default file type, which an Agg canvas reads from
    ``rcParams["savefig.format"]``. A PDF, SVG or PS default would switch
    to that print canvas, which sets the Figure DPI to 72 and leaves it
    there. Fixing the default here keeps the measurement at the Figure DPI
    without writing to the process-wide rcParams.
    """

    @classmethod
    def get_default_filetype(cls) -> str:
        """Return ``"png"`` whatever ``savefig.format`` says."""
        return "png"


def get_renderer(fig: Figure | SubFigure) -> RendererBase:
    """Return a measurement renderer without replacing the caller's canvas.

    Live rendering canvases keep their native renderer, without a draw. A
    plain Figure, a vector canvas, or a Figure closed by matplotlib 3.11
    has no ``canvas.get_renderer``. Then a temporary Agg canvas at the
    Figure's current DPI draws the root Figure once without output
    (``Figure.draw_without_rendering``) so artist positions are current,
    and its renderer is returned. The caller's canvas is set back even
    when drawing fails; artist errors propagate unchanged. The temporary
    canvas prints PNG whatever ``savefig.format`` says, which avoids the
    DPI change made by the PDF/SVG/PS print renderers.

    Such a Figure is always measured with Agg, also when another canvas is
    registered for PNG (``backend_bases.register_backend("png", ...)``,
    cairo say), whose text metrics can differ by a few pixels; a live
    canvas of any backend measures with its own renderer. The temporary
    canvas does not take over the caller's saving state: called while the
    figure is saved, ``canvas.is_saving()`` reads ``False`` in the
    measuring draw, so animated artists are left out of it.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
        Figure or SubFigure to measure. Fallback drawing uses its root
        Figure so SubFigure transforms and sibling positions are current.

    Returns
    -------
    matplotlib.backend_bases.RendererBase
        Native canvas renderer, or a temporary renderer at the Figure DPI.
    """
    native = canvas_renderer(fig)
    if native is not None:
        return native
    root = fig.get_figure(root=True)
    original = root.canvas
    try:
        measuring = _PngCanvas(root)  # attaches itself as root.canvas
        root.draw_without_rendering()
        renderer: RendererBase = measuring.get_renderer()
    finally:
        root.set_canvas(original)
    return renderer
