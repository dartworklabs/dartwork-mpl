"""Value labels on bars: :func:`label_bars`.

Downstream code hand-wrote these labels: ten font sizes, ``"bold"`` against
the ``dm.fw(1)`` rule, mixed greys, formats that repeat the axis unit
(``38 GWh`` above ``(GWh)``). One call settles each of these:

* **Look.** ``dm.fs(-1)``, ``dm.fw(1)``, the preset text colour, 3 pt from
  the bar end (as ``dm.annotate_value``).
* **Unit.** A label prints like its axis's ticks (:func:`tick_scale_of`):
  under ``dm.axis_unit`` the label names the unit, so labels are plain
  scaled numbers (``33.0`` under ``Energy (GWh)``); a formatter whose
  ticks carry a suffix gives the labels the same unit and suffix (``33G``
  under the library's default numbers or ``format_axis_si``, ``31%`` under
  a ``PercentFormatter``). The decision is re-read at every draw, so a
  later ``set_ylim``, ``dm.axis_unit`` or ``dm.simple_layout`` that moves
  the tick unit moves the labels with it.
* **Decimals.** Three significant digits on the largest ``|value|``, cut to
  the fewest decimals that print every value exactly, one count for the
  whole call (:func:`value_label_decimals`): ``21.4, 18.0, 21.5``;
  ``120, 135``; never a meaningless ``.0``. Zero prints ``0``; U+2212 minus
  like the ticks.
* **Side.** Outside the bar end; a negative bar's label below it (``barh``:
  left of it); an inverted value axis flips the side with the bar; error
  bars push the label past their caps, but not past the view.
* **View.** A label shows while its bar's end (its middle for
  ``where="center"``) lies in the view, within one pixel: a bar ending on a
  limit keeps its label just outside the axes, a bar outside the view or
  running past a limit the caller set has none (nor any room in a
  ``bbox_inches="tight"`` save).
* **Twins.** On a ``twinx`` / ``twiny`` pair the labels go on the Axes drawn
  last (by zorder, then figure order), placed with the bars' own data
  transform, so no partner's line is drawn over them.
* **Explicit wins.** A label's text and placement are rewritten only while
  they still hold what this module last wrote; a later ``Text.set_*`` on a
  returned label is kept through every draw and layout.

Each call is recorded on its Axes as a :class:`BarLabelFamily` in
``ax._dm_bar_label_families`` (the labels, the containers, the options) for
the layout's later passes. The geometry (anchor, side, view, host Axes)
lives in :mod:`._bar_label_geometry`.
"""

from __future__ import annotations

import math
import numbers
import string
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import matplotlib as mpl
import matplotlib.colors as mcolors
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.text import Annotation, Text
from matplotlib.transforms import IdentityTransform

from .._colors.contrast import ensure_contrast
from .._figure_geometry import same_position_axes
from ..formatting import (
    TickScale,
    number_text,
    tick_scale_of,
    value_label_decimals,
)
from ..scale import fs, fw
from ._bar_label_geometry import host_axes, in_view, place

if TYPE_CHECKING:
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.patches import Rectangle
    from matplotlib.typing import CoordsType

__all__ = ["BarLabel", "BarLabelFamily", "BarLabelOptions", "label_bars"]

Where: TypeAlias = Literal["auto", "outside", "inside", "center"]
Total: TypeAlias = Literal["auto", "only", False]
Crowded: TypeAlias = Literal["rotate", "skip", "inside"]
Orientation: TypeAlias = Literal["vertical", "horizontal"]
Fmt: TypeAlias = str | Callable[[float], object] | None
RGB: TypeAlias = tuple[float, float, float]

_UNSET: Any = object()


# ------------------------------------------------------------ the options
def _parse_where(where: str) -> Where:
    match where:
        case "auto" | "outside" | "inside" | "center":
            return where
        case _:
            raise ValueError(
                "where must be 'auto', 'outside', 'inside' or 'center' "
                f"(got {where!r})"
            )


def _parse_total(total: object) -> Total:
    if total is False:
        return False
    match total:
        case "auto" | "only":
            return total
        case _:
            raise ValueError(
                f"total must be 'auto', 'only' or False (got {total!r})"
            )


def _parse_crowded(crowded: str) -> Crowded:
    match crowded:
        case "rotate" | "skip" | "inside":
            return crowded
        case _:
            raise ValueError(
                "crowded must be 'rotate', 'skip' or 'inside' "
                f"(got {crowded!r})"
            )


