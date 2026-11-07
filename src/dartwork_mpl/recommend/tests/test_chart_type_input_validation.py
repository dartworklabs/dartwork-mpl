"""The recommender answers only for the selections it documents (#501 task 8).

An unknown ``x_type`` used to fall through to a default and return a confident
chart label, which the MCP wrapper turned into a template URI for a chart the
caller never described. These tests pin the rejection and, just as importantly,
pin that every documented selection still returns exactly what it did before.
"""

from __future__ import annotations

import itertools

import pytest

from dartwork_mpl.recommend import suggest_chart_type

X_TYPES = ("continuous", "categorical", "temporal")
Y_TYPES = ("continuous", "categorical", "count", None)

#: Every documented selection with the thresholds the heuristic reads, measured
#: on `ab3e3347` before the validation landed. All 360 combinations of these
#: arguments were compared; the table below carries one case per outcome so a
#: future edit that moves a boundary fails here with the inputs in view.
UNCHANGED = [
    (("continuous", None, 50, 1), "histogram"),
    (("categorical", None, 50, 1), "count_bar"),
    (("temporal", None, 50, 1), "line"),
    (("categorical", "continuous", 50, 1), "bar"),
    (("categorical", "continuous", 50, 2), "grouped_bar"),
    (("categorical", "count", 5, 1), "bar"),
    (("categorical", "count", 5, 4), "grouped_bar"),
    (("temporal", "continuous", 19, 1), "bar_line"),
    (("temporal", "continuous", 20, 1), "line"),
    (("temporal", "continuous", 19, 3), "multi_line"),
    (("continuous", "continuous", 49, 1), "scatter"),
    (("continuous", "continuous", 50, 1), "scatter_density"),
    (("continuous", "continuous", 499, 1), "scatter_density"),
    (("continuous", "continuous", 500, 1), "hexbin"),
    (("continuous", "categorical", 50, 1), "line"),
    (("continuous", "count", 50, 1), "line"),
]


@pytest.mark.parametrize(("arguments", "expected"), UNCHANGED)
def test_documented_selections_keep_their_answer(arguments, expected) -> None:
    """Enforcing the set changes no answer the function already gave."""
    assert suggest_chart_type(*arguments) == expected


@pytest.mark.parametrize(
    ("x_type", "y_type"), list(itertools.product(X_TYPES, Y_TYPES))
)
def test_every_documented_pair_is_accepted(x_type, y_type) -> None:
    """No documented pair is refused — the guard must not over-reject."""
    assert suggest_chart_type(x_type, y_type, 50, 1)


@pytest.mark.parametrize(
    "x_type", ["weird", "catagorical", "CONTINUOUS", "", "Continuous", "bar"]
)
def test_undocumented_x_type_is_rejected(x_type) -> None:
    """The message names the argument, the value and the permitted set."""
    with pytest.raises(ValueError) as caught:
        suggest_chart_type(x_type, "continuous", 50, 1)
    message = str(caught.value)
    assert "x_type must be one of" in message
    assert repr(x_type) in message
    for permitted in X_TYPES:
        assert repr(permitted) in message


@pytest.mark.parametrize("y_type", ["counts", "COUNT", "", "none", "numeric"])
def test_undocumented_y_type_is_rejected(y_type) -> None:
    """``y_type`` is checked too, and ``None`` is named as the way to omit it."""
    with pytest.raises(ValueError) as caught:
        suggest_chart_type("continuous", y_type, 50, 1)
    message = str(caught.value)
    assert "y_type must be one of" in message
    assert "or None" in message
    assert repr(y_type) in message


def test_x_type_is_checked_before_y_type() -> None:
    """Two bad arguments report ``x_type``, so the caller fixes the first one."""
    with pytest.raises(ValueError, match="x_type must be one of"):
        suggest_chart_type("weird", "counts", 50, 1)


def test_none_y_type_is_not_a_rejected_value() -> None:
    """``None`` means "single variable" and must not hit the ``y_type`` guard."""
    assert suggest_chart_type("continuous", None, 50, 1) == "histogram"


@pytest.mark.parametrize("value", [1, 0.5, True, (), ["continuous"]])
def test_non_string_x_type_is_rejected(value) -> None:
    """A non-string is outside the set as well, and says so without a TypeError."""
    with pytest.raises(ValueError, match="x_type must be one of"):
        suggest_chart_type(value, "continuous", 50, 1)
