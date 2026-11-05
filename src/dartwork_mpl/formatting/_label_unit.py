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


def _sharing(axis: Axis) -> list[Axis]:
    """Every axis that shares ``axis``'s ticker (``sharex`` / ``sharey``)."""
    ax = axis.axes
    along_x = axis is ax.xaxis
    group = ax.get_shared_x_axes() if along_x else ax.get_shared_y_axes()
    members = group.get_siblings(ax)
    fig = ax.get_figure(root=True)
    order = fig.axes if fig is not None else []
    members.sort(key=lambda m: order.index(m) if m in order else len(order))
    axes = [m.xaxis if along_x else m.yaxis for m in members]
    return [other for other in axes if other.major is axis.major]


def _shows_ticks(axis: Axis) -> bool:
    """Whether the axis prints its tick labels on its label's side."""
    side = axis.get_label_position()
    shown = axis.get_tick_params(which="major").get(f"label{side}", True)
    return axis.get_visible() and bool(shown)


def _inner_unlabelled(axis: Axis, siblings: Sequence[Axis]) -> bool:
    """An inner panel of a shared grid whose empty label ``label_outer`` left.

    Its tick labels are hidden on its label's side while a sibling shows
    them, and its label is empty: the shared ticks are read elsewhere.
    """
    return (
        not axis.label.get_text().strip()
        and not _shows_ticks(axis)
        and any(_shows_ticks(s) for s in siblings if s is not axis)
    )


class LabelUnitFormatter(AxisUnitFormatter):
    """Plain-number ticks with the axis unit written into the axis label.

    The unit and decimals are decided as in :class:`AxisUnitFormatter`
    (``unit`` is ``"max"``, ``"whole"`` or one ladder label). Each
    :meth:`set_locs` (every draw) writes ``fill(template, unit.label)`` to
    the axis label and to every axis sharing the ticker: axes made with
    ``sharex`` / ``sharey`` share one formatter, so one call rescales them
    all. Each keeps its own template: the one :meth:`share_label` (another
    ``axis_unit`` call) gave it, else one made at the first draw from its
    own label (:func:`_sibling_template`): trailing parentheses holding the
    installing template's base unit take its unit group (``인구 (명)`` ->
    ``인구 (억명)`` under ``가구 ({unit}명)``; ``Cost (USD)`` ->
    ``Cost (USD B)``), any other label gets `` ({unit})`` (``인구`` ->
    ``인구 (억)``), kept so later draws write the same text. An inner panel
    whose label
    ``label_outer`` emptied (tick labels hidden, a sibling showing them)
    stays unlabelled; a template meant for it goes to the siblings that show
    the ticks and have no label. On a log or other non-linear axis the
    ticks span decades, which one label cannot name, so every tick prints
    its whole value with thousands separators (``100``, ``1,000,000``), the
    label carries no unit and :attr:`unit` is the empty one
    (``Unit(1.0, "")``).
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
        self._group = _unit_group(template)
        self._shared: dict[Axis, str] = {}
        # The text last written to each label, to tell an edit from our own.
        self._wrote: dict[Axis, str] = {}

    @property
    def template(self) -> str:
        """The label template, with ``{unit}`` where the unit goes."""
        return self._template

    def share_label(
        self, axis: Axis, template: str, last: str | None = None
    ) -> None:
        """Also write ``fill(template, unit)`` to ``axis``'s label each draw.

        ``last`` is the text last written there (by the formatter this one
        replaces), so an edit made since is still recognised as one.
        """
        self._shared[axis] = template
        if last is not None:
            self._wrote[axis] = last

    def last_written(self, axis: Axis) -> str | None:
        """The text this formatter last wrote to ``axis``'s label, if any."""
        return self._wrote.get(axis)

    def note_written(self, axis: Axis, text: str) -> None:
        """Record ``text`` as written to ``axis``'s label (at install)."""
        self._wrote[axis] = text

    def _adopt_edits(self) -> None:
        """A label whose text is not the one last written was set by someone.

        Its text becomes that label's template (:func:`_sibling_template`
        with the installing unit group), so the edit stays and its unit
        follows the ticks; an emptied label stays empty.
        """
        for axis in self.templates():
            last = self._wrote.get(axis)
            text = axis.label.get_text()
            if last is None or text == last:
                continue
            made = (
                _sibling_template(text, self._group, self._ladder)
                if text.strip()
                else ""
            )
            if axis is self.axis:
                self._template = made
            else:
                self._shared[axis] = made

    def templates(self) -> dict[Axis, str]:
        """Every axis with a template here (labels it writes), and the template."""
        written = dict(self._shared)
        if isinstance(self.axis, Axis):
            written[self.axis] = self._template
        return written

    def labels(self) -> dict[Axis, str]:
        """The labels this draw writes: each axis and its template.

        Takes a label someone set since the last draw as its new template
        (:meth:`_adopt_edits`), adopts a sibling that shares the ticker and
        has a label but no template, leaves an inner unlabelled panel alone
        and hands its template to the siblings that show the ticks and have
        no label.
        """
        own = self.axis
        if not isinstance(own, Axis):
            return dict(self._shared)
        self._adopt_edits()
        siblings = _sharing(own)
        for other in siblings:
            text = other.label.get_text()
            if other is not own and other not in self._shared and text.strip():
                self._shared[other] = _sibling_template(
                    text, self._group, self._ladder
                )
        written: dict[Axis, str] = {}
        handed: list[str] = []
        for axis, template in self.templates().items():
            if not _inner_unlabelled(axis, siblings):
                written[axis] = template
            elif template:
                handed.append(template)
        for other in siblings:
            if handed and other not in written and _shows_ticks(other):
                self._shared[other] = written[other] = handed[0]
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
        for axis, template in self.labels().items():
            text = fill(template, unit.label)
            axis.label.set_text(text)
            self._wrote[axis] = text


