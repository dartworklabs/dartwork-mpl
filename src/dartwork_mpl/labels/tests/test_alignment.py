"""Horizontal alignment only moves the selected artist coordinate."""

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.labels.alignment_layout import MeasuredRow, decimal_rows
from dartwork_mpl.vocab.numeric_text import NumericText


@pytest.mark.parametrize(
    ("mode", "point"), [("left", 0), ("center", 0.5), ("right", 1)]
)
def test_edge_alignment_on_existing_artists(mode, point):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    ax.set(xlim=(0, 10), ylim=(0, 5))
    texts = [
        ax.text(2, 1, "Short"),
        ax.annotate(
            "Wider", (2.5, 2), xytext=(2, 0), textcoords="offset points"
        ),
        ax.text(4, 3, "The longest"),
    ]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    before = [
        t.get_window_extent(renderer).y0 - ax.transData.transform((0, y))[1]
        for y, t in enumerate(texts, 1)
    ]
    assert dm.align_texts(texts, mode) == texts
    for size in ("12cm", "16cm"):
        fig.set_size_inches(*dm.figsize(size, "5cm"))
        fig.canvas.draw()
        boxes = [t.get_window_extent(fig.canvas.get_renderer()) for t in texts]
        assert [
            b.y0 - ax.transData.transform((0, y))[1]
            for y, b in enumerate(boxes, 1)
        ] == pytest.approx(before)
        expected = boxes[0].x0 + point * boxes[0].width
        assert [b.x0 + point * b.width for b in boxes] == pytest.approx(
            [expected] * 3
        )
    plt.close(fig)


def test_left_align_tick_labels_in_place():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    ax.set_yticks([0, 1, 2], ["Study A", "Longer title", "Study C"])
    fig.canvas.draw()
    texts = ax.get_yticklabels()
    assert dm.align_texts(texts, "left") == texts
    dm.simple_layout(fig)
    assert ax.get_yticklabels() == texts
    renderer = fig.canvas.get_renderer()
    edge = [t.get_window_extent(renderer).x0 for t in texts]
    assert max(edge) - min(edge) < 0.01
    plt.close(fig)


@pytest.mark.parametrize(
    ("cells", "stops"),
    [
        (["1.1", "88.8"], [2]),
        (["1.1 [-1.1, 9.9]", "88.8 [1.2, 9.1]"], [2, 8, 13]),
        (["1.1", "88.8 (5%)"], []),
    ],
)
def test_decimal_plan(cells, stops):
    # Fixed mock widths make the tab-stop decisions readable as a table.
    rows = decimal_rows(
        [MeasuredRow(NumericText.parse(text), len) for text in cells]
    )
    for row in rows:
        assert [
            piece.offset for piece in row if piece.text.startswith(".")
        ] == stops
    assert bool(rows) == bool(stops)
