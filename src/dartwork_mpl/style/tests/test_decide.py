"""Pure decisions and the parsing they rely on."""

from __future__ import annotations

import pytest

from dartwork_mpl.edgecase import settle
from dartwork_mpl.style import apply, decide, load_style_dict
from dartwork_mpl.style.edges import EDGES
from dartwork_mpl.style.model import Active, Points, Steps, Weight, override_key
from dartwork_mpl.vocab import DefaultLocale, KoreanLocale

REGISTRY = apply.REGISTRY


@pytest.mark.parametrize("name", sorted(REGISTRY.presets))
def test_korean_presets_and_only_they_flip_the_role_colours(name):
    chain = decide.chain(REGISTRY.parse(name))
    korean = KoreanLocale() if name.endswith("-kr") else DefaultLocale()
    assert chain.locale == korean
    assert chain.layers[0] == "base"


def test_a_list_applies_every_preset_layer_in_order():
    chain = decide.chain(REGISTRY.parse(["scientific", "dark"]))
    assert chain.layers == (
        "base",
        "font-scientific",
        "base",
        "font-web",
        "theme-dark",
    )


@pytest.mark.parametrize(
    ("base", "n", "size", "expected"),
    [(7.5, -1, 1.0, 6.5), (19.5, 1, 2.6, 22.1), (1.0, 0.5, 1.0, 1.5)],
)
def test_offset_moves_the_base_by_whole_steps(base, n, size, expected):
    moved = decide.offset(Points(base), Steps(n), Points(size))
    assert moved.pt == pytest.approx(expected)


def _line_width_and_step(name):
    presets = REGISTRY.parse(name)
    base = 1.0
    for layer in decide.chain(presets).layers:
        base = float(load_style_dict(layer).get("lines.linewidth", base))
    active = Active(presets, in_force=True)
    return Points(base), settle(active, decide.step(active), EDGES).plan


@pytest.mark.parametrize("name", sorted(REGISTRY.presets))
def test_every_line_width_step_draws_a_line(name):
    base, size = _line_width_and_step(name)
    widths = [decide.thinner(base, Steps(n), size).pt for n in range(-3, 4)]
    assert widths[3] == base.pt
    assert all(w > 0 for w in widths)
    assert widths == sorted(widths)
    above = [decide.offset(base, Steps(n), size).pt for n in range(4)]
    assert widths[3:] == pytest.approx(above)


@pytest.mark.parametrize(
    ("base", "size", "expected"),
    [(1.0, 1.0, [0.125, 0.25, 0.5]), (1.5, 1.0, [0.125, 0.25, 0.5])],
)
def test_below_half_a_step_each_line_step_halves(base, size, expected):
    widths = [
        decide.thinner(Points(base), Steps(n), Points(size)).pt
        for n in (-3, -2, -1)
    ]
    assert widths == pytest.approx(expected)


@pytest.mark.parametrize(
    ("rc", "n", "expected"),
    [("light", 1, 300), ("normal", 0, 400), ("bold", -1, 600), (400, 0.5, 450)],
)
def test_weight_names_count_as_their_number(rc, n, expected):
    assert decide.bolder(Weight.parse(rc), Steps(n)) == Weight(expected)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("font.size", "font.size"),
        ("font_size", "font.size"),
        ("legend_title_fontsize", "legend.title_fontsize"),
        ("no_such_key", "no_such_key"),
    ],
)
def test_override_keys_name_their_rcparam(key, expected):
    known = ["font.size", "legend.title_fontsize"]
    assert override_key(key, known) == expected


def test_unknown_preset_hint_names_the_closest():
    with pytest.raises(KeyError, match="Did you mean 'scientific'"):
        REGISTRY.parse("sceintific")
    with pytest.raises(TypeError, match="must be str"):
        REGISTRY.parse(["report", 3])
