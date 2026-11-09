"""Bottom tick labels closer than half an em climb the ladder too.

The ladder's wrap and turn keep neighbours ``_TARGET_EM`` (half an em)
apart, but only labels that overlapped started it: ``advanced/bar`` in
``presentation`` drew "Iceland" and "Sweden" 0.38 em apart, which reads
as one name. Now a row closer than half an em wraps or turns the same
way; a row half an em apart or more draws as before. The oracle is the
drawn labels' own boxes, measured here.
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels, get_renderer

COUNTRIES = ["Norway", "Iceland", "Sweden", "China", "Germany"]
STEPS = ["Start", "Gain A", "Loss B", "Gain C", "Loss D", "End"]  # waterfall


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _bars(names, preset: str = "presentation", width: str | None = None):
    """Bars named ``names`` on the canvas ``figsize_for`` gives (or
    ``width``), as the bar templates draw them."""
    dm.style.use(preset)
    size = (
        dm.figsize_for(n_points=len(names), n_series=1)
        if width is None
        else dm.figsize(width, "standard")
    )
    fig, ax = plt.subplots(figsize=size)
    ax.bar(names, np.linspace(40, 90, len(names)))
    ax.set_ylabel("Share of new cars (%)")
    return fig, ax


def _countries():
    """The countries on a 14.5 cm slide: 0.36 em apart, not touching (the
    template drew them 0.38 em apart on its own canvas)."""
    return _bars(COUNTRIES, width="14.5cm")


def _gap_em(fig, ax) -> float:
    """The smallest gap between neighbouring bottom labels, in ems; for
    turned labels the gap across their text direction."""
    fig.canvas.draw()
    renderer = get_renderer(fig)
    labels = [t for t in drawn_tick_labels(ax, "x") if t.get_text().strip()]
    labels.sort(key=lambda t: t.get_window_extent(renderer).x0)
    em = labels[0].get_fontsize() * fig.dpi / 72
    angle = np.radians(labels[0].get_rotation())
    if abs(np.sin(angle)) < 1e-9:
        boxes = [t.get_window_extent(renderer) for t in labels]
        return min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em
    centres = [
        float(t.get_transform().transform(t.get_position())[0]) for t in labels
    ]
    height = labels[0].get_window_extent(renderer).height
    width = max(t.get_window_extent(renderer).width for t in labels)
    # the unturned text height, from the turned box of a known angle
    s, c = abs(np.sin(angle)), abs(np.cos(angle))
    line = (height - width * s) / c if c > 1e-9 else width
    line = min(line, labels[0].get_fontsize() * fig.dpi / 72 * 1.5)
    spacing = min(b - a for a, b in pairwise(sorted(centres)))
    return (spacing * s - line) / em


def _shape(ax) -> tuple[set[float], bool]:
    labels = [t for t in drawn_tick_labels(ax, "x") if t.get_text().strip()]
    return (
        {round(float(t.get_rotation()), 1) for t in labels},
        any("\n" in t.get_text() for t in labels),
    )


def test_single_names_closer_than_half_an_em_turn() -> None:
    """``advanced/bar`` in ``presentation``: five one-word countries 0.38 em
    apart cannot wrap; they turn to the smallest angle that clears."""
    fig, ax = _countries()
    dm.simple_layout(fig, fit_labels=False)
    assert 0 < _gap_em(fig, ax) < 0.5  # precondition: close, no overlap
    dm.simple_layout(fig)
    turns, wrapped = _shape(ax)
    assert turns != {0.0} and not wrapped
    assert _gap_em(fig, ax) >= 0.5


def test_names_with_spaces_closer_than_half_an_em_wrap() -> None:
    """``waterfall`` in ``presentation``: "Gain C" and "Loss D" 0.25 em
    apart wrap at their spaces, flat."""
    fig, ax = _bars(STEPS)
    dm.simple_layout(fig, fit_labels=False)
    assert 0 < _gap_em(fig, ax) < 0.5  # precondition
    dm.simple_layout(fig)
    turns, wrapped = _shape(ax)
    assert turns == {0.0} and wrapped
    assert _gap_em(fig, ax) >= 0.5


def test_labels_half_an_em_apart_draw_as_before() -> None:
    """The same countries in ``report``, over half an em apart: the ladder
    finds nothing, and the figure draws as without it."""

    def drawn(fit_labels) -> bytes:
        with matplotlib.rc_context():
            fig, ax = _bars(COUNTRIES, preset="report")
            dm.simple_layout(fig, fit_labels=fit_labels)
            if fit_labels is not False:
                assert _gap_em(fig, ax) >= 0.5  # precondition
            fig.canvas.draw()
            out = bytes(fig.canvas.buffer_rgba())
            plt.close(fig)
            return out

    assert drawn(True) == drawn(False)


def test_what_you_set_stays() -> None:
    """A rotation, line breaks or a canvas you set stay as set, close or
    not."""
    fig, ax = _countries()
    ax.tick_params(axis="x", labelrotation=0.001)
    dm.simple_layout(fig)
    assert _shape(ax)[0] == {0.0}
    fig, ax = _bars([f"{c}\n" for c in COUNTRIES], width="14.5cm")
    dm.simple_layout(fig)
    assert _shape(ax) == ({0.0}, True)
    fig, ax = _countries()
    size = tuple(fig.get_size_inches())
    dm.simple_layout(fig)
    assert tuple(fig.get_size_inches()) == size


def test_a_second_layout_draws_the_same_and_false_gives_it_back() -> None:
    fig, ax = _countries()
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    unfitted = bytes(fig.canvas.buffer_rgba())
    dm.simple_layout(fig)
    fig.canvas.draw()
    first = bytes(fig.canvas.buffer_rgba())
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert bytes(fig.canvas.buffer_rgba()) == first
    assert first != unfitted
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    assert bytes(fig.canvas.buffer_rgba()) == unfitted
