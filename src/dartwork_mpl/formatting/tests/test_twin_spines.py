"""A twin's own right spine shows at ``dm.simple_layout``, not at import (D7).

Up to 0.7, ``import dartwork_mpl`` replaced ``matplotlib.axes.Axes.twinx``
with a wrapper that ran two lines on the Axes it returned::

    twin.spines["right"].set_visible(True)
    twin.spines["right"].set_linewidth(rcParams["axes.linewidth"])

From 0.8 ``dm.simple_layout`` shows that spine instead (the rule is in the
docstring of ``dartwork_mpl.formatting._twin_spines``). Each case in
``CASES`` builds a figure and lays it out. A parity case must match 0.7 in
two independent ways:

* ``twin_spines_07_golden.json``: the drawn state of every Axes (each
  spine shown / width / colour, the y and x label and tick colours) that
  origin/main recorded with the 0.7 wrapper installed, before any D7 code
  existed (its ``recorded_from`` field). Nothing here derives it from the
  library, so a change to a helper both sides share cannot cancel out. A
  difference is a look change that needs its own decision; never re-record
  the fixture to make a test pass.
* the pixels of the same case with the 0.7 wrapper re-installed and the new
  spine step switched off, rendered in this run.

The controls tell position, shared axes and a native twin apart: side by
side panels (with a shared x too), two Axes in one box, ``sharex`` and
``sharex`` + ``sharey`` overlays, ``twinx``, ``twiny``, three y axes with an
offset spine and an inset's ``twinx``; with scales moved to the right where
0.7 drew no line. Every one also runs under neutral twin colours and with
``format_ticks=False``. Twins with half-moved scales (only the ticks or only
the label moved left, x02 and x03 of the D7 review, and ``b.twinx()`` of a
twin, x04) keep 0.7's line too. The rest pins where 0.8 differs from 0.7 on
purpose: 11-1 to 11-5 and decision 14, all approved by the user on
2026-11-07.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

import dartwork_mpl as dm
import dartwork_mpl.layout as dm_layout

GOLDEN = Path(__file__).with_name("twin_spines_07_golden.json")
X = np.arange(6)
SIDES = ("left", "right", "bottom", "top")


@pytest.fixture(autouse=True)
def _scientific() -> Iterator[None]:
    with matplotlib.rc_context():
        dm.style.use("scientific")
        yield
    plt.close("all")


def install_07(target: Any) -> None:
    """Re-install the 0.7 import-time wrapper on ``target`` (a monkeypatch).

    The body is 0.7's, verbatim. The new spine step is switched off, so the
    figure is what 0.7's code drew.
    """
    original = Axes.twinx

    def twinx(self: Axes, *args: Any, **kwargs: Any) -> Axes:
        ax2 = original(self, *args, **kwargs)
        ax2.spines["right"].set_visible(True)
        ax2.spines["right"].set_linewidth(
            matplotlib.rcParams.get("axes.linewidth", 0.3)
        )
        return ax2

    target.setattr(Axes, "twinx", twinx)
    if hasattr(dm_layout, "_show_twin_spines"):
        target.setattr(dm_layout, "_show_twin_spines", lambda fig: None)


# ------------------------------------------------------------ builders
Built = tuple[Figure, Axes, Axes]


def _figure(width: str = "9cm") -> Figure:
    return plt.figure(figsize=dm.figsize(width, "standard"))


def _draw_pair(a: Axes, b: Axes) -> None:
    a.plot(X, [3, 4, 6, 5, 7, 8], color="dc.blue6", marker="o")
    b.plot(X, [80, 60, 65, 40, 35, 20], color="dc.orange6", marker="s")
    a.set_xlabel("step")
    a.set_ylabel("A (units)")
    b.set_ylabel("B (units)")


def _to_right(ax: Axes) -> None:
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")


def _side_by_side(*, sharex: bool = False) -> Built:
    fig = _figure()
    a, b = fig.subplots(1, 2, sharex=sharex)
    _draw_pair(a, b)
    return fig, a, b


def _one_box(*, sharex: bool = False, sharey: bool = False) -> Built:
    """Two Axes made separately in one GridSpec cell (no ``twinx``)."""
    fig = _figure()
    gs = fig.add_gridspec(1, 1)
    a = fig.add_subplot(gs[0])
    b = fig.add_subplot(
        gs[0], sharex=a if sharex else None, sharey=a if sharey else None
    )
    b.patch.set_visible(False)
    _draw_pair(a, b)
    return fig, a, b


def _twinx_pair() -> Built:
    fig = _figure()
    a = fig.add_subplot()
    b = a.twinx()
    _draw_pair(a, b)
    return fig, a, b


def _twiny_pair() -> Built:
    fig = _figure()
    a = fig.add_subplot()
    b = a.twiny()
    _draw_pair(a, b)
    b.set_xlabel("other step")
    return fig, a, b


def _three_y_axes() -> Built:
    fig = _figure("14cm")
    a = fig.add_subplot()
    b = a.twinx()
    c = a.twinx()
    c.spines["right"].set_position(("axes", 1.15))
    _draw_pair(a, b)
    c.plot(X, [100, 200, 150, 250, 230, 260], color="dc.green6")
    c.set_ylabel("C (units)")
    return fig, a, b


def _inset_twinx() -> Built:
    fig = _figure("12cm")
    host = fig.add_subplot()
    host.plot(X, X, color="dc.gray6")
    a = host.inset_axes((0.55, 0.15, 0.35, 0.35))
    b = a.twinx()
    _draw_pair(a, b)
    return fig, a, b


def _nested_inset_twinx() -> Built:
    fig = _figure("12cm")
    host = fig.add_subplot()
    host.plot(X, X, color="dc.gray6")
    inset = host.inset_axes((0.5, 0.1, 0.45, 0.5))
    inset.plot(X, X, color="dc.gray6")
    a = inset.inset_axes((0.5, 0.5, 0.45, 0.45))
    b = a.twinx()
    _draw_pair(a, b)
    return fig, a, b


def _parent_right_offset(a: Axes, b: Axes) -> None:
    """The parent's scale to the right, at its own offset place (n11)."""
    _to_right(a)
    a.spines["right"].set_position(("outward", 30))


