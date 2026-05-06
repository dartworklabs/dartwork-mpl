"""Tests for dartwork_mpl.units (Length class + parsers)."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl.units import (
    Length,
    cm,
    figsize,
    inch,
    length,
    mm,
    parse_aspect,
    parse_width,
    pt,
)


class TestUnitConstructors:
    """Top-level wrappers ``cm``/``inch``/``mm``/``pt`` return ``Length``;
    ``Length.from_<unit>`` classmethods produce identical values."""

    def test_cm_returns_length(self):
        v = cm(2.54)
        assert isinstance(v, Length)
        assert math.isclose(v.inch, 1.0, rel_tol=1e-6)

    def test_inch_is_identity(self):
        v = inch(3.5)
        assert isinstance(v, Length)
        assert math.isclose(v.inch, 3.5, rel_tol=1e-12)

    def test_mm_returns_length(self):
        v = mm(25.4)
        assert isinstance(v, Length)
        assert math.isclose(v.inch, 1.0, rel_tol=1e-6)

    def test_pt_returns_length(self):
        v = pt(72)
        assert isinstance(v, Length)
        assert math.isclose(v.inch, 1.0, rel_tol=1e-12)

    def test_classmethods_match_wrappers(self):
        assert Length.from_cm(13).inch == cm(13).inch
        assert Length.from_mm(170).inch == mm(170).inch
        assert Length.from_inch(5).inch == inch(5).inch
        assert Length.from_pt(72).inch == pt(72).inch


class TestLengthInit:
    """``Length(value)`` accepts unit strings and other ``Length`` values
    only — bare numbers are rejected to preserve the cm/inch guard."""

    def test_str_init_parses_cm(self):
        assert math.isclose(Length("13cm").inch, 13 / 2.54, rel_tol=1e-9)

    def test_str_init_parses_inch(self):
        assert math.isclose(Length("5in").inch, 5.0, rel_tol=1e-12)

    def test_str_init_parses_mm(self):
        assert math.isclose(Length("170mm").inch, 170 / 25.4, rel_tol=1e-9)

    def test_str_init_parses_pt(self):
        assert math.isclose(Length("72pt").inch, 1.0, rel_tol=1e-12)

    def test_str_init_default_unit_is_cm(self):
        # Bare numeric strings are interpreted as cm, matching parse_width.
        assert math.isclose(Length("13").inch, 13 / 2.54, rel_tol=1e-9)

    def test_length_init_passes_through(self):
        original = cm(9)
        copy = Length(original)
        assert copy.inch == original.inch
        assert copy is not original  # new instance

    def test_top_level_length_wrapper_parses(self):
        assert math.isclose(length("13cm").inch, 13 / 2.54, rel_tol=1e-9)

    @pytest.mark.parametrize("value", [13, 9.0, 0, -3, True, False])
    def test_rejects_bare_numbers(self, value):
        with pytest.raises(TypeError, match="bare numbers carry no unit"):
            Length(value)

    def test_rejects_non_string_non_length(self):
        with pytest.raises(TypeError):
            Length([13])  # type: ignore[arg-type]

    def test_rejects_negative_string(self):
        with pytest.raises(ValueError, match="positive"):
            Length("-5cm")

    def test_rejects_zero_string(self):
        with pytest.raises(ValueError, match="positive"):
            Length("0cm")


class TestLengthViews:
    """``length.cm`` / ``.mm`` / ``.inch`` / ``.pt`` properties."""

    def test_cm_view(self):
        assert math.isclose(cm(13).cm, 13.0, rel_tol=1e-9)

    def test_mm_view(self):
        assert math.isclose(cm(13).mm, 130.0, rel_tol=1e-9)

    def test_inch_view(self):
        assert math.isclose(cm(2.54).inch, 1.0, rel_tol=1e-9)

    def test_pt_view(self):
        # 1 inch = 72 pt
        assert math.isclose(inch(1).pt, 72.0, rel_tol=1e-12)

    def test_round_trip_through_views(self):
        v = cm(13)
        assert math.isclose(Length.from_mm(v.mm).inch, v.inch, rel_tol=1e-12)
        assert math.isclose(Length.from_pt(v.pt).inch, v.inch, rel_tol=1e-12)


class TestLengthRepr:
    def test_repr_uses_inches_for_large(self):
        assert "in" in repr(inch(5))

    def test_repr_uses_cm_for_small(self):
        # 5 mm < 1 in → repr in cm
        assert "cm" in repr(mm(5))


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
            ("72pt", 1.0),
        ],
    )
    def test_accepts_unit_strings(self, value, expected_in):
        assert math.isclose(parse_width(value), expected_in, rel_tol=1e-9)

    def test_accepts_length(self):
        assert math.isclose(parse_width(cm(9)), 9 / 2.54, rel_tol=1e-9)

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

    def test_error_message_says_length_not_inches(self):
        # ``parse_width`` 메시지가 "Length value"를 안내해야 한다 —
        # ``Inches`` 언급은 0.4 in-flight 이름이라 사라져야 한다.
        with pytest.raises(TypeError) as exc:
            parse_width(13)
        message = str(exc.value)
        assert "Length value" in message
        assert "Inches" not in message

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

    def test_typo_points_suggests_pt(self):
        # 새 pt 단위에도 동일한 self-correction이 동작해야 한다.
        with pytest.raises(ValueError) as exc:
            parse_width("24points")
        message = str(exc.value)
        assert "'pt'" in message and "24pt" in message

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

    def test_accepts_length_value(self):
        w, h = figsize(cm(9), "square")
        assert math.isclose(w, 9 / 2.54, rel_tol=1e-9)
        assert math.isclose(h, w, rel_tol=1e-9)
        # Tuple components are plain floats (matplotlib's contract).
        assert isinstance(w, float)
        assert not isinstance(w, Length)

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
    def test_unit_constructors_exposed_at_top_level(self):
        import dartwork_mpl as dm

        assert callable(dm.cm)
        assert callable(dm.inch)
        assert callable(dm.mm)
        assert callable(dm.pt)
        assert callable(dm.length)
        assert math.isclose(dm.cm(2.54).inch, 1.0, rel_tol=1e-6)

    def test_col1_and_col2_are_length_instances(self):
        import dartwork_mpl as dm

        assert isinstance(dm.col1, Length)
        assert isinstance(dm.col2, Length)
        # 9 cm and 17 cm via the cm view.
        assert math.isclose(dm.col1.cm, 9.0, rel_tol=1e-9)
        assert math.isclose(dm.col2.cm, 17.0, rel_tol=1e-9)

    def test_figsize_exposed_at_top_level(self):
        import dartwork_mpl as dm

        assert callable(dm.figsize)
        w, h = dm.figsize("13cm", "wide")
        assert math.isclose(w, 13 / 2.54, rel_tol=1e-9)

    def test_length_class_exposed_at_top_level(self):
        import dartwork_mpl as dm

        assert dm.Length is Length

    def test_inches_no_longer_importable(self):
        import dartwork_mpl as dm

        # ``Inches`` was the in-flight 0.4 name. Hard-removed alongside
        # the rename — accessing it now raises AttributeError, matching
        # the precedent set by ``dm.subplots`` / ``dm.figure`` (#147).
        with pytest.raises(AttributeError):
            dm.Inches  # noqa: B018


class TestLengthArithmetic:
    """Arithmetic preserves the Length tag so doubled/summed values
    still pass parse_width's gate (raw floats are rejected)."""

    def test_mul_scalar_preserves_length(self):
        v = cm(9) * 2
        assert isinstance(v, Length)
        assert math.isclose(v.cm, 18.0, rel_tol=1e-9)

    def test_rmul_scalar_preserves_length(self):
        v = 2 * cm(9)
        assert isinstance(v, Length)
        assert math.isclose(v.cm, 18.0, rel_tol=1e-9)

    def test_mul_two_lengths_rejected(self):
        # ``Length * Length`` (area) has no representation at this layer.
        with pytest.raises(TypeError):
            cm(3) * cm(4)  # type: ignore[operator]

    def test_add_two_lengths(self):
        v = cm(3) + cm(4)
        assert isinstance(v, Length)
        assert math.isclose(v.cm, 7.0, rel_tol=1e-9)

    def test_add_length_and_scalar_preserves_tag(self):
        # ``+`` / ``-`` are lax — they accept any numeric operand and
        # preserve the Length tag. The cm/inch guard lives at the
        # parser boundary (``parse_width`` / ``Length(...)``), not on
        # every arithmetic op against an already-typed Length. This
        # also lets matplotlib internals do ``0 + width`` to compute
        # bbox extents without a doc-wide migration.
        v = cm(3) + 1  # 1 inch
        assert isinstance(v, Length)
        assert math.isclose(v.inch, 3 / 2.54 + 1, rel_tol=1e-9)

        v2 = 1 + cm(3)
        assert isinstance(v2, Length)

    def test_sub_two_lengths(self):
        v = cm(9) - cm(2)
        assert isinstance(v, Length)
        assert math.isclose(v.cm, 7.0, rel_tol=1e-9)

    def test_sub_length_and_scalar_preserves_tag(self):
        v = inch(3) - 1
        assert isinstance(v, Length)
        assert math.isclose(v.inch, 2.0, rel_tol=1e-9)

    def test_div_by_scalar_preserves_length(self):
        v = cm(9) / 2
        assert isinstance(v, Length)
        assert math.isclose(v.cm, 4.5, rel_tol=1e-9)

    def test_div_by_length_returns_dimensionless_ratio(self):
        ratio = cm(9) / cm(3)
        assert isinstance(ratio, float)
        assert not isinstance(ratio, Length)
        assert math.isclose(ratio, 3.0, rel_tol=1e-9)

    def test_neg_preserves_length(self):
        assert isinstance(-cm(9), Length)

    def test_abs_preserves_length(self):
        assert isinstance(abs(-cm(9)), Length)

    def test_parse_width_passes_through_arithmetic(self):
        # The whole point: dm.cm(9) * 2 → 18 cm-equivalent in inches,
        # NOT re-interpreted as 7.087 cm.
        v = cm(9) * 2
        assert math.isclose(parse_width(v), 18 / 2.54, rel_tol=1e-9)


