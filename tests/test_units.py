"""Tests for dartwork_mpl.units (free-form width parsing)."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl.units import cm, figsize, inch, mm, parse_aspect, parse_width


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
        ],
    )
    def test_accepts_unit_strings(self, value, expected_in):
        assert math.isclose(parse_width(value), expected_in, rel_tol=1e-9)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="positive"):
            parse_width("-5cm")

    def test_rejects_zero_string(self):
        with pytest.raises(ValueError, match="positive"):
            parse_width("0cm")

    def test_rejects_unknown_unit(self):
        with pytest.raises(ValueError, match="unit"):
            parse_width("3foot")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError):
            parse_width("abc")

    def test_rejects_nan_string(self):
        # NaN/inf should never reach the finite check via a unit string,
        # but if a caller constructs ``"nancm"`` we still want a clean
        # error rather than a silent pass.
        with pytest.raises(ValueError):
            parse_width("nan")

    def test_accepts_scientific_notation(self):
        # 1e-1 cm = 0.1 cm = 0.1/2.54 inches
        assert math.isclose(parse_width("1e-1cm"), 0.1 / 2.54, rel_tol=1e-9)
        # 5e0 in = 5 inches
        assert math.isclose(parse_width("5e0in"), 5.0, rel_tol=1e-9)


class TestParseWidthRawNumberRejection:
    """Bare ``int``/``float`` carry no unit. Reject with TypeError so a
    raw ``dm.figsize(13)`` call cannot survive (earlier dartwork-mpl
    silently re-interpreted such widths as cm)."""

    @pytest.mark.parametrize(
        "value", [13, 9.0, 1, 0, -3, float("nan"), float("inf")]
    )
    def test_rejects_int_and_float(self, value):
        with pytest.raises(TypeError, match="bare numbers carry no unit"):
            parse_width(value)

    def test_error_message_names_both_escape_hatches(self):
        with pytest.raises(TypeError) as exc:
            parse_width(13)
        message = str(exc.value)
        assert "'13cm'" in message
        assert "dm.cm(13)" in message

    def test_rejects_bool(self):
        with pytest.raises(TypeError, match="bare numbers carry no unit"):
            parse_width(True)
        with pytest.raises(TypeError, match="bare numbers carry no unit"):
            parse_width(False)


class TestParseWidthSelfCorrection:
    """T3: error messages should let an LLM retry on the next call."""

    def test_typo_centi_suggests_cm(self):
        with pytest.raises(ValueError) as exc:
            parse_width("20centi")
        message = str(exc.value)
        assert "20" in message
        assert "'cm'" in message
        assert "20cm" in message

    def test_unit_word_misspelt_in_suggests_in(self):
        with pytest.raises(ValueError) as exc:
            parse_width("6inh")
        message = str(exc.value)
        # 'inh' is a 1-edit typo of 'in' — difflib should recover.
        assert "'in'" in message and "6in" in message

    def test_alien_unit_falls_back_to_supported_list(self):
        # 'foot' shares no letters with cm/in/mm above the cutoff, so
        # the suggestion falls back to the supported-units sentence.
        with pytest.raises(ValueError) as exc:
            parse_width("3foot")
        message = str(exc.value)
        assert "Supported units" in message
        assert "'foot'" in message

    def test_pure_letters_get_format_hint(self):
        # No digit-letter mix → fall through to the format reminder.
        with pytest.raises(ValueError) as exc:
            parse_width("abc")
        message = str(exc.value)
        assert "Supported units" in message or "<number>cm" in message


class TestParseAspectSelfCorrection:
    """T3: misspelt or numerically-quoted aspects should self-explain."""

    def test_misspelt_widee_suggests_wide(self):
        with pytest.raises(ValueError) as exc:
            parse_aspect("widee")
        assert "'wide'" in str(exc.value)

    def test_misspelt_sqaure_suggests_square(self):
        with pytest.raises(ValueError) as exc:
            parse_aspect("sqaure")
        assert "'square'" in str(exc.value)

    def test_quoted_numeric_suggests_dropping_quotes(self):
        with pytest.raises(ValueError) as exc:
            parse_aspect("0.75")
        message = str(exc.value)
        assert "drop the quotes" in message
        assert "0.75" in message

    def test_random_string_has_no_misleading_suggestion(self):
        # ``"abc"`` is far from every aspect token; no "did you mean".
        with pytest.raises(ValueError) as exc:
            parse_aspect("abc")
        message = str(exc.value)
        assert "Did you mean" not in message


class TestInchesArithmetic:
    """Inches arithmetic must preserve the Inches tag so that doubled
    or summed widths still pass the ``isinstance(value, Inches)`` gate
    in ``parse_width`` (raw floats are now rejected)."""

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

    def test_inches_resists_numpy_ufunc(self):
        """Without ``__array_ufunc__ = None``, ``np.float64(2) * cm(9)``
        would route through numpy's multiply ufunc, returning a bare
        ``np.float64`` and silently losing the ``Inches`` tag — which
        ``parse_width`` would then reject outright as a unit-less raw
        number. Opting out of ufunc dispatch makes numpy fall back to
        ``Inches.__rmul__`` so the tag is preserved and the round-trip
        stays valid.
        """
        import numpy as np

        from dartwork_mpl.units import Inches

        v = np.float64(2) * cm(9)
        assert isinstance(v, Inches)
        assert math.isclose(v, 18 / 2.54, rel_tol=1e-9)
        # Round-trip still parses (would TypeError if the tag were lost).
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

    def test_rejects_bool_with_clear_message(self):
        """`bool` is an int subclass; the message must say so explicitly
        rather than silently accepting True/False as 1.0/0.0."""
        with pytest.raises(ValueError, match="bool is not accepted"):
            parse_aspect(True)
        with pytest.raises(ValueError, match="bool is not accepted"):
            parse_aspect(False)


class TestFigsize:
    """``dm.figsize(width, aspect)`` returns ``(w_in, h_in)`` for direct
    use in ``plt.subplots(figsize=...)``."""

    def test_returns_inch_tuple_for_unit_string(self):
        w, h = figsize("13cm", "wide")
        # 13 cm = 5.118 in, wide = 2/3
        assert math.isclose(w, 13 / 2.54, rel_tol=1e-9)
        assert math.isclose(h, w * (2 / 3), rel_tol=1e-9)

    def test_accepts_inches_value(self):
        from dartwork_mpl.units import Inches

        w, h = figsize(cm(9), "square")
        assert math.isclose(w, 9 / 2.54, rel_tol=1e-9)
        assert math.isclose(h, w, rel_tol=1e-9)
        assert isinstance(w, float)
        # Inches arithmetic stays Inches, but the tuple components are
        # plain floats (matplotlib's contract).
        assert not isinstance(figsize(Inches(5.0))[0], Inches)

    def test_default_aspect_is_standard(self):
        w, h = figsize("10cm")
        assert math.isclose(h / w, 3 / 4, rel_tol=1e-6)

    def test_accepts_float_aspect(self):
        w, h = figsize("10cm", 0.5)
        assert math.isclose(h / w, 0.5, rel_tol=1e-9)

    def test_rejects_raw_number_width(self):
        with pytest.raises(TypeError, match="bare numbers carry no unit"):
            figsize(13, "wide")

    def test_pairs_with_col1(self):
        import dartwork_mpl as dm

        w, h = figsize(dm.col1, "standard")
        assert math.isclose(w, 9 / 2.54, rel_tol=1e-9)


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

    def test_figsize_exposed_at_top_level(self):
        import dartwork_mpl as dm

        assert callable(dm.figsize)
        w, h = dm.figsize("13cm", "wide")
        assert math.isclose(w, 13 / 2.54, rel_tol=1e-9)
