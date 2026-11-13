"""Panel labels (a, b, c ...) placed from what each panel draws: its y-axis name and its title."""

from __future__ import annotations

import string
from typing import Any

import numpy as np
from matplotlib import cbook
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox, IdentityTransform

from .._figure_geometry import BBOX_ERRORS, axes_titles, get_renderer
from ..scale import fs
from ._kwarg_guard import AXES_TEXT_PARAMETERS, reject_unusable_kwargs


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


def _owned_label_kwarg(name: str) -> str:
    return (
        f"label_axes() sets {name!r} on the panel labels itself, so "
        f"passing {name!r} cannot take effect. Position the labels with "
        f"x= and y= (both Axes-relative). {_LABEL_AXES_NATIVE_ESCAPE}"
    )


def _unsupported_label_kwarg(name: str) -> str:
    return (
        f"label_axes() does not support {name!r}. It takes labels=, x=, "
        f"y=, fontsize=, fontweight= and any matplotlib Text property "
        f"(color=, rotation=, fontstyle=, ...). "
        f"{_LABEL_AXES_KWARG_HINTS.get(name, '')}"
        f"{_LABEL_AXES_NATIVE_ESCAPE}"
    )


def _reject_unusable_label_kwargs(kwargs: dict[str, Any]) -> None:
    """Fail named, before any label exists, for kwargs that cannot be honoured."""
    reject_unusable_kwargs(
        kwargs,
        owned=_LABEL_AXES_OWNED_KWARGS,
        artist=Text,
        parameters=AXES_TEXT_PARAMETERS,
        owned_error=_owned_label_kwarg,
        unsupported_error=_unsupported_label_kwarg,
    )


# ── placement measured from the drawn panel ─────────────────────────
#
# With ``x="auto"`` a label is an Annotation at the top-left corner of its
# Axes (Axes fraction (0, 1)), shifted by an offset in points. The offset is
# measured from what the panel draws: the outer edge of its y-axis name and
# the baseline of its title. Points survive a layout that resizes the Axes,
# and ``dm.simple_layout`` measures the panels again on every step
# (:func:`settle_panel_labels`), after tick labels and titles have settled.

#: Above the top decoration of a panel without a title, in points.
_TOP_GAP_PT = 4.0
#: Between the label and the left decoration (y-axis name, tick labels)
#: below it, when that decoration rises above the panel, in points.
_CLEARANCE_PT = 2.0

#: Where a figure keeps the groups of labels ``label_axes`` placed.
_GROUPS_ATTR = "_dm_panel_label_groups"


class _Group:
    """The labels one ``label_axes(x="auto")`` call placed.

    ``fixed_y`` is the Axes-relative ``y`` the caller gave, or ``None``
    for the title-baseline rule.
    """

    def __init__(
        self, members: list[tuple[Axes, Annotation]], fixed_y: float | None
    ) -> None:
        self.members = members
        self.fixed_y = fixed_y


def _shown(text: Text) -> bool:
    return text.get_visible() and bool(text.get_text().strip())


def _grid_cell(ax: Axes) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """The row and the column of its top-level grid ``ax`` starts in, each
    keyed by that grid.

    A colour bar made with ``fig.colorbar(..., ax=ax)`` splits the cell
    into a nested grid; the panel still belongs to its top-level cell.
    Each SubFigure (and each ``add_gridspec``) has a grid of its own, so
    row 0 of one is not row 0 of another.
    """
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    top = spec.get_topmost_subplotspec()
    grid = id(top.get_gridspec())
    return (grid, top.rowspan.start), (grid, top.colspan.start)


def _ylabel_box(ax: Axes, renderer: Any) -> Bbox | None:
    """The y-axis name of ``ax`` when it is drawn on the left."""
    label = ax.yaxis.label
    # matplotlib's stub types the position as top/bottom; it is left/right.
    if not _shown(label) or str(ax.yaxis.get_label_position()) != "left":
        return None
    try:
        return label.get_window_extent(renderer)
    except BBOX_ERRORS:
        return None


