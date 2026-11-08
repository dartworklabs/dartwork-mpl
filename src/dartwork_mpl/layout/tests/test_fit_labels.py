"""The label-fitting ladder of ``simple_layout`` (``layout/_fit_labels.py``).

Pure decisions are checked on numbers; the layout contract on figures:
no collision leaves the figure as before, each step acts only where text
collides and only on what nobody set, a second layout gives the same
figure, and ``fit_labels=False`` gives the unfitted figure back. The
overlap oracle is ``TICK_OVERLAP`` (``validate/_checks/tick_overlap.py``),
which measures the drawn labels independently of the ladder's arithmetic.
"""

from __future__ import annotations

import math
from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import get_renderer
from dartwork_mpl.layout._fit_labels import (
    WrappedTickFormatter,
    balanced_lines,
    gap_fraction,
    resolve_steps,
    restore_fitted,
    smallest_angle,
    tokens,
    wrap_limit,
    wrap_to,
)
from dartwork_mpl.validate._checks.tick_overlap import check_tick_overlap


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _chars(line: str) -> float:
    return float(len(line))


# ── pure decisions ─────────────────────────────────────────────────


def test_tokens_keep_a_bracketed_unit_whole() -> None:
    assert tokens("Energy per building (MWh per year)") == [
        "Energy",
        "per",
        "building",
        "(MWh per year)",
    ]
    assert tokens("Load (kW), net") == ["Load", "(kW),", "net"]


def test_balanced_lines_minimise_the_widest_line() -> None:
    lines, w = balanced_lines(["Residential", "heat", "pumps"], 2, _chars)
    assert lines == ["Residential", "heat pumps"]
    assert w == len("Residential")


def test_wrap_to_uses_the_fewest_lines_that_fit() -> None:
    assert wrap_to("Variant A", 7, _chars, 3) == "Variant\nA"
    assert wrap_to("Other renewable sources combined", 15, _chars, 3) == (
        "Other renewable\nsources\ncombined"
    )
    assert wrap_to("Thermoregulation", 5, _chars, 3) is None  # no space
    assert wrap_to("a b c d e", 1, _chars, 3) is None  # needs five lines


def test_wrap_limit_borrows_from_short_neighbours_only() -> None:
    # gap 10, clearance 2: fair share 8; a 2-wide neighbour leaves 14
    assert wrap_limit(1, [2.0, 30.0, 2.0], [10.0, 10.0], 2.0) == 14.0
    # two long neighbours each keep to their share
    assert wrap_limit(1, [30.0, 30.0, 30.0], [10.0, 10.0], 2.0) == 8.0
    # the first label has one neighbour
    assert wrap_limit(0, [30.0, 2.0], [10.0], 2.0) == 14.0


@pytest.mark.parametrize(
    ("spacing", "expected"),
    [(40.0, 30.0), (20.0, 45.0), (15.0, 90.0), (9.0, None)],
)
def test_smallest_angle(spacing: float, expected: float | None) -> None:
    # line height 10, clearance 2: need spacing * sin(angle) >= 12
    assert smallest_angle(spacing, 10.0, 2.0) == expected


def test_smallest_angle_never_turns_back() -> None:
    assert smallest_angle(40.0, 10.0, 2.0, start=45.0) == 45.0


def test_gap_fraction_matches_matplotlib_cells() -> None:
    frac = gap_fraction(20.0, 400.0, 3)
    assert frac is not None
    cell = 400.0 / (3 + frac * 2)
    assert math.isclose(frac * cell, 20.0)
    assert gap_fraction(300.0, 400.0, 3) is None


def test_resolve_steps() -> None:
    assert resolve_steps(True) == {"axis_labels", "space", "wrap", "rotate"}
    assert resolve_steps(False) == frozenset()
    assert resolve_steps(["wrap"]) == {"wrap"}
    assert resolve_steps("wrap") == {"wrap"}
    with pytest.raises(ValueError, match="unknown step"):
        resolve_steps(["shrink"])
    with pytest.raises(TypeError, match="fit_labels"):
        resolve_steps(1)  # type: ignore[arg-type]


def test_an_unknown_step_raises_before_the_figure_is_touched() -> None:
    fig, ax = _bars([f"Variant {c}" for c in "ABCDEFGH"], preset="scientific")
    before = ax.get_position().bounds
    with pytest.raises(ValueError, match="unknown step"):
        dm.simple_layout(fig, fit_labels=("wrap", "shrink"))
    assert ax.get_position().bounds == before


# ── the layout contract ────────────────────────────────────────────


def _bars(labels: list[str], width: str = "9cm", preset: str = "report"):
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    ax.bar(range(len(labels)), np.arange(len(labels)) + 1.0)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel("Output (MWh)")
    return fig, ax


def _overlaps(fig) -> int:
    fig.canvas.draw()
    return len(check_tick_overlap(fig, get_renderer(fig)))


def _pixels(fig) -> bytes:
    fig.canvas.draw()
    return bytes(fig.canvas.buffer_rgba())


def _texts(ax) -> list[str]:
    ax.get_figure().canvas.draw()
    return [t.get_text() for t in ax.get_xticklabels()]


def _angles(ax) -> set[float]:
    ax.get_figure().canvas.draw()
    return {t.get_rotation() for t in ax.get_xticklabels()}


_VARIANTS = [f"Variant {c}" for c in "ABCDEFGH"]
_ONE_WORD = [
    "Thermoregulation",
    "Electrification",
    "Decarbonisation",
    "Interconnection",
] * 2


def test_no_collision_draws_exactly_as_without_the_ladder() -> None:
    fig_a, _ = _bars(["A", "B", "C"])
    dm.simple_layout(fig_a)
    fig_b, _ = _bars(["A", "B", "C"])
    dm.simple_layout(fig_b, fit_labels=False)
    assert _pixels(fig_a) == _pixels(fig_b)


def test_crowded_two_word_labels_wrap_and_stop_overlapping() -> None:
    fig, ax = _bars(_VARIANTS, preset="scientific")
    dm.simple_layout(fig, fit_labels=False)
    assert _overlaps(fig) == 1
    dm.simple_layout(fig)
    assert isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)
    assert _texts(ax)[0] == "Variant\nA"
    assert _angles(ax) == {0.0}
    assert _overlaps(fig) == 0


