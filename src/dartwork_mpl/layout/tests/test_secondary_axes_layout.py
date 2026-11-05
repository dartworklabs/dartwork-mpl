"""``dm.simple_layout`` fits the text of ``secondary_xaxis`` / ``secondary_yaxis``.

Matplotlib keeps a secondary axis in its parent's ``child_axes``, not in
``fig.axes``, so the layout never measured its tick labels or axis label and
pushed them off the canvas (follow-up F2); ``dm.validate_figure`` did not see
them either. Both now treat them as the parent's own decorations.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm

# (orientation, location); for "bottom" / "left" the parent's own ticks and
# label move to the other side, so the secondary owns that edge.
SIDES = [("x", "top"), ("x", "bottom"), ("y", "left"), ("y", "right")]
_IDS = [loc for _, loc in SIDES]
# A label flush with the canvas edge is drawn whole; beyond this it is cut.
_EDGE_TOL_PX = 1.0


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _figure(orientation: str, location: str):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    t = np.linspace(0, 10, 50)
    ax.plot(t, 40 + 6 * t)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Speed (km/h)")
    if location == "bottom":
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position("top")
    if location == "left":
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
    if orientation == "x":
        secondary = ax.secondary_xaxis(
            location, functions=(lambda s: s * 60, lambda m: m / 60)
        )
        secondary.set_xlabel("Time (min)")
    else:
        secondary = ax.secondary_yaxis(
            location, functions=(lambda k: k / 1.609, lambda m: m * 1.609)
        )
        secondary.set_ylabel("Speed (mph)")
    return fig, ax, secondary


def _secondary_texts(secondary, orientation: str):
    """The secondary's drawn text: its label and the tick labels in view."""
    axis = secondary.xaxis if orientation == "x" else secondary.yaxis
    low, high = sorted(axis.get_view_interval())
    ticks = [
        label
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low <= loc <= high and label.get_visible() and label.get_text()
    ]
    return [axis.label, *ticks]


def _past_canvas_px(fig, texts) -> list[tuple[str, float]]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = fig.bbox
    out = []
    for text in texts:
        ext = text.get_window_extent(renderer)
        past = max(box.x0 - ext.x0, ext.x1 - box.x1, box.y0 - ext.y0)
        past = max(past, ext.y1 - box.y1)
        if past > _EDGE_TOL_PX:
            out.append((text.get_text(), round(float(past), 1)))
    return out


def _edge_findings(fig) -> list[tuple[str, str]]:
    """``(check id, text)`` of each OVERFLOW / CLIPPED_TEXT finding."""
    found = dm.validate_figure(
        fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
    )
    return [(w.check_id, str(w.detail.get("text", ""))) for w in found]


@pytest.mark.parametrize(("orientation", "location"), SIDES, ids=_IDS)
def test_secondary_axis_text_stays_on_the_canvas(orientation, location):
    fig, _ax, secondary = _figure(orientation, location)
    dm.simple_layout(fig)
    texts = _secondary_texts(secondary, orientation)
    assert len(texts) >= 3, [t.get_text() for t in texts]
    assert _past_canvas_px(fig, texts) == []
    assert _edge_findings(fig) == []


@pytest.mark.parametrize(("orientation", "location"), SIDES, ids=_IDS)
def test_secondary_axis_side_is_fitted_flush(orientation, location):
    """With ``margin=0`` the secondary's outer text meets the canvas edge.

    The secondary's labels reserve their room like the parent's own: just
    enough, not more.
    """
    fig, _ax, secondary = _figure(orientation, location)
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    exts = [
        t.get_window_extent(renderer)
        for t in _secondary_texts(secondary, orientation)
    ]
    box = fig.bbox
    gap = {
        "top": box.y1 - max(e.y1 for e in exts),
        "bottom": min(e.y0 for e in exts) - box.y0,
        "left": min(e.x0 for e in exts) - box.x0,
        "right": box.x1 - max(e.x1 for e in exts),
    }[location]
    assert abs(gap) <= 1.5, gap


def test_top_and_right_secondaries_together():
    """The PoC case: ``secondary_xaxis("top")`` and ``secondary_yaxis("right")``."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    t = np.linspace(0, 10, 50)
    ax.plot(t, 40 + 6 * t)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Speed (km/h)")
    top = ax.secondary_xaxis(
        "top", functions=(lambda s: s * 60, lambda m: m / 60)
    )
    top.set_xlabel("Time (min)")
    right = ax.secondary_yaxis(
        "right", functions=(lambda k: k / 1.609, lambda m: m * 1.609)
    )
    right.set_ylabel("Speed (mph)")
    dm.simple_layout(fig)
    texts = [*_secondary_texts(top, "x"), *_secondary_texts(right, "y")]
    assert _past_canvas_px(fig, texts) == []
    assert _edge_findings(fig) == []


@pytest.mark.parametrize(("orientation", "location"), SIDES, ids=_IDS)
def test_validate_figure_sees_secondary_text_past_the_canvas(
    orientation, location
):
    """Margins too small for the secondary: the checks report its text."""
    fig, _ax, secondary = _figure(orientation, location)
    flush = 0.0 if location in ("left", "bottom") else 1.0
    fig.subplots_adjust(**{location: flush})  # no room on that side
    texts = _secondary_texts(secondary, orientation)
    assert _past_canvas_px(fig, texts), "the figure must push text off"
    words = {t.get_text() for t in texts}
    findings = _edge_findings(fig)
    assert {check for check, text in findings if text in words} == {
        "OVERFLOW",
        "CLIPPED_TEXT",
    }, findings
