"""``dm.figsize``, the units, ``dm.grid_shape`` and ``dm.figsize_for`` as users call them."""

from __future__ import annotations

import pytest

import dartwork_mpl as dm

CM = 2.54


def _cm(size: tuple[float, float]) -> tuple[float, float]:
    return (round(size[0] * CM, 2), round(size[1] * CM, 2))


class TestFigsize:
    """A physical width and an aspect, a ratio or a height, to inches."""

    @pytest.mark.parametrize(
        ("aspect", "height_cm"),
        [
            ("standard", 9.75),
            ("WIDE", 8.67),
            (" 'square' ", 13.0),
            ("16:9", 7.31),
            ("2:1", 6.5),
            (0.5, 6.5),
            (1, 13.0),
            ("8cm", 8.0),
            ("80mm", 8.0),
            (dm.cm(8), 8.0),
        ],
    )
    def test_second_argument_forms(
        self, aspect: object, height_cm: float
    ) -> None:
        assert _cm(dm.figsize("13cm", aspect)) == (13.0, height_cm)

    def test_listed_aspects_are_the_tokens_figsize_reads(self) -> None:
        listed = dm.list_aspects()
        for aspect in listed:
            assert dm.figsize("13cm", aspect["name"]) == dm.figsize(
                "13cm", aspect["ratio"]
            )
        with pytest.raises(ValueError) as unknown:
            dm.figsize("13cm", "nope")
        assert all(repr(a["name"]) in str(unknown.value) for a in listed)

    @pytest.mark.parametrize("width", ["13cm", "130mm", dm.cm(13), " 13 cm "])
    def test_width_forms_agree(self, width: object) -> None:
        assert dm.figsize(width) == pytest.approx(dm.figsize("13cm"))

    def test_returns_plain_floats_matplotlib_accepts(self) -> None:
        w, h = dm.figsize("15cm", "10cm")
        assert type(w) is float and type(h) is float
        assert dm.figsize(dm.col1) == pytest.approx((9 / CM, 6.75 / CM))

    @pytest.mark.parametrize("width", [13, 13.0, True])
    def test_a_bare_number_has_no_unit(self, width: object) -> None:
        with pytest.raises(TypeError, match=r"dm\.cm\(13\)"):
            dm.figsize(width)

    @pytest.mark.parametrize(
        ("width", "hint"),
        [
            ("13", "has no unit"),
            ("13centi", "Did you mean 'cm'"),
            ("5 inches", "Did you mean 'in'"),
            ("1920px", "DPI"),
            ("13furlongs", "Supported units"),
            ("-3cm", "positive"),
        ],
    )
    def test_a_bad_width_says_how_to_fix_it(
        self, width: str, hint: str
    ) -> None:
        with pytest.raises(ValueError, match=hint):
            dm.figsize(width)

    @pytest.mark.parametrize(
        ("aspect", "hint"),
        [
            ("widee", "Did you mean 'wide'"),
            ("0.5", "drop the quotes"),
            ("1080px", "DPI"),
            ("16:", "width:height"),
            ("0:9", "two positive numbers"),
            (0, "positive"),
            (True, "bool"),
        ],
    )
    def test_a_bad_aspect_says_how_to_fix_it(
        self, aspect: object, hint: str
    ) -> None:
        with pytest.raises(ValueError, match=hint):
            dm.figsize("9cm", aspect)


class TestLength:
    """A positive length that never passes for a bare float."""

    def test_unit_views(self) -> None:
        length = dm.cm(2.54)
        assert length.inch == pytest.approx(1.0)
        assert (length.cm, length.mm, length.pt) == pytest.approx(
            (2.54, 25.4, 72.0)
        )
        assert dm.inch(1) == dm.Length(inch=1.0)
        assert dm.mm(10).cm == pytest.approx(1.0)
        assert dm.pt(72).inch == pytest.approx(1.0)

    def test_columns(self) -> None:
        assert (dm.col1.cm, dm.col2.cm) == pytest.approx((9.0, 17.0))
        assert dm.col1 < dm.col2

    def test_parse_reads_unit_strings(self) -> None:
        assert dm.Length.parse("1in") == dm.inch(1)
        assert dm.Length.parse(dm.col1) is dm.col1

    @pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
    def test_rejects_non_positive(self, value: float) -> None:
        with pytest.raises(ValueError, match="positive and finite"):
            dm.cm(value)

    @pytest.mark.parametrize("value", [True, "3"])
    def test_rejects_non_numbers(self, value: object) -> None:
        with pytest.raises(TypeError, match="must be int or float"):
            dm.cm(value)  # type: ignore[arg-type]

    def test_needs_a_named_unit(self) -> None:
        with pytest.raises(TypeError):
            dm.Length(5.0)  # type: ignore[misc]


class TestFigsizeFor:
    """The active preset's canvas, the same for the same request."""

    @pytest.mark.parametrize(
        ("preset", "expected"),
        [
            ("report", (12.0, 9.0)),
            ("report-kr", (12.0, 9.0)),
            ("web", (12.0, 9.0)),
            ("scientific", (9.0, 6.75)),
            ("presentation", (23.4, 10.5)),
            ("presentation-kr", (23.4, 10.5)),
            ("poster", (18.0, 13.5)),
        ],
    )
    def test_each_preset_maps_onto_its_page(
        self, preset: str, expected: tuple[float, float]
    ) -> None:
        dm.style.use(preset)
        assert _cm(dm.figsize_for()) == expected

    def test_a_font_override_does_not_resize_the_slide(self) -> None:
        dm.style.use("presentation", font_size=14)
        assert _cm(dm.figsize_for()) == (23.4, 10.5)

    def test_context_restores_the_outer_preset(self) -> None:
        dm.style.use("report")
        with dm.style.context("scientific"):
            assert _cm(dm.figsize_for(n_points=20, n_series=1))[0] == 9.0
        assert _cm(dm.figsize_for(n_points=20, n_series=1))[0] == 14.5

    @pytest.mark.parametrize("preset", ["report", "presentation", "poster"])
    def test_slide_kinds_are_the_same_everywhere(self, preset: str) -> None:
        dm.style.use(preset)
        assert _cm(dm.figsize_for("slide")) == (23.4, 10.5)
        assert _cm(dm.figsize_for("full_slide")) == (25.4, 14.29)

    def test_unknown_kind_lists_the_kinds(self) -> None:
        with pytest.raises(ValueError, match="barh"):
            dm.figsize_for("line")

    @pytest.mark.parametrize(
        "kwargs",
        [{"nrows": 0}, {"ncols": 0}, {"n_points": -1}, {"n_series": -2}],
    )
    def test_counts_below_minimum(self, kwargs: dict[str, int]) -> None:
        with pytest.raises(ValueError, match="must be >="):
            dm.figsize_for(**kwargs)  # type: ignore[arg-type]

    @pytest.mark.parametrize("value", [2.0, True, "3"])
    def test_counts_must_be_int(self, value: object) -> None:
        with pytest.raises(TypeError, match="must be an int"):
            dm.figsize_for(n_points=value)  # type: ignore[arg-type]

    @pytest.mark.parametrize("labels", ["abc", {"a", "b"}, {"a": 1}, 5])
    def test_labels_need_an_axis_order(self, labels: object) -> None:
        with pytest.raises(TypeError, match="labels must be"):
            dm.figsize_for(labels=labels)