def test_a_long_label_beside_short_ones_wraps_alone() -> None:
    labels = ["Coal", "Gas", "Combined heat and power plants", "Oil", "Hydro"]
    fig, ax = _bars(labels, width="9cm", preset="report")
    dm.simple_layout(fig, fit_labels=False)
    assert _overlaps(fig) == 1
    dm.simple_layout(fig)
    texts = _texts(ax)
    assert texts == [
        *labels[:2],
        "Combined heat\nand power plants",
        *labels[3:],
    ]
    assert _overlaps(fig) == 0


def test_labels_that_cannot_wrap_turn_instead() -> None:
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig)
    assert _angles(ax) == {30.0}  # the smallest angle that clears
    assert {t.get_rotation_mode() for t in ax.get_xticklabels()} == {"xtick"}
    assert _overlaps(fig) == 0


def test_two_word_labels_turn_when_wrapping_is_not_allowed() -> None:
    fig, ax = _bars(_VARIANTS, preset="scientific")
    dm.simple_layout(fig, fit_labels=("rotate",))
    assert not isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)
    assert _angles(ax) == {30.0}
    assert _overlaps(fig) == 0


def test_labels_that_cannot_wrap_stay_when_turning_is_not_allowed() -> None:
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig, fit_labels=("wrap",))
    assert _angles(ax) == {0.0}
    assert _overlaps(fig) == 1  # left for the author, and reported


def test_labels_however_long_turn_when_the_plot_keeps_its_share() -> None:
    """Upright these names clear and take 40 % of the figure height; the
    plot keeps 62 % of its height, so the check after the round keeps the
    turn (no share cap on the turned labels themselves)."""
    names = [f"Thermoregulation{i}" for i in range(6)]
    heights = []
    for fit in (False, True):
        dm.style.use("presentation")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "tall"))
        ax.bar(range(len(names)), np.ones(len(names)))
        ax.set_xticks(range(len(names)), names)
        dm.simple_layout(fig, fit_labels=fit)
        heights.append(ax.get_window_extent().height)
    assert _angles(ax) == {90.0}
    assert _overlaps(fig) == 0
    assert heights[1] / heights[0] == pytest.approx(0.62, abs=0.01)


def test_a_second_layout_draws_the_same_figure() -> None:
    """Undone and fitted again, a wrapped or turned figure draws the same."""
    for preset, labels in (("scientific", _VARIANTS), ("report", _ONE_WORD)):
        fig, ax = _bars(labels, width="9cm", preset=preset)
        dm.simple_layout(fig)
        first = (_texts(ax), _angles(ax), _pixels(fig))
        dm.simple_layout(fig)
        assert (_texts(ax), _angles(ax), _pixels(fig)) == first


def test_a_wider_canvas_refits_from_the_unfitted_labels() -> None:
    fig, ax = _bars(_VARIANTS, preset="scientific")
    dm.simple_layout(fig)
    assert "\n" in _texts(ax)[0]
    fig.set_size_inches(dm.figsize("17cm", "standard"))
    dm.simple_layout(fig)
    assert _texts(ax) == _VARIANTS


def _label_state(ax) -> list[tuple]:
    ax.get_figure().canvas.draw()
    return [
        (t.get_text(), t.get_rotation(), t.get_rotation_mode(), t.get_ha())
        for t in ax.get_xticklabels()
    ]


def test_fit_labels_false_undoes_an_earlier_fit() -> None:
    """Labels, formatter and spacing come back, and the figure draws
    exactly as a fresh layout without fitting: the re-layout starts from
    the edges the first one started from, not from those it left (the
    margin fit stops within half a pixel of its fixed point, so its start
    decides the last hundredths: 0.028 px for the turned labels here)."""
    for labels in (_VARIANTS, _ONE_WORD):
        ref, ref_ax = _bars(labels, preset="scientific")
        dm.simple_layout(ref, fit_labels=False)
        fig, ax = _bars(labels, preset="scientific")
        dm.simple_layout(fig)
        assert _label_state(ax) != _label_state(ref_ax)
        dm.simple_layout(fig, fit_labels=False)
        assert type(ax.xaxis.get_major_formatter()) is type(
            ref_ax.xaxis.get_major_formatter()
        )
        assert ax.xaxis.isDefault_majfmt == ref_ax.xaxis.isDefault_majfmt
        assert _label_state(ax) == _label_state(ref_ax)
        assert _pixels(fig) == _pixels(ref)


def test_a_second_layout_draws_the_same_figure_when_a_turn_was_taken_back() -> (
    None
):
    """advanced/boxplot at 9 cm: the turn is tried and taken back, each try
    fitting the margins again. Without fitting, and with it, a second and a
    third call draw what the first did (the margins converge on the
    plot's height slowly here: each fit moved them 0.02-0.2 px)."""
    for fit in (False, True):
        fig, ax = _template_figure("advanced/boxplot.py", "presentation", "9cm")
        draws = []
        for _call in range(3):
            dm.simple_layout(fig, margin=dm.inch(0.08), fit_labels=fit)
            draws.append(_pixels(fig))
        assert draws[1] == draws[0]
        assert draws[2] == draws[0]


def test_the_next_layout_starts_from_where_the_last_one_did() -> None:
    fig, ax = _bars(_ONE_WORD)
    gs = ax.get_gridspec()
    start = (gs.left, gs.right, gs.bottom, gs.top)
    dm.simple_layout(fig)
    assert (gs.left, gs.right, gs.bottom, gs.top) != start
    restore_fitted(fig)
    assert (gs.left, gs.right, gs.bottom, gs.top) == start
    # moved Axes follow (a figure pyplot does not manage as well)
    assert ax.get_position().bounds == pytest.approx(
        gs[0].get_position(fig).bounds
    )

    fig, ax = _bars(_ONE_WORD)
    gs = ax.get_gridspec()
    dm.simple_layout(fig)
    gs.update(left=0.2)  # yours since: stays
    restore_fitted(fig)
    assert gs.left == 0.2
    assert gs.bottom is not None


def test_fit_labels_false_leaves_colliding_labels_as_they_are() -> None:
    for labels in (_VARIANTS, _ONE_WORD):
        fig, ax = _bars(labels, preset="scientific")
        before = _label_state(ax)
        dm.simple_layout(fig, fit_labels=False)
        assert _label_state(ax) == before
        assert _overlaps(fig) == 1