def _parse_decimals(decimals: object) -> int | None:
    if decimals is None:
        return None
    if (
        isinstance(decimals, bool)
        or not isinstance(decimals, numbers.Integral)
        or int(decimals) < 0
    ):
        raise ValueError(
            f"decimals must be None or an integer >= 0 (got {decimals!r})"
        )
    return int(decimals)


def _template_fields(template: str) -> list[tuple[str, str | None, str, str]]:
    """``string.Formatter().parse`` of ``template`` with ``None`` specs as ``""``."""
    return [
        (literal, name, spec or "", conversion or "")
        for literal, name, spec, conversion in string.Formatter().parse(
            template
        )
    ]


def _minus(text: str) -> str:
    """Matplotlib's minus (U+2212 unless ``axes.unicode_minus`` is off)."""
    if mpl.rcParams["axes.unicode_minus"]:
        return text.replace("-", "\N{MINUS SIGN}")
    return text


def _render_template(template: str, number: str, value: float) -> str:
    """``template`` with each ``{}`` replaced by ``number``.

    A field with a format spec or conversion (``{:.2f}``) formats ``value``
    itself instead, with matplotlib's minus.
    """
    formatter = string.Formatter()
    out: list[str] = []
    for literal, name, spec, conversion in _template_fields(template):
        out.append(literal)
        if name is None:
            continue
        if not spec and not conversion:
            out.append(number)
            continue
        converted = formatter.convert_field(value, conversion or None)
        out.append(_minus(formatter.format_field(converted, spec)))
    return "".join(out)


def _parse_fmt(fmt: object) -> Fmt:
    if fmt is None or callable(fmt):
        return fmt
    if not isinstance(fmt, str):
        raise ValueError(
            f"fmt must be None, a '{{}}' template or a callable (got {fmt!r})"
        )
    hint = "e.g. fmt='${}B'; a callable gets the scaled value"
    try:
        fields = [name for _, name, _, _ in _template_fields(fmt)]
    except ValueError as error:
        raise ValueError(f"fmt {fmt!r} is not a template: {error}") from None
    names = [name for name in fields if name is not None]
    if not names:
        raise ValueError(
            f"fmt must hold a '{{}}' placeholder for the number ({hint}); "
            f"got {fmt!r}"
        )
    if any(name not in ("", "0") for name in names):
        raise ValueError(
            f"fmt placeholders must be '{{}}' or '{{:spec}}' ({hint}); "
            f"got {fmt!r}"
        )
    try:
        _render_template(fmt, "1", 1.0)
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"fmt {fmt!r} cannot format a number: {error}"
        ) from None
    return fmt


def _is_series(color: object) -> bool:
    return isinstance(color, str) and color == "series"


def _parse_color(color: object) -> object:
    if color is None or _is_series(color):
        return color
    try:
        mcolors.to_rgba(color)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"color must be None, 'series' or a matplotlib colour: {error}"
        ) from None
    return color


@dataclass(frozen=True)
class BarLabelOptions:
    """The keywords of one :func:`label_bars` call, validated."""

    where: Where = "auto"
    total: Total = "auto"
    crowded: Crowded = "rotate"
    decimals: int | None = None
    fmt: Fmt = None
    size: float | str | None = None
    color: object = None


# ------------------------------------------------------------ the labels
def _compose(
    scaled: float, scale: TickScale, decimals: int, options: BarLabelOptions
) -> str:
    """The label text for a value already divided by ``scale.factor``."""
    fmt = options.fmt
    fixed = options.decimals is not None
    if callable(fmt):
        return str(fmt(scaled))
    if isinstance(fmt, str):
        return _render_template(
            fmt, number_text(scaled, decimals, fixed=fixed), scaled
        )
    return number_text(
        scaled, decimals, fixed=fixed, prefix=scale.prefix, suffix=scale.suffix
    )


