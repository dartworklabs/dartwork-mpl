"""The shape of the shipped colour tables, checked as they are decoded.

:func:`decode` reads a table's text; each other function here takes one part
of a decoded table and returns it typed, or raises ``ValueError`` naming the
part out of shape. Nothing here reads a file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from ..colorspace import Hex
from .model import Items, Row


class JsonObject(dict[str, object]):
    """A decoded JSON object: :func:`decode` builds every one."""


def decode(text: str) -> object:
    """The JSON ``text``, each of its objects a :class:`JsonObject`."""
    found: object = json.loads(text, object_pairs_hook=JsonObject)
    return found


def json_object(value: object, where: str) -> JsonObject:
    """A decoded JSON object; ``ValueError`` names ``where``."""
    if not isinstance(value, JsonObject):
        raise ValueError(f"{where}: expected a JSON object")
    return value


def json_list(value: object, where: str) -> list[object]:
    """A decoded JSON array; ``ValueError`` names ``where``.

    Of the values :func:`decode` gives, a string, an object and an array
    have items; an array is the one that is neither of the others.
    """
    if isinstance(value, str | JsonObject) or not isinstance(value, Items):
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
