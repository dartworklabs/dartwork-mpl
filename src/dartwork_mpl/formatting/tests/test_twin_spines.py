"""A twin's own right spine shows at ``dm.simple_layout``, not at import (D7).

Up to 0.7, ``import dartwork_mpl`` replaced ``matplotlib.axes.Axes.twinx``
with a wrapper that ran two lines on the Axes it returned::

    twin.spines["right"].set_visible(True)
    twin.spines["right"].set_linewidth(rcParams["axes.linewidth"])

From 0.8 ``dm.simple_layout`` shows that spine instead (the rule is in the
docstring of ``dartwork_mpl.formatting._twin_spines``). The oracle of the
parity tests is that 0.7 behaviour re-enacted by hand: each figure is built
twice, plainly and with those two lines run right after every ``twinx()``,
both are laid out, and the drawn pixels and every spine's drawn state must
match. The controls are the ones that tell position, shared axes and a native
twin apart (``_figure_geometry/tests/test_shared_axes_contract.py``):
side-by-side Axes, two Axes in one box, a ``sharex`` overlay, ``twinx``,
``twiny``, plus three y axes with an offset spine.

The rest pins where 0.8 differs from 0.7 on purpose: a figure that is not laid
out keeps the preset's hidden right spine, and a right spine hidden between
``twinx()`` and the first layout cannot be told from the preset's and shows.
"""

from __future__ import annotations

from collections.abc import Callable

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting import show_twin_spines

X = np.arange(6)
SIDES = ("left", "right", "bottom", "top")


@pytest.fixture(autouse=True)
def _scientific():
    with matplotlib.rc_context():
        dm.style.use("scientific")
        yield
    plt.close("all")


def _twinx(ax: Axes, old: bool) -> Axes:
    """``ax.twinx()``; with ``old``, what the 0.7 import-time patch added."""
    twin = ax.twinx()
    if old:
        twin.spines["right"].set_visible(True)
        twin.spines["right"].set_linewidth(
            matplotlib.rcParams["axes.linewidth"]
        )
    return twin


def _figure() -> Figure:
    return plt.figure(figsize=dm.figsize("9cm", "standard"))


def _draw_pair(a: Axes, b: Axes) -> None:
    a.plot(X, [3, 4, 6, 5, 7, 8], color="dc.blue6", marker="o")
    b.plot(X, [80, 60, 65, 40, 35, 20], color="dc.orange6", marker="s")
    a.set_xlabel("step")
    a.set_ylabel("A (units)")
    b.set_ylabel("B (units)")


def _side_by_side(old: bool) -> tuple[Figure, Axes, Axes]:
    fig = _figure()
    a, b = fig.subplots(1, 2)
    _draw_pair(a, b)
    return fig, a, b


def _one_box(*, sharex: bool) -> tuple[Figure, Axes, Axes]:
    """Two Axes made separately in one GridSpec cell (no ``twinx``)."""
    fig = _figure()
    gs = fig.add_gridspec(1, 1)
    a = fig.add_subplot(gs[0])
    b = fig.add_subplot(gs[0], sharex=a if sharex else None)
    _draw_pair(a, b)
    return fig, a, b


def _coincident(old: bool) -> tuple[Figure, Axes, Axes]:
    return _one_box(sharex=False)


def _sharex_overlay(old: bool) -> tuple[Figure, Axes, Axes]:
    return _one_box(sharex=True)


def _twinx_pair(old: bool) -> tuple[Figure, Axes, Axes]:
    fig = _figure()
    a = fig.add_subplot()
    b = _twinx(a, old)
    _draw_pair(a, b)
    return fig, a, b


def _twiny_pair(old: bool) -> tuple[Figure, Axes, Axes]:
    fig = _figure()
    a = fig.add_subplot()
    b = a.twiny()
    _draw_pair(a, b)
    b.set_xlabel("other step")
    return fig, a, b


def _three_y_axes(old: bool) -> tuple[Figure, Axes, Axes]:
    fig, a = plt.subplots(figsize=dm.figsize("14cm", "standard"))
    b = _twinx(a, old)
    c = _twinx(a, old)
    c.spines["right"].set_position(("axes", 1.15))
    _draw_pair(a, b)
    c.plot(X, [100, 200, 150, 250, 230, 260], color="dc.green6")
    c.set_ylabel("C (units)")
    return fig, a, b


Builder = Callable[[bool], tuple[Figure, Axes, Axes]]
CONTROLS: dict[str, Builder] = {
    "side_by_side": _side_by_side,
    "coincident": _coincident,
    "sharex_overlay": _sharex_overlay,
    "twinx": _twinx_pair,
    "twiny": _twiny_pair,
    "three_y_axes": _three_y_axes,
}


def _spines(fig: Figure) -> list[dict[str, tuple[bool, float, str]]]:
    """Every spine as drawn: shown, line width, colour."""
    return [
        {
            side: (
                bool(
                    ax.axison
                    and ax.get_frame_on()
                    and ax.spines[side].get_visible()
                ),
                float(ax.spines[side].get_linewidth()),
                matplotlib.colors.to_hex(
                    ax.spines[side].get_edgecolor(), keep_alpha=True
                ),
            )
            for side in SIDES
        }
        for ax in fig.axes
    ]


def _pixels(fig: Figure) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _laid_out(
    build: Builder, old: bool, edit: Callable[..., None] | None = None
) -> tuple[np.ndarray, list[dict[str, tuple[bool, float, str]]]]:
    fig, a, b = build(old)
    if edit is not None:
        edit(fig, a, b)
    dm.simple_layout(fig)
    result = _pixels(fig), _spines(fig)
    plt.close(fig)
    return result


