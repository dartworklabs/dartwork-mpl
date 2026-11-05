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
    own label (:func:`_sibling_template`): the installing template's unit
    slot - its ``( )`` or ``[ ]`` group or the word holding ``{unit}`` - is
    recognised in the label with its base unit or a ladder unit already
    written (``인구 (명)`` -> ``인구 (억명)`` under ``가구 ({unit}명)``;
    ``Cost (USD)`` -> ``Cost (USD B)``; ``Loss [W]`` -> ``Loss [kW]``), any
    other label gets `` ({unit})`` (``인구`` -> ``인구 (억)``). A label
    someone sets later (an edit, ``dm.wrap_axis_labels``) is read the same
    way, so its unit follows the ticks and is never doubled. An inner panel
    whose label ``label_outer`` emptied (tick labels hidden, a sibling
    showing them) stays unlabelled. When no label would name the unit, the
    first axis that shows the ticks carries it: the inner panel's template,
    or just `` ({unit})`` after a visible label was emptied. On a log or
    other non-linear axis the ticks span decades, which one label cannot
    name, so every tick prints its whole value with thousands separators
    (``100``, ``1,000,000``), the label carries no unit and :attr:`unit` is
    the empty one (``Unit(1.0, "")``).
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
        # The installing template: where a sharing axes' label takes the unit.
        self._installed = template
        self._shared: dict[Axis, str] = {}
        # The text last written to each label, to tell an edit from our own.
        self._wrote: dict[Axis, str] = {}
        # A label's template before it was emptied (label_outer, set_ylabel("")).
        self._emptied: dict[Axis, str] = {}
        # The axis that showed the unit last draw only because no label did.
        self._fallback: Axis | None = None

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

        Its text becomes that label's template (:func:`_adopt`): the unit is
        recognised where the label's own template or the installing one puts
        it (a unit already written is kept, never doubled; line breaks from
        ``dm.wrap_axis_labels`` stay), else appended. An emptied label stays
        empty; its template is kept for :meth:`_last_place`.
        """
        for axis, template in self.templates().items():
            last = self._wrote.get(axis)
            text = axis.label.get_text()
            if last is None or text == last:
                continue
            made = _adopt(
                text,
                [t for t in (template, self._installed) if t],
                self._ladder,
            )
            if not made and template:
                self._emptied[axis] = template
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
        has a label of its own but no template (not text this formatter
        wrote), and leaves an inner unlabelled panel alone.
        """
        own = self.axis
        if not isinstance(own, Axis):
            return dict(self._shared)
        self._adopt_edits()
        siblings = _sharing(own)
        for other in siblings:
            text = other.label.get_text()
            if (
                other is not own
                and other not in self._shared
                and text.strip()
                and text != self._wrote.get(other)
            ):
                self._shared[other] = _sibling_template(
                    text, self._installed, self._ladder
                )
        return {
            axis: template
            for axis, template in self.templates().items()
            if not _inner_unlabelled(axis, siblings)
        }

    def _last_place(self, written: dict[Axis, str]) -> tuple[Axis, str] | None:
        """Where the unit goes when no label written this draw names it.

        Scaled ticks need a label that says so. When every label is empty
        or hidden, the first sharing axis that shows the ticks takes the
        template of an inner panel that ``label_outer`` (or an inner
        installer) left empty, else just `` ({unit})``.
        """
        own = self.axis
        if not isinstance(own, Axis):
            return None
        if any(
            template and axis.get_visible() and axis.label.get_visible()
            for axis, template in written.items()
        ):
            return None
        siblings = _sharing(own)
        source = next(
            (
                template or self._emptied.get(axis, "")
                for axis, template in self.templates().items()
                if _inner_unlabelled(axis, siblings)
                and (template or self._emptied.get(axis))
            ),
            f"({_PLACEHOLDER})",
        )
        target = next((axis for axis in siblings if _shows_ticks(axis)), None)
        return None if target is None else (target, source)

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
        written = self.labels()
        previous, self._fallback = self._fallback, None
        last_place = self._last_place(written)
        if last_place is not None:
            target, template = last_place
            written[target] = template
            self._fallback = target
        if (
            previous is not None
            and previous not in written
            and previous.label.get_text() == self._wrote.get(previous)
        ):
            written[previous] = ""  # no longer the last place: clear it
        for axis, template in written.items():
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


_BRACKETS = (("(", ")"), ("[", "]"))


