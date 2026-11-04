"""Text checks see left/right axes titles and skip hidden twin axes (#523).

``ax.set_title(..., loc="left")`` stores the headline in a private Text the
checks used to skip, so a title pushed off the canvas validated clean. A
twin (``twinx`` / ``twiny``) hides the axis it shares, yet
CROSS_AXES_OVERLAP compared that hidden axis's tick labels with the host's
and reported every dual-axis figure. Real collisions between twins (two
titles) must still be reported.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import validate_figure

HEADLINE = "Revenue has doubled since 2020"


def _warnings(fig, checks):
    return validate_figure(fig, checks=checks, quiet=True)


def _titled_axes_flush_to_top(loc: str):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([1, 3, 2])
    ax.set_title(HEADLINE, loc=loc)
    # The axes box touches the canvas top, so the title sits above it.
    fig.subplots_adjust(top=1.0)
    return fig


@pytest.mark.parametrize("loc", ["left", "right"])
@pytest.mark.parametrize("check", ["OVERFLOW", "CLIPPED_TEXT"])
def test_side_title_past_the_canvas_is_flagged(loc: str, check: str) -> None:
    fig = _titled_axes_flush_to_top(loc)
    found = _warnings(fig, (check,))
    assert any(w.detail.get("text") == HEADLINE for w in found), found
    plt.close(fig)


def test_side_title_inside_the_canvas_is_clean() -> None:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([1, 3, 2])
    ax.set_title(HEADLINE, loc="left")
    dm.simple_layout(fig)
    assert _warnings(fig, ("OVERFLOW", "CLIPPED_TEXT")) == []
    plt.close(fig)


def test_overlap_sees_a_left_title() -> None:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([1, 3, 2])
    title = ax.set_title(HEADLINE, loc="left")
    dm.simple_layout(fig)
    fig.canvas.draw()
    ext = title.get_window_extent(fig.canvas.get_renderer())
    ax.annotate("Subtitle", xy=(ext.x0, ext.y0), xycoords="figure pixels")
    pairs = {
        frozenset((w.detail["label_a"], w.detail["label_b"]))
        for w in _warnings(fig, ("OVERLAP",))
    }
    assert frozenset((HEADLINE[:30], "Subtitle")) in pairs
    plt.close(fig)


def test_cross_axes_sees_a_lower_panels_left_title() -> None:
    dm.style.use("scientific")
    # Default hspace is too small for an upper xlabel plus a lower title.
    fig, (upper, lower) = plt.subplots(2, 1, figsize=dm.figsize("9cm", 0.75))
    for ax in (upper, lower):
        ax.plot([1, 3, 2])
        ax.set_xlabel("Time", fontsize=dm.fs(2))
        ax.set_title("Panel headline", loc="left", fontsize=dm.fs(4))
    roles = {
        (w.detail["role_a"], w.detail["role_b"])
        for w in _warnings(fig, ("CROSS_AXES_OVERLAP",))
    }
    assert any("title" in pair for pair in roles), roles
    plt.close(fig)


def _twins(twin: str):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot([0, 1, 2], [1, 2, 3])
    ax.set_xlabel("x")
    ax.set_ylabel("left")
    other = getattr(ax, twin)()
    other.plot([0, 1, 2], [30, 10, 20], color="C1")
    other.set_ylabel("right")
    other.set_xlabel("top")
    return fig, ax, other


@pytest.mark.parametrize("twin", ["twinx", "twiny"])
def test_clean_twin_axes_are_not_a_cross_axes_overlap(twin: str) -> None:
    fig, _ax, _other = _twins(twin)
    dm.simple_layout(fig)
    assert _warnings(fig, ("CROSS_AXES_OVERLAP",)) == []
    plt.close(fig)


@pytest.mark.parametrize("twin", ["twinx", "twiny"])
def test_colliding_twin_titles_are_still_reported(twin: str) -> None:
    fig, ax, other = _twins(twin)
    ax.set_title("Host headline")
    other.set_title("Twin headline")
    dm.simple_layout(fig)
    roles = {
        (w.detail["role_a"], w.detail["role_b"])
        for w in _warnings(fig, ("CROSS_AXES_OVERLAP",))
    }
    assert roles == {("title", "title")}
    plt.close(fig)


def test_shared_axis_panels_in_separate_boxes_are_still_checked() -> None:
    dm.style.use("scientific")
    fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", 0.75), sharex=True)
    for ax in axes:
        ax.plot([1, 3, 2])
        ax.set_xlabel("Time", fontsize=dm.fs(2))
        ax.set_title("Panel headline", fontsize=dm.fs(4))
    assert _warnings(fig, ("CROSS_AXES_OVERLAP",)) != []
    plt.close(fig)
