"""Regenerate ``src/dartwork_mpl/colors/_typing.py`` from the live registries.

The two public ``Literal`` vocabularies (``DartworkColor``,
``DartworkColormap``) fossilized badly when maintained by hand (the
pre-0.5 file had ~98% phantom/missing entries), so they are now
generated from the same runtime registries the names resolve against:

- ``DartworkColor``   ← ``matplotlib.colors.get_named_colors_mapping()``
  for the seven canonical library prefixes (``dc/oc/tw/md/ad/cu/pr``;
  ``dm.*`` is not a color namespace).
- ``DartworkColormap`` ← every registered ``dc.*`` colormap, including
  the derived ``_r`` variants.

Run after any palette/colormap add/remove/rename::

    .venv-local/bin/python scripts/generate_typing.py

``tests/test_typing_parity.py`` pins the emitted file to the registries,
so forgetting to rerun this script fails CI.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "src" / "dartwork_mpl" / "colors" / "_typing.py"

# The canonical library prefixes (dot included). ``dm.`` is not a color
# namespace and is intentionally not part of the typed vocabulary.
COLOR_PREFIXES: tuple[str, ...] = (
    "ad.",
    "cu.",
    "dc.",
    "md.",
    "oc.",
    "pr.",
    "tw.",
)

HEADER = '''"""Static type hints for colors and colormaps.

GENERATED FILE — do not edit by hand. Regenerate with::

    .venv-local/bin/python scripts/generate_typing.py

``tests/test_typing_parity.py`` pins these Literals to the live
registries (named-color mapping / colormap registry), so a palette or
colormap change that skips the regen fails CI.
"""

from typing import Literal

'''


def _color_names() -> list[str]:
    import matplotlib.colors as mcolors

    import dartwork_mpl  # noqa: F401 — registers the color namespaces

    mapping = mcolors.get_named_colors_mapping()
    return sorted(k for k in mapping if k.startswith(COLOR_PREFIXES))


def _colormap_names() -> list[str]:
    import matplotlib as mpl

    from dartwork_mpl.cmap import ensure_loaded

    ensure_loaded()
    return sorted(n for n in mpl.colormaps if n.startswith("dc."))


def _literal_block(name: str, entries: list[str]) -> str:
    lines = [f"{name} = Literal["]
    lines.extend(f'    "{entry}",' for entry in entries)
    lines.append("]")
    return "\n".join(lines)


def build() -> str:
    """Return the full generated module source."""
    colors = _color_names()
    cmaps = _colormap_names()
    return (
        HEADER
        + _literal_block("DartworkColor", colors)
        + "\n\n"
        + _literal_block("DartworkColormap", cmaps)
        + "\n"
    )


def main() -> None:
    source = build()
    TARGET.write_text(source, encoding="utf-8")
    n_colors = source.count('",')
    print(f"wrote {TARGET} ({n_colors} literal entries)")


if __name__ == "__main__":
    main()
