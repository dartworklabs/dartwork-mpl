"""Each named edge case of the default canvas: when it fires and what it fixes.

The decision-level tests call ``settle`` with hand-made facts. The drawn tests
check the reason each case exists on real figures.
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.edgecase import settle
from dartwork_mpl.geometry import drawn_tick_labels, get_renderer
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
from dartwork_mpl.vocab import X

REPORT, PAPER, SLIDES = Page(), Page(Paper()), Page(Slides())
TEMPLATES_WITH_NAMES = (
    "advanced/bar.py",
    "waterfall.py",
    "advanced/boxplot.py",
    "advanced/violin.py",
)
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

    @pytest.mark.parametrize("name", TEMPLATES_WITH_NAMES)
    def test_templates_draw_their_names_flat_on_a_slide(
        self, name: str
    ) -> None:
        """Without the names, these turned or wrapped their labels on a slide
        (0.38, 0.25, -0.78 and -0.88 em apart flat)."""
        source = dm.guide.read("template/" + name.removesuffix(".py"))
        ends = ("dm.check(fig)", "dm.save_formats(")
        source = source[: min(source.find(e) % (len(source) + 1) for e in ends)]
        source = source.replace(
            'dm.style.use("scientific")', 'dm.style.use("presentation")'
        )
        namespace: dict[str, object] = {}
        exec(compile(source, name, "exec"), namespace)
        fig = namespace["fig"]
        assert isinstance(fig, plt.Figure)
        dm.simple_layout(fig)
        fig.canvas.draw()
        labels = [
            t for t in drawn_tick_labels(fig.axes[0], X()) if t.get_text()
        ]
        renderer = get_renderer(fig)
        boxes = sorted(
            (t.get_window_extent(renderer) for t in labels), key=lambda b: b.x0
        )
        em = labels[0].get_fontsize() * fig.dpi / 72
        assert {float(t.get_rotation()) for t in labels} == {0.0}
        assert not any("\n" in t.get_text() for t in labels)
        assert min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em >= 0.5
