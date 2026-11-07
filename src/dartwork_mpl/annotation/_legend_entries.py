"""Legend entries: reading a legend's drawn entries, the rebuildable test, twin merging and settings kept across a rebuild."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any, TypeAlias

from matplotlib.axes import Axes
from matplotlib.colors import to_hex, to_rgba
from matplotlib.legend import Legend
from matplotlib.offsetbox import DrawingArea, TextArea

from .._figure_geometry import same_position_axes
from ._bar_label_geometry import host_axes


def _legend_entries(ax: Axes) -> tuple[list[Any], list[str]]:
    """The labelled artists of ``ax`` as legend handles and labels."""
    handles, labels = ax.get_legend_handles_labels()
    return list(handles), list(labels)


_EntrySignature: TypeAlias = tuple[str, tuple[type, ...]]
"""One legend entry: its text and the artist types its handle draws."""

# What reading a legend's offset boxes or building a probe legend can raise on
# a handle or handler matplotlib lays out unexpectedly: a missing attribute or
# child (AttributeError, IndexError) or a rejected argument (TypeError,
# ValueError). Anything else is a bug and propagates.
_UNREADABLE = (AttributeError, IndexError, TypeError, ValueError)


def _entry_signatures(legend: Legend) -> list[_EntrySignature]:
    """Each drawn entry of ``legend``, in legend order: text and handle artist types.

    Read through the public ``get_children`` of the legend's offset boxes:
    an entry is the box that holds a handle area and a text. A tuple handle
    draws several artists where a plain one draws one, and a custom handler
    draws its own types, so the signature tells a rebuildable entry from one
    that is not. A legend with no readable entry gives ``[]``.
    """
    found: list[_EntrySignature] = []

    def walk(node: Any) -> None:
        children = node.get_children()
        areas = [c for c in children if isinstance(c, DrawingArea)]
        texts = [c for c in children if isinstance(c, TextArea)]
        if areas and texts:
            found.append(
                (
                    texts[0].get_text(),
                    tuple(type(a) for a in areas[0].get_children()),
                )
            )
            return
        for child in children:
            if child.__class__.__module__ == "matplotlib.offsetbox":
                walk(child)

    walk(legend.get_children()[0])
    return found


def _probe_signatures(
    host: Axes,
    handles: list[Any],
    labels: list[str],
    handler_map: dict[Any, Any],
) -> list[_EntrySignature]:
    """What plain ``handles`` draw through ``handler_map``, via a detached legend."""
    probe = Legend(host, handles, labels, handler_map=handler_map)
    return _entry_signatures(probe)


def _rebuildable(
    legend: Legend, host: Axes, candidates: list[tuple[list[Any], list[str]]]
) -> bool:
    """Whether ``legend`` is what plain artists would draw, entry for entry.

    ``candidates`` are the (handles, labels) the legend may have been built
    from: the whole pair's artists (a hand merge, or the merged legend) or one
    Axes' own. The legend is rebuildable when its entries equal, position by
    position and in count, what some candidate draws through the legend's own
    ``handler_map``. Fails safe: an empty or unreadable legend, or any
    ``_UNREADABLE`` error while reading it or the probe, is not rebuildable.
    """
    handler_map: dict[Any, Any] = dict(legend.get_legend_handler_map())

    def read(
        signatures: Callable[[], list[_EntrySignature]],
    ) -> list[_EntrySignature] | None:
        # Only matplotlib's legend layout and a detached Legend are read
        # under the guard; the comparison below stays outside it, so a
        # defect there surfaces instead of reading as "leave it".
        try:
            return signatures()
        except _UNREADABLE:
            return None

    drawn = read(lambda: _entry_signatures(legend))
    if not drawn:
        return False
    for handles, labels in candidates:
        if not handles:
            continue
        probe = read(
            partial(_probe_signatures, host, handles, labels, handler_map)
        )
        if probe is not None and drawn == probe:
            return True
    return False


def _mark_placed(legend: Legend) -> None:
    """Mark ``legend`` as built by ``place_legend``, with its entries as built.

    ``_dm_placed_legend`` (documented) says the legend is the library's;
    ``_dm_placed_entries`` holds what its entries read now, so a later call
    can tell an entry the caller edited since (``[]`` when unreadable).
    """
    try:
        entries = _entry_signatures(legend)
    except _UNREADABLE:
        entries = []
    legend._dm_placed_legend = True  # type: ignore[attr-defined]
    legend._dm_placed_entries = entries  # type: ignore[attr-defined]


def _placed_as_built(legend: Legend) -> bool:
    """Whether ``place_legend`` built ``legend`` and its entries read as built.

    Such a legend is the library's: the next call rebuilds it from the
    artists drawn then (series added or removed since). One whose entries
    changed since (a text set by the caller) or cannot be read is not, and
    meets the structure rule of a caller's legend (:func:`_rebuildable`).
    """
    if getattr(legend, "_dm_placed_legend", False) is not True:
        return False
    built = getattr(legend, "_dm_placed_entries", None)
    if not built:
        return False
    try:
        now = _entry_signatures(legend)
    except _UNREADABLE:
        return False
    return bool(now == built)


def _legend_settings(
    legend: Legend | None, default: Legend | None
) -> dict[str, Any]:
    """The settings of ``legend`` a rebuilt legend repeats, as ``Legend`` keywords.

    Only what the public ``Legend`` API reads, and only what differs from
    ``default`` (a fresh legend of the same entries under the current
    preset), so an untouched default stays a default and follows a later
    style change. ``ncols`` has no public getter: pass it to ``place_legend``
    to keep it.
    """
    if legend is None or default is None:
        return {}
    kept: dict[str, Any] = {}
    title = legend.get_title()
    if title.get_text():
        kept["title"] = title.get_text()
    if title.get_fontproperties() != default.get_title().get_fontproperties():
        kept["title_fontproperties"] = title.get_fontproperties().copy()
    default_map = Legend.get_default_handler_map()
    custom = {
        key: handler
        for key, handler in legend.get_legend_handler_map().items()
        if default_map.get(key) is not handler
    }
    if custom:
        kept["handler_map"] = custom
    if legend.get_frame_on() != default.get_frame_on():
        kept["frameon"] = legend.get_frame_on()
    if legend.get_alignment() != default.get_alignment():
        kept["alignment"] = legend.get_alignment()
    if legend.markerscale != default.markerscale:
        kept["markerscale"] = legend.markerscale
    if legend.get_draggable():
        kept["draggable"] = True
    texts, defaults = legend.get_texts(), default.get_texts()
    if texts and defaults:
        if texts[0].get_fontproperties() != defaults[0].get_fontproperties():
            kept["prop"] = texts[0].get_fontproperties().copy()
        colors = {to_rgba(t.get_color()) for t in texts}
        if len(colors) == 1 and colors != {to_rgba(defaults[0].get_color())}:
            kept["labelcolor"] = to_hex(texts[0].get_color(), keep_alpha=True)
    return kept


def _caller_wins(kept: dict[str, Any], kw: dict[str, Any]) -> dict[str, Any]:
    """Kept settings under the caller's keywords; a caller size drops the kept font."""
    merged = {**kept, **kw}
    if "fontsize" in kw and "prop" not in kw:
        merged.pop("prop", None)
    if "title_fontsize" in kw and "title_fontproperties" not in kw:
        merged.pop("title_fontproperties", None)
    return merged


