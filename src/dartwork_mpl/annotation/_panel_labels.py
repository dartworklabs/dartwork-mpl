"""Panel labels (a, b, c ...) for the Axes of a figure and their placement before a title."""

from __future__ import annotations

import inspect
import string
from typing import Any

import numpy as np
from matplotlib import cbook
from matplotlib.axes import Axes
from matplotlib.text import Text

from .._figure_geometry import BBOX_ERRORS, axes_titles
from ..scale import fs
from ._placement_geometry import _renderer_for_axes


def _auto_panel_labels(n: int) -> list[str]:
    """Spreadsheet-style panel labels: a, b, ..., z, aa, ab, ....

    ``string.ascii_lowercase[:n]`` silently truncated at 26, dropping
    labels for any grid larger than 26 panels; this extends past z.
    """
    labels: list[str] = []
    for i in range(n):
        chars = ""
        k = i
        while True:
            chars = string.ascii_lowercase[k % 26] + chars
            k = k // 26 - 1
            if k < 0:
                break
        labels.append(chars)
    return labels


# Gap between a panel label and the title it precedes, in label font sizes.
_PANEL_LABEL_GAP_EM = 0.5


def _shown_title(ax: Axes, loc: str) -> Text | None:
    """Return the ``loc`` title of ``ax`` when it is visible and not blank."""
    title = axes_titles(ax).get(loc)
    if title is None or not title.get_visible() or not title.get_text().strip():
        return None
    return title


def _title_in_the_way(ax: Axes, label: Text, gap_pt: float) -> Text | None:
    """Return the title of ``ax`` that ``label`` must sit before, if any.

    A left title always: the label belongs on its line, so every panel of a
    grid reads the same. A centre or right title only when ``label`` at its
    default spot would come within ``gap_pt`` of it (measured after a
    draw); then the leftmost such title.
    """
    left = _shown_title(ax, "left")
    if left is not None:
        return left
    others = [
        title
        for loc in ("center", "right")
        if (title := _shown_title(ax, loc)) is not None
    ]
    if not others:
        return None
    fig, renderer = _renderer_for_axes(ax)
    gap_px = gap_pt * fig.dpi / 72.0
    try:
        box = label.get_window_extent(renderer)
    except BBOX_ERRORS:
        return None
    hits: list[tuple[float, Text]] = []
    for title in others:
        try:
            ext = title.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if (
            box.x1 + gap_px > ext.x0
            and box.x0 < ext.x1 + gap_px
            and box.y1 > ext.y0
            and box.y0 < ext.y1
        ):
            hits.append((ext.x0, title))
    return min(hits, key=lambda hit: hit[0])[1] if hits else None


#: Properties ``label_axes`` sets on the label itself. Passing any spelling of
#: these used to collide inside ``ax.text`` (``ha``, ``va``, ``transform``) or be
#: accepted and then overridden without a word (the full alignment names).
_LABEL_AXES_OWNED_KWARGS = frozenset(
    {"ha", "horizontalalignment", "transform", "va", "verticalalignment"}
)

#: What the agent most likely meant, for the arguments #483 saw in real loops.
_LABEL_AXES_KWARG_HINTS = {
    "fmt": (
        "There is no format string: pass finished strings with labels=, "
        "for example labels=[f'({c})' for c in 'abc']. "
    ),
    "loc": "Use x= and y=, which are Axes-relative, for placement. ",
    "xy": "Use x= and y=, which are Axes-relative, for placement. ",
}

_LABEL_AXES_NATIVE_ESCAPE = (
    "For a different placement API, write the text yourself with "
    "ax.text(x, y, label, transform=ax.transAxes)."
)


#: ``Axes.text`` arguments of its own, which are not ``Text`` setters and so
#: would be misread as unsupported. Taken from the signature rather than listed,
#: so the check cannot drift from the matplotlib in use. Today: ``fontdict``.
_AXES_TEXT_OWN_PARAMETERS = frozenset(
    name
    for name, parameter in inspect.signature(Axes.text).parameters.items()
    if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    and name not in {"self", "x", "y", "s"}
)


def _label_kwarg_is_accepted(name: str) -> bool:
    """Report whether the label call takes ``name``, resolving matplotlib aliases."""
    if name in _AXES_TEXT_OWN_PARAMETERS:
        return True
    try:
        canonical = next(iter(cbook.normalize_kwargs({name: None}, Text)))
    except TypeError:
        return False
    return callable(getattr(Text, f"set_{canonical}", None))


