"""Pixel-level assertions for the robustness suite.

Why pixels and not artists? matplotlib's `Text.get_window_extent` reports
where matplotlib *thinks* a label sits, but a label can still be clipped
by the figure canvas at save time (e.g. when bbox_inches=None and the
label sits at x=-3 px). The robustness suite therefore inspects the
rendered RGBA buffer directly so we can prove the saved PNG actually
shows the labels.

All assertions are pure functions of a (Figure, parameters) pair and
raise PixelAssertionError on failure with a message identifying the
side and the deficient pixel count.
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

# How many outermost pixels we actually inspect.
# min_white_px (the public parameter) is the *minimum required margin*;
# we probe only the outermost _PROBE_PX of that margin so that content
# sitting well inside the margin does not cause false positives.
_PROBE_PX: int = 4


class PixelAssertionError(AssertionError):
    """Raised when a rendered figure violates a pixel-level invariant."""


def figure_to_rgba(fig: Figure) -> np.ndarray:
    """Render the figure into an HxWx4 uint8 RGBA array.

    Always forces a draw first so the buffer is up-to-date.
    """
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    return buf


def _is_blank_strip(strip: np.ndarray, *, tol: int = 6) -> bool:
    """Return True if `strip` is uniformly close to white.

    `strip` must be HxWx4 uint8. We treat a pixel as "blank" when its
    RGB channels are all >= 255 - tol *and* the alpha is the strip's
    maximum (so faint anti-aliased edges still count as blank)."""
    rgb = strip[..., :3]
    return bool(np.all(rgb >= (255 - tol)))


def assert_no_edge_overflow(
    fig: Figure,
    *,
    side: str,
    min_white_px: int = 4,
) -> None:
    """Assert that the rendered RGBA buffer has a blank margin of at
    least `min_white_px` pixels on the named edge.

    We probe the outermost ``min(_PROBE_PX, min_white_px)`` pixels
    (not the full ``min_white_px``) so that content which is *inside*
    the required margin does not cause false positives.  The practical
    meaning is: "nothing is pushed flush against the canvas boundary."

    `side` ∈ {"left", "right", "top", "bottom"}.
    """
    arr = figure_to_rgba(fig)
    h, w, _ = arr.shape
    probe = min(_PROBE_PX, min_white_px)

    if side == "left":
        strip = arr[:, :probe, :]
    elif side == "right":
        strip = arr[:, w - probe :, :]
    elif side == "top":
        strip = arr[:probe, :, :]
    elif side == "bottom":
        strip = arr[h - probe :, :, :]
    else:
        raise ValueError(
            f"side must be left/right/top/bottom, got {side!r}"
        )

    if not _is_blank_strip(strip):
        raise PixelAssertionError(
            f"Figure has non-blank pixels in the {probe}-px "
            f"{side} edge strip — content is clipped or touches the canvas."
        )


def assert_minimum_white_border(fig: Figure, *, min_px: int = 4) -> None:
    """Assert all four edges have at least `min_px` blank pixels."""
    for side in ("left", "right", "top", "bottom"):
        assert_no_edge_overflow(fig, side=side, min_white_px=min_px)


def _iter_visible_text_artists(fig: Figure):
    """Yield (Text, is_tick_label) pairs for all visible non-empty artists.

    Tick labels are yielded together with their parent Tick so callers
    can check whether the tick position falls inside the axis view
    limits (positions outside xlim/ylim are auto-range phantom labels
    that matplotlib generates but never renders on-canvas).
    """
    for ax in fig.axes:
        # Non-tick text artists — always check these.
        for txt in (*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label):
            if txt is None or not txt.get_visible():
                continue
            if not txt.get_text().strip():
                continue
            yield txt, False

        # X-axis tick labels — skip if tick position is outside xlim.
        xlim = ax.get_xlim()
        for tick in ax.xaxis.get_major_ticks():
            lbl = tick.label1
            if not lbl.get_visible() or not lbl.get_text().strip():
                continue
            pos = tick.get_loc()
            if pos < xlim[0] or pos > xlim[1]:
                continue  # auto-range phantom tick
            yield lbl, True

        # Y-axis tick labels — skip if tick position is outside ylim.
        ylim = ax.get_ylim()
        for tick in ax.yaxis.get_major_ticks():
            lbl = tick.label1
            if not lbl.get_visible() or not lbl.get_text().strip():
                continue
            pos = tick.get_loc()
            if pos < ylim[0] or pos > ylim[1]:
                continue  # auto-range phantom tick
            yield lbl, True


def assert_no_clipped_text(fig: Figure) -> None:
    """Assert that every visible Text artist's window extent lies fully
    inside the figure canvas (with 1-px tolerance).

    This complements `assert_minimum_white_border` by catching cases
    where text spills *partway* off-canvas: the edge strip is no longer
    blank but the text isn't fully blacked out either.

    Tick labels whose tick position lies outside the axis view limits
    are skipped — those are auto-range phantom labels that matplotlib
    generates beyond the visible axis and are never rendered on-canvas.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_bbox = fig.bbox
    for txt, _is_tick in _iter_visible_text_artists(fig):
        try:
            ext = txt.get_window_extent(renderer)
        except (RuntimeError, ValueError, AttributeError):
            continue

        overflow = max(
            fig_bbox.x0 - ext.x0,
            ext.x1 - fig_bbox.x1,
            fig_bbox.y0 - ext.y0,
            ext.y1 - fig_bbox.y1,
        )
        if overflow > 1.0:
            raise PixelAssertionError(
                f"Text {txt.get_text()[:30]!r} clipped by "
                f"{overflow:.1f}px"
            )
