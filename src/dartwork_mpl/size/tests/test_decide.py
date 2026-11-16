"""The ordinary canvas decision, called directly: no preset, no figure."""

from __future__ import annotations

import pytest

from dartwork_mpl.length import cm
from dartwork_mpl.size import decide
from dartwork_mpl.size.canvas import (
    CanvasRequest,
    DefaultCanvas,
    Page,
    Paper,
    Poster,
    Slides,
    parse_canvas_kind,
)
from dartwork_mpl.size.model import Grid

REPORT, PAPER, SLIDES = Page(), Page(Paper()), Page(Slides())
POSTER = Page(Poster(), 1.5)


def _cm(request: CanvasRequest, page: Page) -> tuple[float, float]:
    width, height = decide.canvas(request, page).size().inches
    return (round(width * 2.54, 2), round(height * 2.54, 2))


def _ask(kind: str = "default", **hints: object) -> CanvasRequest:
    return CanvasRequest(kind=parse_canvas_kind(kind), **hints)  # type: ignore[arg-type]


def test_figure_size_takes_a_share_or_a_height() -> None:
    share = decide.figure_size(cm(13), DefaultCanvas.spec.aspect)
    assert (share.width.cm, share.height.cm) == pytest.approx((13.0, 9.75))
    height = decide.figure_size(cm(13), cm(8))
    assert height.height == cm(8)


@pytest.mark.parametrize(
    ("request_", "expected"),
    [
        (_ask(), (12.0, 9.0)),
        (_ask(n_points=8, n_series=3), (12.0, 9.0)),
        (_ask(n_points=5, n_series=2), (9.0, 6.75)),
        (_ask(n_points=5, n_series=2, dual_axis=True), (14.5, 10.88)),
        (_ask(n_points=13, n_series=1), (14.5, 10.88)),
        (_ask(n_points=8, n_series=4), (14.5, 10.88)),
        (_ask("barh", n_points=9, n_series=1), (14.5, 10.88)),
        (_ask("compact"), (9.0, 6.75)),
        (_ask("matrix", n_points=40), (12.0, 12.0)),
        (_ask("dense", n_points=3, n_series=1), (17.0, 8.5)),
        (_ask("strip"), (17.0, 7.65)),
    ],
)
def test_report_density_tiers(
    request_: CanvasRequest, expected: tuple[float, float]
) -> None:
    assert _cm(request_, REPORT) == expected


@pytest.mark.parametrize(
    ("request_", "width"),
    [
        (_ask(n_points=100, n_series=2), 9.0),
        (_ask("barh", n_points=8), 9.0),
        (_ask("matrix"), 9.0),
        (_ask("dense"), 17.0),
        (_ask(grid=Grid(2, 2)), 17.0),
    ],
)
def test_a_journal_sets_one_panel_in_one_column(
    request_: CanvasRequest, width: float
) -> None:
    assert _cm(request_, PAPER)[0] == width


@pytest.mark.parametrize(
    ("n_points", "width"),
    [(1, 11.4), (4, 11.4), (5, 15.4), (6, 15.4), (7, 23.4), (None, 23.4)],
)
def test_a_slide_chart_is_as_wide_as_its_positions(
    n_points: int | None, width: float
) -> None:
    assert _cm(_ask(n_points=n_points, n_series=2), SLIDES) == (width, 10.5)


@pytest.mark.parametrize(
    "request_",
    [
        _ask(n_points=3, n_series=4),
        _ask(n_points=3, dual_axis=True),
        _ask("barh", n_points=3),
        _ask(grid=Grid(1, 3)),
    ],
)
def test_busy_slide_charts_fill_the_body(request_: CanvasRequest) -> None:
    assert _cm(request_, SLIDES) == (23.4, 10.5)


@pytest.mark.parametrize(
    ("grid", "expected"),
    [
        (Grid(1, 2), (23.4, 10.5)),
        (Grid(1, 4), (23.4, 10.5)),  # one row: under the slide title
        (Grid(2, 1), (25.4, 14.29)),
        (Grid(2, 2), (25.4, 14.29)),  # two rows or more: the whole slide
        (Grid(3, 4), (25.4, 14.29)),
    ],
)
def test_a_slide_grid_of_rows_fills_the_slide(
    grid: Grid, expected: tuple[float, float]
) -> None:
    assert _cm(_ask(grid=grid), SLIDES) == expected


def test_slide_half_and_square() -> None:
    assert _cm(_ask("compact"), SLIDES) == (11.4, 10.5)
    assert _cm(_ask("matrix"), SLIDES) == (10.5, 10.5)


def test_a_poster_scales_the_tiers_with_its_font() -> None:
    assert _cm(_ask(), POSTER) == (18.0, 13.5)


@pytest.mark.parametrize(
    ("kind", "grid", "page", "expected"),
    [
        ("default", Grid(2, 2), REPORT, (17.0, 13.0)),
        ("default", Grid(2, 3), REPORT, (17.0, 8.5)),  # 3.1 cm plots: kept
        ("default", Grid(3, 3), REPORT, (17.0, 13.0)),  # 3.25 cm plots
        ("matrix", Grid(2, 2), REPORT, (17.0, 17.0)),
        ("default", Grid(1, 2), REPORT, (17.0, 6.5)),
        ("default", Grid(3, 2), REPORT, (17.0, 17.0)),  # no taller than wide
        ("default", Grid(3, 1), POSTER, (25.5, 14.5)),  # 16:9 on a poster
    ],
)
def test_a_grid_takes_the_widest_tier_and_keeps_its_panels(
    kind: str, grid: Grid, page: Page, expected: tuple[float, float]
) -> None:
    assert _cm(_ask(kind, grid=grid), page) == expected


@pytest.mark.parametrize(
    ("kind", "grid", "page", "expected"),
    [
        # Plots under 3 cm once the text is spent: the plot keeps 4:3 and
        # each row adds 1.5 cm of text on top.
        ("default", Grid(1, 3), REPORT, (17.0, 6.0)),  # 4.25 + 1.5
        ("default", Grid(1, 4), REPORT, (17.0, 4.5)),  # 3.19 + 1.5
        ("default", Grid(1, 4), PAPER, (17.0, 4.5)),
        ("default", Grid(2, 4), REPORT, (17.0, 9.5)),
        ("default", Grid(3, 4), REPORT, (17.0, 14.0)),
        ("default", Grid(1, 6), REPORT, (17.0, 4.5)),  # at least a 3 cm plot
        ("matrix", Grid(1, 4), REPORT, (17.0, 6.0)),  # 4.25 + 1.5
        ("default", Grid(1, 4), POSTER, (25.5, 7.0)),  # text x 1.5
        ("default", Grid(2, 4), POSTER, (25.5, 14.0)),
    ],
)
def test_grid_plots_under_3_cm_add_their_text_on_top(
    kind: str, grid: Grid, page: Page, expected: tuple[float, float]
) -> None:
    assert _cm(_ask(kind, grid=grid), page) == expected


def test_half_cm_rounds_a_half_that_went_through_inches_up() -> None:
    assert decide.half_cm(cm(12.75)).cm == pytest.approx(13.0)
    assert decide.half_cm(cm(12.74)).cm == pytest.approx(12.5)


def test_the_slide_scale_is_the_slide_body_over_a_column() -> None:
    from dartwork_mpl.style import SLIDE_SCALE

    body = decide.SLIDE_BODY.width
    assert body.cm / decide.COLUMN.cm == pytest.approx(SLIDE_SCALE)