def test_your_rotation_line_breaks_alignment_and_mathtext_stay() -> None:
    fig, ax = _bars(_VARIANTS)
    ax.tick_params(axis="x", labelrotation=20)
    dm.simple_layout(fig)
    assert _angles(ax) == {20.0}
    assert not isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)

    fig, ax = _bars([f"Variant\n{c}" for c in "ABCDEFGH"])
    dm.simple_layout(fig)
    assert _angles(ax) == {0.0}
    assert not isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)

    fig, ax = _bars(_ONE_WORD)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    dm.simple_layout(fig)
    assert _angles(ax) == {0.0}

    fig, ax = _bars([rf"$\alpha_{{{i}}}$ variant" for i in range(30)])
    dm.simple_layout(fig)
    assert _angles(ax) == {0.0}
    assert not isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)


def test_a_rotation_you_set_after_a_layout_stays() -> None:
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig)
    assert _angles(ax) == {30.0}
    plt.setp(ax.get_xticklabels(), rotation=60)
    dm.simple_layout(fig)
    assert _angles(ax) == {60.0}


def test_spacing_you_passed_stays_and_free_spacing_grows() -> None:
    dm.style.use("scientific")

    def panels(**kw):
        fig, axs = plt.subplots(2, 1, figsize=dm.figsize("9cm", "tall"), **kw)
        for ax in axs:
            ax.plot([0, 1], [0, 1])
            ax.set_title("Panel")
            ax.set_xlabel("Time (h)")
        return fig, axs

    fig, axs = panels(gridspec_kw={"hspace": 0.05})
    dm.simple_layout(fig)
    assert axs[0].get_gridspec().hspace == 0.05
    fig, axs = panels()
    dm.simple_layout(fig)
    assert axs[0].get_gridspec().hspace > fig.subplotpars.hspace
    assert (
        dm.validate_figure(fig, checks=("CROSS_AXES_OVERLAP",), quiet=True)
        == []
    )
    dm.simple_layout(fig, fit_labels=False)
    assert axs[0].get_gridspec().hspace is None


def test_panels_whose_text_does_not_meet_keep_their_spacing() -> None:
    dm.style.use("scientific")
    fig, axs = plt.subplots(2, 2, figsize=dm.figsize("17cm", "standard"))
    for ax in axs.flat:
        ax.plot([0, 1], [0, 1])
    dm.simple_layout(fig)
    gs = axs[0, 0].get_gridspec()
    assert (gs.wspace, gs.hspace) == (None, None)


def test_a_name_beside_a_panel_wraps_and_comes_back() -> None:
    dm.style.use("presentation")
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("12cm", "standard")
    )
    for ax in (left, right):
        ax.plot([0, 1], [0, 1])
    name = "Cumulative delivered heat per building (MWh)"
    left.set_xlabel(name)
    dm.simple_layout(fig)
    assert "\n" in left.get_xlabel()
    assert left.get_xlabel().split("\n")[-1].endswith("(MWh)")
    dm.simple_layout(fig, fit_labels=False)
    assert left.get_xlabel() == name


def test_a_name_longer_than_the_figure_wraps() -> None:
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 1])
    name = "Cumulative delivered heat energy per connected building (MWh)"
    ax.set_ylabel(name)
    dm.simple_layout(fig)
    assert "\n" in ax.get_ylabel()
    assert ax.get_ylabel().split("\n")[-1].endswith("(MWh)")
    dm.simple_layout(fig, fit_labels=False)
    assert ax.get_ylabel() == name


def test_a_name_with_nothing_in_its_way_stays_on_one_line() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 1])
    name = "Delivered heat energy per connected building (MWh)"
    ax.set_ylabel(name)
    dm.simple_layout(fig)
    renderer = get_renderer(fig)
    assert ax.yaxis.label.get_window_extent(renderer).height > (
        ax.get_window_extent(renderer).height
    ), "precondition: longer than its side of the plot"
    assert ax.get_ylabel() == name


def test_config_default_is_read_per_call() -> None:
    fig, ax = _bars(_VARIANTS, preset="scientific")
    with dm.config.override(fit_labels=False):
        dm.simple_layout(fig)
    assert not isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)
    with dm.config.override(fit_labels=("rotate",)):
        dm.simple_layout(fig)
    assert _angles(ax) == {30.0}
    dm.simple_layout(fig)
    assert _angles(ax) == {0.0}
    assert isinstance(ax.xaxis.get_major_formatter(), WrappedTickFormatter)


# ── each rung acts only where text collides ────────────────────────


def _clearance_px(ax) -> float:
    """Smallest room between neighbouring bottom tick labels (px)."""
    fig = ax.get_figure()
    fig.canvas.draw()
    renderer = get_renderer(fig)
    spans = sorted(
        (b.x0, b.x1)
        for b in (t.get_window_extent(renderer) for t in ax.get_xticklabels())
    )
    return min(b[0] - a[1] for a, b in pairwise(spans))


def test_tick_labels_that_only_come_close_stay() -> None:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9.2cm", "standard"))
    ax.bar(range(8), np.arange(8) + 1.0)
    ax.set_xticks(range(8), _VARIANTS)
    dm.simple_layout(fig, fit_labels=False)
    em = ax.get_xticklabels()[0].get_fontsize() * fig.dpi / 72
    assert 0 < _clearance_px(ax) < 0.5 * em, "precondition: close, apart"
    before = _pixels(fig)
    dm.simple_layout(fig)
    assert _texts(ax) == _VARIANTS
    assert _pixels(fig) == before


def test_panels_whose_text_only_comes_close_keep_their_spacing() -> None:
    from dartwork_mpl.layout._content_extent import _axes_content_extent_px

    dm.style.use("scientific")
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("14cm", "standard")
    )
    for ax in (left, right):
        ax.plot([0, 1], [0, 1000])
    right.set_ylabel("Load (kW)")
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    renderer = get_renderer(fig)
    room = (
        _axes_content_extent_px(right, renderer, fig)[0]
        - _axes_content_extent_px(left, renderer, fig)[1]
    )
    em = matplotlib.rcParams["font.size"] * fig.dpi / 72
    assert 0 < room < 0.5 * em, "precondition: close, apart"
    dm.simple_layout(fig)
    assert left.get_gridspec().wspace is None


_LONG_NAMES = [f"A very long category name, number {i}" for i in range(4)]


def _wide_names_on_the_right(names=_LONG_NAMES, **adjust):
    dm.style.use("scientific")
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("6cm", "standard")
    )
    if adjust:
        fig.subplots_adjust(**adjust)
    left.plot([0, 1], [0, 1])
    right.barh(names, [1, 2, 3, 4])
    return fig, left


