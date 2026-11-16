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
    assert str(found) == "dm.check: no defects found."


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


def test_a_value_against_a_line_end_name_is_crowded():
    from tests.visual.scenarios import all_scenarios

    built = {s.name: s for s in all_scenarios()}
    ends = dm.check(built["line_ends_annotated"].build())
    assert "'19.4 TWh'" in _of(ends, "TEXT_CROWD")[0].message
