"""The rules ``dm.check`` runs, in report order: one named entry each.

The registry is the edge-case list itself (plan = the findings so far): a
rule applies when the figure has the thing it judges, and appends what it
finds. ``settle`` runs them in order; its ``fired`` list is the rules that
ran. A new rule is one more entry here and a test that names it.
"""

from __future__ import annotations

from ..edgecase import EdgeCase
from . import alignment, decide
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


def has_empty(facts: Facts, found: Findings) -> bool:
    """Any framed Axes that draws nothing."""
    return bool(facts.empty)


def has_values_on_data(facts: Facts, found: Findings) -> bool:
    """Any value label drawn on a line, marker or error bar."""
    return bool(facts.values)


def has_letters_on_data(facts: Facts, found: Findings) -> bool:
    """Any panel letter drawn on data."""
    return bool(facts.letters)


def has_ticks(facts: Facts, found: Findings) -> bool:
    """Any drawn tick labels."""
    return bool(facts.ticks)


def has_frames(facts: Facts, found: Findings) -> bool:
    """Any flat Axes with tick labels."""
    return bool(facts.frames and facts.ticks)


def has_polar_theta(facts: Facts, found: Findings) -> bool:
    """Any drawn angle tick labels on a full polar disc."""
    return bool(facts.polar_theta)


def has_minus_labels(facts: Facts, found: Findings) -> bool:
    """Any numeric text using a hyphen-minus."""
    return bool(facts.minus_labels)


def has_occluded_ticks(facts: Facts, found: Findings) -> bool:
    """Any radial tick measured against a fill."""
    return bool(facts.occluded_ticks)


def has_edge_texts(facts: Facts, found: Findings) -> bool:
    """Any visible, manually placed Axes text."""
    return bool(facts.edge_texts)


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
        name="TEXT_MISALIGNMENT",
        why="forest estimates stacked beside the plot had ragged decimal marks",
        example="test_edges.py::test_TEXT_MISALIGNMENT_on_forest_values",
        applies=has_panel_texts,
        adjust=alignment.misalignment,
    ),
    EdgeCase(
        name="VALUE_LABEL_DECIMAL",
        why="respondent counts labelled '12.0, 31.0' carry decimals that say nothing",
        example="test_edges.py::test_VALUE_LABEL_DECIMAL",
        applies=has_panel_texts,
        adjust=decide.value_label_decimal,
    ),
    EdgeCase(
        name="LEGEND_ON_DATA",
        why=(
            "a legend on the lines hides the data it explains; one anchored "
            "above the plot was drawn over the title"
        ),
        example="test_edges.py::test_LEGEND_ON_DATA_reports_what_it_covers",
        applies=has_legends,
        adjust=decide.legend_on_data,
    ),
    EdgeCase(
        name="VALUE_LABEL_ON_DATA",
        why=(
            "bar values were printed on their error bars, the line "
            "striking through each number"
        ),
        example="test_edges.py::test_VALUE_LABEL_ON_DATA",
        applies=has_values_on_data,
        adjust=decide.value_label_on_data,
    ),
    EdgeCase(
        name="LETTER_ON_DATA",
        why=(
            "titles too long to follow their letters put the letters inside "
            "the plots, and letter b sat on the start of its curve"
        ),
        example="test_edges.py::test_LETTER_ON_DATA",
        applies=has_letters_on_data,
        adjust=decide.letter_on_data,
    ),
    EdgeCase(
        name="TEXT_CONTRAST",
        why=(
            "white values centred in pale yellow bars read at 1.39:1 and "
            "disappeared"
        ),
        example="test_edges.py::test_TEXT_CONTRAST",
        applies=has_panel_texts,
        adjust=decide.text_contrast,
    ),
    EdgeCase(
        name="TICK_OVERLAP",
        why="neighbouring tick labels drawn on each other read as neither",
        example="test_edges.py::test_TICK_OVERLAP",
        applies=has_ticks,
        adjust=decide.tick_overlap,
    ),
    EdgeCase(
        name="EMPTY_AXES",
        why=(
            "five groups drawn in a 2 x 3 grid left a sixth panel as an "
            "empty 0-1 frame"
        ),
        example="test_edges.py::test_EMPTY_AXES",
        applies=has_empty,
        adjust=decide.empty_axes,
    ),
    EdgeCase(
        name="MISSING_AXIS_LABEL",
        why=(
            "a scatter of engine size against fuel economy named neither "
            "axis: its numbers could not be read"
        ),
        example="test_edges.py::test_MISSING_AXIS_LABEL",
        applies=has_ticks,
        adjust=decide.missing_axis_label,
    ),
    EdgeCase(
        name="SMALL_PANEL",
        why=(
            "a report's 2 x 2 grid moved to slide text left each plot 5 "
            "tick labels tall, and nothing else stood out"
        ),
        example="test_edges.py::test_SMALL_PANEL",
        applies=has_frames,
        adjust=decide.small_panel,
    ),
    EdgeCase(
        name="TEXT_TOO_CLOSE",
        why="a text placed just under the title read as part of the title",
        example="test_edges.py::test_TEXT_TOO_CLOSE",
        applies=has_panel_texts,
        adjust=decide.text_too_close,
    ),
    EdgeCase(
        name="POLAR_TICK_ON_PLOT",
        why="long radar tick labels can cross the circle into the data",
        example="test_edges.py::test_POLAR_TICK_ON_PLOT",
        applies=has_polar_theta,
        adjust=decide.polar_tick_on_plot,
    ),
    EdgeCase(
        name="MIXED_MINUS",
        why="negative bar labels used a hyphen while the ticks printed a minus",
        example="test_edges.py::test_MIXED_MINUS",
        applies=has_minus_labels,
        adjust=decide.mixed_minus,
    ),
    EdgeCase(
        name="RADIAL_TICK_COVERED",
        why="a polar band painted over the radial numbers, so part of a number vanished",
        example="test_edges.py::test_RADIAL_TICK_COVERED",
        applies=has_occluded_ticks,
        adjust=decide.radial_tick_covered,
    ),
    EdgeCase(
        name="TEXT_AT_EDGE",
        why="a group heading drawn flush with the paper reads as cut off",
        example="test_edges.py::test_TEXT_AT_EDGE",
        applies=has_edge_texts,
        adjust=decide.text_at_edge,
    ),
)
