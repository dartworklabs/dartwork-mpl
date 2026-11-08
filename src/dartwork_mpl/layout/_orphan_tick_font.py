"""Orphan tick-label font adoption: tick labels of an axis without a name take the axis-label font."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from matplotlib.figure import Figure

if TYPE_CHECKING:
    from matplotlib.text import Text


# ─────────────────────────────────────────────────────────────────────
# orphan tick-label font adoption
# ─────────────────────────────────────────────────────────────────────

# When an axis carries tick labels but no axis label, the tick labels
# become that axis's most prominent textual descriptor. Under every
# preset they are styled lighter/smaller than the axis label, so a
# self-describing axis renders its descriptor in the subordinate tick
# style. These helpers copy the axis-label font onto such "orphan" tick
# labels. Color is intentionally excluded so user-set tick colors stay.


def _copy_label_font(src: Text, dst: Text) -> None:
    """Copy fontsize/weight/family/style from ``src`` Text onto ``dst``.

    Both arguments are matplotlib :class:`~matplotlib.text.Text` artists
    (axis labels and tick labels alike). Typed as ``Text`` rather than
    ``Any`` so static analysis catches accidental calls with a
    non-Text artist.
    """
    dst.set_fontsize(src.get_fontsize())
    dst.set_fontweight(src.get_fontweight())
    dst.set_fontfamily(src.get_fontfamily())
    dst.set_fontstyle(src.get_fontstyle())


def _adopt_axis_label_font_core(fig: Figure) -> None:
    """Make unlabeled axes' tick labels adopt that axis's label font.

    For each axes and each axis direction (x, y) **independently**: if the
    axis has no axis label, copy the axis-label font (size, weight,
    family, style — *not* color) onto that axis's visible, non-empty tick
    labels (major and minor) and its offset text. Axes that *do* carry a
    label are left untouched, preserving any user tick-font customization.

    Assumes the figure has already been drawn so the tick label Text
    objects exist. The change persists across later redraws and locator
    regeneration because matplotlib copies the prototype tick's font onto
    any ticks it creates afterwards.
    """
    mutated_axes = (
        0  # debug-warning counter — see dm.config.warn_on_orphan_tick_adoption
    )
    for ax in fig.axes:
        for axis, get_label in (
            (getattr(ax, "xaxis", None), getattr(ax, "get_xlabel", None)),
            (getattr(ax, "yaxis", None), getattr(ax, "get_ylabel", None)),
        ):
            if axis is None or get_label is None:
                continue
            try:
                if get_label().strip():
                    continue  # labeled axis — leave ticks as-is
                label = axis.label
                targets: list[Any] = []
                for minor in (False, True):
                    targets.extend(
                        tick
                        for tick in axis.get_ticklabels(minor=minor)
                        if tick.get_visible() and tick.get_text().strip()
                    )
                offset = axis.get_offset_text()
                if offset.get_visible() and offset.get_text().strip():
                    targets.append(offset)
                for tick in targets:
                    _copy_label_font(label, tick)
                if targets:
                    mutated_axes += 1
            except (AttributeError, ValueError):
                # Non-standard axes (polar/3D) — skip defensively.
                continue

    if mutated_axes:
        from ..config import config

        if config.warn_on_orphan_tick_adoption:
            warnings.warn(
                f"Orphan tick-label font adoption applied to {mutated_axes} "
                f"axis(es) on this figure. Disable with "
                f"`adopt_orphan_tick_font=False` on the calling function "
                f"(simple_layout / save_formats / save_and_show) or set "
                f"`dm.config.adopt_orphan_tick_font = False` globally. "
                f"Silence this warning with "
                f"`dm.config.warn_on_orphan_tick_adoption = False`.",
                UserWarning,
                stacklevel=3,
            )


def adopt_axis_label_font(fig: Figure) -> None:
    """Draw ``fig`` then apply :func:`_adopt_axis_label_font_core`.

    Use this when you are not calling :func:`simple_layout` with
    ``adopt_orphan_tick_font=True`` but still want unlabeled axes' tick
    labels to take the axis-label font. A no-op on figures without axes.

    Note that the adoption reflects the figure state at call time: if you
    later add an axis label to a previously unlabeled axis, the ticks that
    already adopted the label font keep it. In the normal flow axis labels
    are set before layout, so this does not arise.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")
    >>> fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    >>> ax.bar(["A", "B", "C"], [3, 5, 4])
    >>> ax.set_ylabel("Count")         # x has no label
    >>> dm.adopt_axis_label_font(fig)  # x tick labels now use the label font
    """
    if not fig.axes:
        return
    fig.canvas.draw()
    _adopt_axis_label_font_core(fig)
