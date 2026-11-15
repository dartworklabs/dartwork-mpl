"""Pure decisions and the parsing they rely on."""

from __future__ import annotations

import pytest

from dartwork_mpl.style import apply, decide
from dartwork_mpl.style.model import Locale, Points, Steps, Weight, override_key

REGISTRY = apply.REGISTRY


@pytest.mark.parametrize("name", sorted(REGISTRY.presets))
def test_korean_presets_and_only_they_flip_the_role_colours(name):
    chain = decide.chain(REGISTRY.parse(name))
    korean = Locale.KR if name.endswith("-kr") else Locale.DEFAULT
    assert chain.locale is korean
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
