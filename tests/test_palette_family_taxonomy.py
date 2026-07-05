"""v5 palette-family taxonomy parity (G13).

v4 had a separate palette -> family mapping and explorer JS data file. In v5
the public taxonomy is the 16-key ``_generated.PALETTE`` mapping: each
``dc.<family>`` palette is its own family. This guard keeps the generated
explorer fragment and docs count claim tied to that SSOT.
"""

from __future__ import annotations

import re
import runpy
from pathlib import Path

from dartwork_mpl.colors import _generated

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "docs" / "_static" / "scripts"
_EXPLORER = _REPO / "docs" / "_static" / "categorical_explorer.html"
_DOC = _REPO / "docs" / "color_system" / "categorical-palettes.md"


def _v5_palette() -> dict[str, tuple[str, ...]]:
    return {family: tuple(row) for family, row in _generated.PALETTE.items()}


def _explorer_builder() -> dict[str, object]:
    return runpy.run_path(str(_SCRIPTS / "build_categorical_explorer.py"))


def _explorer_palette() -> dict[str, tuple[str, ...]]:
    html = _EXPLORER.read_text(encoding="utf-8")
    cards = re.findall(
        r'<article class="dm-v5-card"><h3>dc\.([a-z]+)</h3>.*?'
        r'<div class="dm-v5-row">(.*?)</div></article>',
        html,
        re.S,
    )
    parsed: dict[str, tuple[str, ...]] = {}
    for family, body in cards:
        colors: list[str | None] = [None] * 10
        for hex_color, token_family, step_text in re.findall(
            r'style="--c:(#[0-9a-fA-F]{6});[^"]*"\s+'
            r'data-token="dc\.([a-z]+)(\d)"',
            body,
        ):
            assert token_family == family
            colors[int(step_text)] = hex_color.lower()
        assert all(color is not None for color in colors), family
        parsed[family] = tuple(color for color in colors if color is not None)
    return parsed


def test_explorer_builder_families_match_v5_palette_ssot() -> None:
    """The v5 explorer builder has no legacy palette -> family taxonomy."""
    palette = _v5_palette()
    builder = _explorer_builder()
    order = list(builder["ORDER"])
    intent = dict(builder["INTENT"])

    assert len(order) == len(set(order)), (
        f"duplicate explorer families: {order}"
    )
    assert set(order) == set(palette), (
        f"builder ORDER drift: only-builder={sorted(set(order) - set(palette))}, "
        f"only-PALETTE={sorted(set(palette) - set(order))}"
    )
    assert set(intent) == set(palette), (
        f"builder INTENT drift: only-builder={sorted(set(intent) - set(palette))}, "
        f"only-PALETTE={sorted(set(palette) - set(intent))}"
    )
    assert not (_SCRIPTS / "categorical_explorer_data.js").exists()


def test_explorer_fragment_tokens_match_v5_palette_ssot() -> None:
    palette = _v5_palette()
    explorer = _explorer_palette()

    assert set(explorer) == set(palette), (
        f"explorer card drift: only-explorer="
        f"{sorted(set(explorer) - set(palette))}, "
        f"only-PALETTE={sorted(set(palette) - set(explorer))}"
    )
    mismatched = {
        family: (explorer[family], palette[family])
        for family in palette
        if explorer[family] != palette[family]
    }
    assert not mismatched, (
        f"explorer color drift (explorer, PALETTE): {mismatched}"
    )

    html = _EXPLORER.read_text(encoding="utf-8")
    m = re.search(r"(\d+)\s+families\s*/\s*(\d+)\s+colors", html)
    assert m, "explorer family/color count label not found"
    assert int(m.group(1)) == len(palette)
    assert int(m.group(2)) == sum(len(row) for row in palette.values())


def test_family_count_matches_docs_16_palette_claim() -> None:
    palette = _v5_palette()
    doc = _DOC.read_text(encoding="utf-8")
    m = re.search(
        r"curated\s+(\d+)-palette\s+system\s+across\s+"
        r"the\s+v5\s+color\s+families",
        doc,
        re.S,
    )
    assert m, "v5 palette-count claim not found in categorical-palettes.md"
    assert int(m.group(1)) == len(palette), (
        f"docs claim {m.group(1)} palettes; PALETTE SSOT has {len(palette)} "
        "v5 families"
    )
