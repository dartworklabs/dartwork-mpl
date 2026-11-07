"""Pure chart-selection heuristics, independent of optional transports."""

from __future__ import annotations

#: The documented ``x_type`` and ``y_type`` values, in docstring order.
#: Both this function and the ``suggest_chart_type`` MCP tool type these as a
#: plain string and name the allowed values in prose only, so an unknown value
#: used to fall through to a default: a typo returned a confident chart label,
#: and the MCP wrapper then built a template URI for a chart nobody asked about
#: (#501 task 8). Enforcing the documented set is what makes the reply mean
#: what it says.
_X_TYPES = ("continuous", "categorical", "temporal")
_Y_TYPES = ("continuous", "categorical", "count")


def _check_type(value: str | None, allowed: tuple[str, ...], name: str) -> None:
    """Reject a value outside ``allowed``, naming the argument and the set."""
    if value in allowed:
        return
    permitted = ", ".join(repr(item) for item in allowed)
    optional = " or None" if name == "y_type" else ""
    raise ValueError(
        f"{name} must be one of {permitted}{optional}; got {value!r}. "
        "Unknown values cannot be guessed: the recommendation and the "
        "template it points at would describe different data than you have."
    )


def suggest_chart_type(
    x_type: str, y_type: str | None, n_points: int, n_series: int = 1
) -> str:
    """Suggest appropriate chart type based on data characteristics.

    Parameters
    ----------
    x_type : str
        Type of x data: "continuous", "categorical", "temporal"
    y_type : str | None
        Type of y data: "continuous", "categorical", "count", None
    n_points : int
        Number of data points
    n_series : int
        Number of data series

    Returns
    -------
    str
        Suggested chart type

    Raises
    ------
    ValueError
        If ``x_type`` or ``y_type`` is outside the documented set above.

    Examples
    --------
    >>> chart_type = suggest_chart_type("categorical", "continuous", 5, 1)
    >>> print(chart_type)  # "bar"
    """
    _check_type(x_type, _X_TYPES, "x_type")
    if y_type is not None:
        _check_type(y_type, _Y_TYPES, "y_type")

    if y_type is None:
        # Single variable
        if x_type == "continuous":
            return "histogram"
        if x_type == "categorical":
            return "count_bar"
        return "line"  # temporal

    # Two variables
    if x_type == "categorical":
        if n_series == 1:
            return "bar"
        return "grouped_bar"

    if x_type == "temporal":
        if n_series == 1:
            if n_points < 20:
                return "bar_line"  # Bar with line overlay
            return "line"
        return "multi_line"

    # x_type == "continuous", the only remaining validated value. This used to
    # be guarded by an ``if`` with a trailing ``return "scatter"`` default; with
    # the set enforced the default was unreachable, and keeping it would have
    # read as a live fallback.
    if y_type == "continuous":
        if n_points < 50:
            return "scatter"
        if n_points < 500:
            return "scatter_density"
        return "hexbin"
    return "line"


# Preserve historical pickle lookup and callable metadata.
suggest_chart_type.__module__ = "dartwork_mpl.helpers.quality"
