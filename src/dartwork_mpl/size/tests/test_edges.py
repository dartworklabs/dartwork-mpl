"""Each named edge case of the default canvas: when it fires and what it fixes.

The decision-level tests call ``settle`` with hand-made facts. The drawn tests
check the reason each case exists on real figures.
"""

from __future__ import annotations

from dartwork_mpl.edgecase import settle
from dartwork_mpl.size import decide
from dartwork_mpl.size.canvas import (
    CanvasFacts,
    CanvasRequest,
    NameWidths,
    Page,
    Paper,
    Slides,
)
from dartwork_mpl.size.edges import EDGES
from dartwork_mpl.size.model import Grid

REPORT, PAPER, SLIDES = Page(), Page(Paper()), Page(Slides())
CM = 2.54


def _settle(
    request: CanvasRequest, page: Page, names: NameWidths | None = None
) -> tuple[tuple[float, float], tuple[str, ...]]:
    plan = decide.canvas(request, page)
    settled = settle(CanvasFacts(request, page, names), plan, EDGES)
    width, height = settled.plan.size().inches
    return (round(width * CM, 2), round(height * CM, 2)), settled.fired


class TestFlatCategoryNames:
    """flat-category-names: names widen the canvas until they stand flat."""

    def _names(self, width_pt: float, n: int) -> NameWidths:
        return NameWidths((width_pt,) * n, 10.0)

    def test_short_names_change_nothing(self) -> None:
        request = CanvasRequest(n_points=3, n_series=1)
        size, _ = _settle(request, REPORT, self._names(10.0, 3))
        assert size[0] == 9.0

    def test_long_names_take_the_next_tier_that_fits(self) -> None:
        request = CanvasRequest(n_points=3, n_series=1)
        size, fired = _settle(request, REPORT, self._names(80.0, 3))
        assert size[0] == 12.0 and "flat-category-names" in fired

    def test_past_the_widest_the_widest(self) -> None:
        request = CanvasRequest(n_points=3, n_series=1)
        assert _settle(request, SLIDES, self._names(900.0, 3))[0][0] == 23.4

    def test_a_journal_column_and_a_grid_keep_their_width(self) -> None:
        names = self._names(900.0, 3)
        assert _settle(CanvasRequest(), PAPER, names)[1] == ()
        grid = CanvasRequest(grid=Grid(1, 2))
        assert _settle(grid, REPORT, names)[1] == ()
