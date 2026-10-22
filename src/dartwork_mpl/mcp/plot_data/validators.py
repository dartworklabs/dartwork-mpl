"""Per-template data-shape parsers behind ``validate_plot_data``.

``parse_<plot_type>(data)`` takes the decoded JSON payload and returns one
``PlotDataVerdict``: ``Parsed`` (the shape fits), ``Invalid`` (the issues, in
check order) or ``Malformed`` (a field's type broke a check, e.g. ``len()`` of
a number). ``PARSERS`` maps each plot type to its parser in the order the
tool lists them. Pure: no I/O, no other unit, never raises for JSON input.

The checks read untrusted values only through ``_has`` / ``_at`` /
``_len``, which perform the legacy operation and report its ``TypeError``
as ``Malformed`` with the interpreter's own message, so replies match the
legacy text on every supported Python version.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeAlias

__all__ = [
    "PARSERS",
    "Invalid",
    "Malformed",
    "Parsed",
    "PlotDataVerdict",
    "parse_bar",
    "parse_bar_grouped",
    "parse_bar_horizontal",
    "parse_boxplot",
    "parse_contour",
    "parse_heatmap",
    "parse_histogram",
    "parse_line",
    "parse_pie",
    "parse_plot_3d",
    "parse_polar",
    "parse_scatter",
    "parse_small_multiples",
    "parse_stacked_bar",
    "parse_tornado",
    "parse_twin_axis",
    "parse_violin",
    "parse_waterfall",
]


@dataclass(frozen=True)
class Parsed:
    """The payload fits the plot type's shape; ``label`` names the plot in the reply."""

    label: str


@dataclass(frozen=True)
class Invalid:
    """The payload's shape issues in check order; construction rejects none (ValueError)."""

    issues: tuple[str, ...]

    def __post_init__(self) -> None:
        """An invalid payload has at least one issue."""
        if not self.issues:
            raise ValueError("Invalid requires at least one issue")


@dataclass(frozen=True)
class Malformed:
    """A field's type broke a shape check; ``error_type``/``detail`` are Python's error."""

    error_type: str
    detail: str


PlotDataVerdict: TypeAlias = Parsed | Invalid | Malformed


class _Fault(Exception):
    """A legacy check's ``TypeError`` on an untrusted value; never leaves this module."""

    def __init__(self, error: TypeError) -> None:
        """Keep the original error for its type name and message."""
        super().__init__(error)
        self.error = error


def _has(data: Any, key: str) -> bool:
    """``key in data``; a non-container payload is a fault."""
    try:
        return key in data
    except TypeError as error:
        raise _Fault(error) from None


def _at(data: Any, key: str) -> Any:
    """``data[key]`` after ``_has``; a list or string payload is a fault."""
    try:
        return data[key]
    except TypeError as error:
        raise _Fault(error) from None


def _len(value: Any) -> int:
    """``len(value)``; a number, boolean or null is a fault."""
    try:
        return len(value)
    except TypeError as error:
        raise _Fault(error) from None


def _verdict(
    label: str, check: Callable[[Any], list[str]], data: object
) -> PlotDataVerdict:
    """Run one shape check and name its result."""
    try:
        issues = check(data)
    except _Fault as fault:
        return Malformed(type(fault.error).__name__, str(fault.error))
    return Invalid(tuple(issues)) if issues else Parsed(label)


def _tornado_issues(data: Any) -> list[str]:
    """Tornado issues: ``categories`` and a ``positive`` / ``negative`` array."""
    issues = []
    if not _has(data, "categories"):
        issues.append("Missing 'categories' key (list of category labels).")
    if not _has(data, "positive") and not _has(data, "negative"):
        issues.append(
            "Need at least 'positive' and/or 'negative' value arrays."
        )
    if (
        _has(data, "categories")
        and _has(data, "positive")
        and _len(_at(data, "categories")) != _len(_at(data, "positive"))
    ):
        issues.append(
            "Length mismatch: 'categories' and 'positive' must have equal length."
        )
    return issues


def _scatter_issues(data: Any) -> list[str]:
    """Scatter issues: ``x`` and ``y`` of equal length."""
    issues = []
    if not _has(data, "x"):
        issues.append("Missing 'x' key (list of x-coordinates).")
    if not _has(data, "y"):
        issues.append("Missing 'y' key (list of y-coordinates).")
    if (
        _has(data, "x")
        and _has(data, "y")
        and _len(_at(data, "x")) != _len(_at(data, "y"))
    ):
        issues.append("Length mismatch: 'x' and 'y' must have equal length.")
    return issues