@pytest.mark.parametrize(
    "names",
    [
        [f"Category name {i}" for i in range(4)],  # needs about 2 cells
        _LONG_NAMES,  # needs more than the whole grid
    ],
)
def test_panels_that_one_and_a_half_cells_cannot_part_stay(names) -> None:
    """Narrower panels would not clear the names, so the spacing stays.

    (The names reach into the left panel's plot area, which
    ``CROSS_AXES_OVERLAP`` does not read yet; text over text it reports.)
    """
    fig, left = _wide_names_on_the_right(names)
    dm.simple_layout(fig)
    assert left.get_gridspec().wspace is None


def test_panel_spacing_never_narrows() -> None:
    fig, left = _wide_names_on_the_right(wspace=2.0)
    dm.simple_layout(fig)
    assert left.get_gridspec().wspace is None
    assert fig.subplotpars.wspace == 2.0


def test_spaced_numbers_turn_rather_than_break() -> None:
    labels = [
        f"{n:,}".replace(",", " ")
        for n in range(1_250_000, 11_000_000, 1_250_000)
    ]
    fig, ax = _bars(labels)
    dm.simple_layout(fig, fit_labels=False)
    assert _overlaps(fig) == 1
    dm.simple_layout(fig)
    assert not any("\n" in t for t in _texts(ax))
    assert _angles(ax) == {30.0}


def test_names_that_fit_or_that_you_broke_stay() -> None:
    dm.style.use("presentation")
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("12cm", "standard")
    )
    for ax in (left, right):
        ax.plot([0, 1], [0, 1])
        ax.set_ylabel("Load (kW)")
    right.set_xlabel("Time (s)")
    broken = "Heat\nper connected building over the whole season (MWh)"
    math = r"$E_{\mathrm{heat}}$ per connected building over the season (MWh)"
    left.set_xlabel(broken)
    left.set_title(" ")
    dm.simple_layout(fig)
    assert right.get_xlabel() == "Time (s)"
    assert right.get_ylabel() == "Load (kW)"
    assert left.get_xlabel() == broken
    left.set_xlabel(math)
    dm.simple_layout(fig)
    assert left.get_xlabel() == math


def test_a_settled_figure_ends_in_one_confirming_round(monkeypatch) -> None:
    """Cost guard: once the labels clear, one more round finds nothing.

    (A rung that re-applied the angle it already set would spend every
    remaining round on a fresh margin fit without changing the figure.)
    """
    import dartwork_mpl.layout._fit_labels as fit

    rounds = []
    real = fit.fit_round

    def counted(*args):
        rounds.append(real(*args))
        return rounds[-1]

    monkeypatch.setattr(fit, "fit_round", counted)
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig)
    assert _angles(ax) == {30.0}
    # found, then made again after the figure is measured; then nothing left
    assert [[c.key[0] for c in r] for r in rounds] == [
        ["rotate"],
        ["rotate"],
        [],
    ]


def test_a_name_or_spacing_you_change_after_a_layout_stays() -> None:
    dm.style.use("presentation")
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("12cm", "standard")
    )
    for ax in (left, right):
        ax.plot([0, 1], [0, 1])
    left.set_xlabel("Cumulative delivered heat per building (MWh)")
    dm.simple_layout(fig)
    assert "\n" in left.get_xlabel()
    left.set_xlabel("Heat (MWh)")
    dm.simple_layout(fig, fit_labels=False)
    assert left.get_xlabel() == "Heat (MWh)"

    dm.style.use("scientific")
    fig, axs = plt.subplots(2, 1, figsize=dm.figsize("9cm", "tall"))
    for ax in axs:
        ax.plot([0, 1], [0, 1])
        ax.set_title("Panel")
        ax.set_xlabel("Time (h)")
    dm.simple_layout(fig)
    gs = axs[0].get_gridspec()
    assert gs.hspace is not None
    gs.update(hspace=0.9)
    dm.simple_layout(fig, fit_labels=False)
    assert gs.hspace == 0.9


