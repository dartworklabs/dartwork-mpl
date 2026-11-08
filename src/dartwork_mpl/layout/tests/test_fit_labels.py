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
    assert _angles(ax) - {0.0}
    assert _overlaps(fig) == 0


def test_labels_that_cannot_wrap_stay_when_turning_is_not_allowed() -> None:
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig, fit_labels=("wrap",))
    assert _angles(ax) == {0.0}
    assert _overlaps(fig) == 1  # left for the author, and reported


def test_labels_too_long_to_turn_stay_and_are_reported() -> None:
    names = [f"Supercalifragilisticexpialidocious{i}" for i in range(12)]
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))
    ax.bar(range(len(names)), np.ones(len(names)))
    ax.set_xticks(range(len(names)), names)
    dm.simple_layout(fig)
    assert _angles(ax) == {0.0}
    assert _overlaps(fig) == 1


def test_a_second_layout_fits_the_same_way() -> None:
    """Same wraps, angles and spacing; positions within the solver's 0.5 px.

    (``simple_layout`` itself moves a re-laid-out figure by less than its
    0.5 px convergence tolerance, without the ladder too, so pixels are not
    compared.)
    """
    for preset, labels in (("scientific", _VARIANTS), ("report", _ONE_WORD)):
        fig, ax = _bars(labels, width="9cm", preset=preset)
        dm.simple_layout(fig)
        first = (_texts(ax), _angles(ax))
        box = ax.get_window_extent()
        dm.simple_layout(fig)
        assert (_texts(ax), _angles(ax)) == first
        assert np.allclose(ax.get_window_extent().bounds, box.bounds, atol=0.5)


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
    """Labels, formatter and spacing come back; positions within 0.5 px.

    (A re-layout starts from the edges the previous one left, so it settles
    within the solver's tolerance of a fresh layout, not on its pixels.)
    """
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
        assert np.allclose(
            ax.get_window_extent().bounds,
            ref_ax.get_window_extent().bounds,
            atol=0.5,
        )


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
    assert _angles(ax) - {0.0}
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
    assert _angles(ax) - {0.0}


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
    import dartwork_mpl.layout._simple_layout as simple

    calls = []
    real = simple.fit_round

    def counted(*args):
        calls.append(real(*args))
        return calls[-1]

    monkeypatch.setattr(simple, "fit_round", counted)
    fig, ax = _bars(_ONE_WORD)
    dm.simple_layout(fig)
    assert _angles(ax) == {30.0}
    assert calls == [True, False]


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
