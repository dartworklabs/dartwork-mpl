"""The preset's default canvas: same request, same size, whoever asks.

``dm.figsize_for`` replaces a size an agent would otherwise pick by habit
(measured 2026-10-22: two hosts chose the same canvas for 15 of 40 requests).
The widths are the report tiers 9 / 12 / 14.5 / 17 cm; ``dm.grid_shape``
lays out small multiples the same way every time.
"""

from __future__ import annotations

import pytest

import dartwork_mpl as dm

CM = 2.54


def _cm(size: tuple[float, float]) -> tuple[float, float]:
    return (round(size[0] * CM, 2), round(size[1] * CM, 2))


@pytest.fixture(autouse=True)
def _report() -> None:
    dm.style.use("report")


class TestReportTiers:
    """Kind and density hints pick one of the four report widths."""

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({}, (12.0, 9.0)),
            ({"n_points": 8, "n_series": 3}, (12.0, 9.0)),
            ({"n_points": 5, "n_series": 2}, (9.0, 6.75)),
            ({"n_points": 5, "n_series": 2, "dual_axis": True}, (14.5, 10.88)),
            ({"n_points": 13, "n_series": 1}, (14.5, 10.88)),
            ({"n_points": 8, "n_series": 4}, (14.5, 10.88)),
            ({"kind": "barh", "n_points": 9, "n_series": 1}, (14.5, 10.88)),
            ({"kind": "compact"}, (9.0, 6.75)),
            ({"kind": "matrix", "n_points": 40}, (12.0, 12.0)),
            ({"kind": "dense", "n_points": 3, "n_series": 1}, (17.0, 8.5)),
            ({"kind": "strip"}, (17.0, 7.65)),
            ({"kind": "slide", "n_points": 3}, (23.4, 10.5)),
        ],
    )
    def test_width_tier(
        self, kwargs: dict[str, object], expected: tuple[float, float]
    ) -> None:
        assert _cm(dm.figsize_for(**kwargs)) == expected  # type: ignore[arg-type]

    def test_same_request_same_canvas(self) -> None:
        first = dm.figsize_for("barh", n_points=7, n_series=2)
        assert dm.figsize_for("barh", n_points=7, n_series=2) == first


class TestGrid:
    """Panel grids take the widest tier; panels keep the kind's aspect."""

    def test_two_by_three(self) -> None:
        assert _cm(dm.figsize_for(nrows=2, ncols=3)) == (17.0, 8.5)

    def test_one_by_two_ignores_hints(self) -> None:
        size = dm.figsize_for(nrows=1, ncols=2, n_points=3, n_series=1)
        assert _cm(size) == (17.0, 6.5)

    def test_tall_grid_is_capped(self) -> None:
        assert _cm(dm.figsize_for(nrows=4, ncols=1)) == (17.0, 24.0)