def test_upright_only_when_it_leaves_less_overlap() -> None:
    labels = [f"Variant {c}" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123"]
    fig, ax = _bars(labels, preset="scientific")
    dm.simple_layout(fig)
    assert _angles(ax) == {90.0}  # nothing clears; upright overlaps least

    # Two short numbers on an axis squeezed to nothing by long row names:
    # upright they would overlap more than flat, so they stay flat.
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    names = [f"District heating network, branch {i}" for i in range(30)]
    ax.barh(names, np.arange(30.0) * 2)
    dm.simple_layout(fig)
    assert _angles(ax) == {0.0}


def test_a_name_whose_lines_would_crush_the_plot_stays() -> None:
    """Four presentation lines under a 9 cm plot would take half its height."""
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot(np.arange(10), np.arange(10) ** 1.5)
    name = "Average weekly portfolio return relative to the market baseline (%)"
    ax.set_xlabel(name)
    ax.set_ylabel("Energy (MWh)")
    dm.simple_layout(fig)
    assert ax.get_xlabel() == name
    assert ax.get_window_extent().height > 0.5 * fig.bbox.height


# ── a rung keeps a change only if it harmed nothing (review of #645) ──


def _template_figure(name: str, preset: str, width: str | None):
    """A shipped template drawn up to its layout, at another preset and
    size (``None``: its own)."""
    from pathlib import Path

    source = (
        Path(dm.__file__).parent / "asset/prompt/05-templates" / name
    ).read_text(encoding="utf-8")
    source = source[: source.index("dm.simple_layout(fig")]
    source = source.replace(
        'dm.style.use("scientific")', f'dm.style.use("{preset}")'
    )
    namespace: dict = {}
    exec(compile(source, name, "exec"), namespace)
    fig = namespace["fig"]
    if width is not None:
        fig.set_size_inches(dm.figsize(width, "standard"))
    return fig, namespace["ax"]


def _warned_axes(fig) -> set[str]:
    fig.canvas.draw()
    return {
        w.detail["axis"] for w in check_tick_overlap(fig, get_renderer(fig))
    }


def test_a_turn_that_would_crush_the_plot_is_taken_back() -> None:
    """advanced/boxplot in presentation at 9 cm: turned 45 degrees, the
    names, the y name and the means above the box left the data area 5 px
    tall and its y ticks overlapping. The turn is taken back and the figure
    draws exactly as without fitting (the margins are fitted afresh: each
    take-back's fit stopped 0.02-0.3 px from where the last one had), its x
    labels reported. The harmful turn is tried twice (in its round, then
    alone) and not again."""
    import dartwork_mpl.layout._fit_labels as fit_module

    real = fit_module.fit_round
    rounds: list[list[str]] = []

    def recorded(*args):
        changes = real(*args)
        rounds.append([c.key[0] for c in changes])
        return changes

    draws, warned = [], []
    for fit in (False, True):
        fig, ax = _template_figure("advanced/boxplot.py", "presentation", "9cm")
        fit_module.fit_round = recorded
        try:
            dm.simple_layout(fig, margin=dm.inch(0.08), fit_labels=fit)
        finally:
            fit_module.fit_round = real
        draws.append(_pixels(fig))
        warned.append(_warned_axes(fig))
        assert _angles(ax) == {0.0}
    assert draws[1] == draws[0]
    assert warned == [{"x"}, {"x"}]
    # its round (found, made again after measuring), then alone (the same),
    # then nothing left to try
    assert rounds == [["rotate"]] * 4 + [[]]


def test_a_name_in_nobodys_way_draws_as_without_the_ladder() -> None:
    """Longer than its plot, beside a panel, but clear of it and of the
    figure edge: nothing to fit."""

    def render(fit: bool) -> bytes:
        dm.style.use("scientific")
        fig, axs = plt.subplots(
            1,
            2,
            figsize=dm.figsize("17cm", "standard"),
            gridspec_kw={"wspace": 1.4},
        )
        for ax in axs:
            ax.plot([0, 1], [0, 1])
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
        axs[0].set_xlabel("Cumulative delivered heat per building (MWh)")
        dm.simple_layout(fig, fit_labels=fit)
        return _pixels(fig)

    assert render(True) == render(False)


def test_top_labels_you_turned_stay_through_the_ladder_and_its_undo() -> None:
    fig, ax = _bars(_ONE_WORD)
    ax.tick_params(top=True, labeltop=True)
    for tick in ax.xaxis.get_major_ticks():
        tick.label2.set_rotation(60)
    dm.simple_layout(fig)
    ticks = ax.xaxis.get_major_ticks()
    assert {t.label2.get_rotation() for t in ticks} == {60.0}
    assert {t.label1.get_rotation() for t in ticks} == {30.0}

    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig)
    for tick in ax.xaxis.get_major_ticks():
        tick.label2.set_rotation(60)
    restore_fitted(fig)
    ticks = ax.xaxis.get_major_ticks()
    assert {t.label2.get_rotation() for t in ticks} == {60.0}
    assert {t.label1.get_rotation() for t in ticks} == {0.0}


def test_the_undo_keeps_one_bottom_label_you_turned_after_a_layout() -> None:
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig)
    first, *rest = ax.xaxis.get_major_ticks()
    first.label1.set_rotation(60)
    restore_fitted(fig)
    assert first.label1.get_rotation() == 60.0
    assert {t.label1.get_rotation() for t in rest} == {0.0}
    assert {t.label1.get_rotation_mode() for t in rest} == {"default"}


def test_spacing_you_set_on_the_figure_stays() -> None:
    dm.style.use("scientific")
    fig, axs = plt.subplots(2, 1, figsize=dm.figsize("9cm", "tall"))
    for ax in axs:
        ax.plot([0, 1], [0, 1])
        ax.set_title("Panel")
        ax.set_xlabel("Time (h)")
    fig.subplots_adjust(hspace=0.05)
    dm.simple_layout(fig)
    gs = axs[0].get_gridspec()
    assert gs.hspace is None
    assert gs.get_subplot_params(fig).hspace == 0.05


def _two_grids():
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("17cm", "standard"))
    a = fig.add_gridspec(1, 1, left=0.05, right=0.4)
    b = fig.add_gridspec(1, 1, left=0.6, right=0.95)
    left, right = fig.add_subplot(a[0]), fig.add_subplot(b[0])
    left.plot([0, 1], [0, 1])
    right.bar(range(8), np.arange(8) + 1.0)
    right.set_xticks(range(8), _ONE_WORD)
    return fig, a, right


def test_a_layout_of_one_grid_fits_and_restores_only_that_grid() -> None:
    fig, a, right = _two_grids()
    before = _label_state(right)
    dm.simple_layout(fig, gs=a, use_all_axes=False)
    assert _label_state(right) == before

    fig, a, right = _two_grids()
    dm.simple_layout(fig)  # every Axes: the right one turns
    turned = _label_state(right)
    assert {state[1] for state in turned} == {45.0}
    dm.simple_layout(fig, gs=a, use_all_axes=False, fit_labels=False)
    assert _label_state(right) == turned


@pytest.mark.parametrize("value", [("wrap", 1), b"wrap", 3, ("wrap", None)])
def test_steps_that_are_not_strings_raise_type_error(value) -> None:
    with pytest.raises(TypeError, match="fit_labels"):
        resolve_steps(value)
    fig, ax = _bars(_VARIANTS)
    before = _pixels(fig)
    with pytest.raises(TypeError, match="fit_labels"):
        dm.simple_layout(fig, fit_labels=value)
    with dm.config.override(fit_labels=value):
        with pytest.raises(TypeError, match="fit_labels"):
            dm.simple_layout(fig)
    assert _pixels(fig) == before


def test_an_unknown_step_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown step"):
        resolve_steps(("wrap", "shrink"))
    with pytest.raises(ValueError, match="unknown step"):
        resolve_steps("shrink")


def test_a_round_harms_when_a_plot_side_falls_below_the_share() -> None:
    """The verdict on a round: a plot side kept below ``_MIN_PLOT_SHARE``
    (0.3; kept rounds measured 0.39 or more, the crushing one 0.01-0.22) or
    an axis with more overlapping tick labels than before."""
    from dartwork_mpl.layout._fit_labels import _harmed, _Health

    before = _Health({1: (400.0, 400.0)}, {(1, "x"): 3, (1, "y"): 0})

    def after(w: float, h: float, x: int = 3, y: int = 0) -> _Health:
        return _Health({1: (w, h)}, {(1, "x"): x, (1, "y"): y})

    assert not _harmed(before, after(400, 160))  # kept 0.4
    assert _harmed(before, after(400, 100))  # kept 0.25
    assert _harmed(before, after(100, 400))
    assert not _harmed(before, after(400, 400, x=0))  # fewer overlaps
    assert _harmed(before, after(400, 400, y=1))  # a new one elsewhere
    assert _harmed(before, after(400, 400, x=4))  # more on its own axis


