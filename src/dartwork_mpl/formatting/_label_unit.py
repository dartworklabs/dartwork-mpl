"""The axis unit in the axis label: ``dm.axis_unit`` and ``dm.axis_unit_of``.

``0, 0.2 … 1.0`` under ``인구 (억명)`` instead of ``0.2억 … 1.0억`` under
``인구 (명)``. :class:`LabelUnitFormatter` is an
:class:`~._axis_wide.AxisUnitFormatter` that settles one unit and one decimal
count per axis from the visible ticks, prints the ticks as plain numbers and
writes the unit into the axis label in the same draw-time hook, so zooming
or a later ``set_ylim`` keeps label and ticks in step.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

from matplotlib.axes import Axes
from matplotlib.axis import Axis

from ._axis_wide import (
    FINANCE_LADDER,
    MYRIAD_LADDER,
    SI_LADDER,
    UNIT_RULES,
    AxisUnitFormatter,
    Unit,
    _Plan,
)
from ._defaults import config_ladder

__all__ = ["LabelUnitFormatter", "axis_unit", "axis_unit_of", "fill"]

LadderName = Literal["auto", "myriad", "finance", "si"]

_LADDERS: dict[str, tuple[Unit, ...]] = {
    "myriad": MYRIAD_LADDER,
    "finance": FINANCE_LADDER,
    "si": SI_LADDER,
}
_PLACEHOLDER = "{unit}"


def fill(template: str, unit: str) -> str:
    """Put ``unit`` into ``template``'s ``{unit}`` and tidy the brackets.

    Spaces just inside a bracket go (``"(USD )"`` -> ``"(USD)"``) and an
    empty ``()`` goes with the space before it, so an axis without a unit
    reads ``"Count"``, not ``"Count ()"``.
    """
    text = template.replace(_PLACEHOLDER, unit)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return re.sub(r"\s*\(\)", "", text)


class LabelUnitFormatter(AxisUnitFormatter):
    """Plain-number ticks with the axis unit written into the axis label.

    The unit and decimals are decided as in :class:`AxisUnitFormatter`
    (``unit`` is ``"max"``, ``"whole"`` or one ladder label). Each
    :meth:`set_locs` (every draw) writes ``fill(template, unit.label)`` to
    the axis label, and to the label of every axis :meth:`share_label`
    added: axes made with ``sharex`` / ``sharey`` share one formatter, and
    each keeps its own template. On a log or other non-linear axis the
    ticks span decades, which one label cannot name, so the ticks print
    linearly in full (``100``, ``1,000,000``) and the label carries no unit.
    """

    def __init__(
        self,
        ladder: Sequence[Unit],
        unit: str = "max",
        *,
        template: str,
        decimals: int | None = None,
    ) -> None:
        super().__init__(ladder, unit, decimals=decimals)
        self._template = template
        self._shared: dict[Axis, str] = {}

    @property
    def template(self) -> str:
        """The label template, with ``{unit}`` where the unit goes."""
        return self._template

    def share_label(self, axis: Axis, template: str) -> None:
        """Also write ``fill(template, unit)`` to ``axis``'s label each draw."""
        self._shared[axis] = template

    def templates(self) -> dict[Axis, str]:
        """Every axis whose label this formatter writes, with its template."""
        written = dict(self._shared)
        if isinstance(self.axis, Axis):
            written[self.axis] = self._template
        return written

    @property
    def unit(self) -> Unit | None:
        """The unit of the last tick decision; ``None`` before any."""
        return None if self._plan is None else self._plan.axis_unit

    @property
    def label_text(self) -> str:
        """The label this formatter writes for its current unit."""
        unit = self.unit
        return fill(self._template, "" if unit is None else unit.label)

    def _make_plan(self, values: Sequence[float]) -> _Plan:
        plan = super()._make_plan(values)
        if plan.axis_unit is not None:
            return plan
        # A per-tick unit cannot move into one label: plain numbers.
        return _Plan(self._ladder[0], plan.decimals)

    def _label(self, value: float, unit: Unit, decimals: int) -> str:
        return super()._label(value, Unit(unit.factor, ""), decimals)

    def set_locs(self, locs: list[float]) -> None:
        """Settle the unit and decimals, then write the unit to the labels."""
        super().set_locs(locs)
        unit = self.unit
        if unit is None:
            return
        for axis, template in self.templates().items():
            axis.label.set_text(fill(template, unit.label))


def _target(ax: Axes, axis: str) -> Axis:
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    return ax.xaxis if axis == "x" else ax.yaxis


def _template(label: str) -> str:
    if _PLACEHOLDER in label:
        return label
    return f"{label} ({_PLACEHOLDER})" if label.strip() else f"({_PLACEHOLDER})"


def _ladder(name: str, ax: Axes, template: str) -> tuple[Unit, ...]:
    """The ladder ``name`` stands for; ``"auto"`` asks ``dm.config``.

    ``config.number_ladder="auto"`` picks 만/억/조 when the figure's labels,
    titles or legends (the new label included) hold Hangul, else SI.
    """
    if name not in ("auto", *_LADDERS):
        raise ValueError(
            f"ladder must be 'auto', 'myriad', 'finance' or 'si', got {name!r}"
        )
    if name != "auto":
        return _LADDERS[name]
    return config_ladder(ax.get_figure(root=True), template)