def _bar_issues(data: Any) -> list[str]:
    """Categories plus values (vertical and horizontal bars share it)."""
    issues = []
    if not _has(data, "categories"):
        issues.append("Missing 'categories' key (list of category labels).")
    if not _has(data, "values"):
        issues.append("Missing 'values' key (list of numeric values).")
    if (
        _has(data, "categories")
        and _has(data, "values")
        and _len(_at(data, "categories")) != _len(_at(data, "values"))
    ):
        issues.append(
            "Length mismatch: 'categories' and 'values' must have equal length."
        )
    return issues


def _heatmap_issues(data: Any) -> list[str]:
    """Heatmap issues: ``matrix`` as a list of lists."""
    issues = []
    if not _has(data, "matrix"):
        issues.append("Missing 'matrix' key (2D array of numeric values).")
    else:
        matrix = _at(data, "matrix")
        if not isinstance(matrix, list) or not all(
            isinstance(row, list) for row in matrix
        ):
            issues.append("'matrix' must be a 2D array (list of lists).")
    return issues


def _series_issues(data: Any) -> list[str]:
    """Categories plus a series dict of equal-length values (stacked and grouped bars)."""
    issues = []
    if not _has(data, "categories"):
        issues.append("Missing 'categories' key.")
    if not _has(data, "series"):
        issues.append("Missing 'series' key (dict of series_name -> values).")
    else:
        series = _at(data, "series")
        if isinstance(series, dict):
            cat_len = _len(data.get("categories", []))
            for name, vals in series.items():
                if _len(vals) != cat_len:
                    issues.append(
                        f"Series '{name}' length ({_len(vals)}) != "
                        f"categories length ({cat_len})."
                    )
    return issues


def _pie_issues(data: Any) -> list[str]:
    """Pie issues: ``labels`` and ``sizes`` of equal length."""
    issues = []
    if not _has(data, "labels"):
        issues.append("Missing 'labels' key.")
    if not _has(data, "sizes"):
        issues.append("Missing 'sizes' key (list of numeric values).")
    if (
        _has(data, "labels")
        and _has(data, "sizes")
        and _len(_at(data, "labels")) != _len(_at(data, "sizes"))
    ):
        issues.append(
            "Length mismatch: 'labels' and 'sizes' must have equal length."
        )
    return issues


def _line_issues(data: Any) -> list[str]:
    """Line issues: ``x`` with ``y`` or ``series``."""
    issues = []
    if not _has(data, "x"):
        issues.append("Missing 'x' key (list of x values or time points).")
    if not _has(data, "y") and not _has(data, "series"):
        issues.append(
            "Need 'y' (single series) or 'series' (dict of named series)."
        )
    return issues


def _grouped_samples_issues(data: Any, plot_label: str) -> list[str]:
    """Shared strict validator for violin/boxplot grouped samples.

    Accepts one of two shapes:

    1. ``groups`` (list of string labels) **and** ``values``
       (list of numeric lists, one inner list per group).
       ``len(groups) == len(values)`` and each inner list must be
       non-empty and numeric.
    2. ``series`` (mapping of label → list of numeric samples).
       Each value list must be non-empty and numeric.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        issues.append(f"'{plot_label}' data must be a JSON object (dict).")
        return issues

    has_pair = "groups" in data and "values" in data
    has_series = "series" in data

    if not has_pair and not has_series:
        issues.append(
            "Need either 'groups' (list of labels) + 'values' "
            "(list of numeric lists), or 'series' (dict of label -> "
            "numeric list)."
        )
        return issues

    if has_pair:
        groups = data["groups"]
        values = data["values"]
        if not isinstance(groups, list) or not all(
            isinstance(g, str) for g in groups
        ):
            issues.append("'groups' must be a list of string labels.")
        if not isinstance(values, list) or not all(
            isinstance(v, list) for v in values
        ):
            issues.append("'values' must be a list of lists of numbers.")
        elif isinstance(groups, list) and len(groups) != len(values):
            issues.append(
                f"Length mismatch: 'groups' ({len(groups)}) != "
                f"'values' ({len(values)})."
            )
        if isinstance(values, list):
            for i, inner in enumerate(values):
                if not isinstance(inner, list):
                    continue
                if len(inner) < 1:
                    issues.append(
                        f"'values[{i}]' must contain at least one sample."
                    )
                if not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in inner
                ):
                    issues.append(
                        f"'values[{i}]' must contain only numeric samples "
                        f"(int/float)."
                    )

    if has_series:
        series = data["series"]
        if not isinstance(series, dict):
            issues.append(
                "'series' must be a dict mapping label -> numeric list."
            )
        else:
            for name, inner in series.items():
                if not isinstance(name, str):
                    issues.append(
                        f"'series' key {name!r} must be a string label."
                    )
                if not isinstance(inner, list):
                    issues.append(
                        f"'series[{name!r}]' must be a list of numbers."
                    )
                    continue
                if len(inner) < 1:
                    issues.append(
                        f"'series[{name!r}]' must contain at least one sample."
                    )
                if not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in inner
                ):
                    issues.append(
                        f"'series[{name!r}]' must contain only numeric "
                        f"samples (int/float)."
                    )

    return issues


def _histogram_issues(data: Any) -> list[str]:
    """Validate data for a histogram.

    Required: ``values`` — a 1-D list of numbers.
    Optional: ``bins`` — either a positive integer or a 1-D list of
    numeric bin edges.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["histogram data must be a JSON object (dict)."]

    if "values" not in data:
        issues.append("Missing 'values' key — a 1-D list of numeric samples.")
    else:
        samples = data["values"]
        if not isinstance(samples, list):
            issues.append("'values' must be a 1-D list of numbers.")
        elif not all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in samples
        ):
            issues.append(
                "'values' must contain only numeric samples (int/float)."
            )

    if "bins" in data:
        bins = data["bins"]
        if isinstance(bins, bool):
            issues.append("'bins' must be a positive int or list of edges.")
        elif isinstance(bins, int):
            if bins < 1:
                issues.append("'bins' (int) must be >= 1.")
        elif isinstance(bins, list):
            if not all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in bins
            ):
                issues.append("'bins' list must contain only numeric edges.")
            elif len(bins) < 2:
                issues.append("'bins' list must contain at least two edges.")
        else:
            issues.append(
                "'bins' must be a positive int or a list of numeric edges."
            )

    return issues


