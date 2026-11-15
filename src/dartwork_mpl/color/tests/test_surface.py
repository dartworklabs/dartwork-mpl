"""The colour surface the guidance and templates use, on real charts."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


@pytest.fixture(autouse=True)
def _isolated():
    with mpl.rc_context():
        yield
    plt.close("all")


def test_shipped_names_and_colormaps_work_in_plotting_calls():
    fig, ax = plt.subplots()
    ax.bar([0, 1], [1, 2], color=["dc.teal5", "oc.red5"])
    ax.imshow([[0, 1]], cmap="dc.aurora")
    assert mcolors.to_hex("dc.teal5") == dm.color("dc.teal5").to_hex()
    assert mcolors.to_hex("tw.blue500") == "#3b82f6"
    assert {"dc.aurora", "dc.aurora_r", "dc.vivid", "dc.octave"} <= set(
        mpl.colormaps
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#ff0000", "#ff0000"),
        ("#f00", "#ff0000"),
        ("rgb(255, 128, 0)", "#ff8000"),
        ("rgb(1, 0, 0)", "#ff0000"),
        ("oklch(0.7, 0.4, 30)", "#ff6551"),  # out of gamut: chroma reduced
        ("oc.red5", "#ff6b6b"),
        ("tab:blue", "#1f77b4"),
    ],
)
def test_color_parses_every_written_form(text, expected):
    assert dm.color(text).to_hex() == expected


def test_constructors_agree_with_the_parser():
    assert dm.oklch(0.7, 0.15, 30) == dm.color("oklch(0.7, 0.15, 30)")
    assert dm.rgb(255, 0, 0) == dm.hex("#ff0000") == dm.rgb(1, 0, 0)
    assert dm.oklab(*dm.color("dc.teal5").to_oklab()) == dm.color("dc.teal5")


def test_unknown_names_say_what_was_meant():
    with pytest.raises(
        ValueError, match="Closest registered names: 'dc.teal5'"
    ):
        dm.color("dc.tael5")
    with pytest.raises(ValueError, match="Nearest names: teal"):
        dm.colors("dc.tael", n=3)
    with pytest.raises(ValueError, match="max n=8"):
        dm.colors("dc.vivid", n=9)
    with pytest.raises(ValueError, match="mixes 0-1 and 0-255"):
        dm.rgb(255, 0.5, 0)


def test_gradient_bars_like_the_bar_template():
    gradient = dm.cspace("dc.teal5", "dc.teal1", n=5)
    hexes = [c.to_hex() for c in gradient]
    assert hexes[0] == mcolors.to_hex("dc.teal5")
    assert hexes[-1] == mcolors.to_hex("dc.teal1")
    assert len(set(hexes)) == 5
    fig, ax = plt.subplots()
    ax.bar(range(5), [5, 4, 3, 2, 1], color=hexes)


def test_families_forms_and_colormaps():
    families = dm.list_colors()
    assert len(families) == 56
    assert {
        "name": "vivid",
        "kind": "qualitative",
        "continuous": False,
        "discrete_size": 8,
    } in families
    assert [f["name"] for f in dm.list_colors("cyclic")] == [
        "hue",
        "halo",
        "corona",
    ]
    assert dm.colors("dc.teal", n=4) == dm.colors("teal", n=4)
    assert dm.colors("teal", n=3, reverse=True) == dm.colors("teal", n=3)[::-1]
    assert dm.colors("aurora").name == "dc.aurora"
    assert dm.colors("vivid", reverse=True).name == "dc.vivid_r"
    with pytest.raises(ValueError, match="Unknown color kind"):
        dm.list_colors("pastel")


def test_set_colors_sets_the_cycle_a_chart_draws_with():
    dm.set_colors("dc.vivid")
    fig, ax = plt.subplots()
    (line,) = ax.plot([0, 1])
    assert mcolors.to_hex(line.get_color()) == dm.colors("vivid", n=1)[0]
    dm.set_colors(["red", "blue"], ax=ax, styles=True)
    lines = [ax.plot([0, 1])[0] for _ in range(3)]
    assert [ln.get_color() for ln in lines] == ["red", "blue", "red"]
    assert [ln.get_linestyle() for ln in lines] == ["-", "-", "--"]
    with pytest.raises(ValueError, match="requires n="):
        dm.set_colors("dc.teal")


def test_annotation_ink_stays_readable_on_any_face():
    fig, ax = plt.subplots()
    ink = dm.ensure_contrast("dc.amber5", ax.get_facecolor())
    assert ink == "#a96600"
    assert dm.ensure_contrast("black", "white") == "black"
    assert dm.readable_text_color("#222222") == "white"
    assert dm.readable_text_color("#f7f7f7") == "black"
    assert dm.readable_text_color("dc.blue7", light="w", dark="k") in {"w", "k"}


def test_flat_alpha():
    assert dm.pseudo_alpha("red", 1.0) == pytest.approx((1.0, 0.0, 0.0))
    assert dm.pseudo_alpha("red", 0.0) == pytest.approx((1.0, 1.0, 1.0))
    with pytest.raises(ValueError, match=r"alpha must be .* \[0, 1\]"):
        dm.pseudo_alpha("red", 1.5)


def test_presets_rebind_the_role_colours():
    named = mcolors.get_named_colors_mapping()
    dm.style.use("report-kr")
    assert named["dc.pos"] == mcolors.to_hex("dc.red5")
    dm.style.use("report")
    assert named["dc.pos"] == mcolors.to_hex("dc.green6")


def test_a_role_colour_follows_the_preset_after_it_was_looked_up():
    dm.style.use("report")
    gain = mcolors.to_hex("dc.pos")
    dm.style.use("report-kr")
    assert mcolors.to_hex("dc.pos") != gain  # Korean: gains are red
    dm.style.use("report")
    assert mcolors.to_hex("dc.pos") == gain