def axis_unit(
    ax: Axes,
    axis: Literal["x", "y"] = "y",
    *,
    label: str | None = None,
    ladder: LadderName = "auto",
    scale: str = "max",
    decimals: int | None = None,
) -> LabelUnitFormatter:
    """Put the axis unit in the axis label and print the ticks as plain numbers.

    ``0, 0.2 … 1.0`` under ``인구 (억명)``, not ``0.2억 … 1.0억`` under
    ``인구 (명)``. The axis takes one unit from a ladder and the fewest
    decimals that show every visible tick exactly (the same count on every
    tick, ``0`` for zero, thousands separators), decided on every draw, so
    the label follows zooming and later ``set_xlim`` / ``set_ylim`` calls::

        dm.axis_unit(ax, "y", label="인구 ({unit}명)")  # 0, 0.2 … 1.0, 인구 (억명)
        dm.axis_unit(ax, "y", label="인구 ({unit}명)", scale="whole")  # (만명)
        dm.axis_unit(ax, "y", label="인구 ({unit}명)", scale="만")  # fixed
        dm.axis_unit(ax, "y", label="Exports (USD {unit})", ladder="finance")

    The formatter owns the label text from then on: it rewrites the label on
    every draw, so change the label by calling ``axis_unit`` again. Axes made
    with ``sharex`` / ``sharey`` share one formatter: call ``axis_unit`` on
    each (``for a in axes: dm.axis_unit(a, "y", label=...)``); every label
    keeps its own template and they read the same unit. On a log
    axis the ticks span decades, which one label cannot name, so they print
    in full (``100``, ``1,000,000``) and the label carries no unit.

    Parameters
    ----------
    ax:
        Matplotlib axes to format.
    axis:
        ``"y"`` (default) or ``"x"``.
    label:
        The label template; ``{unit}`` marks where the unit goes
        (``"인구 ({unit}명)"``, ``"Exports (USD {unit})"``). Without the
        placeholder the unit is appended in parentheses (``"인구"`` ->
        ``"인구 (억)"``). ``None`` (default) does the same with the axis's
        current label (``"Exports"`` -> ``"Exports (B)"``), read once here.
        An axis without a unit drops empty parentheses
        (``"Count ({unit})"`` -> ``"Count"``).
    ladder:
        ``"auto"`` (default) follows ``dm.config.number_ladder``, whose own
        ``"auto"`` picks ``"myriad"`` when the figure's labels, titles or
        legends are Korean (this label included) and ``"si"`` otherwise.
        ``"myriad"``: none, 만, 억, 조, 경. ``"finance"``: none, k, M, B, T.
        ``"si"``: none, k, M, G, T.
    scale:
        ``"max"`` (default) takes the unit of the largest visible ``|tick|``;
        ``"whole"`` a unit in which every visible tick is a whole number (of
        those, the one with the shortest longest tick); a ladder symbol
        (``"억"``, ``"M"``, ``""``) fixes the unit.
    decimals:
        ``None`` (default) chooses decimals as above; an integer fixes the
        count on every tick.

    Returns
    -------
    LabelUnitFormatter
        The installed formatter; its ``unit`` is the unit of the last draw.

    Raises
    ------
    ValueError
        If ``axis``, ``ladder`` or ``scale`` is not one of the values above
        (``scale`` must be on the chosen ladder), ``decimals`` is negative,
        or ``dm.config.number_ladder`` is not ``"auto"``, ``"si"`` or
        ``"myriad"``. The axis is left unchanged.
    """
    target = _target(ax, axis)
    if decimals is not None and decimals < 0:
        raise ValueError(f"decimals must be non-negative, got {decimals!r}")
    current = target.get_major_formatter()
    # Shared axes share this formatter: the axes it already writes.
    written = (
        current.templates() if isinstance(current, LabelUnitFormatter) else {}
    )
    if label is None:
        label = target.label.get_text()
        # Called again without a label on a label this formatter wrote (or
        # set at install): keep its template rather than append a second unit.
        known = written.get(target)
        if known is not None and isinstance(current, LabelUnitFormatter):
            unit = current.unit
            if label in (
                fill(known, ""),
                fill(known, unit.label if unit else ""),
            ):
                label = known
    template = _template(label)
    rungs = _ladder(ladder, ax, template)
    symbols = [rung.label for rung in rungs]
    if scale not in UNIT_RULES and scale not in symbols:
        listed = ", ".join(repr(symbol) for symbol in symbols)
        raise ValueError(
            f"scale must be 'max', 'whole' or one of {listed} on this "
            f"ladder, got {scale!r}"
        )
    formatter = LabelUnitFormatter(
        rungs, scale, template=template, decimals=decimals
    )
    for other, other_template in written.items():
        if other is not target and other.major is target.major:
            formatter.share_label(other, other_template)
    target.set_major_formatter(formatter)
    target.label.set_text(fill(template, ""))
    return formatter


def axis_unit_of(ax: Axes, axis: Literal["x", "y"] = "y") -> Unit | None:
    """The unit :func:`axis_unit` chose for this axis at the last draw.

    For value labels that should match the axis: divide by ``factor`` and
    print ``label`` the way the axis label does. ``None`` when the axis has
    no :func:`axis_unit` formatter or has not been drawn since it got one
    (``dm.simple_layout`` and saving draw).

    Raises
    ------
    ValueError
        If ``axis`` is not ``"x"`` or ``"y"``.
    """
    formatter = _target(ax, axis).get_major_formatter()
    if isinstance(formatter, LabelUnitFormatter):
        return formatter.unit
    return None