def _contour_issues(data: Any) -> list[str]:
    """Validate data for a contour plot.

    Required: ``Z`` — a 2-D array (list of lists) with rows of equal
    length and at least one row/column.
    Optional: ``X``, ``Y`` — meshgrid 2-D arrays with the same shape
    as ``Z``.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["contour data must be a JSON object (dict)."]

    if "Z" not in data:
        issues.append("Missing 'Z' key — a 2-D array of values to contour.")
        Z = None
    else:
        Z = data["Z"]
        if not isinstance(Z, list) or not all(
            isinstance(row, list) for row in Z
        ):
            issues.append("'Z' must be a 2-D array (list of lists).")
            Z = None
        elif len(Z) < 1 or len(Z[0]) < 1:
            issues.append("'Z' must have at least one row and one column.")
            Z = None
        elif any(len(row) != len(Z[0]) for row in Z):
            issues.append("'Z' rows must all have equal length.")
            Z = None
        elif not all(
            all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in row
            )
            for row in Z
        ):
            issues.append("'Z' must contain only numeric values (int/float).")

    for key in ("X", "Y"):
        if key not in data:
            continue
        grid = data[key]
        if not isinstance(grid, list) or not all(
            isinstance(row, list) for row in grid
        ):
            issues.append(f"'{key}' must be a 2-D array (list of lists).")
            continue
        if Z is not None:
            z_rows = len(Z)
            z_cols = len(Z[0])
            if len(grid) != z_rows or any(len(r) != z_cols for r in grid):
                issues.append(
                    f"'{key}' shape must match 'Z' shape ({z_rows}x{z_cols})."
                )
                continue
        if not all(
            all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in row
            )
            for row in grid
        ):
            issues.append(
                f"'{key}' must contain only numeric values (int/float)."
            )

    return issues


def _twin_axis_issues(data: Any) -> list[str]:
    """Validate data for a twin-axis chart.

    Required:

    * ``x`` — a list of numeric values.
    * ``left`` — a dict with keys ``y`` (numeric list, same length
      as ``x``) and ``label`` (string).
    * ``right`` — same shape as ``left``.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["twin_axis data must be a JSON object (dict)."]

    x = data.get("x")
    if "x" not in data:
        issues.append("Missing 'x' key (list of shared x values).")
    elif not isinstance(x, list):
        issues.append("'x' must be a list of numbers.")
    elif not all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in x
    ):
        issues.append("'x' must contain only numeric values (int/float).")

    n = len(x) if isinstance(x, list) else None

    for side in ("left", "right"):
        if side not in data:
            issues.append(f"Missing '{side}' key (dict with 'y' and 'label').")
            continue
        spec = data[side]
        if not isinstance(spec, dict):
            issues.append(
                f"'{side}' must be a dict with 'y' (numeric list) and "
                f"'label' (string)."
            )
            continue
        if "y" not in spec:
            issues.append(f"'{side}' is missing required 'y' key.")
        else:
            y = spec["y"]
            if not isinstance(y, list):
                issues.append(f"'{side}.y' must be a list of numbers.")
            else:
                if not all(
                    isinstance(v, (int, float)) and not isinstance(v, bool)
                    for v in y
                ):
                    issues.append(
                        f"'{side}.y' must contain only numeric values "
                        f"(int/float)."
                    )
                if n is not None and len(y) != n:
                    issues.append(
                        f"'{side}.y' length ({len(y)}) != 'x' length ({n})."
                    )
        if "label" not in spec:
            issues.append(f"'{side}' is missing required 'label' key.")
        elif not isinstance(spec["label"], str):
            issues.append(f"'{side}.label' must be a string.")

    return issues