class BarLabel(Annotation):
    """One bar's value label: an ``Annotation`` that keeps reading like its axis.

    It belongs to its call's :class:`BarLabelFamily`. Each time matplotlib
    positions it (every draw, every extent measurement) the family re-reads
    the bar axis's tick unit and rewrites what it still owns.
    """

    def __init__(
        self,
        bar_family: BarLabelFamily,
        container: BarContainer,
        index: int,
        value: float,
        *,
        bar_axes: Axes,
        xycoords: CoordsType,
        **text_kw: Any,
    ) -> None:
        # Set first: get_visible (overridden below) reads them.
        self.bar_family = bar_family
        self.container = container
        self.index = index
        self.bar: Rectangle = container.patches[index]
        self.bar_axes = bar_axes
        self.value = value
        self.orientation: Orientation = (
            "horizontal"
            if container.orientation == "horizontal"
            else "vertical"
        )
        self.kind = "edge"
        # The tick scale the text was last written in (None: not yet).
        self.tick_scale: TickScale | None = None
        # What this module last wrote to each property it owns.
        self._written: dict[str, object] = {}
        super().__init__(
            "",
            (0.0, 0.0),
            xytext=(0.0, 0.0),
            xycoords=xycoords,
            textcoords="offset points",
            annotation_clip=False,
            **text_kw,
        )

    @property
    def value_axis(self) -> Axis:
        """The axis that scales the bar's value (y for ``bar``, x for ``barh``)."""
        if self.orientation == "vertical":
            return self.bar_axes.yaxis
        return self.bar_axes.xaxis

    def own(
        self,
        name: str,
        current: object,
        wanted: object,
        write: Callable[[Any], object],
    ) -> None:
        """Write ``wanted`` unless ``name`` changed since this module wrote it.

        A property someone else set (``Text.set_*`` on a returned label) is
        theirs from then on.
        """
        last = self._written.get(name, _UNSET)
        if last is not _UNSET and current != last:
            return
        if current != wanted:
            write(wanted)
        self._written[name] = wanted

    def get_visible(self) -> bool:
        """Visible, and the bar's anchor lies in the bar axes' view.

        A bar outside the view (or past a limit the caller set) shows no
        label: matplotlib neither draws an invisible text nor counts it in a
        tight bbox (``Text.get_tightbbox`` is null), and the layout and the
        validation checks skip it.
        """
        return super().get_visible() and in_view(
            self, self.bar_family.options.where
        )

    def update_positions(self, renderer: RendererBase) -> None:
        """Follow the tick unit and the bar end, then position as usual."""
        self.bar_family.follow(self)
        super().update_positions(renderer)


@dataclass(eq=False)
class BarLabelFamily:
    """One :func:`label_bars` call: its labels, the bars and the options."""

    ax: Axes
    containers: list[BarContainer]
    options: BarLabelOptions
    texts: list[BarLabel] = field(default_factory=list)

    def refresh(self) -> None:
        """Write every label's text in its axis's current tick scale.

        One decimal count for the whole call, unless ``decimals=`` fixed it.
        A text someone else set is kept.
        """
        scales = [tick_scale_of(t.value_axis, t.value) for t in self.texts]
        scaled = [
            t.value / s.factor for t, s in zip(self.texts, scales, strict=True)
        ]
        decimals = self.options.decimals
        if decimals is None:
            decimals = value_label_decimals(scaled)
        for label, scale, value in zip(self.texts, scales, scaled, strict=True):
            label.tick_scale = scale
            text = _compose(value, scale, decimals, self.options)
            label.own("text", label.get_text(), text, label.set_text)

    def follow(self, label: BarLabel) -> None:
        """Re-read the tick scale for ``label``; rewrite the call when it moved."""
        if tick_scale_of(label.value_axis, label.value) != label.tick_scale:
            self.refresh()
        place(label, self.options.where)


# ------------------------------------------------------------ the call
def _containers(ax: Axes, bars: object) -> list[BarContainer]:
    if bars is None:
        found = [c for c in ax.containers if isinstance(c, BarContainer)]
        if not found:
            raise ValueError(
                "ax has no bars to label: dm.label_bars labels what "
                "ax.bar / ax.barh / ax.hist drew on this Axes (bars on a "
                "twin? pass that Axes)"
            )
        return found
    if isinstance(bars, BarContainer):
        return [bars]
    message = (
        "bars must be a BarContainer (what ax.bar / ax.barh return) or a "
        f"list of them (got {type(bars).__name__})"
    )
    if not isinstance(bars, Iterable):
        raise TypeError(message)
    items = list(bars)
    if not all(isinstance(item, BarContainer) for item in items):
        raise TypeError(message)
    return items


def _check_plot_area(ax: Axes, containers: list[BarContainer]) -> None:
    """Every container is drawn on ``ax`` or a twin of it (the same box)."""
    plot_area = same_position_axes(ax)
    for container in containers:
        for patch in container.patches:
            drawn_on = patch.axes
            if drawn_on is not None and drawn_on not in plot_area:
                raise ValueError(
                    f"bars must be drawn on {ax!r} or a twin of it (an Axes "
                    f"in the same box); these are on {drawn_on!r}: pass that "
                    "Axes as ax"
                )


