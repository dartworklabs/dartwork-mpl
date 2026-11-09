"""TICK_CORNER_OVERLAP: an x tick label on a y tick label at a corner.

No other check sees the pair: ``TICK_OVERLAP`` compares neighbours along
one axis, ``CROSS_AXES_OVERLAP`` other plots. The oracle is the labels'
own boxes, measured in the test, and the fix it suggests, applied.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels, get_renderer


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _square(limit: float = 3.0):
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    x = np.linspace(-3, 3, 50)
    ax.plot(x, 3 * np.sin(x))
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    return fig, ax


def _corner(fig):
    return [
        w
        for w in dm.validate_figure(fig, quiet=True)
        if w.check_id == "TICK_CORNER_OVERLAP"
    ]


def _one(fig):
    found = _corner(fig)
    assert len(found) == 1, [w.check_id for w in found]
    return found[0]


def _worst(fig, ax) -> float:
    fig.canvas.draw()
    renderer = get_renderer(fig)
    boxes = {
        which: [
            t.get_window_extent(renderer)
            for t in drawn_tick_labels(ax, which)
            if t.get_text().strip()
        ]
        for which in ("x", "y")
    }
    return max(
        min(
            min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)
        )
        for a in boxes["x"]
        for b in boxes["y"]
    )


def test_the_corner_pair_is_reported() -> None:
    fig, ax = _square()
    assert _worst(fig, ax) > 0.5  # precondition: they collide
    warning = _one(fig)
    assert str(warning.severity.value) == "WARNING"
    assert warning.detail["corner"] == "lower left"
    minus_three = chr(0x2212) + "3"  # matplotlib's minus sign
    assert warning.detail["x_label"] == warning.detail["y_label"] == minus_three
    assert warning.detail["pairs"] == 1
    assert warning.detail["px"] == pytest.approx(_worst(fig, ax), abs=0.2)
    assert "lower left" in warning.message


def test_labels_that_clear_are_not_reported() -> None:
    fig, ax = _square(limit=3.2)
    assert _worst(fig, ax) <= 0.5
    assert _corner(fig) == []


def test_the_suggested_pad_clears_the_pair() -> None:
    """The fix names the axis that moves less and the pad that clears."""
    from dartwork_mpl.validate.fixes import get_fix_suggestions

    fig, ax = _square()
    warning = _one(fig)
    text = "\n".join(get_fix_suggestions(warning))
    assert "dm.simple_layout(fig)" in text
    axis, pad = warning.detail["axis"], warning.detail["pad"]
    assert f"ax.tick_params(axis={axis!r}, pad={pad:g})" in text
    ax.tick_params(axis=axis, pad=pad)
    fig.canvas.draw()
    assert _worst(fig, ax) <= 0.5
    assert _corner(fig) == []


def test_after_the_layout_nothing_is_left() -> None:
    fig, _ax = _square()
    dm.simple_layout(fig)
    assert _corner(fig) == []


def test_a_polar_plot_has_no_corner() -> None:
    dm.style.use("report")
    fig = plt.figure(figsize=dm.figsize("9cm", "square"))
    ax = fig.add_subplot(projection="polar")
    ax.plot(np.linspace(0, 6, 20), np.linspace(0, 1, 20))
    fig.canvas.draw()
    assert _corner(fig) == []
