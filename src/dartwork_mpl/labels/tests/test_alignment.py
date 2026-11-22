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


@pytest.mark.parametrize(
    ("text", "left", "right", "gap"),
    [
        ("1.1, 2.2", ".1,", "2", 1),
        ("1.1 [-2.2]", ".1", "[\u22122", 1),
        ("1.1(2.2%", ".1", "(2", 0),
        ("1.1,   2.2", ".1,", "2", 3),
        ("1.1,\xa02.2", ".1,", "2", 2),
    ],
)
def test_decimal_plan_keeps_literal_spacing(text, left, right, gap):
    """A tab joint includes the font advance of every supplied separator."""

    def advance(value):
        return len(value) + value.count("\xa0")

    (plan,) = decimal_rows([MeasuredRow(NumericText.parse(text), advance)])
    trailing = next(piece for piece in plan if piece.text == left)
    leading = next(piece for piece in plan if piece.text == right)
    assert (
        leading.offset - advance(right) - trailing.offset - advance(left) == gap
    )


@pytest.mark.parametrize("how", ["left", "center", "right", "decimal"])
def test_alignment_is_repeatable_before_or_after_layout(how):
    """Applying alignment again returns the same rendered rows."""
    results = []
    for early in (True, False):
        with dm.style.context("scientific"):
            fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
            ax.set(ylim=(0, 4), xlabel="Effect")
            originals = [
                ax.text(1.02, y, text, transform=ax.get_yaxis_transform())
                for y, text in enumerate(
                    ("9.4 [2.4, 16.4]", "-1.2 [0.3, 9.8]"), 1
                )
            ]
            if not early:
                dm.simple_layout(fig)
            rows = dm.align_texts(originals, how)
            dm.simple_layout(fig)
            assert dm.align_texts(originals, how) == rows
            assert dm.align_texts(rows, how) == rows
            renderer = fig.canvas.get_renderer()
            results.append(
                [
                    float(value)
                    for t in rows
                    for value in t.get_window_extent(renderer).extents
                ]
            )
            plt.close(fig)
    assert results[0] == pytest.approx(results[1], abs=0.02)


def test_editing_returned_rows_updates_the_drawn_text():
    """An edited value draws as one Text and styling reaches the original pieces."""
    from matplotlib.colors import to_rgba

    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "5cm"))
    ax.set(ylim=(0, 3))
    source = [
        ax.text(1.02, y, value, transform=ax.get_yaxis_transform())
        for y, value in enumerate(("12.3", "4.5"), 1)
    ]
    row, sibling = dm.align_texts(source, "decimal")
    dm.simple_layout(fig)
    renderer = fig.canvas.get_renderer()
    prior = row.get_window_extent(renderer)
    row.set_color("red")
    row.set_fontweight("bold")
    fig.canvas.draw()
    assert all(
        to_rgba(piece.get_color()) == to_rgba("red")
        and piece.get_fontweight() == "bold"
        for piece in row.pieces
    )
    row.set_text("Revised text, much wider than either number")
    fig.canvas.draw()
    assert row.get_window_extent(renderer).width > prior.width
    advance, _, _ = renderer.get_text_width_height_descent(
        row.get_text(), row.get_fontproperties(), False
    )
    assert row.get_window_extent(renderer).width == pytest.approx(advance)
    assert dm.align_texts(source, "decimal") == [row, sibling]
    plt.close(fig)
