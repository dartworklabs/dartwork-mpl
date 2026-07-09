"""Label and legend helpers.

Higher-level composition helpers for legend placement. Renamed from
``helpers.formatting`` to avoid the name clash with the top-level
``dartwork_mpl.formatting`` module (which houses the ``format_axis_*``
tick formatters).

For axis labels, use ``ax.set_xlabel`` / ``ax.set_ylabel`` directly.
For per-point value annotations, use an ``ax.text`` loop inline.
"""

from __future__ import annotations

from matplotlib.axes import Axes

from ..scale import fs


def optimize_legend(
    ax: Axes,
    preferred_loc: str = "best",
    max_cols: int = 3,
    outside: bool = False,
) -> None:
    """Optimize legend placement and formatting.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    preferred_loc : str
        Preferred location if space permits
    max_cols : int
        Maximum number of columns for legend
    outside : bool
        Whether to place legend outside plot area

    Examples
    --------
    >>> optimize_legend(ax, preferred_loc="upper right")
    >>> optimize_legend(ax, outside=True)
    """
    # ``edgecolor="oc.gray3"`` below needs the dartwork colours registered;
    # don't depend on an import side effect having already loaded them.
    from .._colors._loader import ensure_loaded

    ensure_loaded()
    handles, _labels = ax.get_legend_handles_labels()
    if not handles:
        return

    n_items = len(handles)

    # Determine number of columns
    if n_items <= 3:
        ncol = 1
    elif n_items <= 6:
        ncol = min(2, max_cols)
    else:
        ncol = min(3, max_cols)

    # Legend parameters
    legend_params = {
        "fontsize": fs(-1),
        "framealpha": 0.95,
        "edgecolor": "oc.gray3",
        "ncol": ncol,
    }

    if outside:
        # Place outside plot area
        legend_params["bbox_to_anchor"] = (1.02, 1)
        legend_params["loc"] = "upper left"
    else:
        # Inside plot area
        legend_params["loc"] = preferred_loc

    ax.legend(**legend_params)