def _ytick_box(ax: Axes, renderer: Any) -> Bbox | None:
    """The left y tick labels of ``ax`` that are drawn (inside the view)."""
    lo, hi = sorted(ax.get_ylim())
    boxes: list[Bbox] = []
    for tick in ax.yaxis.get_major_ticks():
        label = tick.label1
        if not _shown(label):
            continue
        if not lo - 1e-9 <= tick.get_loc() <= hi + 1e-9:
            continue
        try:
            boxes.append(label.get_window_extent(renderer))
        except BBOX_ERRORS:
            continue
    return Bbox.union(boxes) if boxes else None


def _baseline_px(text: Text, renderer: Any) -> float:
    """The baseline of ``text`` in display pixels.

    A baseline-aligned Text's anchor is its baseline (an Annotation's
    transform places its text position once drawn); any other alignment is
    converted with the descent of the same string in the same font.
    """
    if text.get_verticalalignment() == "baseline":
        return float(text.get_transform().transform(text.get_position())[1])
    probe = Text(
        0,
        0,
        text.get_text(),
        fontproperties=text.get_fontproperties(),
        va="baseline",
    )
    probe.set_figure(text.figure)
    probe.set_transform(IdentityTransform())
    descent = -probe.get_window_extent(renderer).y0
    return float(text.get_window_extent(renderer).y0 + descent)


def _virtual_ylabel_left(ax: Axes, renderer: Any) -> float:
    """Where the outer edge of a y-axis name of ``ax`` would be, in px."""
    k = ax.figure.dpi / 72.0
    x0 = float(ax.transAxes.transform((0.0, 1.0))[0])
    ticks = _ytick_box(ax, renderer)
    inner = min(x0, ticks.x0) if ticks is not None else x0
    _w, height, _d = renderer.get_text_width_height_descent(
        "Ag", ax.yaxis.label.get_fontproperties(), ismath=False
    )
    return inner - float(ax.yaxis.labelpad) * k - float(height)


def _titles_in_the_way(
    ax: Axes, left: float, width: float, gap: float, renderer: Any
) -> list[Bbox]:
    """Title boxes the label at ``left`` must stay ``gap`` px before.

    A left title always counts (the label belongs before it on its line);
    a centre or right title only when the label's span reaches it.
    """
    boxes: list[Bbox] = []
    for loc, title in axes_titles(ax).items():
        if not _shown(title):
            continue
        try:
            ext = title.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if loc == "left" or (
            left < ext.x1 + gap and left + width + gap > ext.x0
        ):
            boxes.append(ext)
    return boxes


