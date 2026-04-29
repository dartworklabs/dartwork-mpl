"""Tests for dartwork_mpl.units (free-form width parsing)."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl.units import cm, inch, mm, parse_aspect, parse_width


class TestUnitConverters:
    def test_cm_returns_inches(self):
        assert math.isclose(cm(2.54), 1.0, rel_tol=1e-6)

    def test_inch_is_identity(self):
        assert math.isclose(inch(3.5), 3.5, rel_tol=1e-12)

    def test_mm_returns_inches(self):
        assert math.isclose(mm(25.4), 1.0, rel_tol=1e-6)


class TestParseWidth:
    @pytest.mark.parametrize(
        "value,expected_in",
        [
            ("9cm", 9 / 2.54),
            ("9.5cm", 9.5 / 2.54),
            ("17 cm", 17 / 2.54),
            ("6.7in", 6.7),
            ('"6.7in"', 6.7),  # stripped quotes
            ("170mm", 170 / 25.4),
            (13, 13 / 2.54),  # raw int → cm
            (9.0, 9.0 / 2.54),  # raw float → cm
        ],
    )
    def test_accepts_string_and_numeric(self, value, expected_in):
        assert math.isclose(parse_width(value), expected_in, rel_tol=1e-9)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="positive"):
            parse_width("-5cm")

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="positive"):
            parse_width(0)

    def test_rejects_unknown_unit(self):
        with pytest.raises(ValueError, match="unit"):
            parse_width("3foot")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            parse_width("abc")

    def test_rejects_nan(self):
        with pytest.raises(ValueError, match="finite"):
            parse_width(float("nan"))

    def test_rejects_inf(self):
        with pytest.raises(ValueError, match="finite"):
            parse_width(float("inf"))

    def test_accepts_scientific_notation(self):
        # 1e-1 cm = 0.1 cm = 0.1/2.54 inches
        assert math.isclose(parse_width("1e-1cm"), 0.1 / 2.54, rel_tol=1e-9)
        # 5e0 in = 5 inches
        assert math.isclose(parse_width("5e0in"), 5.0, rel_tol=1e-9)


class TestInchesArithmetic:
    """0.4 contract: arithmetic preserves the Inches tag so a doubled
    or summed Inches value is not silently re-interpreted as cm by
    parse_width."""

    def test_mul_preserves_inches(self):
        from dartwork_mpl.units import Inches

        v = cm(9) * 2
        assert isinstance(v, Inches)
        assert math.isclose(v, 18 / 2.54, rel_tol=1e-9)

    def test_rmul_preserves_inches(self):
        from dartwork_mpl.units import Inches

        v = 2 * cm(9)
        assert isinstance(v, Inches)

    def test_add_preserves_inches(self):
        from dartwork_mpl.units import Inches

        assert isinstance(cm(3) + cm(4), Inches)

    def test_sub_preserves_inches(self):
        from dartwork_mpl.units import Inches

        assert isinstance(cm(9) - cm(2), Inches)

    def test_div_preserves_inches(self):
        from dartwork_mpl.units import Inches

        assert isinstance(cm(9) / 2, Inches)

    def test_neg_preserves_inches(self):
        from dartwork_mpl.units import Inches

        assert isinstance(-cm(9), Inches)

    def test_parse_width_passes_through_inches_arithmetic(self):
        # The whole point: dm.cm(9) * 2 → 18 cm-equivalent in inches,
        # NOT re-interpreted as 7.087 cm.
        v = cm(9) * 2
        assert math.isclose(parse_width(v), 18 / 2.54, rel_tol=1e-9)


class TestParseAspect:
    @pytest.mark.parametrize(
        "name,ratio",
        [
            ("square", 1.0),
            ("portrait", 5 / 4),  # h/w
            ("standard", 3 / 4),
            ("golden", 1 / 1.618),
            ("wide", 2 / 3),
            ("cinema", 1 / 2),
        ],
    )
    def test_known_tokens(self, name, ratio):
        assert math.isclose(parse_aspect(name), ratio, rel_tol=1e-6)

    def test_numeric_passthrough(self):
        assert parse_aspect(0.5) == 0.5
        assert parse_aspect(1) == 1.0

    def test_rejects_unknown_token(self):
        with pytest.raises(ValueError, match="aspect"):
            parse_aspect("ultra")

    def test_rejects_non_positive(self):
        with pytest.raises(ValueError, match="positive"):
            parse_aspect(-0.5)
        with pytest.raises(ValueError, match="positive"):
            parse_aspect(0)


class TestPublicSurface:
    def test_cm_inch_mm_exposed_at_top_level(self):
        import dartwork_mpl as dm

        assert callable(dm.cm)
        assert callable(dm.inch)
        assert callable(dm.mm)
        assert math.isclose(dm.cm(2.54), 1.0, rel_tol=1e-6)

    def test_col1_and_col2_are_constants(self):
        import dartwork_mpl as dm

        # 9 cm and 17 cm in inches.
        assert math.isclose(dm.col1, 9 / 2.54, rel_tol=1e-9)
        assert math.isclose(dm.col2, 17 / 2.54, rel_tol=1e-9)
