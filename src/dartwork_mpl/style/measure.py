"""Read the bundled layers and the live rcParams."""

from __future__ import annotations

import copy
from importlib.resources import files
from typing import TYPE_CHECKING, cast

import matplotlib as mpl
from matplotlib import RcParams

from .model import Points, Registry, Weight

if TYPE_CHECKING:
    from collections.abc import Mapping

    from matplotlib.typing import RcKeyType

ASSETS = files(__package__ or __name__) / "assets"


def registry() -> Registry:
    """The presets ``assets/presets.json`` ships."""
    return Registry.from_json((ASSETS / "presets.json").read_text("utf-8"))


def layer_path(layer: str) -> str:
    """The bundled ``.mplstyle`` file of ``layer``; ``ValueError`` if none."""
    path = ASSETS / f"{layer}.mplstyle"
    if not path.is_file():
        known = sorted(
            p.name.removesuffix(".mplstyle")
            for p in ASSETS.iterdir()
            if p.name.endswith(".mplstyle")
        )
        raise ValueError(
            f"Style {layer!r} not found. Available styles: {known}."
        )
    return str(path)


def load_style_dict(layer: str) -> RcParams:
    """The rcParams a bundled layer declares, as matplotlib reads them."""
    return mpl.rc_params_from_file(  # pyright: ignore[reportUnknownMemberType]
        layer_path(layer), use_default_template=False
    )


def differs(a: object, b: object) -> bool:
    """``a != b``, by ``repr`` for values that do not compare (cyclers)."""
    try:
        return bool(a != b)
    except (TypeError, ValueError):
        return repr(a) != repr(b)


def edits(values: Mapping[str, object]) -> dict[str, object]:
    """Live rcParams the caller changed: off the value the active preset
    wrote (``values``), or off matplotlib's default where it wrote none."""
    defaults = mpl.rcParamsDefault
    found: dict[str, object] = {}
    for key in list(mpl.rcParams):
        if key not in defaults:
            continue
        value = mpl.rcParams[key]
        if differs(value, values.get(key, defaults[key])):
            found[key] = copy.deepcopy(value)
    return found


def in_force(values: Mapping[str, object]) -> bool:
    """Whether the live rcParams still hold a preset that wrote ``values``.

    Not when every key on which the preset differs from matplotlib's default
    has since moved off the preset's value: a native reset
    (``plt.rcdefaults()``, ``plt.style.use("default")``).
    """
    defaults = mpl.rcParamsDefault
    changed = [
        key
        for key, value in values.items()
        if key in defaults and differs(value, defaults[cast("RcKeyType", key)])
    ]
    if not changed:
        return bool(values)
    return not all(
        differs(mpl.rcParams[cast("RcKeyType", key)], values[key])
        for key in changed
    )


def font_size() -> Points:
    """``rcParams['font.size']``."""
    return Points(float(mpl.rcParams["font.size"]))


def line_width() -> Points:
    """``rcParams['lines.linewidth']``."""
    return Points(float(mpl.rcParams["lines.linewidth"]))


def font_weight() -> Weight:
    """``rcParams['font.weight']``."""
    return Weight.parse(mpl.rcParams["font.weight"])