def _waterfall_issues(data: Any) -> list[str]:
    """Waterfall issues: ``labels`` / ``deltas`` (and ``is_total``) aligned."""
    issues = []
    if not _has(data, "labels"):
        issues.append("Missing 'labels' key (list of step labels).")
    if not _has(data, "deltas"):
        issues.append("Missing 'deltas' key (list of signed numeric values).")
    if (
        _has(data, "labels")
        and _has(data, "deltas")
        and _len(_at(data, "labels")) != _len(_at(data, "deltas"))
    ):
        issues.append(
            "Length mismatch: 'labels' and 'deltas' must have equal length."
        )
    if (
        _has(data, "is_total")
        and _has(data, "deltas")
        and _len(_at(data, "is_total")) != _len(_at(data, "deltas"))
    ):
        issues.append("Length mismatch: 'is_total' must align with 'deltas'.")
    return issues


def _small_multiples_issues(data: Any) -> list[str]:
    """Small-multiples issues: a ``panels`` list of equal-length ``x``/``y`` dicts."""
    issues = []
    if not _has(data, "panels"):
        issues.append(
            "Missing 'panels' key (list of {label, x, y} panel dicts)."
        )
    elif not isinstance(panels := _at(data, "panels"), list):
        issues.append("'panels' must be a list.")
    else:
        for i, panel in enumerate(panels):
            if not isinstance(panel, dict):
                issues.append(f"Panel #{i} is not a dict.")
                continue
            if "x" not in panel or "y" not in panel:
                issues.append(f"Panel #{i} missing 'x' or 'y'.")
                continue
            if _len(panel["x"]) != _len(panel["y"]):
                issues.append(f"Panel #{i}: 'x' and 'y' length mismatch.")
    return issues


def _polar_issues(data: Any) -> list[str]:
    """Polar issues: ``values`` (list or series dict) as long as ``categories``."""
    issues = []
    if not _has(data, "categories"):
        issues.append("Missing 'categories' key (list of axis labels).")
    if not _has(data, "values"):
        issues.append(
            "Missing 'values' key (list, or dict of series_name -> list)."
        )
    if _has(data, "categories") and _has(data, "values"):
        cat_len = _len(_at(data, "categories"))
        vals = _at(data, "values")
        if isinstance(vals, dict):
            for name, series in vals.items():
                if _len(series) != cat_len:
                    issues.append(
                        f"Series '{name}' length ({_len(series)}) != "
                        f"categories length ({cat_len})."
                    )
        elif isinstance(vals, list) and len(vals) != cat_len:
            issues.append(
                "Length mismatch: 'values' must equal 'categories' length."
            )
    return issues


def _plot_3d_issues(data: Any) -> list[str]:
    """Scatter: equal-length 1D ``x``/``y``/``z``; surface: 2D ``z`` matching ``y`` x ``x``."""
    issues = [
        f"Missing '{key}' key."
        for key in ("x", "y", "z")
        if not _has(data, key)
    ]
    if all(_has(data, k) for k in ("x", "y", "z")):
        z = _at(data, "z")
        if isinstance(z, list) and z and isinstance(z[0], list):
            # Surface: 2D z, x and y are 1D.
            if len(z) != _len(_at(data, "y")):
                issues.append(
                    "Surface mode: rows of 'z' must match 'y' length."
                )
            if z and len(z[0]) != _len(_at(data, "x")):
                issues.append(
                    "Surface mode: cols of 'z' must match 'x' length."
                )
        # Scatter: x, y, z all 1D and equal length.
        elif not (_len(_at(data, "x")) == _len(_at(data, "y")) == _len(z)):
            issues.append(
                "Scatter mode: 'x', 'y', and 'z' must have equal length."
            )
    return issues


