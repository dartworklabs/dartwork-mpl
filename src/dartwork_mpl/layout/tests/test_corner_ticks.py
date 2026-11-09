"""The ``pad`` step: x and y tick labels that meet at a plot corner.

When both axes end on a tick, the first bottom label and the lowest left
label overlap at the corner (the ``-3`` and ``-3`` of a -3..3 square, 1.6
to 4.2 px in the old contour template and in eight docs examples). The
step grows the tick pad of the axis whose labels move less, by the overlap
plus a hair space, and only where a pair collides. The oracle here is the
drawn labels' own boxes, measured in the test.
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


def _square(preset: str = "report", width: str = "9cm", span: float = 3):
    """A -3..3 square: both axes end on a tick, so ``-3`` meets ``-3``
    (``span=30``: ``-30`` and ``30`` reach every corner)."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize(width, "square"))
    x = np.linspace(-span, span, 50)
    ax.plot(x, span * np.sin(x / span * 3))
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    return fig, ax


def _boxes(fig, axes, which):
    """Every drawn tick label box of ``which``, major and minor."""
    renderer = get_renderer(fig)
    return [
        label.get_window_extent(renderer)
        for ax in axes
        for minor in (False, True)
        for label in drawn_tick_labels(ax, which, minor=minor)
        if label.get_text().strip()
    ]


def _worst(fig, axes=None) -> float:
    """The deepest overlap (px) of an x tick label box with a y one."""
    fig.canvas.draw()
    axes = fig.axes if axes is None else axes
    worst = 0.0
    for a in _boxes(fig, axes, "x"):
        for b in _boxes(fig, axes, "y"):
            across = min(a.x1, b.x1) - max(a.x0, b.x0)
            down = min(a.y1, b.y1) - max(a.y0, b.y0)
            worst = max(worst, min(across, down))
    return worst


def _pads(ax) -> tuple[float, float]:
    return (
        float(ax.xaxis.get_major_ticks()[0].get_pad()),
        float(ax.yaxis.get_major_ticks()[0].get_pad()),
    )


@pytest.mark.parametrize(
    ("preset", "width"),
    [("scientific", "9cm"), ("report", "9cm"), ("presentation", "15.4cm")],
)
def test_the_corner_labels_of_a_square_part(preset: str, width: str) -> None:
    fig, ax = _square(preset, width)
    dm.simple_layout(fig, fit_labels=False)
    assert _worst(fig) > 0.5  # precondition: they collide unfitted
    pads = _pads(ax)
    dm.simple_layout(fig)
    assert _worst(fig) <= 0.5
    # the x labels moved (they move less here); the y labels did not
    assert _pads(ax)[0] > pads[0]
    assert _pads(ax)[1] == pads[1]


def test_the_row_keeps_its_line_and_every_label_its_tick() -> None:
    """A pad moves the whole row: one baseline, each label on its tick."""
    fig, ax = _square()
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = get_renderer(fig)
    labels = [t for t in drawn_tick_labels(ax, "x") if t.get_text().strip()]
    boxes = [t.get_window_extent(renderer) for t in labels]
    assert len({round(b.y1, 3) for b in boxes}) == 1
    ticks = ax.transData.transform([(v, 0) for v in ax.get_xticks()])[:, 0]
    centres = sorted((b.x0 + b.x1) / 2 for b in boxes)
    assert np.allclose(centres, sorted(ticks)[: len(centres)], atol=0.6)


def test_the_gap_is_a_hair_space() -> None:
    """Cleared by a tenth of an em of the moved labels, not by a pixel
    count (which would change with the dpi) nor by a gap as wide as the
    room between labels (0.25 em left the row plainly lower)."""
    fig, ax = _square()
    dm.simple_layout(fig)
    fig.canvas.draw()
    (x_box,) = [
        b for b in _boxes(fig, [ax], "x") if b.x0 < ax.get_window_extent().x0
    ]
    (y_box,) = [
        b for b in _boxes(fig, [ax], "y") if b.y0 < ax.get_window_extent().y0
    ]
    size_px = ax.xaxis.get_major_ticks()[0].label1.get_fontsize() * fig.dpi / 72
    gap = y_box.y0 - x_box.y1
    assert gap == pytest.approx(0.1 * size_px, abs=0.5)


def test_a_plot_whose_labels_clear_is_left_as_it_was() -> None:
    """Only a colliding pair moves anything: limits off the ticks, no pad."""
    fig, ax = _square()
    ax.set_xlim(-3.2, 3.2)
    ax.set_ylim(-3.2, 3.2)
    before = _pads(ax)
    dm.simple_layout(fig)
    assert _worst(fig) <= 0.5
    assert _pads(ax) == before


def test_labels_that_only_touch_stay() -> None:
    """Under half a pixel the pair touches, as everywhere in the ladder:
    an x pad of 2.93 pt leaves the corner 0.3 px deep, and nothing moves."""
    fig, ax = _square()
    ax.tick_params(axis="x", pad=2.93)
    dm.simple_layout(fig, fit_labels=False)
    assert 0 < _worst(fig) <= 0.5  # precondition: touching
    before = _pads(ax)
    dm.simple_layout(fig)
    assert _pads(ax) == before


