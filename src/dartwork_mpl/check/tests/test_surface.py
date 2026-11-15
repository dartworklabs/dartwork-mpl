"""``dm.check`` on real charts: what it finds, and that it changes nothing."""

from __future__ import annotations

import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    return buf.getvalue()


def _line_chart():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    x = np.arange(10)
    ax.plot(x, x**1.2, label="Revenue")
    ax.plot(x, 8 - 0.5 * x, label="Cost")
    ax.set_xlabel("Quarter")
    ax.set_ylabel("Amount (M USD)")
    dm.place_legend(ax)
    dm.simple_layout(fig, margin="1mm")
    return fig, ax


def test_a_laid_out_chart_is_clean_and_unchanged():
    fig, _ax = _line_chart()
    before = _png(fig)
    found = dm.check(fig)
    assert not found, found.report()
    assert _png(fig) == before
    assert str(found) == "dm.check: no defects found."


def test_a_legend_on_the_points_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    rng = np.random.default_rng(0)
    ax.scatter(rng.uniform(0, 1, 400), rng.uniform(0, 1, 400), label="Samples")
    ax.legend(loc="center")
    found = dm.check(fig).of("LEGEND_ON_DATA")
    assert found and "markers ('Samples')" in found[0].message
    assert found[0].artists == (ax.get_legend(),)


def test_text_past_the_edge_and_overlapping_text():
    fig, ax = _line_chart()
    long = ax.text(9, 5, "a note running far past the right edge")
    ax.text(2, 4, "Peak demand")
    ax.text(2.3, 4, "Peak supply")
    found = dm.check(fig)
    assert long in found.of("OVERFLOW")[0].artists
    assert "'Peak demand'" in found.of("OVERLAP")[0].message


def test_a_tight_grid_collides_across_panels():
    fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", "9cm"))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("Hour of day")
    fig.subplots_adjust(hspace=0)
    axes[1].set_title("Zone temperature", y=0.9)  # down onto the ticks above
    assert dm.check(fig).of("CROSS_AXES_OVERLAP")


def test_value_labels_on_their_line_but_not_on_their_bars():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    x = np.arange(6)
    y = np.array([3, 5, 4, 6, 5, 7])
    ax.plot(x, y, linewidth=3)
    for xi, yi in zip(x, y, strict=True):
        ax.text(xi, yi, f"{yi}", ha="center", va="center")
    assert dm.check(fig).of("VALUE_LABEL_ON_DATA")

    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(["A", "B", "C"], [120, 135, 90])
    dm.label_bars(ax)
    dm.simple_layout(fig)
    found = dm.check(fig)
    assert not found.of("VALUE_LABEL_ON_DATA")
    assert not found.of("VALUE_LABEL_DECIMAL")


def test_faint_text_and_trailing_zero_ticks():
    fig, ax = _line_chart()
    ax.text(1, 6, "draft", color="#eeeeee")
    ax.set_yticks([0, 2, 4, 6, 8], labels=["0.0", "2.0", "4.0", "6.0", "8.0"])
    found = dm.check(fig)
    assert "'draft'" in found.of("TEXT_CONTRAST")[0].message
    assert "whole number" in found.of("TICK_DECIMAL")[0].message


def test_an_empty_slot_of_a_grid():
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("12cm", "wide"))
    axes[0].plot([0, 1], [0, 1])
    found = dm.check(fig).of("EMPTY_AXES")
    assert [f.panels for f in found] == [(1,)]


def test_corner_tick_labels_meet():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    ax.plot([-3, 3], [-3, 3])
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.tick_params(axis="x", pad=0)
    ax.tick_params(axis="y", pad=0)
    assert dm.check(fig).of("TICK_CORNER_OVERLAP")


def test_the_default_margin_clears_the_edge_and_crowding_is_caught():
    """Text no longer sits on the canvas edge; a value against a name is reported."""
    from tests.visual.scenarios import all_scenarios

    built = {s.name: s for s in all_scenarios()}
    ends = dm.check(built["line_ends_annotated"].build())
    assert "'19.4 TWh'" in ends.of("TEXT_CROWD")[0].message
    for name in (
        "line_ends_annotated",
        "panel_grid_figure_legend",
        "kr_myriad_dates",
    ):
        assert not dm.check(built[name].build()).of("TEXT_AT_EDGE")


def test_a_zero_margin_puts_text_on_the_edge():
    """TEXT_AT_EDGE: asking for margin=0 leaves the outer text flush with the canvas."""
    from tests.visual.scenarios import all_scenarios

    built = {s.name: s for s in all_scenarios()}
    fig = built["kr_myriad_dates"].build()
    dm.simple_layout(fig, margin=0)
    assert "'방문객 수'" in dm.check(fig).of("TEXT_AT_EDGE")[0].message
