"""The colour arithmetic on its own: colour values in, values out."""

from __future__ import annotations

import numpy as np
import pytest

from dartwork_mpl.colorspace import (
    LEGIBLE,
    ContrastFacts,
    DarkInk,
    LightInk,
    Ratio,
    Rgb,
    Rgba,
    decide,
)

WHITE, BLACK = Rgb(1.0, 1.0, 1.0), Rgb(0.0, 0.0, 0.0)


def test_contrast_is_wcag():
    assert decide.contrast(BLACK, WHITE).value == pytest.approx(21.0)
    assert decide.contrast(WHITE, WHITE).value == pytest.approx(1.0)
    grey = Rgb.from_hex("#767676")  # the classic 4.5:1 grey on white
    assert decide.contrast(grey, WHITE).value == pytest.approx(4.54, abs=0.01)


def test_lift_is_none_for_a_passing_colour_and_darkens_on_white():
    passing = ContrastFacts(BLACK, WHITE, Ratio(4.5))
    assert decide.lift(passing) is None
    pale = ContrastFacts(Rgb.from_hex("#ddddaa"), WHITE, Ratio(4.5))
    lift = decide.lift(pale)
    assert lift is not None and not lift.lighten
    assert decide.contrast(lift.rgb(), WHITE).value >= 4.5


def test_readable_picks_the_higher_contrast_ink():
    dark_bg, pale_bg = Rgb.from_hex("#222222"), Rgb.from_hex("#f7f7f7")
    assert decide.readable(dark_bg, WHITE, BLACK) == LightInk()
    assert decide.readable(pale_bg, WHITE, BLACK) == DarkInk()


def test_composite_paints_over():
    half_red = Rgba(Rgb(1.0, 0.0, 0.0), 0.5)
    assert decide.composite_over(half_red, WHITE).channels == (1.0, 0.5, 0.5)


def test_contrasts_of_pixel_rows_equal_the_contrast_of_each_pair():
    """The array arithmetic is the scalar one: a row per colour pair."""
    inks = [BLACK, WHITE, Rgb.from_hex("#767676"), Rgb.from_hex("#0b2a5b")]
    papers = [WHITE, Rgb.from_hex("#f9d969"), WHITE, BLACK]
    got = decide.contrasts(
        np.array([c.channels for c in inks]),
        np.array([c.channels for c in papers]),
    )
    want = [
        decide.contrast(a, b).value for a, b in zip(inks, papers, strict=True)
    ]
    assert got == pytest.approx(want)
    one = decide.contrasts(np.array(BLACK.channels), np.array([[1.0, 1, 1]]))
    assert one == pytest.approx([21.0])


def _text(
    *runs: tuple[int, int], per_window: int = 40, line: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Black ink along one line of a text, ``per_window`` pixels to a
    window: runs of (pixels on white, then pixels on navy)."""
    white, navy = (1.0, 1.0, 1.0), Rgb.from_hex("#0b2a5b").channels
    paper = [c for on, lost in runs for c in [white] * on + [navy] * lost]
    along = (np.arange(len(paper)) + 0.5) / per_window
    places = np.column_stack([along, np.full(len(paper), float(line))])
    return np.zeros((len(paper), 3)), np.array(paper), places


@pytest.mark.parametrize(
    ("runs", "low", "worst", "reads"),
    [
        (((120, 0),), 0.0, 0.0, True),
        (((0, 80),), 1.0, 1.0, False),  # all of it on navy
        (((80, 40),), 1 / 3, 1.0, False),  # the last third
        (((40, 19), (61, 0)), 19 / 120, 19 / 40, True),  # under half a window
        (((40, 21), (59, 0)), 21 / 120, 21 / 40, False),  # over half
        # a band one window wide that straddles two fixed windows is one
        # window all the same: the window slides
        (((60, 40), (60, 0)), 0.25, 1.0, False),
        (((70, 21), (69, 0)), 21 / 160, 21 / 40, False),
    ],
)
def test_a_text_reads_until_one_window_loses_half_its_ink(
    runs: tuple[tuple[int, int], ...], low: float, worst: float, reads: bool
):
    """Black on white reads (21:1), black on navy does not (1.5:1): the
    share of ink lost, the worst window wherever it starts, and whether
    the text still reads."""
    got = decide.legibility(*_text(*runs), LEGIBLE)
    assert got.low == pytest.approx(low)
    assert got.worst == pytest.approx(worst, abs=0.03)
    assert got.reads is reads


def test_a_window_with_too_little_ink_is_not_judged_alone():
    """Three lost pixels a window away from the rest (a comma after a
    gap) are not a window of text; and a line is judged by itself, so
    one lost line of two is found whatever the other does."""
    ink, paper, places = _text((80, 0), (0, 3))
    places[-3:, 0] += 2.0
    assert decide.legibility(ink, paper, places, LEGIBLE).reads
    first, second = _text((120, 0)), _text((0, 120), line=1)
    both = [np.concatenate(pair) for pair in zip(first, second, strict=True)]
    got = decide.legibility(*both, LEGIBLE)
    assert got.low == pytest.approx(0.5) and not got.reads


def test_the_faintest_ink_names_its_colours_and_a_text_with_no_ink_reads():
    """``lowest`` is the ratio between ``ink`` and ``paper``; no pixels at
    all (a text clipped away) is a text that reads."""
    got = decide.legibility(*_text((40, 0), (0, 40)), LEGIBLE)
    assert got.paper.hex() == "#0b2a5b" and got.ink.hex() == "#000000"
    assert got.lowest.value == pytest.approx(
        decide.contrast(BLACK, Rgb.from_hex("#0b2a5b")).value
    )
    none = np.zeros((0, 3))
    empty = decide.legibility(none, none, np.zeros((0, 2)), LEGIBLE)
    assert empty.reads and empty.low == 0.0 and empty.lowest.value == 21.0