def _over(top: tuple[float, float, float, float], below: RGB) -> RGB:
    alpha = top[3]
    r, g, b = (
        alpha * t + (1.0 - alpha) * u
        for t, u in zip(top[:3], below, strict=True)
    )
    return (r, g, b)


def _background(bar_axes: Axes) -> RGB:
    """What shows behind the bars: the figure, then each visible Axes patch."""
    below: RGB = (1.0, 1.0, 1.0)
    root = bar_axes.get_figure(root=True)
    parent = bar_axes.get_figure(root=False)
    for container in (root, parent if parent is not root else None):
        if container is not None and container.patch.get_visible():
            below = _over(mcolors.to_rgba(container.get_facecolor()), below)
    for member in sorted(
        same_position_axes(bar_axes), key=lambda m: m.get_zorder()
    ):
        if member.get_frame_on() and member.patch.get_visible():
            below = _over(mcolors.to_rgba(member.get_facecolor()), below)
    return below


def _series_ink(patch: Rectangle, background: RGB) -> str:
    """The bar's colour as drawn, darkened (or lightened) to 4.5:1 text."""
    face = mcolors.to_rgba(patch.get_facecolor())
    if face[3] == 0 and patch.get_linewidth() > 0:
        face = mcolors.to_rgba(patch.get_edgecolor())
    shown = mcolors.to_hex(_over(face, background))
    return ensure_contrast(shown, mcolors.to_hex(background))


def _format_ticks_now(axis: Axis) -> None:
    """Let ``axis``'s formatter decide now, as the next draw would."""
    axis.get_major_formatter().format_ticks(list(axis.get_majorticklocs()))