class TestPresets:
    """The active preset maps the tiers onto its page."""

    @pytest.mark.parametrize("preset", ["scientific", "scientific-kr"])
    def test_paper_uses_journal_columns(self, preset: str) -> None:
        dm.style.use(preset)
        assert _cm(dm.figsize_for()) == (9.0, 6.75)
        assert _cm(dm.figsize_for(n_points=20, n_series=2))[0] == 17.0
        assert _cm(dm.figsize_for(nrows=2, ncols=2))[0] == 17.0

    @pytest.mark.parametrize("preset", ["presentation", "presentation-kr"])
    @pytest.mark.parametrize(
        "kwargs",
        [
            {},
            {"n_points": 7},
            {"n_points": 36, "n_series": 2},
            {"n_points": 3, "n_series": 4},
            {"n_points": 3, "dual_axis": True},
            {"kind": "barh", "n_points": 3, "n_series": 1},
            {"kind": "dense"},
            {"kind": "slide"},
            {"nrows": 3, "ncols": 1},
        ],
    )
    def test_presentation_fills_the_slide_body(
        self, preset: str, kwargs: dict[str, object]
    ) -> None:
        # A 16:9 slide less its title band and margins: 2.8 cm title,
        # 1 cm margins. Measured 2026-10-25: "for slides" got 19 x 14.25 cm
        # from the density tiers or the whole 25.4 x 14.29 cm slide, both
        # taller than the room left under a slide title.
        dm.style.use(preset)
        assert _cm(dm.figsize_for(**kwargs)) == (23.4, 10.5)  # type: ignore[arg-type]

    @pytest.mark.parametrize("preset", ["presentation", "presentation-kr"])
    @pytest.mark.parametrize(
        ("n_points", "width"),
        [(1, 11.4), (4, 11.4), (5, 15.4), (6, 15.4), (7, 23.4), (12, 23.4)],
    )
    def test_presentation_width_follows_x_positions(
        self, preset: str, n_points: int, width: float
    ) -> None:
        # Decision 4-A (2026-11-03): at 18.2 pt slide ticks, six company
        # names overlapped 4 times at 11.4 cm (-8.6 pt) and had 9.2 pt to
        # spare at 15.4 cm; 12 month names overlapped 10 times at 15.4 cm.
        # The height stays 10.5 cm so text is the same size on every slide.
        dm.style.use(preset)
        got = _cm(dm.figsize_for(n_points=n_points, n_series=2))
        assert got == (width, 10.5)

    def test_presentation_half_and_square(self) -> None:
        dm.style.use("presentation")
        assert _cm(dm.figsize_for("compact")) == (11.4, 10.5)
        assert _cm(dm.figsize_for("matrix")) == (10.5, 10.5)

    def test_poster_scales_with_its_font(self) -> None:
        dm.style.use("poster")
        assert _cm(dm.figsize_for()) == (18.0, 13.5)
        assert _cm(dm.figsize_for(nrows=3, ncols=1)) == (25.5, 14.5)

    def test_font_override_does_not_resize_the_canvas(self) -> None:
        dm.style.use("presentation", font_size=14)
        assert _cm(dm.figsize_for()) == (23.4, 10.5)

    @pytest.mark.parametrize("preset", ["web", "minimal", "dark", "report-kr"])
    def test_other_presets_use_report_tiers(self, preset: str) -> None:
        dm.style.use(preset)
        assert _cm(dm.figsize_for()) == (12.0, 9.0)

    @pytest.mark.parametrize("preset", ["report", "presentation", "scientific"])
    def test_slide_body_is_the_same_everywhere(self, preset: str) -> None:
        dm.style.use(preset)
        assert _cm(dm.figsize_for("slide")) == (23.4, 10.5)

    @pytest.mark.parametrize(
        "preset", ["report", "presentation", "scientific", "poster"]
    )
    def test_full_slide_is_the_whole_10in_slide_everywhere(
        self, preset: str
    ) -> None:
        """'A full-slide 16:9 chart' is the 10 in slide the slide sizes assume.

        2026-11-03 decision 20-A: 25.4 x 14.29 cm under any preset, not
        PowerPoint's 13.33 in slide (text 25 % smaller on screen) and not
        the 23.4 cm body at 16:9.
        """
        dm.style.use(preset)
        width, height = _cm(dm.figsize_for("full_slide"))
        assert width == 25.4
        assert height == pytest.approx(25.4 * 9 / 16, abs=0.01)

    def test_default_shape_matches_figsize_default(self) -> None:
        width, height = dm.figsize_for()
        assert height / width == pytest.approx(
            dm.figsize("9cm")[1] / dm.figsize("9cm")[0]
        )

    def test_context_restores_the_outer_preset(self) -> None:
        with dm.style.context("scientific"):
            assert _cm(dm.figsize_for(n_points=20, n_series=1))[0] == 17.0
        assert _cm(dm.figsize_for(n_points=20, n_series=1))[0] == 14.5


class TestGridShape:
    """One row up to three panels, then a near-square grid, wider than tall."""

    @pytest.mark.parametrize(
        ("n", "shape"),
        [
            (1, (1, 1)),
            (2, (1, 2)),
            (3, (1, 3)),
            (4, (2, 2)),
            (5, (2, 3)),
            (6, (2, 3)),
            (7, (3, 3)),
            (9, (3, 3)),
            (10, (3, 4)),
            (12, (3, 4)),
        ],
    )
    def test_shape(self, n: int, shape: tuple[int, int]) -> None:
        assert dm.grid_shape(n) == shape

    def test_rejects_zero_and_floats(self) -> None:
        with pytest.raises(ValueError, match="must be >= 1"):
            dm.grid_shape(0)
        with pytest.raises(TypeError, match="must be an int"):
            dm.grid_shape(2.0)  # type: ignore[arg-type]


class TestArguments:
    """Unknown kinds and bad counts are rejected."""

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

    @pytest.mark.parametrize("name", ["figsize_for", "grid_shape"])
    def test_is_provisional(self, name: str) -> None:
        assert name in dm.EXPERIMENTAL
        assert name in dm.__all__
