"""Per-template data-shape validators behind ``validate_plot_data``.

Each ``_validate_<plot_type>(data)`` takes the decoded JSON payload and
returns the tool's message: a ``"✅ Data structure valid ..."`` line, or the
newline-joined issues. Pure: no I/O, no other unit. A wrong-typed field may
raise ``TypeError`` / ``KeyError`` / ``ValueError`` / ``AttributeError``; the
caller (``validate.validate_data``) turns those into its structured message.
"""

from typing import Any


def _validate_tornado(data: dict[str, Any]) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "positive" not in data and "negative" not in data:
        issues.append(
            "Need at least 'positive' and/or 'negative' value arrays."
        )
    if (
        "categories" in data
        and "positive" in data
        and len(data["categories"]) != len(data["positive"])
    ):
        issues.append(
            "Length mismatch: 'categories' and 'positive' must have equal length."
        )
    return (
        "✅ Data structure valid for tornado plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_scatter(data: dict[str, Any]) -> str:
    issues = []
    if "x" not in data:
        issues.append("Missing 'x' key (list of x-coordinates).")
    if "y" not in data:
        issues.append("Missing 'y' key (list of y-coordinates).")
    if "x" in data and "y" in data and len(data["x"]) != len(data["y"]):
        issues.append("Length mismatch: 'x' and 'y' must have equal length.")
    return (
        "✅ Data structure valid for scatter plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_bar(data: dict[str, Any]) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "values" not in data:
        issues.append("Missing 'values' key (list of numeric values).")
    if (
        "categories" in data
        and "values" in data
        and len(data["categories"]) != len(data["values"])
    ):
        issues.append(
            "Length mismatch: 'categories' and 'values' must have equal length."
        )
    return (
        "✅ Data structure valid for bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_heatmap(data: dict[str, Any]) -> str:
    issues = []
    if "matrix" not in data:
        issues.append("Missing 'matrix' key (2D array of numeric values).")
    elif not isinstance(data["matrix"], list) or not all(
        isinstance(row, list) for row in data["matrix"]
    ):
        issues.append("'matrix' must be a 2D array (list of lists).")
    return (
        "✅ Data structure valid for heatmap."
        if not issues
        else "\n".join(issues)
    )


def _validate_stacked_bar(data: dict[str, Any]) -> str:
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key.")
    if "series" not in data:
        issues.append("Missing 'series' key (dict of series_name -> values).")
    elif isinstance(data["series"], dict):
        cat_len = len(data.get("categories", []))
        for name, vals in data["series"].items():
            if len(vals) != cat_len:
                issues.append(
                    f"Series '{name}' length ({len(vals)}) != categories length ({cat_len})."
                )
    return (
        "✅ Data structure valid for stacked bar."
        if not issues
        else "\n".join(issues)
    )


def _validate_pie(data: dict[str, Any]) -> str:
    issues = []
    if "labels" not in data:
        issues.append("Missing 'labels' key.")
    if "sizes" not in data:
        issues.append("Missing 'sizes' key (list of numeric values).")
    if (
        "labels" in data
        and "sizes" in data
        and len(data["labels"]) != len(data["sizes"])
    ):
        issues.append(
            "Length mismatch: 'labels' and 'sizes' must have equal length."
        )
    return (
        "✅ Data structure valid for pie chart."
        if not issues
        else "\n".join(issues)
    )


def _validate_line(data: dict[str, Any]) -> str:
    issues = []
    if "x" not in data:
        issues.append("Missing 'x' key (list of x values or time points).")
    if "y" not in data and "series" not in data:
        issues.append(
            "Need 'y' (single series) or 'series' (dict of named series)."
        )
    return (
        "✅ Data structure valid for line plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_grouped_samples(
    data: dict[str, Any], plot_label: str
) -> list[str]:
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


def _validate_violin(data: dict[str, Any]) -> str:
    """Validate data for a violin plot.

    See :func:`_validate_grouped_samples` for the accepted shapes.
    """
    issues = _validate_grouped_samples(data, "violin")
    return (
        "✅ Data structure valid for violin plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_boxplot(data: dict[str, Any]) -> str:
    """Validate data for a boxplot.

    See :func:`_validate_grouped_samples` for the accepted shapes.
    """
    issues = _validate_grouped_samples(data, "boxplot")
    return (
        "✅ Data structure valid for boxplot."
        if not issues
        else "\n".join(issues)
    )


def _validate_histogram(data: dict[str, Any]) -> str:
    """Validate data for a histogram.

    Required: ``values`` — a 1-D list of numbers.
    Optional: ``bins`` — either a positive integer or a 1-D list of
    numeric bin edges.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return "histogram data must be a JSON object (dict)."

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

    return (
        "✅ Data structure valid for histogram."
        if not issues
        else "\n".join(issues)
    )


def _validate_contour(data: dict[str, Any]) -> str:
    """Validate data for a contour plot.

    Required: ``Z`` — a 2-D array (list of lists) with rows of equal
    length and at least one row/column.
    Optional: ``X``, ``Y`` — meshgrid 2-D arrays with the same shape
    as ``Z``.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return "contour data must be a JSON object (dict)."

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

    return (
        "✅ Data structure valid for contour plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_twin_axis(data: dict[str, Any]) -> str:
    """Validate data for a twin-axis chart.

    Required:

    * ``x`` — a list of numeric values.
    * ``left`` — a dict with keys ``y`` (numeric list, same length
      as ``x``) and ``label`` (string).
    * ``right`` — same shape as ``left``.
    """
    issues: list[str] = []
    if not isinstance(data, dict):
        return "twin_axis data must be a JSON object (dict)."

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

    return (
        "✅ Data structure valid for twin-axis plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_bar_horizontal(data: dict[str, Any]) -> str:
    """Validate data for a horizontal bar chart.

    Same shape as a vertical bar: ``categories`` + ``values``.
    """
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of category labels).")
    if "values" not in data:
        issues.append("Missing 'values' key (list of numeric values).")
    if (
        "categories" in data
        and "values" in data
        and len(data["categories"]) != len(data["values"])
    ):
        issues.append(
            "Length mismatch: 'categories' and 'values' must have equal length."
        )
    return (
        "✅ Data structure valid for horizontal bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_bar_grouped(data: dict[str, Any]) -> str:
    """Validate data for a grouped (dodged) bar chart.

    Expected: ``categories`` + ``series`` (dict of series_name -> values),
    each series same length as ``categories``.
    """
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key.")
    if "series" not in data:
        issues.append("Missing 'series' key (dict of series_name -> values).")
    elif isinstance(data["series"], dict):
        cat_len = len(data.get("categories", []))
        for name, vals in data["series"].items():
            if len(vals) != cat_len:
                issues.append(
                    f"Series '{name}' length ({len(vals)}) != "
                    f"categories length ({cat_len})."
                )
    return (
        "✅ Data structure valid for grouped bar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_waterfall(data: dict[str, Any]) -> str:
    """Validate data for a waterfall (bridge) chart.

    Expected: ``labels`` + ``deltas`` (signed contributions). Optional
    ``is_total`` flag list selects total/anchor bars.
    """
    issues = []
    if "labels" not in data:
        issues.append("Missing 'labels' key (list of step labels).")
    if "deltas" not in data:
        issues.append("Missing 'deltas' key (list of signed numeric values).")
    if (
        "labels" in data
        and "deltas" in data
        and len(data["labels"]) != len(data["deltas"])
    ):
        issues.append(
            "Length mismatch: 'labels' and 'deltas' must have equal length."
        )
    if (
        "is_total" in data
        and "deltas" in data
        and len(data["is_total"]) != len(data["deltas"])
    ):
        issues.append("Length mismatch: 'is_total' must align with 'deltas'.")
    return (
        "✅ Data structure valid for waterfall plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_small_multiples(data: dict[str, Any]) -> str:
    """Validate data for small multiples / faceted panels.

    Expected: ``panels`` (list of {label, x, y} dicts). Each panel's
    ``x`` and ``y`` arrays must have equal length.
    """
    issues = []
    if "panels" not in data:
        issues.append(
            "Missing 'panels' key (list of {label, x, y} panel dicts)."
        )
    elif not isinstance(data["panels"], list):
        issues.append("'panels' must be a list.")
    else:
        for i, panel in enumerate(data["panels"]):
            if not isinstance(panel, dict):
                issues.append(f"Panel #{i} is not a dict.")
                continue
            if "x" not in panel or "y" not in panel:
                issues.append(f"Panel #{i} missing 'x' or 'y'.")
                continue
            if len(panel["x"]) != len(panel["y"]):
                issues.append(f"Panel #{i}: 'x' and 'y' length mismatch.")
    return (
        "✅ Data structure valid for small multiples."
        if not issues
        else "\n".join(issues)
    )


def _validate_polar(data: dict[str, Any]) -> str:
    """Validate data for a polar / radar chart.

    Expected: ``categories`` (axis labels) + ``values`` (one value per
    category). For multi-series radar, ``values`` may be a dict of
    series_name -> values.
    """
    issues = []
    if "categories" not in data:
        issues.append("Missing 'categories' key (list of axis labels).")
    if "values" not in data:
        issues.append(
            "Missing 'values' key (list, or dict of series_name -> list)."
        )
    if "categories" in data and "values" in data:
        cat_len = len(data["categories"])
        vals = data["values"]
        if isinstance(vals, dict):
            for name, series in vals.items():
                if len(series) != cat_len:
                    issues.append(
                        f"Series '{name}' length ({len(series)}) != "
                        f"categories length ({cat_len})."
                    )
        elif isinstance(vals, list) and len(vals) != cat_len:
            issues.append(
                "Length mismatch: 'values' must equal 'categories' length."
            )
    return (
        "✅ Data structure valid for polar plot."
        if not issues
        else "\n".join(issues)
    )


def _validate_plot_3d(data: dict[str, Any]) -> str:
    """Validate data for a 3D scatter / surface plot.

    Expected: ``x``, ``y``, ``z`` arrays of equal length (scatter)
    or 2D ``z`` matrix matching ``x`` x ``y`` (surface).
    """
    issues = [
        f"Missing '{key}' key." for key in ("x", "y", "z") if key not in data
    ]
    if all(k in data for k in ("x", "y", "z")):
        z = data["z"]
        if isinstance(z, list) and z and isinstance(z[0], list):
            # Surface: 2D z, x and y are 1D.
            if len(z) != len(data["y"]):
                issues.append(
                    "Surface mode: rows of 'z' must match 'y' length."
                )
            if z and len(z[0]) != len(data["x"]):
                issues.append(
                    "Surface mode: cols of 'z' must match 'x' length."
                )
        else:
            # Scatter: x, y, z all 1D and equal length.
            if not (len(data["x"]) == len(data["y"]) == len(z)):
                issues.append(
                    "Scatter mode: 'x', 'y', and 'z' must have equal length."
                )
    return (
        "✅ Data structure valid for 3D plot."
        if not issues
        else "\n".join(issues)
    )
