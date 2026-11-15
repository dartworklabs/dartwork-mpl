"""The shape of the shipped colour tables, checked as they are decoded.

``json.loads`` gives untyped values; each function here takes one part of a
table and returns it typed, or raises ``ValueError`` naming the part out of
shape. Nothing here reads a file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeGuard

from .model import Row
from .space import Hex


def _is_object(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, dict)


def _is_array(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, list)


def json_object(value: object, where: str) -> dict[str, object]:
    """A JSON object with string keys; ``ValueError`` names ``where``."""
    if not _is_object(value):
        raise ValueError(f"{where}: expected a JSON object")
    found: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{where}: key {key!r} is not a string")
        found[key] = item
    return found


def json_list(value: object, where: str) -> list[object]:
    """A JSON array; ``ValueError`` names ``where``."""
    if not _is_array(value):
        raise ValueError(f"{where}: expected a JSON array")
    return list(value)


def json_text(value: object, where: str) -> str:
    """A JSON string; ``ValueError`` names ``where``."""
    if not isinstance(value, str):
        raise ValueError(f"{where}: expected a string, got {value!r}")
    return value


def json_whole(value: object, where: str) -> int:
    """A JSON integer; ``ValueError`` names ``where``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where}: expected an integer, got {value!r}")
    return value


def rows(value: object, where: str) -> dict[str, Row]:
    """``{name: ["#rrggbb", ...]}`` as rows of hex values."""
    return {
        name: tuple(
            Hex(json_text(h, f"{where}.{name}"))
            for h in json_list(row, f"{where}.{name}")
        )
        for name, row in json_object(value, where).items()
    }


def shades(value: object, where: str) -> dict[str, tuple[tuple[str, str], ...]]:
    """``{name: [[weight, "rrggbb"], ...]}``: a library's shades by name."""
    found: dict[str, tuple[tuple[str, str], ...]] = {}
    for name, row in json_object(value, where).items():
        pairs: list[tuple[str, str]] = []
        for pair in json_list(row, f"{where}.{name}"):
            weight, shade = json_list(pair, f"{where}.{name}")
            pairs.append(
                (
                    json_text(weight, f"{where}.{name}"),
                    json_text(shade, f"{where}.{name}"),
                )
            )
        found[name] = tuple(pairs)
    return found


def picks(value: object, where: str) -> dict[str, tuple[tuple[int, ...], ...]]:
    """``{family: {n: [index, ...]}}``: each form's colormap indices, in file
    order."""
    return {
        name: tuple(
            tuple(
                json_whole(i, f"{where}.{name}")
                for i in json_list(ix, f"{where}.{name}")
            )
            for ix in json_object(forms, f"{where}.{name}").values()
        )
        for name, forms in json_object(value, where).items()
    }


@dataclass(frozen=True)
class Shipped:
    """``dartwork.json``: the rows every ``dc.*`` family is built from."""

    ladders: Mapping[str, Row]
    cycles: Mapping[str, Row]
    colormaps: Mapping[str, Row]
    picks: Mapping[str, tuple[tuple[int, ...], ...]]
    qualitative: Mapping[str, Row]
    diverging: Mapping[str, Row]

    @classmethod
    def parse(cls, data: object) -> Shipped:
        """The decoded file; ``ValueError`` names the part out of shape."""
        table = json_object(data, "dartwork.json")
        return cls(
            ladders=rows(table["ladders"], "ladders"),
            cycles=rows(table["cycles"], "cycles"),
            colormaps=rows(table["colormaps"], "colormaps"),
            picks=picks(table["multi_hue_stops"], "multi_hue_stops"),
            qualitative=rows(table["qualitative"], "qualitative"),
            diverging=rows(table["diverging"], "diverging"),
        )
