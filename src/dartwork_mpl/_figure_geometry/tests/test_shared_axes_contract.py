"""Shared axes, same position, a native twin and the twin role are four contracts.

Measured on matplotlib 3.11.2:

* two independent Axes in one box: same position, nothing shared, not a
  twin either way;
* a separate Axes in one box with ``sharex``: same position, x shared, not
  a native twin and not drawn as a twin (its x axis shows);
* the same overlay with its x axis hidden (decision 14 of the D7 review):
  not a native twin, but drawn as a twin is;
* a real ``twinx``: same position, x shared, a native twin, drawn as one;
* that twin with its x axis shown again: still a native twin, no longer
  drawn as one.

``shared_axes`` answers only the sharing question and ``same_position_axes``
only the box question. The native twin is matplotlib's private
``_twinned_axes`` grouper: no library code reads it, and this module reads it
only as an independent control. The twin role is
:func:`dartwork_mpl.formatting.drawn_like_twin`, which ``PRESET_OVERRIDE``
skips; it is read from public state. The three cases where the native twin
and the role agree say nothing about whether they mean the same; the two
where they differ pin the role's own meaning.
"""

from __future__ import annotations

from collections.abc import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from dartwork_mpl._figure_geometry import same_position_axes, shared_axes
from dartwork_mpl.formatting import _twin_colors, drawn_like_twin

BOX = (0.1, 0.1, 0.8, 0.8)


def _native_twin(first: Axes, second: Axes) -> bool:
    """Whether matplotlib joined the pair in its private twin grouper."""
    return second in first._twinned_axes.get_siblings(first)


def _independent() -> tuple[Figure, Axes, Axes]:
    fig = plt.figure()
    return fig, fig.add_axes(BOX), fig.add_axes(BOX)


def _sharex_overlay() -> tuple[Figure, Axes, Axes]:
    fig = plt.figure()
    first = fig.add_axes(BOX)
    return fig, first, fig.add_axes(BOX, sharex=first)


def _overlay_drawn_like_a_twin() -> tuple[Figure, Axes, Axes]:
    fig, first, second = _sharex_overlay()
    second.xaxis.set_visible(False)
    return fig, first, second


def _twinx() -> tuple[Figure, Axes, Axes]:
    fig, first = plt.subplots()
    return fig, first, first.twinx()


def _twin_with_its_x_axis_shown() -> tuple[Figure, Axes, Axes]:
    fig, first, second = _twinx()
    second.xaxis.set_visible(True)
    return fig, first, second


Build = Callable[[], tuple[Figure, Axes, Axes]]

# name -> (builder, shared x, native twin, twin role)
CASES: dict[str, tuple[Build, bool, bool, bool]] = {
    "independent": (_independent, False, False, False),
    "sharex_overlay": (_sharex_overlay, True, False, False),
    "overlay_drawn_like_a_twin": (
        _overlay_drawn_like_a_twin,
        True,
        False,
        True,
    ),
    "twinx": (_twinx, True, True, True),
    "twin_with_its_x_axis_shown": (
        _twin_with_its_x_axis_shown,
        True,
        True,
        False,
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_each_contract_answers_on_its_own(name: str) -> None:
    build, shares_x, native_twin, twin_role = CASES[name]
    fig, first, second = build()
    assert same_position_axes(first) == [first, second]
    assert (shared_axes(first, "x") == [first, second]) is shares_x
    assert shared_axes(first, "y") == [first]
    assert _native_twin(first, second) is native_twin
    assert drawn_like_twin(second) is twin_role
    assert drawn_like_twin(first) is False  # nothing before it in its box
    # the twin-colour grouping is by position, so every case forms a group
    assert _twin_colors._twin_groups(fig) == [[first, second]]
    assert _twin_colors._reads_on(first, "bottom", second) is shares_x
    assert _twin_colors._reads_on(first, "left", second) is False
    plt.close(fig)


def test_twinx_and_twiny_share_one_axis_each() -> None:
    fig, ax = plt.subplots()
    right, top = ax.twinx(), ax.twiny()
    assert shared_axes(ax, "x") == [ax, right]
    assert shared_axes(ax, "y") == [ax, top]
    assert _twin_colors._own_sides(right, [ax, right, top]) == ["right"]
    assert [drawn_like_twin(m) for m in (ax, right, top)] == [False, True, True]
    plt.close(fig)


def test_shared_panels_and_figure_order() -> None:
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)
    flat = list(axs.flat)
    assert shared_axes(flat[3], "x") == flat
    assert shared_axes(flat[0], "y") == flat
    assert all(len(same_position_axes(ax)) == 1 for ax in flat)
    assert not any(drawn_like_twin(ax) for ax in flat)
    plt.close(fig)


def test_the_twin_role_needs_one_box_and_an_earlier_axes() -> None:
    """A ``sharex`` panel in another box with its x axis hidden is no twin;
    in one box, the role goes to the later Axes, not to a parent that hides
    the shared axis while its twin shows it."""
    fig, (upper, lower) = plt.subplots(2, 1, sharex=True)
    lower.xaxis.set_visible(False)
    assert drawn_like_twin(lower) is False
    plt.close(fig)
    fig, first, second = _twin_with_its_x_axis_shown()
    first.xaxis.set_visible(False)
    assert [drawn_like_twin(first), drawn_like_twin(second)] == [False, False]
    plt.close(fig)


def test_the_twin_role_needs_exactly_one_shared_axis_and_hides_it() -> None:
    """An overlay sharing both axes is no twin, x axis hidden or not; a
    ``twiny`` whose y axis shows again leaves the role as a ``twinx`` does."""
    fig = plt.figure()
    first = fig.add_axes(BOX)
    both = fig.add_axes(BOX, sharex=first, sharey=first)
    both.xaxis.set_visible(False)
    assert drawn_like_twin(both) is False
    plt.close(fig)
    fig, ax = plt.subplots()
    top = ax.twiny()
    assert drawn_like_twin(top) is True
    top.yaxis.set_visible(True)
    assert _native_twin(ax, top) is True
    assert drawn_like_twin(top) is False
    plt.close(fig)


def test_inset_axes_stand_alone() -> None:
    fig, ax = plt.subplots()
    inset = ax.inset_axes((0.5, 0.5, 0.4, 0.4))
    assert shared_axes(inset, "x") == [inset]
    assert drawn_like_twin(inset) is False
    plt.close(fig)


def test_an_inset_twin_plays_the_role_though_its_box_is_not_in_fig_axes() -> (
    None
):
    """``inset.twinx()`` lands in ``fig.axes``, the inset does not; the role
    walks the insets too (each Axes followed by its insets)."""
    fig, ax = plt.subplots()
    inset = ax.inset_axes((0.5, 0.5, 0.4, 0.4))
    twin = inset.twinx()
    fig.canvas.draw()  # the inset's place comes from its locator
    assert inset not in fig.axes and twin in fig.axes
    assert _native_twin(inset, twin) is True
    assert same_position_axes(twin) == [twin]  # its own walk is fig.axes
    assert drawn_like_twin(twin) is True
    assert drawn_like_twin(inset) is False
    plt.close(fig)
