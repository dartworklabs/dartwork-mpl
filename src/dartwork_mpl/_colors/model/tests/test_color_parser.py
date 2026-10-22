"""Tests for ``Color.parse`` and the module-level ``dm.color`` parser."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl._colors import Color

# --- Hex ------------------------------------------------------------------- #


def test_parse_hex_long():
    assert Color.parse("#ff0000").to_hex() == "#ff0000"


def test_parse_hex_short():
    assert Color.parse("#f00").to_hex() == "#ff0000"


def test_parse_hex_with_surrounding_whitespace():
    assert Color.parse("  #00ff00  ").to_hex() == "#00ff00"


# --- Functional rgb(...) --------------------------------------------------- #


def test_parse_rgb_unit_floats():
    expected = Color.from_rgb(1.0, 0.0, 0.0)
    assert Color.parse("rgb(1.0, 0.0, 0.0)").to_hex() == expected.to_hex()


def test_parse_rgb_byte_ints():
    expected = Color.from_rgb(255, 0, 0)
    assert Color.parse("rgb(255, 0, 0)").to_hex() == expected.to_hex()


def test_parse_rgb_internal_whitespace():
    assert Color.parse("rgb( 1.0 , 0 , 0 )").to_hex() == "#ff0000"


def test_parse_rgb_case_insensitive():
    assert Color.parse("RGB(1, 0, 0)").to_hex() == "#ff0000"


def test_parse_rgb_wrong_argc():
    with pytest.raises(ValueError, match="rgb"):
        Color.parse("rgb(1, 0)")


# --- Functional oklch(...) ------------------------------------------------- #


def test_parse_oklch_matches_factory():
    expected = Color.from_oklch(0.5, 0.1, 30.0)
    got = Color.parse("oklch(0.5, 0.1, 30)")
    L_e, a_e, b_e = expected.to_oklab()
    L_g, a_g, b_g = got.to_oklab()
    assert math.isclose(L_g, L_e, abs_tol=1e-9)
    assert math.isclose(a_g, a_e, abs_tol=1e-9)
    assert math.isclose(b_g, b_e, abs_tol=1e-9)


def test_parse_oklch_case_insensitive():
    expected = Color.from_oklch(0.7, 0.15, 120.0)
    got = Color.parse("OkLch(0.7, 0.15, 120)")
    L_e, _, _ = expected.to_oklab()
    L_g, _, _ = got.to_oklab()
    assert math.isclose(L_g, L_e, abs_tol=1e-9)


# --- Functional oklab(...) ------------------------------------------------- #


def test_parse_oklab_matches_factory():
    expected = Color.from_oklab(0.5, 0.05, 0.05)
    got = Color.parse("oklab(0.5, 0.05, 0.05)")
    L_e, a_e, b_e = expected.to_oklab()
    L_g, a_g, b_g = got.to_oklab()
    assert math.isclose(L_g, L_e, abs_tol=1e-9)
    assert math.isclose(a_g, a_e, abs_tol=1e-9)
    assert math.isclose(b_g, b_e, abs_tol=1e-9)


# --- Palette name fallback ------------------------------------------------- #


def test_parse_palette_name_oc():
    expected = Color.from_name("oc.red5")
    assert Color.parse("oc.red5").to_hex() == expected.to_hex()


def test_parse_palette_name_tw():
    expected = Color.from_name("tw.blue500")
    assert Color.parse("tw.blue500").to_hex() == expected.to_hex()


def test_parse_palette_name_matplotlib_basic():
    expected = Color.from_name("red")
    assert Color.parse("red").to_hex() == expected.to_hex()


# --- Errors ---------------------------------------------------------------- #


def test_parse_rejects_non_string():
    with pytest.raises(TypeError):
        Color.parse(0xFF0000)  # type: ignore[arg-type]


def test_parse_unknown_palette_name_raises():
    with pytest.raises(ValueError):
        Color.parse("definitely-not-a-color-name-xyz")


def test_parse_unknown_function_falls_through_and_raises():
    """Unknown leading function name is treated as a palette name and fails."""
    with pytest.raises(ValueError):
        Color.parse("hsv(0, 1, 1)")


def test_parse_rgb_non_numeric_args_raises():
    with pytest.raises(ValueError):
        Color.parse("rgb(red, 0, 0)")


# --------------------------------------------------------------------------- #
# Module-level color() — thin wrapper over Color.parse                        #
# --------------------------------------------------------------------------- #


from dartwork_mpl._colors import color  # noqa: E402  (intentional late import)


def test_color_passthrough_copies_instance():
    # Mirrors ``Length(other_length)``: a fresh instance with the same
    # canonical store, not identity passthrough.
    c = Color.from_hex("#ff0000")
    copied = color(c)
    assert copied is not c
    assert copied.to_hex() == c.to_hex()
    assert copied.to_oklab() == c.to_oklab()


def test_color_string_delegates_to_parse():
    expected = Color.parse("oc.red5")
    assert color("oc.red5").to_hex() == expected.to_hex()


def test_color_hex_via_module_function():
    assert color("#00ff00").to_hex() == "#00ff00"


def test_color_rejects_non_str_non_color():
    with pytest.raises(TypeError):
        color(123)  # type: ignore[arg-type]


def test_color_rejects_none():
    with pytest.raises(TypeError):
        color(None)  # type: ignore[arg-type]


def test_color_is_exported_at_top_level():
    import dartwork_mpl as dm

    assert dm.color is color
    assert dm.color("#ff0000").to_hex() == "#ff0000"


# --------------------------------------------------------------------------- #
# Color(value) — string-parser constructor (mirrors Length(value))
# --------------------------------------------------------------------------- #


def test_color_init_accepts_hex_string():
    assert Color("#ff0000").to_hex() == "#ff0000"


def test_color_init_accepts_functional_rgb():
    assert Color("rgb(1, 0, 0)").to_hex() == "#ff0000"


def test_color_init_accepts_functional_oklch():
    expected = Color.from_oklch(0.7, 0.15, 30)
    assert Color("oklch(0.7, 0.15, 30)").to_hex() == expected.to_hex()


def test_color_init_accepts_palette_name():
    assert Color("oc.red5").to_hex() == Color.from_name("oc.red5").to_hex()


def test_color_init_accepts_color_instance_as_copy():
    src = Color.from_oklab(0.7, 0.1, 0.2)
    dup = Color(src)
    assert dup is not src
    assert dup.to_oklab() == src.to_oklab()


def test_color_init_rejects_bare_float():
    with pytest.raises(TypeError, match="from_oklab"):
        Color(0.5)  # type: ignore[arg-type]


def test_color_init_rejects_bare_int():
    with pytest.raises(TypeError, match="from_oklab"):
        Color(1)  # type: ignore[arg-type]


def test_color_init_rejects_bool():
    # ``bool`` is an ``int`` subclass — make sure it's trapped too.
    with pytest.raises(TypeError, match="from_oklab"):
        Color(True)  # type: ignore[arg-type]


def test_color_init_rejects_three_floats():
    # The historical OKLab-coordinate constructor is gone — three-arg
    # callers must migrate to Color.from_oklab.
    with pytest.raises(TypeError):
        Color(0.5, 0.1, 0.2)  # type: ignore[call-arg]


def test_color_init_rejects_none():
    with pytest.raises(TypeError):
        Color(None)  # type: ignore[arg-type]


def test_color_init_rejects_tuple():
    with pytest.raises(TypeError):
        Color((0.5, 0.1, 0.2))  # type: ignore[arg-type]
