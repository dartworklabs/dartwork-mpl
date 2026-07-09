"""Every color/colormap token in the docs must resolve (G2).

Six doc surfaces were found teaching removed ``dc.*`` names (the wheel-
bundled quickstart's ``dc.ocean`` crash among them). Rather than a
backward-looking denylist of removed names — the trap that let the
0.5.5 wave through — this test extracts every prefixed token from the
prose (tables and inline code included, not just fences) and requires
it to resolve against the live registries, so the *next* rename wave
fails CI in every stale file at once.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.colors as mcolors
import pytest

import dartwork_mpl as dm

_REPO = Path(__file__).resolve().parents[1]
_DOCS = _REPO / "docs"

# Files that intentionally document *removed* APIs or internal design
# history (development notes discuss hypothetical/removed names).
_EXCLUDE_PARTS = ("_build", "examples_gallery", "superpowers", "development")
_EXCLUDE_NAMES = {"migration.md"}

_IGNORE_MARKER = "color-lint: ignore"


def _scan_files() -> list[Path]:
    return sorted(
        f
        for f in _DOCS.rglob("*.md")
        if not any(part in f.parts for part in _EXCLUDE_PARTS)
        and f.name not in _EXCLUDE_NAMES
    )


def _registries() -> tuple[set[str], set[str], set[str]]:
    named = set(mcolors.get_named_colors_mapping())
    cmaps = {n for n in mpl.colormaps if n.startswith("dc.")}
    palette_pattern = re.compile(r"^([a-z]+)\.([a-z][a-z_]*)\d+$")
    palettes = set()
    for color_name in named:
        match = palette_pattern.match(color_name)
        if match and match.group(1) != "dm":
            palettes.add(f"{match.group(1)}.{match.group(2)}")
    return named, cmaps, palettes


def _prefix_pattern() -> re.Pattern[str]:
    named, _, _ = _registries()
    prefixes = sorted({k.split(".")[0] for k in named if "." in k})
    return re.compile(r"\b(" + "|".join(prefixes) + r")\.[a-z][a-z_0-9]*\b")


@pytest.mark.parametrize(
    "doc", _scan_files(), ids=lambda p: str(p.relative_to(_REPO))
)
def test_doc_color_tokens_resolve(doc: Path) -> None:
    named, cmaps, palettes = _registries()
    pattern = _prefix_pattern()
    unresolved: dict[str, int] = {}
    for lineno, line in enumerate(
        doc.read_text(encoding="utf-8").splitlines(), 1
    ):
        if _IGNORE_MARKER in line:
            continue
        # In the palette-demo builder, ``"id"``/``"label"`` values are
        # display names for third-party categorical *mixes*
        # (``oc.classic`` …), not registry tokens.
        if doc.suffix == ".py" and ('"id":' in line or '"label":' in line):
            continue
        for m in pattern.finditer(line):
            token = m.group(0)
            # ``dm.*`` doubles as the package namespace: only
            # digit-suffixed tokens (``dm.teal3``) are color aliases —
            # the rest are API references (live or documented-removed),
            # which the deprecation-registry guards own.
            if token.startswith("dm.") and (
                not token[-1].isdigit() or hasattr(dm, token[3:])
            ):
                continue
            # A trailing ``_r`` names a reversed colormap.
            base = token[:-2] if token.endswith("_r") else token
            if (
                token in named
                or token in cmaps
                or base in cmaps
                or token in palettes
            ):
                continue
            unresolved.setdefault(token, lineno)
    assert not unresolved, (
        f"{doc.relative_to(_REPO)}: unresolvable tokens "
        f"{sorted(unresolved.items(), key=lambda kv: kv[1])} — every "
        f"prefixed name in docs must resolve against the live registries "
        f"(add '<!-- {_IGNORE_MARKER} -->' on the line only for an "
        f"intentional negative example)"
    )


def test_scanner_finds_tokens_at_all() -> None:
    """Guard the guard: the extractor must see a healthy token volume."""
    pattern = _prefix_pattern()
    total = 0
    for doc in _scan_files():
        total += sum(
            1 for _ in pattern.finditer(doc.read_text(encoding="utf-8"))
        )
    assert total > 100, f"only {total} tokens found — scanner broken?"