def test_a_minor_label_at_the_corner_parts() -> None:
    """Major ticks at -2, 0, 2 and labelled minor ones at -3 ... 3: the
    minor ``-3`` meets the y ``-3``."""
    from matplotlib.ticker import FixedLocator

    fig, ax = _square()
    ax.xaxis.set_major_locator(FixedLocator([-2, 0, 2]))
    ax.xaxis.set_minor_locator(FixedLocator([-3, -1, 1, 3]))
    ax.xaxis.set_minor_formatter("{x:g}")

    def worst() -> float:
        fig.canvas.draw()
        renderer = get_renderer(fig)
        xs = [
            t.get_window_extent(renderer)
            for minor in (False, True)
            for t in drawn_tick_labels(ax, "x", minor=minor)
            if t.get_text().strip()
        ]
        ys = _boxes(fig, [ax], "y")
        return max(
            min(
                min(a.x1, b.x1) - max(a.x0, b.x0),
                min(a.y1, b.y1) - max(a.y0, b.y0),
            )
            for a in xs
            for b in ys
        )

    dm.simple_layout(fig, fit_labels=False)
    assert worst() > 0.5  # precondition
    dm.simple_layout(fig)
    assert worst() <= 0.5


def test_a_wrap_that_clears_the_corner_leaves_the_pads() -> None:
    """The first of four long names reaches under the y labels until the
    names wrap; the pad step looks only once the wrap has settled, so it
    finds nothing to move."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    names = [
        "Residential heat pumps",
        "Commercial chillers",
        "District heating network",
        "Industrial waste heat",
    ]
    ax.bar(names, [3, 5, 2, 4])
    dm.simple_layout(fig, fit_labels=False)
    assert _worst(fig) > 0.5  # precondition: the first name under the 0
    before = _pads(ax)
    dm.simple_layout(fig)
    texts = [t.get_text() for t in drawn_tick_labels(ax, "x")]
    assert any("\n" in text for text in texts)  # the names wrapped
    assert _worst(fig) <= 0.5
    assert _pads(ax) == before


def test_the_axis_that_moves_less_moves() -> None:
    """Tall y labels against a narrow ``-3``: the y column moves out."""
    fig, ax = _square()
    ax.tick_params(axis="y", labelsize=14)
    dm.simple_layout(fig, fit_labels=False)
    assert _worst(fig) > 0.5  # precondition
    pads = _pads(ax)
    dm.simple_layout(fig)
    assert _worst(fig) <= 0.5
    assert _pads(ax)[0] == pads[0]
    assert _pads(ax)[1] > pads[1]


def test_a_pad_you_set_stays() -> None:
    fig, ax = _square()
    ax.tick_params(axis="x", pad=2)
    dm.simple_layout(fig)
    assert _worst(fig) <= 0.5  # the y column moved instead
    assert _pads(ax)[0] == 2
    fig, ax = _square()
    ax.tick_params(axis="x", pad=2)
    ax.tick_params(axis="y", pad=1)
    dm.simple_layout(fig)
    assert _pads(ax) == (2, 1)  # both yours: left for the author
    assert _worst(fig) > 0.5
    found = [w.check_id for w in dm.validate_figure(fig, quiet=True)]
    assert "TICK_CORNER_OVERLAP" in found


@pytest.mark.parametrize("corner", ["lower right", "upper left", "upper right"])
def test_every_corner_parts(corner: str) -> None:
    fig, ax = _square(span=30)
    if "right" in corner:
        ax.yaxis.tick_right()
    if "upper" in corner:
        ax.xaxis.tick_top()
        # a y label rises less above its tick than it hangs below
        # (centre-baseline): larger ones reach the top row
        ax.tick_params(axis="y", labelsize=14)
    dm.simple_layout(fig, fit_labels=False)
    assert _worst(fig) > 0.5  # precondition
    dm.simple_layout(fig)
    assert _worst(fig) <= 0.5


def test_a_twins_right_labels_part_from_the_bottom_row() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 10], [0.2, 1])
    ax.set_xlim(0, 10)
    ax.set_ylim(0.2, 1)
    right = ax.twinx()
    right.plot([0, 10], [-3, 3])
    right.set_ylim(-3, 3)
    dm.simple_layout(fig, fit_labels=False)
    assert _worst(fig, [ax, right]) > 0.5  # precondition: 10 meets -3
    dm.simple_layout(fig)
    assert _worst(fig, [ax, right]) <= 0.5


@pytest.mark.parametrize("scene", ["minor y", "minor x", "twin"])
def test_the_ticks_and_the_axes_that_collide_move(scene: str) -> None:
    """The step moves the labels of the pair, whatever they are: tall minor
    y labels (major ticks at -2, 0, 2) move their minor pad, wide minor x
    labels theirs, a twin's tall right labels the twin's pad (#663: the
    check's fix had named the major ticks and the first Axes)."""
    from matplotlib.ticker import FixedLocator

    if scene == "twin":
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 10], [0.2, 1])
        ax.set_xlim(0, 10)
        ax.set_ylim(0.2, 1)
        right = ax.twinx()
        right.plot([0, 10], [-3, 3])
        right.set_ylim(-3, 3)
        right.tick_params(axis="y", labelsize=14)
        moved = right.yaxis
    else:
        fig, ax = _square()
        axis = ax.yaxis if scene == "minor y" else ax.xaxis
        axis.set_major_locator(FixedLocator([-2, 0, 2]))
        axis.set_minor_locator(FixedLocator([-3, -1, 1, 3]))
        axis.set_minor_formatter("{x:g}" if scene == "minor y" else "{x:.2f}")
        if scene == "minor y":
            ax.tick_params(axis="y", which="minor", labelsize=14)
        moved = axis
    dm.simple_layout(fig, fit_labels=False)
    assert _worst(fig) > 0.5  # precondition
    ticks = (
        moved.get_major_ticks() if scene == "twin" else moved.get_minor_ticks()
    )
    before = float(ticks[0].get_pad())
    dm.simple_layout(fig)
    assert _worst(fig) <= 0.5
    ticks = (
        moved.get_major_ticks() if scene == "twin" else moved.get_minor_ticks()
    )
    assert float(ticks[0].get_pad()) > before


