"""Label and legend helpers.

Higher-level composition helpers for legend placement. Renamed from
``helpers.formatting`` to avoid the name clash with the top-level
``dartwork_mpl.formatting`` module (which houses the ``format_axis_*``
tick formatters).

For axis labels, use ``ax.set_xlabel`` / ``ax.set_ylabel`` directly.
For per-point value annotations, use an ``ax.text`` loop inline.
"""

from ..annotation import optimize_legend as optimize_legend

__all__ = ["optimize_legend"]