def _ticks_both_label_right(a: Axes, b: Axes) -> None:
    """Tick labels on both sides and the label right (m03)."""
    b.tick_params(
        axis="y", left=True, labelleft=True, right=True, labelright=True
    )
    b.yaxis.set_label_position("right")


def _moved(build: Callable[[], Built], move: Callable[..., None]) -> Built:
    fig, a, b = build()
    move(a, b)
    return fig, a, b


BUILDS: dict[str, Callable[[], Built]] = {
    "side_by_side": _side_by_side,
    "side_by_side_sharex_b_right": lambda: _moved(
        lambda: _side_by_side(sharex=True), lambda a, b: _to_right(b)
    ),
    "one_box": _one_box,
    "one_box_b_right": lambda: _moved(_one_box, lambda a, b: _to_right(b)),
    "sharex_overlay": lambda: _one_box(sharex=True),
    "sharex_overlay_b_label_right": lambda: _moved(
        lambda: _one_box(sharex=True),
        lambda a, b: b.yaxis.set_label_position("right"),
    ),
    "sharex_overlay_b_ticks_both_label_right": lambda: _moved(
        lambda: _one_box(sharex=True), _ticks_both_label_right
    ),
    "sharex_sharey_overlay_b_right": lambda: _moved(
        lambda: _one_box(sharex=True, sharey=True), lambda a, b: _to_right(b)
    ),
    "twinx": _twinx_pair,
    "twinx_a_label_right": lambda: _moved(
        _twinx_pair, lambda a, b: a.yaxis.set_label_position("right")
    ),
    "twinx_a_right_too": lambda: _moved(_twinx_pair, lambda a, b: _to_right(a)),
    "twinx_a_right_offset": lambda: _moved(_twinx_pair, _parent_right_offset),
    "twinx_b_marks_off": lambda: _moved(
        _twinx_pair, lambda a, b: b.tick_params(axis="y", right=False)
    ),
    "twinx_b_ticks_left": lambda: _moved(
        _twinx_pair, lambda a, b: b.yaxis.tick_left()
    ),
    "twinx_b_label_left": lambda: _moved(
        _twinx_pair, lambda a, b: b.yaxis.set_label_position("left")
    ),
    "twin_of_the_twin": lambda: _moved(_twinx_pair, lambda a, b: b.twinx()),
    "twiny": _twiny_pair,
    "three_y_axes": _three_y_axes,
    "inset_twinx": _inset_twinx,
    "nested_inset_twinx": _nested_inset_twinx,
}


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


