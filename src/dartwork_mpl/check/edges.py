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


def has_value_labels(facts: Facts, found: Findings) -> bool:
    """Any value label inside an Axes."""
    return bool(facts.values)


def has_ticks(facts: Facts, found: Findings) -> bool:
    """Any drawn tick labels."""
    return bool(facts.ticks)


def has_corners(facts: Facts, found: Findings) -> bool:
    """Any x/y tick labels meeting at a corner."""
    return bool(facts.corners)


def has_panels(facts: Facts, found: Findings) -> bool:
    """Any drawn Axes."""
    return bool(facts.panels)


def has_content(facts: Facts, found: Findings) -> bool:
    """Drawn content whose margins can be compared."""
    return facts.content is not None


def has_contrast(facts: Facts, found: Findings) -> bool:
    """Texts whose ink was read against their background."""
    return bool(facts.contrast)


EDGES: tuple[EdgeCase[Facts, Findings], ...] = (
    EdgeCase(
        name="OVERFLOW",
        why="a text past the canvas edge is cut off in every saved file",
        example="test_edges.py::test_OVERFLOW_cut_at_the_edge",
        applies=has_texts,
        adjust=decide.overflow,
    ),
    EdgeCase(
        name="TEXT_AT_EDGE",
        why=(
            "a line-end name flush with the right edge lost the arm of its "
            "'r', and panel letters flush with the left edge looked cramped"
        ),
        example="test_edges.py::test_TEXT_AT_EDGE_flush_is_one_info",
        applies=has_texts,
        adjust=decide.at_edge,
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
            "an upper panel's tick labels ran into the lower panel's title "
            "when the grid was too tight"
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
        name="LEGEND_OVERFLOW",
        why="a legend bigger than its plot, or past the canvas, crowds out the data",
        example="test_edges.py::test_LEGEND_OVERFLOW_too_big_or_off_canvas",
        applies=has_legends,
        adjust=decide.legend_overflow,
    ),
    EdgeCase(
        name="LEGEND_OVERLAP",
        why="a legend anchored above the Axes was drawn over the title",
        example="test_edges.py::test_LEGEND_OVERLAP_over_a_title",
        applies=has_legends,
        adjust=decide.legend_overlap,
    ),
    EdgeCase(
        name="LEGEND_ON_DATA",
        why="a legend on the points hides the data it explains",
        example="test_edges.py::test_LEGEND_ON_DATA_reports_what_it_covers",
        applies=has_legends,
        adjust=decide.legend_on_data,
    ),
    EdgeCase(
        name="VALUE_LABEL_ON_DATA",
        why="a value label on its line or a neighbouring bar hides the value",
        example="test_edges.py::test_VALUE_LABEL_ON_DATA_per_axes",
        applies=has_value_labels,
        adjust=decide.value_label_on_data,
    ),
    EdgeCase(
        name="VALUE_LABEL_DECIMAL",
        why="'120.0, 135.0' carry decimals that say nothing",
        example="test_edges.py::"
        "test_VALUE_LABEL_DECIMAL_whole_numbers_with_decimals",
        applies=has_panel_texts,
        adjust=decide.value_label_decimal,
    ),
    EdgeCase(
        name="TICK_OVERLAP",
        why="neighbouring tick labels drawn on each other read as neither",
        example="test_edges.py::test_TICK_OVERLAP",
        applies=has_ticks,
        adjust=decide.tick_overlap,
    ),
    EdgeCase(
        name="TICK_CROWD",
        why="labels packed closer than half an em read as one string",
        example="test_edges.py::test_TICK_CROWD_needs_both_fill_and_closeness",
        applies=has_ticks,
        adjust=decide.tick_crowd,
    ),
    EdgeCase(
        name="TICK_CORNER_OVERLAP",
        why="the first x and the lowest y tick label met at the corner of a -3..3 square",
        example="test_edges.py::test_TICK_CORNER_OVERLAP",
        applies=has_corners,
        adjust=decide.tick_corner,
    ),
    EdgeCase(
        name="TICK_DECIMAL",
        why="ticks printing '2.0, 4.0' or the same text twice mislead",
        example="test_edges.py::test_TICK_DECIMAL",
        applies=has_ticks,
        adjust=decide.tick_decimal,
    ),
    EdgeCase(
        name="MISSING_AXIS_LABEL",
        why="numbers on an axis with no name or unit cannot be read",
        example="test_edges.py::"
        "test_MISSING_AXIS_LABEL_only_for_numbers_named_nowhere",
        applies=has_ticks,
        adjust=decide.missing_axis_label,
    ),
    EdgeCase(
        name="TEXT_CONTRAST",
        why="light text on a light fill disappears in print and on projectors",
        example="test_edges.py::test_TEXT_CONTRAST_grouped_by_colours",
        applies=has_contrast,
        adjust=decide.contrast,
    ),
    EdgeCase(
        name="EMPTY_AXES",
        why="an Axes left empty by a grid larger than the data is a blank hole",
        example="test_edges.py::test_EMPTY_AXES",
        applies=has_panels,
        adjust=decide.empty_axes,
    ),
    EdgeCase(
        name="MARGIN_ASYMMETRY",
        why="a figure laid out by hand sat off-centre with one wide empty side",
        example="test_edges.py::test_MARGIN_ASYMMETRY",
        applies=has_content,
        adjust=decide.margin_asymmetry,
    ),
)
