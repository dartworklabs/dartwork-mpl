"""Public Model B color API."""

from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Literal, overload

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from cycler import cycler

from ._discrete import discrete_colors
from ._families import FAMILIES, Family, FamilyKind
from ._register import ensure_registered

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.colors import Colormap
    from matplotlib.figure import Figure

__all__ = ["colors", "list_colors", "set_colors", "show_colors"]

_KIND_ORDER: tuple[FamilyKind, ...] = (
    "sequential",
    "multi-hue",
    "diverging",
    "cyclic",
    "qualitative",
)
_DEFAULT_LINESTYLES = ("-", "--", ":")


def _family_name(name: str) -> str:
    return name[3:] if name.startswith("dc.") else name


def _nearest_names(name: str) -> tuple[str, str, str]:
    ranked = sorted(
        (
            (candidate, SequenceMatcher(None, name, candidate).ratio())
            for candidate in FAMILIES
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(candidate for candidate, _score in ranked[:3])  # type: ignore[return-value]


def _resolve_family_name(name: str) -> str:
    family_name = _family_name(name)
    if family_name in FAMILIES:
        return family_name
    nearest = ", ".join(_nearest_names(family_name))
    raise ValueError(
        f"Unknown color family {family_name!r}. Nearest names: {nearest}."
    )


def _validate_kind(kind: str | None) -> FamilyKind | None:
    if kind is None:
        return None
    if kind not in _KIND_ORDER:
        expected = ", ".join(_KIND_ORDER)
        raise ValueError(
            f"Unknown color kind {kind!r}; expected one of: {expected}."
        )
    return kind  # type: ignore[return-value]


def _qualitative_cmap(name: str, family: Family, *, reverse: bool) -> Colormap:
    n = int(family.discrete_size or 0)
    hexes = discrete_colors(name, n, reverse=reverse)
    suffix = "_r" if reverse else ""
    return mcolors.ListedColormap(
        [mcolors.to_rgba(hex_value) for hex_value in hexes],
        name=f"dc.{name}{suffix}",
    )


@overload
def colors(
    name: str, n: None = None, *, reverse: bool = False
) -> mcolors.Colormap: ...


@overload
def colors(name: str, n: int, *, reverse: bool = False) -> list[str]: ...


def colors(
    name: str, n: int | None = None, *, reverse: bool = False
) -> mcolors.Colormap | list[str]:
    """Return a Model B colormap or designed discrete color form.

    Bare family names (``"aurora"``) and registered names
    (``"dc.aurora"``) are equivalent. ``n=None`` returns the matplotlib
    colormap for that family; ``n=int`` returns the deterministic designed
    discrete form as hex strings.
    """
    family_name = _resolve_family_name(name)
    family = FAMILIES[family_name]
    if n is not None:
        return discrete_colors(family_name, n, reverse=reverse)

    ensure_registered()
    cmap_name = f"dc.{family_name}"
    if reverse:
        reverse_name = f"{cmap_name}_r"
        if reverse_name in mpl.colormaps:
            return mpl.colormaps[reverse_name]
        if cmap_name in mpl.colormaps:
            return mpl.colormaps[cmap_name].reversed(name=reverse_name)
        return _qualitative_cmap(family_name, family, reverse=True)
    if cmap_name in mpl.colormaps:
        return mpl.colormaps[cmap_name]
    if family.kind == "qualitative":
        return _qualitative_cmap(family_name, family, reverse=False)
    raise ValueError(f"Registered colormap {cmap_name!r} is not available.")


def _colors_for_cycle(
    name_or_list: str | Iterable[str] | None, n: int | None
) -> list[str]:
    if name_or_list is None:
        return discrete_colors("octave", 8)
    if isinstance(name_or_list, str):
        family_name = _resolve_family_name(name_or_list)
        family = FAMILIES[family_name]
        if n is None:
            if family.kind != "qualitative":
                raise ValueError(
                    f"{family_name!r} is a {family.kind} family and requires n= "
                    "when used with dm.set_colors(...)."
                )
            n = int(family.discrete_size or 0)
        return discrete_colors(family_name, n)
    return list(name_or_list)


def set_colors(
    name_or_list: str | Iterable[str] | None = None,
    *,
    ax: Axes | None = None,
    n: int | None = None,
    styles: bool = False,
) -> None:
    """Set the matplotlib color cycle from a Model B family or explicit list."""
    selected = _colors_for_cycle(name_or_list, n)
    prop_cycle = cycler(color=selected)
    if styles:
        prop_cycle = cycler(linestyle=list(_DEFAULT_LINESTYLES)) * prop_cycle

    if ax is None:
        from ..style import _style_lock

        with _style_lock:
            plt.rcParams["axes.prop_cycle"] = prop_cycle
    else:
        ax.set_prop_cycle(prop_cycle)


def list_colors(
    kind: Literal[
        "sequential", "multi-hue", "diverging", "cyclic", "qualitative"
    ]
    | str
    | None = None,
) -> list[dict[str, object]]:
    """List Model B color families and their metadata."""
    kind_filter = _validate_kind(kind)
    return [
        {
            "name": name,
            "kind": family.kind,
            "continuous": family.has_continuous,
            "discrete_size": family.discrete_size,
        }
        for name, family in FAMILIES.items()
        if kind_filter is None or family.kind == kind_filter
    ]


def _preview_n(family: Family, requested: int | None) -> int:
    if requested is not None:
        return requested
    if family.kind == "qualitative":
        return int(family.discrete_size or 8)
    if family.kind == "sequential":
        return 5
    if family.kind == "diverging":
        return 5
    if family.kind == "multi-hue":
        return 6
    return 12


def show_colors(
    kind: Literal[
        "sequential", "multi-hue", "diverging", "cyclic", "qualitative"
    ]
    | str
    | None = None,
    names: Iterable[str] | None = None,
    n: int | None = None,
) -> Figure:
    """Return a compact preview figure for Model B color families."""
    kind_filter = _validate_kind(kind)
    if names is None:
        selected_names = [
            name
            for name, family in FAMILIES.items()
            if kind_filter is None or family.kind == kind_filter
        ]
    else:
        selected_names = [_resolve_family_name(name) for name in names]
        if kind_filter is not None:
            selected_names = [
                name
                for name in selected_names
                if FAMILIES[name].kind == kind_filter
            ]
    if not selected_names:
        raise ValueError("No color families match the requested preview.")

    from ..units import figsize, inch

    row_count = len(selected_names)
    fig_height = max(1.2, 0.42 * row_count + 0.4)
    fig, ax = plt.subplots(figsize=figsize("16cm", inch(fig_height)))
    ax.set_xlim(-0.24, 1.0)
    ax.set_ylim(0, row_count)
    ax.axis("off")

    for row_index, name in enumerate(selected_names):
        family = FAMILIES[name]
        y = row_count - row_index - 1
        ax.text(-0.02, y + 0.5, name, ha="right", va="center", fontsize=8)

        if family.has_continuous:
            gradient = [list(range(256))]
            ax.imshow(
                gradient,
                aspect="auto",
                cmap=colors(name),
                extent=(0.0, 1.0, y + 0.56, y + 0.88),
                interpolation="nearest",
            )
            swatch_y0, swatch_y1 = y + 0.14, y + 0.46
        else:
            swatch_y0, swatch_y1 = y + 0.24, y + 0.76

        swatches = discrete_colors(name, _preview_n(family, n))
        width = 1.0 / len(swatches)
        for i, color_value in enumerate(swatches):
            ax.add_patch(
                mpatches.Rectangle(
                    (i * width, swatch_y0),
                    width,
                    swatch_y1 - swatch_y0,
                    facecolor=color_value,
                    edgecolor="white",
                    linewidth=0.3,
                )
            )

    fig.subplots_adjust(left=0.22, right=0.98, top=0.96, bottom=0.04)
    return fig