def _place_group(group: _Group, renderer: Any) -> bool:
    """Put each label of ``group`` where the rule says; ``True`` if one moved."""
    # A label removed since (``text.remove()``) is no longer placed.
    live = [
        (ax, t) for ax, t in group.members if t.axes is ax and t in ax.texts
    ]
    if not live:
        return False
    axes = [ax for ax, _t in live]
    texts = [t for _ax, t in live]
    root = axes[0].get_figure(root=True)
    if root is None:
        return False
    k = root.dpi / 72.0
    corners = [
        tuple(map(float, ax.transAxes.transform((0.0, 1.0)))) for ax in axes
    ]
    cells = [_grid_cell(ax) for ax in axes]
    widths = [t.get_window_extent(renderer).width for t in texts]
    rows: dict[tuple[int, int], list[int]] = {}
    cols: dict[tuple[int, int], list[int]] = {}
    for i, cell in enumerate(cells):
        if cell is not None:
            rows.setdefault(cell[0], []).append(i)
            cols.setdefault(cell[1], []).append(i)

    # Horizontal: the outer edge of the y-axis name; a column takes its
    # leftmost.
    lefts: list[float | None] = []
    for ax in axes:
        box = _ylabel_box(ax, renderer) if ax.name == "rectilinear" else None
        lefts.append(None if box is None else float(box.x0))
    for members in cols.values():
        known = [v for i in members if (v := lefts[i]) is not None]
        if known:
            for i in members:
                lefts[i] = min(known)
    # A panel with no y-axis name in its column keeps the spine distance of
    # the named panels: the largest in its row, else in the figure; with no
    # name anywhere, where a name would be.
    reach = {i: corners[i][0] - v for i, v in enumerate(lefts) if v is not None}
    for i, value in enumerate(lefts):
        if value is not None:
            continue
        cell = cells[i]
        same_row = (
            [reach[j] for j in rows.get(cell[0], []) if j in reach]
            if cell
            else []
        )
        if same_row or reach:
            lefts[i] = corners[i][0] - max(same_row or list(reach.values()))
        elif axes[i].name == "rectilinear":
            lefts[i] = _virtual_ylabel_left(axes[i], renderer)
        else:
            lefts[i] = corners[i][0]
    placed: list[float] = [float(v) for v in lefts if v is not None]
    # A title in the way: the label's right edge half a label size before
    # it (2026-11-13 owner decision, PoC 11-A: the rule first, a left title
    # only pushes the label further left, never pulls it onto the title).
    for i, (ax, text) in enumerate(zip(axes, texts, strict=True)):
        gap = _PANEL_LABEL_GAP_EM * float(text.get_fontsize()) * k
        for box in _titles_in_the_way(ax, placed[i], widths[i], gap, renderer):
            placed[i] = min(placed[i], float(box.x0) - gap - widths[i])
    for members in cols.values():
        value = min(placed[i] for i in members)
        for i in members:
            placed[i] = value

    # Vertical: the title's baseline; without a title, a little above the
    # panel's top decoration, raised to the highest baseline of its row;
    # clear of a y-axis name or tick label that rises above the panel. A
    # titled panel keeps its own title's baseline (2026-11-13 owner
    # decision, PoC 10-B: a neighbour's title lifted over a legend does not
    # lift this label off its own title).
    baselines: list[float] = []
    titled: list[bool] = []
    for i, (ax, text) in enumerate(zip(axes, texts, strict=True)):
        titles = [t for t in axes_titles(ax).values() if _shown(t)]
        titled.append(bool(titles))
        if titles:
            base = max(_baseline_px(t, renderer) for t in titles)
        else:
            top = corners[i][1]
            try:
                xbox = ax.xaxis.get_tightbbox(renderer)
            except BBOX_ERRORS:
                xbox = None
            if xbox is not None:
                top = max(top, float(xbox.y1))
            base = top + _TOP_GAP_PT * k
        box = text.get_window_extent(renderer)
        descent = _baseline_px(text, renderer) - float(box.y0)
        x0, x1 = placed[i], placed[i] + widths[i]
        for deco in (_ylabel_box(ax, renderer), _ytick_box(ax, renderer)):
            if deco is not None and deco.x0 < x1 and deco.x1 > x0:
                base = max(base, float(deco.y1) + _CLEARANCE_PT * k + descent)
        baselines.append(base)
    for members in rows.values():
        value = max(baselines[i] for i in members)
        for i in members:
            if not titled[i]:
                baselines[i] = value

    moved = False
    for i, text in enumerate(texts):
        dx = (placed[i] - corners[i][0]) / k
        dy = (
            0.0
            if group.fixed_y is not None
            else (baselines[i] - corners[i][1]) / k
        )
        old = text.xyann
        if abs(old[0] - dx) > 1e-3 or abs(old[1] - dy) > 1e-3:
            text.xyann = (dx, dy)
            moved = True
    return moved


