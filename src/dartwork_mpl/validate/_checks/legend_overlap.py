"""LEGEND_OVERLAP: a legend box over a title, axis label, tick label or figure text.

``OVERLAP`` and ``CROSS_AXES_OVERLAP`` compare text with text, so a legend
drawn on top of a title (``ax.legend(loc="lower center",
bbox_to_anchor=(0.5, 1.0))`` plus ``ax.set_title``) went unreported. This
check compares the box of every Axes legend and figure legend with every
Axes' titles, axis labels and in-view tick labels and with the figure-level
texts (suptitle, sup-labels, ``fig.text``). Text inside an Axes
(``ax.texts``) is not compared. Hidden Axes and hidden axes (a twin's shared
axis) are skipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

from ..._figure_geometry import (
    axes_titles,
    figure_legends,
    iter_figure_level_extents,
)
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix
from ._tick_utils import iter_view_ticks

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend
    from matplotlib.text import Text
    from matplotlib.transforms import Bbox

__all__ = ["check_legend_overlap"]

Role: TypeAlias = Literal[
    "title",
    "left title",
    "right title",
    "x-axis label",
    "y-axis label",
    "x tick label",
    "y tick label",
    "suptitle",
    "supxlabel",
    "supylabel",
    "figure text",
]
"""What the text a legend covers is."""

_TITLE_ROLES: dict[str, Role] = {
    "center": "title",
    "left": "left title",
    "right": "right title",
}

# An intersection thinner than this in either direction (display px) is a
# touch, not a collision.
_TOLERANCE_PX = 1.0


class LegendOverlapDetail(TypedDict):
    """The legend of ``legend_axes`` covers ``count`` texts of one ``role``.

    ``legend_axes`` and ``artist_axes`` are ``fig.axes`` indices; ``None``
    means a figure legend or a figure-level text. ``text`` is the first
    covered text and ``overlap_px`` the width and height of the largest
    intersection.
    """

    legend_axes: int | None
    legend_labels: list[str]
    role: Role
    artist_axes: int | None
    text: str
    count: int
    overlap_px: list[float]


def _legends(fig: Figure) -> Iterator[tuple[int | None, Legend]]:
    """Yield ``(axes index or None, legend)`` for every visible legend."""
    for index, ax in enumerate(fig.axes):
        legend = ax.get_legend()
        if ax.get_visible() and legend is not None and legend.get_visible():
            yield index, legend
    for legend in figure_legends(fig):  # a SubFigure's are on it
        if legend.get_visible():
            yield None, legend


def _axes_targets(
    ax: Axes, renderer: RendererBase
) -> Iterator[tuple[Role, Text]]:
    """Yield the titles, shown axis labels and in-view tick labels of ``ax``."""
    for loc, title in axes_titles(ax).items():
        yield _TITLE_ROLES[loc], title
    if ax.xaxis.get_visible():
        yield "x-axis label", ax.xaxis.label
        for tick in iter_view_ticks(ax, "x", renderer):
            yield "x tick label", tick
    if ax.yaxis.get_visible():
        yield "y-axis label", ax.yaxis.label
        for tick in iter_view_ticks(ax, "y", renderer):
            yield "y tick label", tick


_FIGURE_ROLES: tuple[tuple[str, Role], ...] = (
    ("_suptitle", "suptitle"),
    ("_supxlabel", "supxlabel"),
    ("_supylabel", "supylabel"),
)


def _figure_role(fig: Figure, art: object) -> Role:
    """Return the role of a figure-level text artist."""
    for attr, role in _FIGURE_ROLES:
        if art is getattr(fig, attr, None):
            return role
    return "figure text"


def _targets(
    fig: Figure, renderer: RendererBase
) -> list[tuple[int | None, Role, str, Bbox]]:
    """Every text a legend must not cover, with its owner, role and extent."""
    found: list[tuple[int | None, Role, str, Bbox]] = []
    for index, ax in enumerate(fig.axes):
        if not ax.get_visible():
            continue
        for role, text in _axes_targets(ax, renderer):
            if not text.get_visible() or not text.get_text().strip():
                continue
            try:
                ext = text.get_window_extent(renderer)
            except BBOX_ERRORS:
                continue
            if ext.width > 0 and ext.height > 0:
                found.append((index, role, text.get_text(), ext))
    for art, ext in iter_figure_level_extents(fig, renderer, legends=False):
        # A SubFigure's suptitle is that SubFigure's, not the figure's.
        owner = art.get_figure(root=False) or fig
        found.append((None, _figure_role(owner, art), art.get_text(), ext))
    return found


def _describe_legend(index: int | None, labels: list[str]) -> str:
    """Name a legend by its owner and first entries."""
    owner = "Figure legend" if index is None else f"Legend of axes[{index}]"
    if not labels:
        return owner
    shown = ", ".join(repr(label) for label in labels[:2])
    more = ", ..." if len(labels) > 2 else ""
    return f"{owner} ({shown}{more})"


def _describe_target(
    role: Role, index: int | None, text: str, count: int
) -> str:
    """Name the covered text by role, owner and its first 30 characters."""
    owner = "the figure" if index is None else f"axes[{index}]"
    label = repr(text.strip()[:30])
    if count > 1:
        return f"{count} {role}s of {owner} (first {label})"
    return f"the {role} {label} of {owner}"


@register_check("LEGEND_OVERLAP", order=45)
def check_legend_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect legends drawn over titles, axis labels, tick labels or figure text.

    One WARNING per legend and covered (owner, role), naming both: a legend
    over three x tick labels is one finding with ``count`` 3. Intersections
    thinner than one pixel are ignored.
    """
    targets = _targets(fig, renderer)
    warnings: list[VisualWarning] = []
    for legend_index, legend in _legends(fig):
        try:
            box = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if box.width <= 0 or box.height <= 0:
            continue
        hits: dict[tuple[int | None, Role], list[tuple[str, float, float]]] = {}
        for owner, role, text, ext in targets:
            width = min(box.x1, ext.x1) - max(box.x0, ext.x0)
            height = min(box.y1, ext.y1) - max(box.y0, ext.y0)
            if width > _TOLERANCE_PX and height > _TOLERANCE_PX:
                hits.setdefault((owner, role), []).append((text, width, height))
        labels = [text.get_text() for text in legend.get_texts()]
        for (owner, role), covered in hits.items():
            first = covered[0][0]
            _text, width, height = max(covered, key=lambda hit: hit[1] * hit[2])
            message = (
                f"{_describe_legend(legend_index, labels)} overlaps "
                f"{_describe_target(role, owner, first, len(covered))}"
            )
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERLAP",
                    message=message,
                    detail=wire(
                        LegendOverlapDetail(
                            legend_axes=legend_index,
                            legend_labels=labels,
                            role=role,
                            artist_axes=owner,
                            text=first[:30],
                            count=len(covered),
                            overlap_px=[
                                round(float(width), 1),
                                round(float(height), 1),
                            ],
                        )
                    ),
                )
            )
    return warnings


@register_fix("LEGEND_OVERLAP")
def _fix_legend_overlap(_warning: VisualWarning) -> list[str]:
    return [
        "# Inside away from the data, or above the plot when nothing is free\n"
        "dm.place_legend(ax)\ndm.simple_layout(fig)",
        "# The side the user named; simple_layout lifts the title above it\n"
        "dm.place_legend(ax, loc='above')  # or 'below', 'right', 'left'\n"
        "dm.simple_layout(fig)",
        "# Fewer rows or a smaller legend\nax.legend(ncols=2, fontsize=dm.fs(-1))",
    ]