def _unit_slot(template: str) -> tuple[int, int] | None:
    """Where ``template`` holds the unit: the span of its unit slot.

    The innermost ``( )`` or ``[ ]`` group around the last ``{unit}``
    (``({unit}명)``, ``(USD {unit})``, ``[{unit}W]``), else the run of
    non-space characters around it (``{unit}W`` in ``Power / {unit}W``).
    ``None`` when the template has no ``{unit}``.
    """
    at = template.rfind(_PLACEHOLDER)
    if at < 0:
        return None
    after = at + len(_PLACEHOLDER)
    best: tuple[int, int] | None = None
    for opener, closer in _BRACKETS:
        start = template.rfind(opener, 0, at)
        stop = template.find(closer, after)
        if start < 0 or stop < 0:
            continue
        inside = template[start + 1 : at] + template[after:stop]
        if any(mark in inside for pair in _BRACKETS for mark in pair):
            continue
        if best is None or start > best[0]:
            best = (start, stop + 1)
    if best is not None:
        return best
    start = max((m.end() for m in re.finditer(r"\s", template[:at])), default=0)
    space = re.search(r"\s", template[after:])
    return start, after + space.start() if space else len(template)


def _loose(text: str) -> str:
    """``text`` as a pattern: literal words, any whitespace between them."""
    return r"\s+".join(re.escape(word) for word in text.split())


def _slot_pattern(slot: str, ladder: Sequence[Unit]) -> str:
    """A pattern for ``slot`` with any unit of ``ladder`` (or none) in it.

    The unit is the named group ``unit``; whitespace (line breaks included,
    as ``dm.wrap_axis_labels`` puts in) may vary. A slot that is not a
    bracket group must stand as a whole word.
    """
    before, _, after = slot.partition(_PLACEHOLDER)
    symbols = sorted(
        (u.label for u in ladder if u.label), key=len, reverse=True
    )
    units = "|".join(re.escape(symbol) for symbol in symbols)
    body = rf"{_loose(before)}\s*(?P<unit>{units})?\s*{_loose(after)}"
    if slot[:1] in "([":
        return body
    return rf"(?<!\S){body}(?!\S)"


def _recognise(
    label: str, template: str, ladder: Sequence[Unit], *, anywhere: bool
) -> str | None:
    """``label`` with its unit slot read the way ``template`` writes it.

    Not ``anywhere``: the slot must sit where the template puts it, before
    the template's own trailing text (``, net``), at the end of the label;
    it may hold any ladder unit or none (``(명)``, ``(억명)``). ``anywhere``:
    the last slot in the label that holds a ladder unit, so a unit already
    written is recognised wherever an edit moved it, never doubled. The
    unit there becomes ``{unit}``; a slot without one takes the template's
    slot. ``None`` when nothing matches.
    """
    span = _unit_slot(template)
    if span is None:
        return None
    slot, tail = template[span[0] : span[1]], template[span[1] :]
    pattern = _slot_pattern(slot, ladder)
    if anywhere:
        found = [m for m in re.finditer(pattern, label) if m["unit"]]
        match = found[-1] if found else None
    else:
        match = re.search(
            rf"(?P<slot>{pattern})\s*{_loose(tail)}\s*\Z", label, re.DOTALL
        )
    if match is None:
        return None
    if match["unit"]:
        return (
            label[: match.start("unit")]
            + _PLACEHOLDER
            + label[match.end("unit") :]
        )
    start, end = match.span("slot") if not anywhere else match.span()
    return label[:start] + slot + label[end:]


def _adopt(label: str, templates: Sequence[str], ladder: Sequence[Unit]) -> str:
    """The template for a label someone wrote, recognising the unit slot.

    Tried in order: the label already holds ``{unit}``; each template's
    slot where that template puts it; a slot holding a ladder unit anywhere
    (the unit written last, kept rather than doubled); otherwise
    `` ({unit})`` appended. An empty label stays empty.
    """
    if not label.strip():
        return ""
    if _PLACEHOLDER in label:
        return label
    for anywhere in (False, True):
        for template in templates:
            made = _recognise(label, template, ladder, anywhere=anywhere)
            if made is not None:
                return made
    return _template(label)


def _sibling_template(label: str, template: str, ladder: Sequence[Unit]) -> str:
    """A shared sibling's template, made from its own label.

    ``template`` is the installing template. The sibling's text takes the
    unit only where it holds that template's unit slot - its base unit
    (``(명)`` for ``({unit}명)``, ``(USD)`` for ``(USD {unit})``, ``[W]``
    for ``[{unit}W]``) at the template's place, or a ladder unit already
    written (``(억명)``, ``(USD B)``), never doubled. Any other label gets
    `` ({unit})`` appended (``(별도)``, ``(2024)``, ``(est.)``, a second
    line, or every label when the installer itself appends).
    """
    return _adopt(label, [template], ladder)


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
    of these axes, or ``dm.wrap_axis_labels``) becomes that label's
    template the same way, the unit you see in it recognised wherever this
    label's template puts it (``[kW]``, ``/ kW``, ``(kW), net``), never
    doubled. An emptied label stays empty unless no other label would show
    the unit of scaled ticks; then the axis that shows the ticks carries it.
    Call ``axis_unit`` on each (``for a in axes: dm.axis_unit(a, "y",
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
    if _inner_unlabelled(target, _sharing(target)):
        formatter.note_written(target, "")  # left empty: an edit shows later
    else:
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