def _shared_panels(width: str):
    """Two panels sharing x (one formatter), the left one half as wide."""
    dm.style.use("scientific")
    fig, (narrow, wide) = plt.subplots(
        1,
        2,
        figsize=dm.figsize(width, "standard"),
        sharex=True,
        gridspec_kw={"width_ratios": [1, 2]},
    )
    for ax in (narrow, wide):
        ax.bar(range(6), np.arange(6) + 1.0)
    wide.set_xticks(
        range(6),
        ["Low fee", "High fee", "No fee", "Mid fee", "Top fee", "Old fee"],
    )
    return fig, narrow, wide


@pytest.mark.parametrize(
    ("width", "rungs"), [("17cm", ["wrap"]), ("12cm", ["rotate"])]
)
def test_panels_sharing_x_wrap_together(width, rungs, monkeypatch) -> None:
    """The narrow panel's labels set the shared wraps; the wide panel no
    longer takes them off again round after round (review of #645)."""
    import dartwork_mpl.layout._fit_labels as fit

    real = fit.fit_round
    fig, narrow, wide = _shared_panels(width)
    dm.simple_layout(fig, fit_labels=False)
    assert _overlaps(fig) == 1  # the narrow panel's labels collide
    calls = []

    def recorded(*args):
        changes = real(*args)
        calls.append([c.key[0] for c in changes])
        return changes

    monkeypatch.setattr(fit, "fit_round", recorded)
    dm.simple_layout(fig)
    assert _overlaps(fig) == 0
    assert calls == [rungs, rungs, []]  # found, made after measuring, done
    texts = _texts(narrow)
    if rungs == ["wrap"]:
        assert texts[0] == "Low\nfee" and _texts(wide) == texts
        assert _angles(narrow) == _angles(wide) == {0.0}
    else:
        assert texts[0] == "Low fee" and _angles(narrow) == {45.0}
        assert _angles(wide) == {0.0}


def test_a_shared_axis_with_labels_you_turned_does_not_wrap() -> None:
    """Wrapping is the shared formatter's, so it would rewrite the labels you
    turned on the wide panel: the narrow one turns its own instead."""
    fig, narrow, wide = _shared_panels("17cm")
    for label in wide.get_xticklabels():
        label.set_rotation(20)
    dm.simple_layout(fig)
    assert not any("\n" in t for t in _texts(narrow) + _texts(wide))
    assert _angles(wide) == {20.0}
    assert _angles(narrow) == {30.0}


def test_a_name_that_collapsed_the_plot_wraps_however_wide_its_lines() -> None:
    """Longer than a 6 cm presentation figure is tall, the y name squeezed
    the plot to a pixel. Its four lines take most of the figure's width,
    yet the plot comes back, so they are kept."""
    for fit in (False, True):
        dm.style.use("presentation")
        fig, ax = plt.subplots(figsize=dm.figsize("6cm", "tall"))
        ax.plot(np.arange(10), np.arange(10) ** 1.5)
        ax.set_ylabel(
            "Cumulative delivered heat energy per connected building (MWh)"
        )
        dm.simple_layout(fig, fit_labels=fit)
        height = ax.get_window_extent().height
        if fit:
            assert ax.get_ylabel().count("\n") == 3
            assert height > 0.5 * fig.bbox.height
        else:
            assert height < 2  # collapsed


def test_a_plot_the_ladder_made_taller_takes_the_ticks_of_its_height() -> None:
    """The y axis of the plot the y name had crushed had room for one
    interval; back at its height it takes matplotlib's ticks for that,
    not the one interval it had before the ladder."""
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "tall"))
    ax.plot(np.arange(10), np.arange(10) ** 1.5)
    ax.set_ylabel(
        "Cumulative delivered heat energy per connected building (MWh)"
    )
    auto = ax.yaxis.get_major_locator()
    dm.simple_layout(fig)
    assert ax.yaxis.get_major_locator() is auto
    assert _visible_ticks(ax.yaxis) == ["0", "10", "20"]


# ── what a scoped layout shares with Axes it leaves out (review N1) ──


def _shared_grids(width: str, n: int, split: float = 0.45, gap: float = 0.15):
    """Two independent grids; the right Axes shares x (one formatter) with
    the left one."""
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize(width, "standard"))
    a = fig.add_gridspec(1, 1, left=0.05, right=split)
    b = fig.add_gridspec(1, 1, left=split + gap, right=0.95)
    left = fig.add_subplot(a[0])
    right = fig.add_subplot(b[0], sharex=left)
    for ax in (left, right):
        ax.bar(range(n), range(n))
    left.set_xticks(range(n), ["Low fee"] * n)
    return fig, a, left, right


def _tick_state(ax) -> list[tuple[str, float]]:
    ax.get_figure().canvas.draw()
    return [(t.get_text(), t.get_rotation()) for t in ax.get_xticklabels()]


def test_scoped_wrap_preserves_excluded_shared_labels() -> None:
    """A layout of the left grid cannot wrap through the formatter the left
    Axes shares with the right one, which it leaves out; the left Axes turns
    its own labels instead."""
    fig, a, left, right = _shared_grids("9cm", 10)
    before = _tick_state(right)
    dm.simple_layout(fig, gs=a, use_all_axes=False)
    assert _tick_state(right) == before
    assert _texts(left) == ["Low fee"] * 10
    assert _angles(left) == {30.0}


def test_scoped_restore_preserves_excluded_shared_labels() -> None:
    """Wraps a layout of every Axes put on the shared formatter stay when one
    grid alone is laid out again with ``fit_labels=False``."""
    fig, a, left, right = _shared_grids("12cm", 6)
    dm.simple_layout(fig)
    before = _tick_state(right)
    assert all("\n" in text for text, _angle in before)  # precondition
    dm.simple_layout(fig, gs=a, use_all_axes=False, fit_labels=False)
    assert _tick_state(right) == before
    dm.simple_layout(fig, fit_labels=False)  # every Axes: the wraps come off
    assert _texts(right) == ["Low fee"] * 6