def settle_panel_labels(fig: Figure, renderer: Any) -> bool:
    """Place the automatic panel labels of ``fig`` for the figure as drawn.

    ``dm.simple_layout`` runs this on every step, after the tick labels,
    legends and titles of that step have settled. Returns whether a label
    moved (the caller redraws before measuring).
    """
    groups: list[_Group] = getattr(fig.get_figure(root=True), _GROUPS_ATTR, [])
    moved = False
    for group in groups:
        moved = _place_group(group, renderer) or moved
    return moved


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
    of a figure, placing each label above the top-left corner of its Axes.

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
        ``"auto"`` (default) places each label from what its panel draws,
        in points, so every panel of a figure reads the same whatever its
        size:

        - its left edge on the outer edge of the panel's y-axis name; a
          grid column takes its leftmost (a colour bar's nested grid
          counts as its panel's column). A panel with no y-axis name in
          its column keeps the spine distance of the named panels (the
          largest in its row, else in the figure); with no y-axis name in
          the whole call, the label goes where one would be (past the tick
          labels by the name's pad and line height).
        - its baseline on the panel's title baseline. A panel without a
          title takes the highest baseline of its grid row, or 4 pt above
          its top decoration when that is higher. A y-axis name or tick
          label that rises above the panel and lies under the label keeps
          2 pt below it.
        - a title in the way (a left title, or a centre or right title the
          label would reach) keeps the label's right edge half a label
          font size before it.

        ``dm.simple_layout`` measures the panels again at the size it
        settles on, so call this first. A number is an Axes-relative
        position (may exceed 0.0-1.0), with the label's left edge there.
    y : float | None, optional
        ``None`` (default): the baseline rule above, or 1.05 with a numeric
        ``x``. A number is an Axes-relative position for the label's bottom
        edge, kept with ``x="auto"`` too.
    **kwargs
        Additional text properties (``color=``, ``rotation=``,
        ``fontstyle=``, ``fontdict=``, ...). An argument this helper cannot
        honour is reported by name: one ``Text`` does not accept raises
        ``AttributeError``, and a property the helper sets itself
        (``transform``, and either spelling of the alignments) raises
        ``TypeError``.

    Returns
    -------
    list
        List of created Text objects (Annotations with ``x="auto"``).
    """
    _reject_unusable_label_kwargs(kwargs)

    if fontsize is None:
        fontsize = fs(1)

    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = _auto_panel_labels(len(axes))

    if x != "auto":
        texts: list[Text] = []
        for ax, label in zip(axes, labels, strict=False):
            texts.append(
                ax.text(
                    float(x),
                    1.05 if y is None else y,
                    label,
                    transform=ax.transAxes,
                    fontsize=fontsize,
                    fontweight=fontweight,
                    va="bottom",
                    ha="left",
                    **kwargs,
                )
            )
        return texts

    # ``fontdict`` is an ``Axes.text`` argument; ``annotate`` takes the
    # properties directly. As in ``ax.text``, a ``fontdict`` key the helper
    # sets gives way to it (its aliases folded first, so ``size`` is
    # ``fontsize``) and the keywords win over both; a keyword alias of a
    # set property keeps matplotlib's own error.
    fontdict = kwargs.pop("fontdict", None) or {}
    properties = {
        **cbook.normalize_kwargs(fontdict, Text),
        "fontsize": fontsize,
        "fontweight": fontweight,
        "verticalalignment": "baseline" if y is None else "bottom",
        "horizontalalignment": "left",
        **kwargs,
    }
    members: list[tuple[Axes, Annotation]] = []
    for ax, label in zip(axes, labels, strict=False):
        members.append(
            (
                ax,
                ax.annotate(
                    label,
                    xy=(0.0, 1.0 if y is None else y),
                    xycoords="axes fraction",
                    xytext=(0.0, 0.0),
                    textcoords="offset points",
                    annotation_clip=False,
                    **properties,
                ),
            )
        )
    if not members:
        return []
    group = _Group(members, fixed_y=y)
    fig = members[0][0].get_figure(root=True)
    if fig is None:
        return [t for _ax, t in members]
    groups = getattr(fig, _GROUPS_ATTR, None)
    if groups is None:
        groups = []
        setattr(fig, _GROUPS_ATTR, groups)
    groups.append(group)
    fig.canvas.draw()
    renderer = get_renderer(fig)
    # A row or column aligns on what its labels look like once placed.
    for _round in range(2):
        if not _place_group(group, renderer):
            break
        fig.canvas.draw()
        renderer = get_renderer(fig)
    return [t for _ax, t in members]