def _hidden_after_a_layout(fig: Figure, a: Axes, b: Axes) -> None:
    dm.simple_layout(fig)
    b.spines["right"].set_visible(False)


def _shown_by_hand_then_hidden_after_a_layout(
    fig: Figure, a: Axes, b: Axes
) -> None:
    b.spines["right"].set_visible(True)
    dm.simple_layout(fig)
    b.spines["right"].set_visible(False)


def _twin_made_after_a_layout() -> Built:
    fig = _figure()
    a = fig.add_subplot()
    dm.simple_layout(fig)
    b = a.twinx()
    _draw_pair(a, b)
    return fig, a, b


def _case(
    build: Callable[[], Built],
    *,
    edit: Callable[[Figure, Axes, Axes], None] | None = None,
    neutral: bool = False,
    preset: str | None = None,
    **layout: Any,
) -> Callable[[], Figure]:
    def make() -> Figure:
        if preset is not None:
            dm.style.use(preset)
        colours = (
            dm.config.override(twin_colors="neutral")
            if neutral
            else contextlib.nullcontext()
        )
        with colours:
            fig, a, b = build()
            if edit is not None:
                edit(fig, a, b)
            dm.simple_layout(fig, **layout)
        return fig

    return make


CASES: dict[str, Callable[[], Figure]] = {}
for _name, _build in BUILDS.items():
    CASES[_name] = _case(_build)
    CASES[f"{_name}/neutral"] = _case(_build, neutral=True)
    CASES[f"{_name}/format_ticks_off"] = _case(_build, format_ticks=False)
for _preset in ("report", "presentation", "minimal"):
    CASES[f"twinx/{_preset}"] = _case(_twinx_pair, preset=_preset)
for _edit in (
    _hand_styled,
    _shown_on_the_parent,
    _frame_off,
    _hidden_after_a_layout,
    _shown_by_hand_then_hidden_after_a_layout,
):
    CASES[f"twinx/{_edit.__name__.strip('_')}"] = _case(_twinx_pair, edit=_edit)
CASES["twin_made_after_a_layout"] = _case(_twin_made_after_a_layout)


# ------------------------------------------------------------ observing
def _members(axes: list[Axes]) -> list[Axes]:
    """``axes``, each followed by its inset Axes, depth first."""
    out: list[Axes] = []
    for ax in axes:
        out.append(ax)
        out.extend(_members([c for c in ax.child_axes if isinstance(c, Axes)]))
    return out


def _hex(color: Any) -> str:
    return matplotlib.colors.to_hex(color, keep_alpha=True)


def state(fig: Figure) -> list[dict[str, Any]]:
    """What each Axes draws for its frame and scales, after a canvas draw."""
    fig.canvas.draw()
    out = []
    for ax in _members(list(fig.axes)):
        row: dict[str, Any] = {
            "spines": {
                side: [
                    bool(
                        ax.axison
                        and ax.get_frame_on()
                        and ax.spines[side].get_visible()
                    ),
                    round(float(ax.spines[side].get_linewidth()), 4),
                    _hex(ax.spines[side].get_edgecolor()),
                ]
                for side in SIDES
            }
        }
        for name, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            tick = (axis.get_major_ticks() or axis.get_major_ticks(1))[0]
            row[name] = [
                bool(axis.get_visible()),
                _hex(axis.label.get_color()),
                _hex(tick.tick1line.get_color()),
                _hex(tick.tick2line.get_color()),
                _hex(tick.label1.get_color()),
                _hex(tick.label2.get_color()),
            ]
        out.append(row)
    return out


