"""Facts from disk and from matplotlib's font manager."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager

from .model import Expected, Face, Table, Weight, math_sets

SUFFIXES = (".ttf", ".otf")
# File-name prefix of the fonts matplotlib ships for each mathtext font set.
MATH_PREFIX = {
    "cm": "cm",
    "stix": "STIX",
    "stixsans": "STIX",
    "dejavusans": "DejaVu",
    "dejavuserif": "DejaVu",
}


def font_dir() -> Path:
    """The directory of the bundled font files."""
    return Path(str(files(__package__ or __name__) / "assets")).resolve()


def bundled_files() -> list[Path]:
    """Every bundled font file, sorted."""
    return sorted(p for p in font_dir().iterdir() if p.suffix in SUFFIXES)


def inside(entry: font_manager.FontEntry, folder: Path) -> bool:
    """Whether the entry's file lies in ``folder``."""
    try:
        return Path(entry.fname).resolve().is_relative_to(folder)
    except (OSError, ValueError):
        return False


def table() -> Table:
    """Matplotlib's font table as faces."""
    bundle = font_dir()
    return Table(
        faces=tuple(
            Face(
                file=Path(entry.fname).name,
                family=entry.name,
                weight=Weight(entry.weight),
                bundled=inside(entry, bundle),
            )
            for entry in font_manager.fontManager.ttflist
        )
    )


def math_families() -> frozenset[str]:
    """Matplotlib-shipped families the active mathtext settings consult.

    A ``custom`` set falls back to ``mathtext.fallback``; the built-in sets
    (Computer Modern included) fall back to STIX; every set takes its
    extensible symbols from ``cmex10``.
    """
    sets = math_sets(
        str(mpl.rcParams["mathtext.fontset"]),
        str(mpl.rcParams["mathtext.fallback"]),
    )
    prefixes = ("cmex10", *(MATH_PREFIX[s] for s in sets if s in MATH_PREFIX))
    data = Path(mpl.get_data_path()).resolve()
    return frozenset(
        entry.name
        for entry in font_manager.fontManager.ttflist
        if entry.name.startswith(prefixes) and inside(entry, data)
    )


def expected(single_weight: frozenset[str]) -> Expected:
    """Where a weight miss is by design, under the rc in force now."""
    return Expected(
        single_weight=single_weight,
        math=math_families(),
        preset_weight=Weight(mpl.rcParams["font.weight"]),
    )
