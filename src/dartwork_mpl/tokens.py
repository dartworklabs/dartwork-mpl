"""Semantic design-token accessors for dartwork-mpl."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, TypedDict, cast

import matplotlib.pyplot as plt
from matplotlib.font_manager import font_scalings


class _ResolvedToken(TypedDict):
    rcparam: str
    offset: float
    multiplier: float


class _TokenData(TypedDict):
    version: str
    type_scale: dict[str, _ResolvedToken]
    lw_ladder: dict[str, _ResolvedToken]
    scatter_size: dict[str, float]


ScatterLevel = Literal["small", "default", "emphasis"]

_TOKEN_PATH = (
    Path(__file__).parent / "asset" / "tokens" / "semantic_tokens.json"
)

_FALLBACK_TOKENS: _TokenData = {
    "version": "1",
    "type_scale": {
        "annotation": {
            "rcparam": "font.size",
            "offset": -1.0,
            "multiplier": 1.0,
        },
        "tick": {
            "rcparam": "xtick.labelsize",
            "offset": 0.0,
            "multiplier": 1.0,
        },
        "body": {"rcparam": "font.size", "offset": 0.0, "multiplier": 1.0},
        "label": {
            "rcparam": "axes.labelsize",
            "offset": 0.0,
            "multiplier": 1.0,
        },
        "title": {
            "rcparam": "axes.titlesize",
            "offset": 0.0,
            "multiplier": 1.0,
        },
        "emphasis": {"rcparam": "font.size", "offset": 1.5, "multiplier": 1.0},
    },
    "lw_ladder": {
        "hairline": {
            "rcparam": "lines.linewidth",
            "offset": 0.0,
            "multiplier": 0.3,
        },
        "reference": {
            "rcparam": "lines.linewidth",
            "offset": 0.0,
            "multiplier": 0.3,
        },
        "trend": {
            "rcparam": "lines.linewidth",
            "offset": 0.0,
            "multiplier": 1.0,
        },
        "emphasis": {
            "rcparam": "lines.linewidth",
            "offset": 0.0,
            "multiplier": 1.6,
        },
    },
    "scatter_size": {"small": 16.0, "default": 30.0, "emphasis": 45.0},
}


def _as_float(value: object) -> float:
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"expected a number, got {type(value).__name__}")


def _coerce_token(token: Mapping[str, object]) -> _ResolvedToken:
    return {
        "rcparam": str(token["rcparam"]),
        "offset": _as_float(token.get("offset", 0.0)),
        "multiplier": _as_float(token.get("multiplier", 1.0)),
    }


def _coerce_token_map(value: object) -> dict[str, _ResolvedToken]:
    raw_tokens = cast(Mapping[str, object], value)
    return {
        str(name): _coerce_token(cast(Mapping[str, object], token))
        for name, token in raw_tokens.items()
    }


def _coerce_float_map(value: object) -> dict[str, float]:
    raw_values = cast(Mapping[str, object], value)
    return {str(name): _as_float(size) for name, size in raw_values.items()}


def _load_tokens() -> _TokenData:
    try:
        raw = json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
        raw_tokens = cast(Mapping[str, object], raw)
        return {
            "version": str(raw_tokens["version"]),
            "type_scale": _coerce_token_map(raw_tokens["type_scale"]),
            "lw_ladder": _coerce_token_map(raw_tokens["lw_ladder"]),
            "scatter_size": _coerce_float_map(raw_tokens["scatter_size"]),
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _FALLBACK_TOKENS


_TOKENS = _load_tokens()


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


def _resolve(token: _ResolvedToken) -> float:
    base = _rcparam_float(token["rcparam"])
    return (base + token["offset"]) * token["multiplier"]


def _type_scale(name: str) -> float:
    return _resolve(_TOKENS["type_scale"][name])


def _line_weight(name: str) -> float:
    return _resolve(_TOKENS["lw_ladder"][name])


def version() -> str:
    """Return the semantic-token schema version."""
    return _TOKENS["version"]


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
    sizes = _TOKENS["scatter_size"]
    if level not in sizes:
        valid = ", ".join(sorted(sizes))
        raise ValueError(
            f"Unknown scatter size level {level!r}. Valid levels: {valid}."
        )
    return sizes[level]


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
    "version",
]
