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


STEPS = [Steps(n) for n in range(-10, 11)]


def _preset(name):
    """The preset's font size, line width, weight and step, as it sets them."""
    presets = REGISTRY.parse(name)
    rc = {"font.size": 10.0, "lines.linewidth": 1.0, "font.weight": "normal"}
    for layer in decide.chain(presets).layers:
        rc.update((k, v) for k, v in load_style_dict(layer).items() if k in rc)
    active = Active(presets, in_force=True)
    step = settle(active, decide.step(active), EDGES).plan
    size, width = (
        Points(float(rc["font.size"])),
        Points(float(rc["lines.linewidth"])),
    )
    return size, width, Weight.parse(rc["font.weight"]), step


@pytest.mark.parametrize("name", sorted(REGISTRY.presets))
def test_every_step_is_a_size_width_and_weight_matplotlib_draws(name):
    size, width, weight, step = _preset(name)
    fs = [decide.smaller(size, n, step).pt for n in STEPS]
    lw = [decide.thinner(width, n, step).pt for n in STEPS]
    fw = [decide.bolder(weight, n).value for n in STEPS]
    assert (fs[10], lw[10], fw[10]) == (size.pt, width.pt, weight.value)
    assert all(v > 0 for v in fs + lw)
    assert all(100 <= v <= 900 for v in fw)
    assert fs == sorted(fs) and lw == sorted(lw) and fw == sorted(fw)
    for n, f, w, b in zip(STEPS, fs, lw, fw, strict=True):
        was_fs, was_lw = (decide.offset(v, n, step).pt for v in (size, width))
        was_fw = weight.value + 100 * n.n
        assert was_fs <= 0 or f == was_fs  # valid today: unchanged
        assert n.n < 0 or w == pytest.approx(was_lw)
        assert not 100 <= was_fw <= 900 or b == was_fw


@pytest.mark.parametrize(
    ("base", "size", "expected"),
    [
        (8.0, 1.0, [1.0, 1.0, 2.0]),
        (7.5, 1.0, [0.5, 0.5, 1.5]),
        (19.5, 2.6, [1.3, 1.3, 3.9]),
    ],
)
def test_a_font_step_past_zero_stops_at_the_smallest_whole_step(
    base, size, expected
):
    sizes = [
        decide.smaller(Points(base), Steps(n), Points(size)).pt
        for n in (-9, -8, -6)
    ]
    assert sizes == pytest.approx(expected)


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
