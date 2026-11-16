"""The rules ``dm.check`` runs, in report order: one named entry each.

The registry is the edge-case list itself (plan = the findings so far): a
rule applies when the figure has the thing it judges, and appends what it
finds. ``settle`` runs them in order; its ``fired`` list is the rules that
ran. A new rule is one more entry here and a test that names it.
"""

from __future__ import annotations

from ..edgecase import EdgeCase
from . import decide
from .findings import Findings
from .model import Facts


def has_texts(facts: Facts, found: Findings) -> bool:
    """Any drawn text."""
    return bool(facts.all_texts)


def has_panel_texts(facts: Facts, found: Findings) -> bool:
    """Any text that belongs to an Axes."""
    return bool(facts.by_panel)


def has_legends(facts: Facts, found: Findings) -> bool:
    """Any drawn legend."""
    return bool(facts.legends)


def has_ticks(facts: Facts, found: Findings) -> bool:
    """Any drawn tick labels."""
    return bool(facts.ticks)


EDGES: tuple[EdgeCase[Facts, Findings], ...] = (
    EdgeCase(
        name="OVERFLOW",
        why="a text past the canvas edge is cut off in every saved file",
        example="test_edges.py::test_OVERFLOW_cut_at_the_edge",
        applies=has_texts,
        adjust=decide.overflow,
    ),
    EdgeCase(
        name="OVERLAP",
        why="two texts of one Axes drawn over each other read as neither",
        example="test_edges.py::test_OVERLAP_within_one_axes",
        applies=has_panel_texts,
        adjust=decide.overlap,
    ),
    EdgeCase(
        name="CROSS_AXES_OVERLAP",
        why=(
            "an inset's tick labels were drawn over its parent's tick "
            "labels, '1.0' on '1'"
        ),
        example="test_edges.py::"
        "test_CROSS_AXES_OVERLAP_title_on_neighbour_ticks",
        applies=has_panel_texts,
        adjust=decide.cross_axes,
    ),
    EdgeCase(
        name="TEXT_CROWD",
        why=(
            "a value annotation 0.9 em before a line-end name read as one "
            "phrase, '19.4 TWh Solar'"
        ),
        example="test_edges.py::test_TEXT_CROWD_value_beside_a_name",
        applies=has_panel_texts,
        adjust=decide.phrase,
    ),
    EdgeCase(
        name="LEGEND_ON_DATA",
        why="a legend on the lines hides the data it explains",
        example="test_edges.py::test_LEGEND_ON_DATA_reports_what_it_covers",
        applies=has_legends,
        adjust=decide.legend_on_data,
    ),
    EdgeCase(
        name="TICK_OVERLAP",
        why="neighbouring tick labels drawn on each other read as neither",
        example="test_edges.py::test_TICK_OVERLAP",
        applies=has_ticks,
        adjust=decide.tick_overlap,
    ),
)