def _merge_twin_legends(
    ax: Axes,
) -> tuple[Axes, list[Any], list[str], dict[str, Any], Legend | None]:
    """One legend for a twin pair: every partner's entries, on the top axes.

    The legend goes on the top twin (the Axes drawn last), so no partner's
    data is drawn over it; the partners' own legends are removed after their
    settings (title, ``handler_map`` and so on) are read for the rebuild. A
    single Axes returns itself and its own entries.

    The last item is a legend to leave untouched: one that is not what the
    pair's own artists would draw (tuple handles, custom handlers, explicit
    labels). The explicit legend wins and nothing is removed. A legend an
    earlier ``place_legend`` built, its entries as built, is the library's
    and is always rebuilt from the artists now (:func:`_placed_as_built`).
    """
    owners = same_position_axes(ax)
    host = host_axes(ax)
    parent = host.get_figure(root=False)
    order = parent.axes if parent is not None else owners
    handles: list[Any] = []
    labels: list[str] = []
    seen: set[str] = set()
    for owner in sorted(owners, key=order.index):
        for handle, label in zip(*_legend_entries(owner), strict=True):
            if label not in seen:
                seen.add(label)
                handles.append(handle)
                labels.append(label)
    existing = [
        legend for o in owners if (legend := o.get_legend()) is not None
    ]
    for owner in owners:
        legend = owner.get_legend()
        if legend is None or _placed_as_built(legend):
            continue
        own = _legend_entries(owner)
        if not _rebuildable(legend, host, [(handles, labels), own]):
            return host, handles, labels, {}, legend
    source = host.get_legend() or next(iter(existing), None)
    default = Legend(host, handles, labels) if handles else None
    settings = _legend_settings(source, default)
    for owner in owners:
        legend = owner.get_legend()
        if owner is not host and legend is not None:
            legend.remove()
    return host, handles, labels, settings, None
