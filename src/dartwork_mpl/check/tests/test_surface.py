"""``dm.check`` on real charts: what it finds, and that it changes nothing."""

from __future__ import annotations

import io

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.check import Finding, Findings


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


def _of(found: Findings, rule: str) -> list[Finding]:
    return [f for f in found if f.rule == rule]


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
    assert str(found) == "dm.check: nothing stands out."


def test_a_legend_on_the_points_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    rng = np.random.default_rng(0)
    ax.scatter(rng.uniform(0, 1, 400), rng.uniform(0, 1, 400), label="Samples")
    ax.legend(loc="center")
    found = _of(dm.check(fig), "LEGEND_ON_DATA")
    assert found and "markers ('Samples')" in found[0].message
    assert found[0].artists == (ax.get_legend(),)


def test_text_past_the_edge_and_overlapping_text():
    fig, ax = _line_chart()
    long = ax.text(9, 5, "a note running far past the right edge")
    ax.text(2, 4, "Peak demand")
    ax.text(2.3, 4, "Peak supply")
    found = dm.check(fig)
    assert long in _of(found, "OVERFLOW")[0].artists
    assert "'Peak demand'" in _of(found, "OVERLAP")[0].message


def test_a_tight_grid_collides_across_panels():
    fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", "9cm"))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("Hour of day")
    fig.subplots_adjust(hspace=0)
    axes[1].set_title("Zone temperature", y=0.9)  # down onto the ticks above
    assert "CROSS_AXES_OVERLAP" in dm.check(fig).rules


def test_a_title_under_its_colorbar_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize_for("matrix"))
    im = ax.imshow(np.arange(36).reshape(6, 6))
    ax.set_title(
        "Stocks and REITs moved together most closely of all six assets (0.72)"
    )
    cbar = fig.colorbar(im, ax=ax)
    dm.simple_layout(fig)
    found = _of(dm.check(fig), "CROSS_AXES_OVERLAP")
    assert found and cbar.ax in found[0].artists


def test_a_value_against_a_line_end_name_is_crowded():
    from tests.visual.scenarios import all_scenarios

    built = {s.name: s for s in all_scenarios()}
    ends = dm.check(built["line_ends_annotated"].build())
    assert "'19.4 TWh'" in _of(ends, "TEXT_CROWD")[0].message


def test_an_empty_grid_cell_is_found_but_not_a_twin():
    fig, axes = plt.subplots(1, 3, figsize=dm.figsize("15cm", "5cm"))
    axes[0].plot([0, 1], [0, 1])
    axes[0].twiny().set_xlabel("Second scale")
    axes[1].set_axis_off()  # hidden on purpose: no frame, no defect
    found = _of(dm.check(fig), "EMPTY_AXES")
    assert [f.panels for f in found] == [(2,)]


def test_an_axis_of_numbers_needs_a_name_but_not_dates_or_a_named_row():
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("15cm", "6cm"))
    days = np.arange("2026-01-01", "2026-03-01", dtype="datetime64[D]")
    for ax in axes:
        ax.plot(days, np.arange(days.size))
    axes[0].set_ylabel("Orders")
    assert "MISSING_AXIS_LABEL" not in dm.check(fig).rules
    axes[0].set_ylabel("")
    found = _of(dm.check(fig), "MISSING_AXIS_LABEL")
    assert [f.panels for f in found] == [(0,), (1,)]


def test_a_value_on_its_error_bar_is_found():
    fig, ax = plt.subplots(figsize=dm.figsize("10cm", "standard"))
    bars = ax.bar(["A", "B"], [3.1, 4.6], yerr=[0.4, 0.7], capsize=4)
    ax.bar_label(bars, fmt="%.1f")
    ax.set_ylabel("Yield (t/ha)")
    assert "VALUE_LABEL_ON_DATA" in dm.check(fig).rules


@pytest.mark.parametrize("image", [False, True])
def test_white_text_on_a_pale_fill_is_found(image: bool):
    fig, ax = plt.subplots(figsize=dm.figsize("10cm", "standard"))
    if image:
        ax.imshow([[0.0, 1.0]], cmap="YlGnBu")
        ax.text(0, 0, "12", ha="center", va="center", color="white")
    else:
        bars = ax.bar(["A", "B"], [4.6, 3.9], color="dc.yellow3")
        ax.bar_label(bars, fmt="%.1f", label_type="center", color="white")
    found = _of(dm.check(fig), "TEXT_CONTRAST")
    assert found and found[0].panels == (0,)
    for t in ax.texts:
        t.set_color("black")
    assert "TEXT_CONTRAST" not in dm.check(fig).rules