def label_bars(
    ax: Axes,
    bars: BarContainer | Iterable[BarContainer] | None = None,
    *,
    where: Where = "auto",
    total: Total = "auto",
    crowded: Crowded = "rotate",
    decimals: int | None = None,
    fmt: str | Callable[[float], object] | None = None,
    size: float | str | None = None,
    color: Any = None,
) -> list[Text]:
    """Label each bar with its value, printed like the axis's ticks.

    One call for "put the values on the bars" / "막대에 값 표시", so every
    caller draws the same labels::

        ax.bar(months, energy_wh)
        dm.axis_unit(ax, "y", label="Energy ({unit}Wh)")
        dm.label_bars(ax)        # 21.4 … 33.0 above the bars
        dm.simple_layout(fig)

    Defaults (every one a keyword away):

    - ``dm.fs(-1)`` text, ``dm.fw(1)`` weight, the preset text colour, 3 pt
      beyond the bar end; negative bars below (``barh``: left);
    - the value in the axis's tick unit with no unit repeated under
      ``dm.axis_unit`` (``33.0`` under ``Energy (GWh)``), or the ticks'
      suffix when they carry one (``33G``, ``31%``); other formatters print
      the plain value (pass ``fmt=``). The unit is re-read at every draw,
      so later limit or formatter changes keep the labels in step;
    - three significant digits on the largest ``|value|``, then the fewest
      decimals that print every value exactly, one count for the call
      (``21.4, 18.0, 21.5``; ``120, 135``); zero prints ``0``; U+2212 minus;
    - on a ``twinx`` / ``twiny`` pair the labels are added to the Axes drawn
      last (by zorder, then figure order; placed with the bars' data), so
      the partner's line never covers them;
    - a label shows while its bar's end (its middle for ``"center"``) lies
      in the view, within one pixel: a bar ending on a limit you set keeps
      its label just outside the axes, a bar outside the view or running
      past such a limit has none. Error bars push a label at most to the
      edge of the view.

    A later ``Text.set_*`` on a returned label (text, colour, size, weight,
    alignment) wins over every redraw and ``dm.simple_layout``.

    Parameters
    ----------
    ax : Axes
        The Axes that drew the bars.
    bars : BarContainer or list of BarContainer, optional
        The bars to label (what ``ax.bar`` / ``ax.barh`` / ``ax.hist``
        return). ``None`` (default) labels every bar container on ``ax``.
    where : {"auto", "outside", "inside", "center"}
        ``"auto"`` (default) and ``"outside"``: beyond the bar end;
        ``"inside"``: just inside the end; ``"center"``: the bar's middle.
    total : {"auto", "only", False}
        Stacked bars: segment labels plus a total (``"auto"``), the total
        only, or no total.
    crowded : {"rotate", "skip", "inside"}
        What labels wider than the bar pitch do: turn vertical (default),
        hide alternate labels, or move inside the bars.
    decimals : int, optional
        A fixed decimal count instead of the rule above.
    fmt : str or callable, optional
        A ``{}`` template around the number (``fmt="${}B"`` -> ``$38.5B``;
        the template supplies any unit, the tick suffix is not added;
        ``{:.2f}`` formats the scaled value itself), or a callable that gets
        the value in the axis's tick unit and returns the whole text. A
        template wraps the signed number, so ``"${}B"`` on -3.5 prints
        ``$-3.5B`` (the minus is U+2212); for ``-$3.5B`` use a callable.
    size : float or str, optional
        Font size; default ``dm.fs(-1)``.
    color : color, optional
        ``None`` (default) the preset text colour; ``"series"`` each bar's
        colour as drawn, darkened to 4.5:1 against the background
        (``dm.ensure_contrast``); any matplotlib colour.

    Returns
    -------
    list of Text
        The labels, container by container and bar by bar; a bar whose
        value is NaN or infinite gets none.

    Raises
    ------
    ValueError
        For an unknown ``where`` / ``total`` / ``crowded``, a negative
        ``decimals``, a ``fmt`` template without ``{}``, an invalid
        ``color``, ``bars=None`` on an Axes without bars, or bars drawn on
        an Axes other than ``ax`` and its twins.
    TypeError
        If ``bars`` is not a ``BarContainer`` or a list of them.
    """
    options = BarLabelOptions(
        where=_parse_where(where),
        total=_parse_total(total),
        crowded=_parse_crowded(crowded),
        decimals=_parse_decimals(decimals),
        fmt=_parse_fmt(fmt),
        size=size,
        color=_parse_color(color),
    )
    containers = _containers(ax, bars)
    _check_plot_area(ax, containers)
    for container in containers:
        if container.orientation not in ("vertical", "horizontal") or (
            container.datavalues is None
        ):
            raise ValueError(
                "bars must come from ax.bar / ax.barh / ax.hist: a "
                "BarContainer with an orientation and datavalues"
            )
    if not containers:
        return []

    family = BarLabelFamily(ax, containers, options)
    fontsize = fs(-1) if size is None else size
    value_axes: list[Axis] = []
    for container in containers:
        # Masked values (np.ma) are missing values, like NaN: no label.
        values: npt.NDArray[np.float64] = np.ma.filled(
            np.ma.asarray(container.datavalues, dtype=float), np.nan
        )
        for index, (patch, value) in enumerate(
            zip(container.patches, values, strict=False)
        ):
            bar_axes = patch.axes
            if not isinstance(bar_axes, Axes) or not math.isfinite(value):
                continue
            host = host_axes(bar_axes)
            xycoords: CoordsType
            if options.where == "center":
                xycoords = patch
            elif host is bar_axes:
                xycoords = "data"
            else:
                xycoords = bar_axes.transData
            text_kw: dict[str, Any] = {
                "fontsize": fontsize,
                "fontweight": fw(1),
            }
            if _is_series(options.color):
                text_kw["color"] = _series_ink(patch, _background(bar_axes))
            elif options.color is not None:
                text_kw["color"] = options.color
            label = BarLabel(
                family,
                container,
                index,
                float(value),
                bar_axes=bar_axes,
                xycoords=xycoords,
                **text_kw,
            )
            # As ax.annotate does: the text is placed in display space, and
            # nothing clips it (a label beyond the bar end may leave the
            # axes). add_artist clips to the Axes patch, a rectangle that
            # matplotlib stores as the clip box: clear both.
            label.set_transform(IdentityTransform())
            host.add_artist(label)
            label.set_clip_box(None)
            label.set_clip_path(None)
            family.texts.append(label)
            if label.value_axis not in value_axes:
                value_axes.append(label.value_axis)

    for axis in value_axes:
        _format_ticks_now(axis)
    family.refresh()
    for label in family.texts:
        place(label, options.where)

    families = getattr(ax, "_dm_bar_label_families", None)
    if families is None:
        families = []
        ax._dm_bar_label_families = families  # type: ignore[attr-defined]
    families.append(family)
    return list(family.texts)