def test_a_scoped_layout_leaves_shared_wraps_a_whole_layout_set() -> None:
    """A narrow panel in a nested grid shares x with a wide panel beside it.
    Laid out alone, it would turn its labels and take the shared wraps off
    the wide panel, which the layout of every Axes set and the call leaves
    out; so it leaves them, and its own labels stay wrapped too."""
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("12cm", "standard"))
    root = fig.add_gridspec(1, 2, width_ratios=[1, 3])
    inner = root[0].subgridspec(1, 1)
    narrow = fig.add_subplot(inner[0])
    wide = fig.add_subplot(root[1], sharex=narrow)
    for ax in (narrow, wide):
        ax.bar(range(4), range(4))
    narrow.set_xticks(range(4), ["Low fee"] * 4)
    dm.simple_layout(fig)
    before = (_tick_state(narrow), _tick_state(wide))
    assert all("\n" in text for text, _angle in before[1])  # precondition
    dm.simple_layout(fig, gs=inner, use_all_axes=False)
    assert (_tick_state(narrow), _tick_state(wide)) == before


def _grid_with_a_nested_cell():
    """A root grid of three cells, the last holding a nested grid."""
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("17cm", "standard"))
    root = fig.add_gridspec(1, 3)
    first, second = fig.add_subplot(root[0]), fig.add_subplot(root[1])
    inner = root[2].subgridspec(2, 1)
    nested = [fig.add_subplot(inner[0]), fig.add_subplot(inner[1])]
    for ax in (first, second, *nested):
        ax.plot([0, 1], [0, 1])
    second.barh([f"Category name {i}" for i in range(4)], [1, 2, 3, 4])
    return fig, root


def test_a_scoped_layout_does_not_grow_the_spacing_of_a_grid_it_shares() -> (
    None
):
    """The root grid's spacing also moves the nested Axes that a layout of
    the root grid alone leaves out, so that layout does not grow it."""
    fig, root = _grid_with_a_nested_cell()
    dm.simple_layout(fig, gs=root, use_all_axes=False)
    assert root.wspace is None
    dm.simple_layout(fig)  # every Axes: the colliding panels part
    assert root.wspace is not None


def test_a_scoped_restore_keeps_the_spacing_of_a_grid_it_shares() -> None:
    fig, root = _grid_with_a_nested_cell()
    dm.simple_layout(fig)
    grown = root.wspace
    assert grown is not None  # precondition: the panels collide
    dm.simple_layout(fig, gs=root, use_all_axes=False, fit_labels=False)
    assert root.wspace == grown


# ── an axis a rung shortened keeps the ticks it had (O1 follow-up) ──


def _visible_ticks(axis) -> list[str]:
    axis.axes.get_figure().canvas.draw()
    lo, hi = sorted(axis.get_view_interval())
    return [
        t.label1.get_text()
        for t in axis.get_major_ticks()
        if lo <= t.get_loc() <= hi
    ]


def _boxplot(fit: bool | None):
    fig, ax = _template_figure("advanced/boxplot.py", "presentation", None)
    if fit is not None:
        dm.simple_layout(fig, margin=dm.inch(0.08), fit_labels=fit)
    return fig, ax


def test_a_plot_a_turn_made_shorter_keeps_its_y_ticks() -> None:
    """advanced/boxplot in presentation: the names turn 30 degrees and the
    plot loses a sixth of its height. Matplotlib would then give the y axis
    room for one interval fewer and draw only 0 and 5; it keeps the ticks
    drawn without fitting, whose labels stay well apart."""
    ticks = []
    for fit in (False, True):
        fig, ax = _boxplot(fit)
        ticks.append(_visible_ticks(ax.yaxis))
    assert _angles(ax) == {30.0}
    assert ticks[1] == ticks[0]
    assert len(ticks[0]) >= 5


def _preset_grid():
    """The docs' preset comparison: four presets' text on a 2 x 2 grid,
    whose panels the ladder parts."""
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize("16cm", "standard"))
    x = np.linspace(0, 10, 100)
    presets = ["scientific", "report", "presentation", "minimal"]
    for ax, preset in zip(axes.flat, presets, strict=True):
        with dm.style.context(preset):
            ax.plot(x, np.sin(x), label="Signal A")
            ax.plot(x, np.cos(x) * 0.8, label="Signal B")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Amplitude")
            ax.legend(loc="upper right", fontsize=dm.fs(-2))
            ax.text(
                0.02,
                0.97,
                f"'{preset}'",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=dm.fs(1),
                fontweight="bold",
            )
    return fig, axes


def test_panels_the_spacing_narrowed_keep_their_x_ticks() -> None:
    """Parted, the panels are a few pixels narrower; matplotlib would pick
    0.0 2.5 ... 10.0 for their x axes instead of the integers they had."""
    ticks = []
    for fit in (False, True):
        fig, axes = _preset_grid()
        dm.simple_layout(fig, fit_labels=fit)
        ticks.append([_visible_ticks(ax.xaxis) for ax in axes.flat])
    assert axes[0, 0].get_gridspec().wspace is not None  # parted
    assert ticks[1] == ticks[0]
    assert ticks[0][0] == ["0", "2", "4", "6", "8", "10"]


def test_ticks_you_set_stay_through_the_ladder() -> None:
    from matplotlib.ticker import AutoLocator, MaxNLocator

    for locator in (MaxNLocator(3), AutoLocator()):
        fig, ax = _boxplot(None)
        ax.yaxis.set_major_locator(locator)
        dm.simple_layout(fig, margin=dm.inch(0.08))
        assert _angles(ax) == {30.0}
        assert ax.yaxis.get_major_locator() is locator


def test_fit_labels_false_gives_the_auto_locator_back() -> None:
    fig, ax = _boxplot(None)
    auto = ax.yaxis.get_major_locator()
    dm.simple_layout(fig, margin=dm.inch(0.08))
    assert ax.yaxis.get_major_locator() is not auto  # precondition: kept
    dm.simple_layout(fig, margin=dm.inch(0.08), fit_labels=False)
    assert ax.yaxis.get_major_locator() is auto
    assert ax.yaxis.isDefault_majloc
    ref, _ref_ax = _boxplot(False)
    assert _pixels(fig) == _pixels(ref)


@pytest.mark.filterwarnings("ignore:dm.label_bars:UserWarning")
def test_margins_that_do_not_settle_are_not_fitted() -> None:
    """advanced/bar_grouped in presentation, with longer phase names: its
    legend is wider than the canvas leaves the plot, so every margin fit
    moves the plot (33 px a step). Turned upright, its names would be
    judged on a plot still moving, and each fit after a round would move
    it on until it was a pixel wide; the figure is not fitted and draws as
    without the ladder."""
    draws = []
    for fit in (False, True):
        fig, ax = _template_figure(
            "advanced/bar_grouped.py", "presentation", None
        )
        ax.set_xticks(
            ax.get_xticks(),
            [
                "Phase 1 design",
                "Phase 2 build",
                "Phase 3 test",
                "Phase 4 launch",
            ],
        )
        dm.simple_layout(fig, margin=dm.inch(0.08), fit_labels=fit)
        draws.append(_pixels(fig))
        assert ax.get_window_extent().width > 0.3 * fig.bbox.width
    assert _angles(ax) == {0.0}
    assert draws[1] == draws[0]


