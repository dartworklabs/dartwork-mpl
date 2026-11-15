"""The shipped colours, read once from ``assets/``.

``dartwork.json`` holds the ``dc.*`` values (ladders, cycles, 256-step
colormaps, multi-hue picks, curated sets). It is the authority: nothing
regenerates it, and ``tests/test_shipped_colors_hash.py`` freezes every
value it ships. The other files are the third-party libraries, registered
under their own prefixes.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib.resources import files
from types import MappingProxyType
from typing import cast

from ..edgecase import settle
from .decide import diverging_row
from .edges import CURATED_ROW
from .model import Catalog, DivergingSource, Family, Kind, Library
from .space import Hex

__all__ = ["CATALOG", "CURATED"]

ASSETS = files(__package__ or __name__) / "assets"
CYCLIC = ("hue", "halo", "corona")
# The two qualitative cycles are colormaps only; every other row is also
# registered as ``dc.<name><index>`` names.
CYCLES = ("octave", "octave_print")
LIBRARIES = (
    Library("dc", "dc.", "dartwork.json", "dartwork Color"),
    Library("opencolor", "oc.", "opencolor.txt", "OpenColor"),
    Library("tw", "tw.", "tailwind_colors.json", "Tailwind"),
    Library("md", "md.", "material_colors.json", "Material Design"),
    Library("ant", "ad.", "ant_colors.json", "Ant Design"),
    Library("chakra", "cu.", "chakra_colors.json", "Chakra UI"),
    Library("primer", "pr.", "primer_colors.json", "Primer"),
)

Row = tuple[Hex, ...]


def _read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def _rows(table: object) -> dict[str, Row]:
    rows = cast("dict[str, list[str]]", table)
    return {name: tuple(Hex(h) for h in row) for name, row in rows.items()}


def _library(library: Library) -> dict[str, Hex]:
    """A third-party library's ``prefix.name`` -> hex entries."""
    prefix = library.prefix
    if library.source.endswith(".txt"):
        named: dict[str, Hex] = {}
        for line in _read(library.source).splitlines():
            if line.startswith("#") or not line.strip():
                continue
            key, value = line.split(":", maxsplit=1)
            named[f"{prefix}{key.strip()}"] = Hex(value.strip())
        return named
    table = json.loads(_read(library.source))
    shades = cast("dict[str, list[list[str]]]", table)
    return {
        f"{prefix}{name.lower().replace(' ', '')}{weight}": Hex(f"#{value}")
        for name, row in shades.items()
        for weight, value in row
    }


def _families(data: Mapping[str, object]) -> dict[str, Family]:
    """Every ``dc.*`` family, by kind in the order ``list_colors`` shows."""
    ladders, cmaps = _rows(data["ladders"]), _rows(data["colormaps"])
    curated = _rows(data["diverging"])
    picks = cast("dict[str, dict[str, list[int]]]", data["multi_hue_stops"])
    diverging = [name for name in cmaps if "_" in name]
    multi_hue = [
        name
        for name in cmaps
        if name not in ladders and name not in diverging and name not in CYCLIC
    ]

    def canonical(name: str) -> Row:
        low, high = name.split("_", maxsplit=1)
        source = DivergingSource(ladders[low], ladders[high], curated.get(name))
        return settle(source, diverging_row(source), (CURATED_ROW,)).plan

    qualitative = {**_rows(data["qualitative"]), **_rows(data["cycles"])}
    families = [
        *(
            Family(name, Kind.SEQUENTIAL, row, cmaps[name])
            for name, row in ladders.items()
        ),
        *(
            Family(
                name,
                Kind.MULTI_HUE,
                cmap=cmaps[name],
                picks=tuple(tuple(ix) for ix in picks[name].values()),
            )
            for name in multi_hue
        ),
        *(
            Family(name, Kind.DIVERGING, canonical(name), cmaps[name])
            for name in diverging
        ),
        *(Family(name, Kind.CYCLIC, cmap=cmaps[name]) for name in CYCLIC),
        *(
            Family(name, Kind.QUALITATIVE, row)
            for name, row in qualitative.items()
        ),
    ]
    return {family.name: family for family in families}


def _named(families: Mapping[str, Family]) -> dict[str, Hex]:
    """Every name registered with matplotlib: the libraries, then ``dc.*``."""
    named: dict[str, Hex] = {}
    for library in LIBRARIES[1:]:
        named.update(_library(library))
    for family in families.values():
        if family.stops and family.name not in CYCLES:
            named.update(
                {f"dc.{family.name}{i}": h for i, h in enumerate(family.stops)}
            )
    return named


def load() -> tuple[Catalog, Mapping[str, Row]]:
    """The catalog, and the hand-tuned sets (the hash test freezes them)."""
    data = cast("dict[str, object]", json.loads(_read("dartwork.json")))
    families = _families(data)
    curated = {**_rows(data["qualitative"]), **_rows(data["diverging"])}
    catalog = Catalog(
        libraries=LIBRARIES,
        families=MappingProxyType(families),
        named=MappingProxyType(_named(families)),
    )
    return catalog, MappingProxyType(curated)


CATALOG, CURATED = load()