def _reject_unusable_label_kwargs(kwargs: dict[str, Any]) -> None:
    """Fail named, before any label exists, for kwargs that cannot be honoured."""
    for name in kwargs:
        if name in _LABEL_AXES_OWNED_KWARGS:
            raise TypeError(
                f"label_axes() sets {name!r} on the panel labels itself, so "
                f"passing {name!r} cannot take effect. Position the labels with "
                f"x= and y= (both Axes-relative). {_LABEL_AXES_NATIVE_ESCAPE}"
            )
        if not _label_kwarg_is_accepted(name):
            raise AttributeError(
                f"label_axes() does not support {name!r}. It takes labels=, x=, "
                f"y=, fontsize=, fontweight= and any matplotlib Text property "
                f"(color=, rotation=, fontstyle=, ...). "
                f"{_LABEL_AXES_KWARG_HINTS.get(name, '')}"
                f"{_LABEL_AXES_NATIVE_ESCAPE}"
            )


def label_axes(
    axes: list[Axes] | np.ndarray[Any, Any],
    labels: list[str] | None = None,
    fontsize: float | None = None,
    fontweight: str = "normal",
    x: float | str = "auto",
    y: float | None = None,
    **kwargs: Any,
) -> list[Text]:
    """Add standardized identification labels (a, b, c, ...) to subplot panels.

    Commonly used in academic papers and reports to annotate multiple panels
    of a figure, placing labels at the left edge or top corner of each Axes.

    Parameters
    ----------
    axes : list[Axes] | np.ndarray
        List or array of Axes objects to label.
    labels : list[str] | None, optional
        Custom text labels. If None, lowercase letters (a, b, c, ...)
        are assigned automatically.
    fontsize : float | None, optional
        Font size for the labels. If ``None`` (default), resolves to
        ``fs(1)`` so panel labels track the active preset's base font
        size instead of a fixed point value.
    fontweight : str, optional
        Font weight for the labels. Default is "normal".
    x : float | str, optional
        Horizontal position in Axes-relative coordinates (may exceed 0.0-1.0).
        If "auto", the optimal x position is determined based on whether
        a y-axis label is present (-0.18 or -0.02). With ``"auto"`` and a
        title in the way, the label is placed before the title instead: on
        the title's line, its right edge half a label font size left of
        the title's start, following the title wherever it moves (a later
        ``simple_layout``, a legend above). A left title
        (``set_title(..., loc="left")``) is always in the way, so every
        panel of a grid reads ``a  Title``; a centre or right title only
        when the label at its default spot would touch it. Set the titles
        before calling this; their text, size and weight are not changed.
    y : float | None, optional
        Vertical position in Axes-relative coordinates. ``None`` (default)
        is 1.05, or the title's line when the label is placed before a
        title. A given ``y`` is kept in both cases.
    **kwargs
        Additional text properties passed to ``ax.text()`` (``ax.annotate``
        for a label placed before a title). An argument this helper cannot
        honour is reported by name: one ``Text`` does not accept raises
        ``AttributeError``, and a property the helper sets itself
        (``transform``, and either spelling of the alignments) raises
        ``TypeError``. ``fontdict`` reaches ``ax.text`` but not
        ``ax.annotate``, so it fails on a panel whose label moves onto a
        title's line; passing the properties directly (``color=``,
        ``fontsize=``) works on both paths.

    Returns
    -------
    list
        List of created Text objects.
    """
    _reject_unusable_label_kwargs(kwargs)

    if fontsize is None:
        fontsize = fs(1)

    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = _auto_panel_labels(len(axes))

    texts: list[Text] = []
    for ax, label in zip(axes, labels, strict=False):
        if x == "auto":
            has_ylabel = ax.get_ylabel().strip() != ""
            x_pos = -0.18 if has_ylabel else -0.02
        else:
            x_pos = float(x)

        t = ax.text(
            x_pos,
            1.05 if y is None else y,
            label,
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va="bottom",
            ha="left",
            **kwargs,
        )
        if x == "auto":
            size_pt = t.get_fontproperties().get_size_in_points()
            gap_pt = _PANEL_LABEL_GAP_EM * size_pt
            title = _title_in_the_way(ax, t, gap_pt)
            if title is not None:
                t.remove()
                t = ax.annotate(
                    label,
                    xy=(0.0, 0.0 if y is None else y),
                    xycoords=title if y is None else (title, "axes fraction"),
                    xytext=(-gap_pt, 0.0),
                    textcoords="offset points",
                    fontsize=fontsize,
                    fontweight=fontweight,
                    va="bottom",
                    ha="right",
                    annotation_clip=False,
                    **kwargs,
                )
        texts.append(t)

    return texts