def _bars_sharing_y(n: int):
    """Bars with long one-word names in a nested grid, a line beside them
    sharing their y axis (one locator)."""
    dm.style.use("presentation")
    fig = plt.figure(figsize=dm.figsize("14.5cm", "standard"))
    root = fig.add_gridspec(1, 2)
    inner = root[0].subgridspec(1, 1)
    bars = fig.add_subplot(inner[0])
    line = fig.add_subplot(root[1], sharey=bars)
    bars.bar(range(n), np.linspace(1, 9, n))
    bars.set_xticks(range(n), _ONE_WORD[:n])
    line.plot([0, 1], [0, 9])
    return fig, inner, bars, line


def test_a_shared_locator_keeps_its_budget_only_with_every_sharer() -> None:
    """Turned upright, the names make the bars' plot shorter. A layout of
    every Axes keeps the shared y ticks; a layout of the bars' grid alone
    does not change the locator the line, left out, shares."""
    fig, _inner, bars, line = _bars_sharing_y(4)
    dm.simple_layout(fig, fit_labels=False)
    unfitted = _visible_ticks(bars.yaxis)

    fig, _inner, bars, line = _bars_sharing_y(4)
    auto = bars.yaxis.get_major_locator()
    dm.simple_layout(fig)
    assert _angles(bars) == {90.0}
    assert bars.yaxis.get_major_locator() is not auto
    assert _visible_ticks(bars.yaxis) == unfitted == ["0", "2", "4", "6", "8"]

    fig, inner, bars, line = _bars_sharing_y(4)
    auto = bars.yaxis.get_major_locator()
    dm.simple_layout(fig, gs=inner, use_all_axes=False)
    assert _angles(bars) == {90.0}
    assert bars.yaxis.get_major_locator() is auto
    assert line.yaxis.get_major_locator() is auto
    assert _visible_ticks(bars.yaxis) != unfitted  # what was not kept


def test_ticks_that_would_crowd_the_shorter_axis_are_matplotlibs() -> None:
    """Turned upright, eight names leave the plot 37 % of its height: the
    five ticks it had would sit 11 px apart (half an em is 38 px), so the
    axis takes matplotlib's ticks for its new length."""
    ticks = []
    for fit in (False, True):
        fig, ax = _bars(_ONE_WORD, width="12cm", preset="presentation")
        auto = ax.yaxis.get_major_locator()
        dm.simple_layout(fig, fit_labels=fit)
        ticks.append(_visible_ticks(ax.yaxis))
    assert _angles(ax) == {90.0}
    assert ax.yaxis.get_major_locator() is auto
    assert ticks == [["0", "2", "4", "6", "8"], ["0", "5"]]


def test_a_locator_you_set_after_a_layout_stays() -> None:
    from matplotlib.ticker import MaxNLocator

    fig, ax = _boxplot(None)
    dm.simple_layout(fig, margin=dm.inch(0.08))
    mine = MaxNLocator(4)
    ax.yaxis.set_major_locator(mine)
    restore_fitted(fig)
    assert ax.yaxis.get_major_locator() is mine


def test_a_figure_pyplot_does_not_manage_starts_where_it_did() -> None:
    """``GridSpec.update`` moves only the Axes of pyplot's open figures;
    the undo moves the others itself."""
    fig, ax = _bars(_ONE_WORD)
    gs = ax.get_gridspec()
    dm.simple_layout(fig)
    plt.close(fig)
    restore_fitted(fig)
    assert ax.get_position().bounds == pytest.approx(
        gs[0].get_position(fig).bounds
    )


def test_a_scoped_restore_keeps_a_shared_budget_a_whole_layout_set() -> None:
    fig, inner, bars, line = _bars_sharing_y(4)
    dm.simple_layout(fig)
    kept = bars.yaxis.get_major_locator()
    dm.simple_layout(fig, gs=inner, use_all_axes=False, fit_labels=False)
    assert line.yaxis.get_major_locator() is kept
    dm.simple_layout(fig, fit_labels=False)  # every Axes: it comes off
    assert line.yaxis.get_major_locator() is not kept
    assert line.yaxis.isDefault_majloc


def test_no_tick_budget_round_where_the_ticks_stay_the_same() -> None:
    """Turned, the names leave the value axis room for fewer intervals,
    but matplotlib picks the same ticks for 0-100 either way: nothing to
    keep, so no round for it."""
    import dartwork_mpl.layout._fit_labels as fit_module

    real = fit_module.fit_round
    rounds: list[list[str]] = []

    def recorded(*args):
        changes = real(*args)
        rounds.append([c.key[0] for c in changes])
        return changes

    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    ax.bar(range(8), np.linspace(10, 95, 8))
    ax.set_xticks(range(8), _ONE_WORD)
    auto = ax.yaxis.get_major_locator()
    fit_module.fit_round = recorded
    try:
        dm.simple_layout(fig)
    finally:
        fit_module.fit_round = real
    assert _angles(ax) != {0.0}
    assert all("ticks" not in keys for keys in rounds)
    assert ax.yaxis.get_major_locator() is auto


def test_a_log_axis_is_left_to_its_own_locator() -> None:
    fig, ax = _bars(_ONE_WORD)
    ax.set_yscale("log")
    locator = ax.yaxis.get_major_locator()
    dm.simple_layout(fig)
    assert _angles(ax) == {30.0}
    assert ax.yaxis.get_major_locator() is locator


def test_an_auto_locator_not_picking_by_length_is_left_alone() -> None:
    """In matplotlib's classic mode ``AutoLocator`` takes nine intervals
    whatever the length; there is no budget to keep."""
    matplotlib.rcParams["_internal.classic_mode"] = True
    fig, ax = _boxplot(None)
    auto = ax.yaxis.get_major_locator()
    dm.simple_layout(fig, margin=dm.inch(0.08))
    assert _angles(ax) == {30.0}
    assert ax.yaxis.get_major_locator() is auto