def test_a_second_layout_draws_the_same_and_false_gives_it_back() -> None:
    fig, ax = _square()
    pads = _pads(ax)
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
    assert _pads(ax) == pads
    assert bytes(fig.canvas.buffer_rgba()) == unfitted


def test_a_figure_without_a_corner_pair_draws_as_without_the_step() -> None:
    """Looking for pairs moves nothing. A fixed-aspect plot (the docs' DNA
    helix, -2..2 by -0.5..13 with ``set_aspect("equal")``) whose labels
    clear draws the same with the step and without it: reading the Axes'
    active position mid-layout would apply its aspect and move it."""

    def drawn(fit_labels) -> bytes:
        with matplotlib.rc_context():
            dm.style.use("report")
            fig, ax = plt.subplots(figsize=dm.figsize("12cm", 1.667))
            t = np.linspace(0, 4 * np.pi, 100)
            ax.plot(np.sin(t), t)
            ax.set_xlim(-2, 2)
            ax.set_ylim(-0.5, 4 * np.pi + 0.5)
            ax.set_aspect("equal")
            ax.set_xlabel("Width")
            dm.simple_layout(fig, fit_labels=fit_labels)
            fig.canvas.draw()
            out = bytes(fig.canvas.buffer_rgba())
            plt.close(fig)
            return out

    others = ("axis_labels", "space", "wrap", "rotate")
    assert drawn(True) == drawn(others)


def test_transparent_labels_move_nothing() -> None:
    """x labels at alpha 0 draw nothing: the corner is clear, no pad moves
    (independent review of #663)."""
    fig, ax = _square()
    for label in ax.get_xticklabels():
        label.set_alpha(0)
    before = _pads(ax)
    dm.simple_layout(fig)
    assert _pads(ax) == before


# ── what you set after a layout is yours (independent review of #663) ──


def test_a_pad_you_set_after_the_layout_stays() -> None:
    """``tick_params(pad=...)`` after a layout, even at the fitted value,
    is yours: the next layout leaves it, and the axis reports what it
    draws."""
    fig, ax = _square()
    dm.simple_layout(fig)
    chosen = ax.xaxis.get_major_ticks()[0].get_pad()
    assert chosen > 2  # precondition: the layout grew it
    ax.tick_params(axis="x", pad=chosen)
    dm.simple_layout(fig, fit_labels=False)
    assert ax.xaxis.get_tick_params()["pad"] == chosen
    assert ax.xaxis.get_major_ticks()[0].get_pad() == chosen


def test_a_tick_you_set_after_the_layout_stays() -> None:
    """One tick's ``set_pad`` after a layout stays; the others, still as
    fitted, go back."""
    fig, ax = _square()
    dm.simple_layout(fig)
    ticks = ax.xaxis.get_major_ticks()
    assert ticks[0].get_pad() > 2  # precondition
    ticks[1].set_pad(20)
    dm.simple_layout(fig, fit_labels=False)
    assert ticks[1].get_pad() == 20
    assert ticks[0].get_pad() == 2


def test_an_axis_with_a_tick_of_its_own_is_yours_next_time() -> None:
    """Once a tick has a pad of its own, the next layout leaves the axis
    alone and moves the other one."""
    fig, ax = _square()
    dm.simple_layout(fig)
    ax.xaxis.get_major_ticks()[1].set_pad(20)
    dm.simple_layout(fig)
    pads = [t.get_pad() for t in ax.xaxis.get_major_ticks()]
    assert pads[1] == 20
    assert {p for i, p in enumerate(pads) if i != 1} == {2}
    assert ax.yaxis.get_major_ticks()[0].get_pad() > 1  # the y labels moved
    assert _worst(fig) <= 0.5
