"""The colour decisions on their own: domain values in, values out."""

from __future__ import annotations

import pytest

from dartwork_mpl.color import decide
from dartwork_mpl.color.catalog import CATALOG
from dartwork_mpl.color.family import Count
from dartwork_mpl.color.model import Form, Gradient, Lookup, Name, Steps, Weight
from dartwork_mpl.colorspace import Color, Oklch, Rgb

WHITE, BLACK = Rgb(1.0, 1.0, 1.0), Rgb(0.0, 0.0, 0.0)


def form(name: str, n: int) -> tuple[str, ...]:
    family = CATALOG.families[name]
    return decide.discrete(Form(family, Count.parse(n, family)))


@pytest.mark.parametrize(
    ("n", "stops"),
    [
        (1, (5,)),
        (2, (1, 8)),
        (3, (1, 5, 8)),
        (4, (1, 3, 6, 8)),
        (8, (1, 2, 3, 4, 5, 6, 7, 8)),
    ],
)
def test_sequential_forms_spread_over_the_middle_stops(n, stops):
    ladder = CATALOG.ladder("teal")
    assert form("teal", n) == tuple(ladder[i] for i in stops)


def test_diverging_forms_keep_outer_stops_and_odd_n_adds_the_midpoint():
    family = CATALOG.families["blue_red"]
    row, middle = family.stops, family.cmap[128]
    assert form("blue_red", 2) == (row[0], row[7])
    assert form("blue_red", 3) == (row[0], middle, row[7])
    assert form("blue_red", 8) == row


def test_multi_hue_cyclic_and_qualitative_forms():
    aurora = CATALOG.families["aurora"]
    assert form("aurora", 2) == (aurora.cmap[55], aurora.cmap[224])
    hue = CATALOG.families["hue"]
    assert form("hue", 4) == tuple(hue.cmap[i] for i in (0, 64, 128, 192))
    assert form("vivid", 3) == CATALOG.families["vivid"].stops[:3]


@pytest.mark.parametrize(
    ("name", "n"),
    [("teal", 0), ("teal", 11), ("blue_red", 10), ("vivid", 9), ("hue", 25)],
)
def test_counts_past_a_form_are_rejected(name, n):
    with pytest.raises(ValueError, match="max n="):
        Count.parse(n, CATALOG.families[name])


def test_mix_weights_the_first_colour():
    red, blue = Color(Rgb(1.0, 0.0, 0.0).oklab()), Color(BLACK.oklab())
    assert decide.mix(red, blue, Weight(1.0)) == red
    assert decide.mix(red, blue, Weight(0.0)) == blue


def test_sample_runs_the_hue_the_short_way_round():
    gradient = Gradient(Oklch(0.7, 0.1, 350.0), Oklch(0.7, 0.1, 10.0))
    middle = decide.sample(gradient, Steps(3))[1].to_oklch()[2]
    assert min(middle, 360.0 - middle) < 1e-6  # through red, not via cyan


def test_suggest_finds_close_registered_names():
    registry = tuple(Name(n) for n in ("dc.teal5", "dc.teal4", "oc.red5"))
    close = decide.suggest(Lookup(Name("dc.tael5"), registry)).names
    assert close[0] == "dc.teal5"
