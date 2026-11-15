"""The colour arithmetic on its own: colour values in, values out."""

from __future__ import annotations

import pytest

from dartwork_mpl.colorspace import (
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


def test_composite_paints_layers_in_order():
    half_red = Rgba(Rgb(1.0, 0.0, 0.0), 0.5)
    assert decide.composite_over(half_red, WHITE).channels == (1.0, 0.5, 0.5)
    opaque = Rgba(BLACK, 1.0)
    assert decide.composite_layers((half_red, opaque), WHITE) == BLACK