def _assert_same_as_07(
    build: Builder, edit: Callable[..., None] | None = None
) -> None:
    old_pixels, old_spines = _laid_out(build, True, edit)
    new_pixels, new_spines = _laid_out(build, False, edit)
    assert new_spines == old_spines
    assert np.array_equal(new_pixels, old_pixels)


# ------------------------------------------------------- import identity
def test_twinx_is_matplotlibs_own() -> None:
    # Axes inherits twinx; a rebinding would put it in Axes' own namespace.
    assert "twinx" not in vars(Axes)
    assert "twiny" not in vars(Axes)


def test_twinx_alone_keeps_the_preset_spines() -> None:
    fig, a, b = _twinx_pair(old=False)
    assert not b.spines["right"].get_visible()  # scientific hides it


# ------------------------------------------------------- 0.7 parity
@pytest.mark.parametrize("name", CONTROLS)
def test_controls_look_as_in_07_after_the_layout(name: str) -> None:
    _assert_same_as_07(CONTROLS[name])


@pytest.mark.parametrize("name", CONTROLS)
def test_controls_under_neutral_twin_colours(name: str) -> None:
    with dm.config.override(twin_colors="neutral"):
        _assert_same_as_07(CONTROLS[name])


@pytest.mark.parametrize("preset", ["report", "presentation", "minimal"])
def test_twinx_under_other_presets(preset: str) -> None:
    dm.style.use(preset)
    _assert_same_as_07(_twinx_pair)


def _hand_styled(fig: Figure, a: Axes, b: Axes) -> None:
    b.spines["right"].set_color("dc.red6")
    b.spines["right"].set_linewidth(1.2)
    b.spines["right"].set_position(("outward", 4))
    b.tick_params(axis="y", colors="dc.red6")
    b.yaxis.label.set_color("dc.red6")


def _shown_on_the_parent(fig: Figure, a: Axes, b: Axes) -> None:
    a.spines["right"].set_visible(True)
    a.spines["top"].set_visible(True)


def _frame_off(fig: Figure, a: Axes, b: Axes) -> None:
    b.set_frame_on(False)


@pytest.mark.parametrize(
    "edit", [_hand_styled, _shown_on_the_parent, _frame_off]
)
def test_explicit_settings_before_the_layout_stay(
    edit: Callable[..., None],
) -> None:
    _assert_same_as_07(_twinx_pair, edit)


def test_spine_hidden_after_a_layout_stays_hidden() -> None:
    def build(old: bool) -> tuple[Figure, Axes, Axes]:
        fig, a, b = _twinx_pair(old)
        dm.simple_layout(fig)
        b.spines["right"].set_visible(False)
        return fig, a, b

    _assert_same_as_07(build)
    fig, _, b = build(False)
    dm.simple_layout(fig)
    dm.simple_layout(fig)
    assert not b.spines["right"].get_visible()


def test_twin_made_after_a_layout_shows_at_the_next() -> None:
    def build(old: bool) -> tuple[Figure, Axes, Axes]:
        fig = _figure()
        a = fig.add_subplot()
        dm.simple_layout(fig)
        b = _twinx(a, old)
        _draw_pair(a, b)
        return fig, a, b

    _assert_same_as_07(build)


def test_series_colour_reaches_the_shown_spine() -> None:
    fig, _, b = _twinx_pair(old=False)
    dm.simple_layout(fig)
    spine = b.spines["right"]
    assert spine.get_visible()
    assert matplotlib.colors.to_hex(spine.get_edgecolor()) != "#000000"


# ------------------------------------------------------- the rule itself
def test_returns_the_spines_it_showed_once() -> None:
    fig, a, b = _three_y_axes(old=False)
    assert show_twin_spines(fig) == 2
    assert show_twin_spines(fig) == 0
    assert [ax.spines["right"].get_visible() for ax in fig.axes] == [
        False,
        True,
        True,
    ]


def test_hidden_before_the_first_layout_shows() -> None:
    """0.8 differs from 0.7: the preset hides it too, so it is not a choice."""
    fig, _, b = _twinx_pair(old=False)
    b.spines["right"].set_visible(False)
    dm.simple_layout(fig)
    assert b.spines["right"].get_visible()


def test_a_sharex_overlay_drawn_on_the_right_shows_its_spine() -> None:
    fig, _, b = _sharex_overlay(old=False)
    b.yaxis.tick_right()
    b.yaxis.set_label_position("right")
    dm.simple_layout(fig)
    assert b.spines["right"].get_visible()


def test_twin_scale_moved_left_shows_no_right_spine() -> None:
    fig, a, b = _twinx_pair(old=False)
    b.yaxis.tick_left()
    b.yaxis.set_label_position("left")
    dm.simple_layout(fig)
    assert not b.spines["right"].get_visible()
    assert not a.spines["right"].get_visible()


def test_twin_with_its_y_axis_hidden_shows_no_right_spine() -> None:
    fig, _, b = _twinx_pair(old=False)
    b.yaxis.set_visible(False)
    dm.simple_layout(fig)
    assert not b.spines["right"].get_visible()


def test_twiny_top_spine_is_left_to_the_preset() -> None:
    fig, a, b = _twiny_pair(old=False)
    dm.simple_layout(fig)
    assert not b.spines["top"].get_visible()
    assert not a.spines["top"].get_visible()


def test_refused_layout_changes_nothing() -> None:
    fig = _figure()
    a = fig.add_axes((0.15, 0.15, 0.7, 0.7))
    b = a.twinx()
    with pytest.warns(UserWarning, match="no GridSpec"):
        dm.simple_layout(fig)
    assert not b.spines["right"].get_visible()
