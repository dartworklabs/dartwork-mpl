"""Shared axes, same position and a native twin are three different contracts.

Measured on matplotlib 3.11.2:

* two independent Axes in one box: same position, nothing shared, not a twin;
* a separate Axes in one box with ``sharex``: same position, x shared, still
  not a native twin;
* a real ``twinx``: same position, x shared, a native twin.

``shared_axes`` answers only the sharing question; the position group
(``same_position_axes``) and the native-twin test keep their own meanings.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from dartwork_mpl._figure_geometry import same_position_axes, shared_axes
from dartwork_mpl.formatting import _twin_colors
from dartwork_mpl.validate._checks.preset_override import _is_twin

BOX = (0.1, 0.1, 0.8, 0.8)


def _independent() -> tuple[Figure, Axes, Axes]:
    fig = plt.figure()
    return fig, fig.add_axes(BOX), fig.add_axes(BOX)


def _sharex_overlay() -> tuple[Figure, Axes, Axes]:
    fig = plt.figure()
    first = fig.add_axes(BOX)
    return fig, first, fig.add_axes(BOX, sharex=first)


def _twinx() -> tuple[Figure, Axes, Axes]:
    fig, first = plt.subplots()
    return fig, first, first.twinx()


# name -> (builder, shared x, native twin)
CASES = {
    "independent": (_independent, False, False),
    "sharex_overlay": (_sharex_overlay, True, False),
    "twinx": (_twinx, True, True),
}


@pytest.mark.parametrize("name", CASES)
def test_each_contract_answers_on_its_own(name: str) -> None:
    build, shares_x, native_twin = CASES[name]
    fig, first, second = build()
    assert same_position_axes(first) == [first, second]
    assert (shared_axes(first, "x") == [first, second]) is shares_x
    assert shared_axes(first, "y") == [first]
    assert _is_twin(second, list(fig.axes)) is native_twin
    # the twin-colour grouping is by position, so all three form a group
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
    plt.close(fig)


def test_shared_panels_and_figure_order() -> None:
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)
    flat = list(axs.flat)
    assert shared_axes(flat[3], "x") == flat
    assert shared_axes(flat[0], "y") == flat
    assert all(len(same_position_axes(ax)) == 1 for ax in flat)
    plt.close(fig)


def test_inset_axes_stand_alone() -> None:
    fig, ax = plt.subplots()
    inset = ax.inset_axes((0.5, 0.5, 0.4, 0.4))
    assert shared_axes(inset, "x") == [inset]
    assert _is_twin(inset, list(fig.axes)) is False
    plt.close(fig)
