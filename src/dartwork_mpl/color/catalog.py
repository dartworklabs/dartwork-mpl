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

from ..edgecase import settle
from .decide import diverging_row
from .edges import CURATED_ROW
from .model import (
    Catalog,
    DivergingSource,
    Family,
    Kind,
    Library,
    Row,
    Shipped,
    paired,
    shades,
)
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


def _read(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


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
    table = shades(json.loads(_read(library.source)), library.source)
    return {
        f"{prefix}{name.lower().replace(' ', '')}{weight}": Hex(f"#{value}")
        for name, row in table.items()
        for weight, value in row
    }


def _families(data: Shipped) -> dict[str, Family]:
    """Every ``dc.*`` family, by kind in the order ``list_colors`` shows."""
    ladders, cmaps = data.ladders, data.colormaps
    curated = data.diverging
    picks = data.picks
    diverging = [name for name in cmaps if paired(name)]
    multi_hue = [
        name
        for name in cmaps
        if name not in ladders and name not in diverging and name not in CYCLIC
    ]

    def canonical(name: str) -> Row:
        low, high = name.split("_", maxsplit=1)
        source = DivergingSource(ladders[low], ladders[high], curated.get(name))
        return settle(source, diverging_row(source), (CURATED_ROW,)).plan

    qualitative = {**data.qualitative, **data.cycles}
    families = [
        *(
            Family(name, Kind.SEQUENTIAL, row, cmaps[name])
            for name, row in ladders.items()
        ),
        *(
            Family(name, Kind.MULTI_HUE, cmap=cmaps[name], picks=picks[name])
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
    data = Shipped.parse(json.loads(_read("dartwork.json")))
    families = _families(data)
    curated = {**data.qualitative, **data.diverging}
    catalog = Catalog(
        libraries=LIBRARIES,
        families=MappingProxyType(families),
        named=MappingProxyType(_named(families)),
    )
    return catalog, MappingProxyType(curated)


CATALOG, CURATED = load()
