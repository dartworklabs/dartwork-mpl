"""Semantic design-token accessors for dartwork-mpl.

The roles come only from the shipped ``asset/tokens/semantic_tokens.json``,
parsed once at import by :mod:`._table`; there is no in-code copy. Size and
weight accessors resolve against the active preset's ``rcParams`` at call
time. The surface is ``__all__``.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import font_scalings

from ._table import (
    RcToken,
    ScatterLevel,
    SpacingLevel,
    TokenFileMalformed,
    TokenFileUnreadable,
    TokenLoad,
    TokenTable,
    TypeRole,
    WeightRole,
    read_tokens,
)

_TOKEN_PATH = (
    Path(__file__).parent.parent / "asset" / "tokens" / "semantic_tokens.json"
)

# Read once at import. A damaged file does not break ``import dartwork_mpl``;
# it surfaces as an error on the first token access (see ``_table``).
_LOADED: TokenLoad = read_tokens(_TOKEN_PATH)


def _table() -> TokenTable:
    """Return the shipped token table.

    Raises ``RuntimeError`` naming the file and the problem when the shipped
    file was unreadable or malformed at import: that is a damaged
    installation, not a caller error.
    """
    match _LOADED:
        case TokenTable():
            return _LOADED
        case TokenFileUnreadable(path=path, detail=detail):
            problem = f"cannot be read ({detail})"
        case TokenFileMalformed(path=path, detail=detail):
            problem = f"is malformed ({detail})"
    raise RuntimeError(
        f"dartwork-mpl's semantic token file {path} {problem}; "
        "reinstall dartwork-mpl."
    )


def _rcparam_float(rcparam: str) -> float:
    value = plt.rcParams[rcparam]
    try:
        return float(value)
    except (TypeError, ValueError):
        if isinstance(value, str) and value in font_scalings:
            return float(plt.rcParams["font.size"]) * float(
                font_scalings[value]
            )
        return float(plt.rcParams["font.size"])


def _resolve(token: RcToken) -> float:
    """Return ``(rcParams[token.rcparam] + offset) * multiplier`` for the active preset."""
    base = _rcparam_float(token.rcparam)
    return (base + token.offset) * token.multiplier


def _type_scale(name: TypeRole) -> float:
    """Return the resolved text size of type role ``name``."""
    return _resolve(_table().type_scale[name])


def _line_weight(name: WeightRole) -> float:
    """Return the resolved stroke width of line-weight role ``name``."""
    return _resolve(_table().lw_ladder[name])


def version() -> str:
    """Return the semantic-token schema version."""
    return _table().version


def fs_annotation() -> float:
    """Return the annotation text size for the active preset."""
    return _type_scale("annotation")


def fs_tick() -> float:
    """Return the tick-label text size for the active preset."""
    return _type_scale("tick")


def fs_body() -> float:
    """Return the body text size for the active preset."""
    return _type_scale("body")


def fs_label() -> float:
    """Return the axis-label text size for the active preset."""
    return _type_scale("label")


def fs_title() -> float:
    """Return the title text size for the active preset."""
    return _type_scale("title")


def fs_emphasis() -> float:
    """Return the emphasized text size for the active preset."""
    return _type_scale("emphasis")


def lw_hairline() -> float:
    """Return the hairline stroke width for the active preset."""
    return _line_weight("hairline")


def lw_reference() -> float:
    """Return the reference stroke width for the active preset."""
    return _line_weight("reference")


def lw_trend() -> float:
    """Return the trend stroke width for the active preset."""
    return _line_weight("trend")


def lw_emphasis() -> float:
    """Return the emphasized stroke width for the active preset."""
    return _line_weight("emphasis")


def scatter_size(level: ScatterLevel = "default") -> float:
    """Return the scatter marker area for the requested semantic level."""
    sizes = _table().scatter_size
    if level not in sizes:
        valid = ", ".join(sorted(sizes))
        raise ValueError(
            f"Unknown scatter size level {level!r}. Valid levels: {valid}."
        )
    return sizes[level]


def space(level: SpacingLevel = "md") -> float:
    """Return the spacing value in points for the requested semantic level."""
    spacing = _table().spacing
    if level not in spacing:
        valid = ", ".join(sorted(spacing))
        raise ValueError(
            f"Unknown spacing level {level!r}. Valid levels: {valid}."
        )
    return spacing[level]


def as_dict() -> dict[str, float]:
    """Return all currently resolved semantic tokens as exportable floats."""
    return {
        "fs_annotation": fs_annotation(),
        "fs_tick": fs_tick(),
        "fs_body": fs_body(),
        "fs_label": fs_label(),
        "fs_title": fs_title(),
        "fs_emphasis": fs_emphasis(),
        "lw_hairline": lw_hairline(),
        "lw_reference": lw_reference(),
        "lw_trend": lw_trend(),
        "lw_emphasis": lw_emphasis(),
        "scatter_small": scatter_size("small"),
        "scatter_default": scatter_size("default"),
        "scatter_emphasis": scatter_size("emphasis"),
        "space_xs": space("xs"),
        "space_sm": space("sm"),
        "space_md": space("md"),
        "space_lg": space("lg"),
        "space_xl": space("xl"),
    }


__all__ = [
    "as_dict",
    "fs_annotation",
    "fs_body",
    "fs_emphasis",
    "fs_label",
    "fs_tick",
    "fs_title",
    "lw_emphasis",
    "lw_hairline",
    "lw_reference",
    "lw_trend",
    "scatter_size",
    "space",
    "version",
]