class TestLengthComparison:
    """Comparison and hashing inherit from ``float`` — equal canonical
    inch values compare equal regardless of which constructor produced
    them. This matches the previous ``Inches(float)`` behaviour and
    is consistent with ``Length`` being a ``float`` subclass."""

    def test_equality_across_units(self):
        # 1 inch == 2.54 cm
        assert cm(2.54) == inch(1)

    def test_inequality(self):
        assert cm(1) != cm(2)

    def test_ordering(self):
        assert cm(1) < cm(2)
        assert cm(2) > cm(1)
        assert cm(1) <= cm(1)
        assert cm(1) >= cm(1)

    def test_hashable_consistent_with_equality(self):
        # Hash agrees with ``__eq__`` (inherited from float): equal
        # canonical inch values → equal hashes.
        assert hash(cm(2.54)) == hash(inch(1))

    def test_usable_as_dict_key(self):
        d = {cm(1): "one", cm(2): "two"}
        assert d[cm(1)] == "one"
        assert d[cm(2)] == "two"


class TestLengthFloatInterop:
    """``Length`` is a ``float`` subclass so matplotlib accepts
    ``Length`` tuples in ``figsize=`` natively. The Color-style
    multi-unit views and str init layered on top do **not** make the
    class opaque — ``isinstance(length, float)`` is True so numpy
    coercion paths (``np.isfinite(figsize)``, ``np.array(figsize) <
    0`` inside ``Figure.__init__``) work without further interop.
    """

    def test_float_yields_inch_value(self):
        assert float(cm(2.54)) == pytest.approx(1.0)
        assert float(inch(5)) == pytest.approx(5.0)

    def test_length_is_float_subclass(self):
        # Pragmatic interop choice: Length is a float subclass so
        # matplotlib's bare ``np.isfinite(figsize)`` path works on
        # tuples of Length. The "Color-pattern" requirement is met
        # at the *interface* layer (multi-unit views + str init),
        # not by structural opacity.
        assert isinstance(cm(1), float)

    def test_figsize_tuple_through_matplotlib(self):
        from matplotlib.figure import Figure

        # The win that justifies the float-subclass choice: existing
        # ``figsize=(dm.cm(15), dm.cm(9))`` call sites in docs and
        # gallery code keep working without a sweeping migration.
        # Use ``Figure`` directly rather than ``plt.figure`` so the
        # interactive backend doesn't quantize the size for display.
        fig = Figure(figsize=(cm(15), cm(9)))
        w, h = fig.get_size_inches()
        assert math.isclose(float(w), 15 / 2.54, rel_tol=1e-9)
        assert math.isclose(float(h), 9 / 2.54, rel_tol=1e-9)

    def test_numpy_ufunc_preserves_length_tag(self):
        """``np.float64(2) * cm(9)`` would normally route through
        numpy's multiply ufunc and return a bare ``np.float64``,
        dropping the Length tag and re-opening the cm/inch hole at
        array boundaries. ``__array_ufunc__ = None`` on Length forces
        numpy to fall back to ``Length.__rmul__`` so the tag is
        preserved."""
        import numpy as np

        v = np.float64(2) * cm(9)
        assert isinstance(v, Length)
        assert math.isclose(v.cm, 18.0, rel_tol=1e-9)
        # Round-trip still parses (would TypeError if the tag were lost).
        assert math.isclose(parse_width(v), 18 / 2.54, rel_tol=1e-9)