def parse_tornado(data: object) -> PlotDataVerdict:
    """``categories`` with ``positive`` and/or ``negative`` arrays of equal length."""
    return _verdict("tornado plot", _tornado_issues, data)


def parse_scatter(data: object) -> PlotDataVerdict:
    """``x`` and ``y`` of equal length."""
    return _verdict("scatter plot", _scatter_issues, data)


def parse_bar(data: object) -> PlotDataVerdict:
    """``categories`` and ``values`` of equal length."""
    return _verdict("bar plot", _bar_issues, data)


def parse_bar_horizontal(data: object) -> PlotDataVerdict:
    """The vertical bar shape: ``categories`` and ``values`` of equal length."""
    return _verdict("horizontal bar plot", _bar_issues, data)


def parse_bar_grouped(data: object) -> PlotDataVerdict:
    """``categories`` and a ``series`` dict, each series as long as ``categories``."""
    return _verdict("grouped bar plot", _series_issues, data)


def parse_heatmap(data: object) -> PlotDataVerdict:
    """``matrix`` as a list of lists."""
    return _verdict("heatmap", _heatmap_issues, data)


def parse_stacked_bar(data: object) -> PlotDataVerdict:
    """``categories`` and a ``series`` dict, each series as long as ``categories``."""
    return _verdict("stacked bar", _series_issues, data)


def parse_pie(data: object) -> PlotDataVerdict:
    """``labels`` and ``sizes`` of equal length."""
    return _verdict("pie chart", _pie_issues, data)


def parse_line(data: object) -> PlotDataVerdict:
    """``x`` with ``y`` (one series) or ``series`` (named series)."""
    return _verdict("line plot", _line_issues, data)


def parse_violin(data: object) -> PlotDataVerdict:
    """Grouped numeric samples; see ``_grouped_samples_issues`` for the shapes."""
    return _verdict(
        "violin plot", lambda d: _grouped_samples_issues(d, "violin"), data
    )


def parse_boxplot(data: object) -> PlotDataVerdict:
    """Grouped numeric samples; see ``_grouped_samples_issues`` for the shapes."""
    return _verdict(
        "boxplot", lambda d: _grouped_samples_issues(d, "boxplot"), data
    )


def parse_histogram(data: object) -> PlotDataVerdict:
    """Numeric ``values`` with optional ``bins`` (a positive int or numeric edges)."""
    return _verdict("histogram", _histogram_issues, data)


def parse_contour(data: object) -> PlotDataVerdict:
    """A numeric 2-D ``Z`` with optional ``X`` / ``Y`` grids of its shape."""
    return _verdict("contour plot", _contour_issues, data)


def parse_twin_axis(data: object) -> PlotDataVerdict:
    """Numeric ``x`` with ``left`` / ``right`` dicts of a matching ``y`` and a ``label``."""
    return _verdict("twin-axis plot", _twin_axis_issues, data)


def parse_waterfall(data: object) -> PlotDataVerdict:
    """``labels`` and ``deltas`` of equal length, with an optional aligned ``is_total``."""
    return _verdict("waterfall plot", _waterfall_issues, data)


def parse_small_multiples(data: object) -> PlotDataVerdict:
    """``panels``: a list of dicts whose ``x`` and ``y`` have equal length."""
    return _verdict("small multiples", _small_multiples_issues, data)


def parse_polar(data: object) -> PlotDataVerdict:
    """``categories`` and ``values`` (a list, or a dict of series) of matching length."""
    return _verdict("polar plot", _polar_issues, data)


def parse_plot_3d(data: object) -> PlotDataVerdict:
    """``x``, ``y``, ``z`` as equal-length arrays or a ``z`` surface over ``x`` x ``y``."""
    return _verdict("3D plot", _plot_3d_issues, data)


PARSERS: Mapping[str, Callable[[object], PlotDataVerdict]] = {
    "tornado": parse_tornado,
    "scatter": parse_scatter,
    "bar": parse_bar,
    "bar_horizontal": parse_bar_horizontal,
    "bar_grouped": parse_bar_grouped,
    "heatmap": parse_heatmap,
    "stacked_bar": parse_stacked_bar,
    "pie": parse_pie,
    "line": parse_line,
    "violin": parse_violin,
    "boxplot": parse_boxplot,
    "histogram": parse_histogram,
    "contour": parse_contour,
    "twin_axis": parse_twin_axis,
    "waterfall": parse_waterfall,
    "small_multiples": parse_small_multiples,
    "polar": parse_polar,
    "plot_3d": parse_plot_3d,
}