def _target(ax: Axes, axis: str) -> Axis:
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    return ax.xaxis if axis == "x" else ax.yaxis


def _template(label: str) -> str:
    if _PLACEHOLDER in label:
        return label
    return f"{label} ({_PLACEHOLDER})" if label.strip() else f"({_PLACEHOLDER})"


# The parenthesised group of a template that holds the unit: ``({unit}명)``.
_UNIT_GROUP = re.compile(r"\([^()]*\{unit\}[^()]*\)")
# A label that ends in a parenthesised group: ``인구 (명)``, ``Cost (USD)``.
_TRAILING_GROUP = re.compile(
    r"^(?P<text>.*?)(?P<gap>\s*)(?P<group>\([^()]*\))(?P<tail>\s*)$", re.DOTALL
)


def _unit_group(template: str) -> str:
    """The last parenthesised group of ``template`` that holds ``{unit}``.

    ``인구 ({unit}명)`` -> ``({unit}명)``; ``Exports (USD {unit})`` ->
    ``(USD {unit})``. A template with none (or the appended `` ({unit})``
    of ``label=None``) gives ``({unit})``, the append form.
    """
    groups = _UNIT_GROUP.findall(template)
    return groups[-1] if groups else f"({_PLACEHOLDER})"


def _sibling_template(label: str, group: str, ladder: Sequence[Unit]) -> str:
    """A shared sibling's template, made from its own label.

    ``group`` is the installing template's unit group (:func:`_unit_group`).
    When the label's trailing parentheses read as that group with any unit
    of ``ladder`` (``(명)`` or ``(억명)`` for ``({unit}명)``; ``(USD)`` or
    ``(USD B)`` for ``(USD {unit})``), the group takes their place, so the
    unit goes where the installer puts it and is never doubled. Any other
    label gets `` ({unit})`` appended (``(별도)``, ``(2024)``, ``(est.)``,
    a second line, or every label when the installer itself appends).
    """
    if _PLACEHOLDER in label:
        return label
    match = _TRAILING_GROUP.match(label)
    if match is not None:
        written = fill(match["group"], "")
        if any(written == fill(group, rung.label) for rung in ladder):
            return f"{match['text']}{match['gap']}{group}{match['tail']}"
    return _template(label)


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

    The formatter writes the label on every draw. Axes made with
    ``sharex`` / ``sharey`` share one formatter, so one call rescales the
    ticks of all of them and writes every label: a sibling's trailing
    parentheses that hold this label's base unit take the unit inside
    (``"인구 (명)"`` -> ``"인구 (억명)"`` for ``label="가구 ({unit}명)"``;
    ``"Cost (USD)"`` -> ``"Cost (USD B)"``), any other sibling label gets
    it appended (``"인구"`` -> ``"인구 (억)"``; all of them with
    ``label=None``). A label you set later (``ax.set_ylabel(...)``, on any
    of these axes) becomes that label's template the same way; an emptied
    label stays empty. Call ``axis_unit`` on each (``for a in axes: dm.axis_unit(a, "y",
    label=...)``) to give each its own template. An inner panel whose label
    ``label_outer`` emptied (the upper panels of a stacked ``sharex`` grid)
    stays unlabelled; the label goes on the panel that shows the ticks. On a
    log (or any
    non-linear) axis the ticks span decades, which one label cannot name,
    so each tick prints its whole value with thousands separators (``100``,
    ``1,000,000``), the label carries no unit and :func:`axis_unit_of`
    returns ``Unit(1.0, "")``.

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
        current label (``"Exports"`` -> ``"Exports (G)"`` on the default SI
        ladder, ``"(B)"`` with ``ladder="finance"``), read once here.
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
        if (
            known is not None
            and isinstance(current, LabelUnitFormatter)
            and current.last_written(target) == label
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
            last = (
                current.last_written(other)
                if isinstance(current, LabelUnitFormatter)
                else None
            )
            formatter.share_label(other, other_template, last)
    target.set_major_formatter(formatter)
    if not _inner_unlabelled(target, _sharing(target)):
        text = fill(template, "")
        target.label.set_text(text)
        formatter.note_written(target, text)
    return formatter


def axis_unit_of(ax: Axes, axis: Literal["x", "y"] = "y") -> Unit | None:
    """The unit :func:`axis_unit` chose for this axis at the last draw.

    For value labels that should match the axis: divide by ``factor`` and
    print ``label`` the way the axis label does. ``None`` when the axis has
    no :func:`axis_unit` formatter or has not been drawn since it got one
    (``dm.simple_layout`` and saving draw); ``Unit(1.0, "")`` on a log or
    other non-linear axis, whose ticks print whole values.

    Raises
    ------
    ValueError
        If ``axis`` is not ``"x"`` or ``"y"``.
    """
    formatter = _target(ax, axis).get_major_formatter()
    if isinstance(formatter, LabelUnitFormatter):
        return formatter.unit
    return None