def _pixels(fig: Figure) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _run(name: str) -> tuple[np.ndarray, list[dict[str, Any]], Figure]:
    fig = CASES[name]()
    return _pixels(fig), state(fig), fig


def _run_07(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    with monkeypatch.context() as patch:
        install_07(patch)
        fig = CASES[name]()
        return _pixels(fig), state(fig)


# ------------------------------------------------------------ import
def test_twinx_is_matplotlibs_own() -> None:
    # Axes inherits twinx; a rebinding would put it in Axes' own namespace.
    assert "twinx" not in vars(Axes)
    assert "twiny" not in vars(Axes)


def test_twinx_alone_keeps_the_preset_spines() -> None:
    fig, a, b = _twinx_pair()
    assert not b.spines["right"].get_visible()  # scientific hides it


# ------------------------------------------------------------ 0.7 parity
def test_golden_names_every_parity_case() -> None:
    recorded = json.loads(GOLDEN.read_text())
    assert recorded["recorded_from"].startswith("origin/main ")
    assert sorted(recorded["cases"]) == sorted(CASES)


@pytest.mark.parametrize("name", sorted(CASES))
def test_case_draws_what_07_drew(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = json.loads(GOLDEN.read_text())["cases"][name]
    pixels, drawn, _ = _run(name)
    assert drawn == golden
    old_pixels, old_drawn = _run_07(name, monkeypatch)
    assert old_drawn == golden  # the live re-enactment is 0.7 too
    assert np.array_equal(pixels, old_pixels)


def test_hand_set_width_and_colour_stay() -> None:
    _, _, fig = _run("twinx/hand_styled")
    spine = fig.axes[1].spines["right"]
    assert spine.get_visible()
    assert spine.get_linewidth() == 1.2
    assert _hex(spine.get_edgecolor()) == _hex("dc.red6")
    assert spine.get_position() == ("outward", 4)


@pytest.mark.parametrize("format_ticks", [True, False])
def test_shown_with_or_without_the_tick_formats(format_ticks: bool) -> None:
    fig, _, b = _twinx_pair()
    dm.simple_layout(fig, format_ticks=format_ticks)
    assert b.spines["right"].get_visible()


def test_inset_twin_gets_no_series_colours() -> None:
    """The inset spine is 0.7's; inset pairs stay out of the twin colours."""
    _, drawn, fig = _run("inset_twinx")
    inset_twin = drawn[-1]
    assert inset_twin["spines"]["right"][:2] == [True, 0.3]
    assert inset_twin["spines"]["right"][2] == _hex("black")


# ------------------------------------------------------- 0.8 differences
def _differs_from_07(
    build: Callable[[], Built],
    edit: Callable[[Figure, Axes, Axes], None],
    monkeypatch: pytest.MonkeyPatch,
    *,
    owner: int,
    shown: bool,
) -> None:
    """``owner``'s right spine shows as ``shown`` in 0.8, the other way in 0.7."""
    for old in (False, True):
        with monkeypatch.context() as patch:
            if old:
                install_07(patch)
            fig, a, b = build()
            edit(fig, a, b)
            spine = fig.axes[owner].spines["right"]
            assert spine.get_visible() is (shown != old)
            plt.close(fig)


def test_11_1_no_layout_keeps_the_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _differs_from_07(
        _twinx_pair, lambda *_: None, monkeypatch, owner=1, shown=False
    )


def test_11_2_hidden_before_the_first_layout_shows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def hide_then_lay_out(fig: Figure, a: Axes, b: Axes) -> None:
        b.spines["right"].set_visible(False)
        dm.simple_layout(fig)

    _differs_from_07(
        _twinx_pair, hide_then_lay_out, monkeypatch, owner=1, shown=True
    )


@pytest.mark.parametrize("marks", [True, False], ids=["marks", "labels_only"])
def test_11_3_sharex_overlay_moved_right_shows(
    marks: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its x axis shows, so ticks and label both count; tick labels without
    marks (``tick_params(right=False)``) are still ticks on the right."""

    def move(fig: Figure, a: Axes, b: Axes) -> None:
        _to_right(b)
        if not marks:
            b.tick_params(axis="y", right=False)
        dm.simple_layout(fig)

    _differs_from_07(
        lambda: _one_box(sharex=True), move, monkeypatch, owner=1, shown=True
    )


def test_11_4_swapped_sides_move_the_line_to_the_parent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def swap(fig: Figure, a: Axes, b: Axes) -> None:
        _to_right(a)
        b.yaxis.tick_left()
        b.yaxis.set_label_position("left")
        dm.simple_layout(fig)

    _differs_from_07(_twinx_pair, swap, monkeypatch, owner=0, shown=True)
    _differs_from_07(_twinx_pair, swap, monkeypatch, owner=1, shown=False)


def test_pending_m02_twin_label_left_and_right_ticks_off_shows_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Awaiting the user's decision (m02, 결정 대기): pins today's behaviour.

    A twin whose y label moved left and whose right ticks are turned off
    draws no y scale on the right, so it gets no line; 0.7 drew one. This is
    not part of the approved 11-4; the decision waits for its own PoC.
    """

    def turn_off(fig: Figure, a: Axes, b: Axes) -> None:
        b.yaxis.set_label_position("left")
        b.tick_params(axis="y", right=False, labelright=False)
        dm.simple_layout(fig)

    _differs_from_07(_twinx_pair, turn_off, monkeypatch, owner=1, shown=False)


def test_11_5_twin_with_its_y_axis_hidden_shows_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def hide(fig: Figure, a: Axes, b: Axes) -> None:
        b.yaxis.set_visible(False)
        dm.simple_layout(fig)

    _differs_from_07(_twinx_pair, hide, monkeypatch, owner=1, shown=False)


def _overlay_like_a_twin() -> Built:
    """A ``sharex`` overlay drawn like a twin: x axis and background hidden."""
    fig, a, b = _one_box(sharex=True)
    b.xaxis.set_visible(False)
    a.set_adjustable("datalim")
    b.set_adjustable("datalim")
    _to_right(b)
    return fig, a, b


@pytest.mark.parametrize(
    "move",
    [
        pytest.param(lambda b: b.yaxis.tick_left(), id="ticks_left"),
        pytest.param(
            lambda b: b.yaxis.set_label_position("left"), id="label_left"
        ),
    ],
)
def test_14_overlay_drawn_like_a_twin_shows_with_half_its_scale_right(
    move: Callable[[Axes], object], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decision 14: the overlay of the x02/x03 counterexample pairs.

    Its public state equals the twin's with the same half-moved scale (only
    matplotlib's private ``_twinned_axes`` differs). The twin keeps 0.7's
    line, so this overlay gains one, which 0.7 did not draw.
    """

    def edit(fig: Figure, a: Axes, b: Axes) -> None:
        move(b)
        dm.simple_layout(fig)

    _differs_from_07(
        _overlay_like_a_twin, edit, monkeypatch, owner=1, shown=True
    )


# ------------------------------------------------------- the rule itself
def test_returns_the_spines_it_showed_once() -> None:
    from dartwork_mpl.formatting import show_twin_spines

    fig, a, b = _three_y_axes()
    assert show_twin_spines(fig) == 2
    assert show_twin_spines(fig) == 0
    assert [ax.spines["right"].get_visible() for ax in fig.axes] == [
        False,
        True,
        True,
    ]


def test_spine_hidden_after_a_layout_stays_hidden_on_relayout() -> None:
    fig, _, b = _twinx_pair()
    dm.simple_layout(fig)
    b.spines["right"].set_visible(False)
    dm.simple_layout(fig)
    dm.simple_layout(fig)
    assert not b.spines["right"].get_visible()


def test_twiny_top_spine_is_left_to_the_preset() -> None:
    fig, a, b = _twiny_pair()
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
