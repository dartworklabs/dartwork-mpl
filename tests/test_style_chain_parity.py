"""Font fallback-chain parity across style layers and docs.

The sans-serif chain is hand-copied across ``base`` / ``dmpl`` /
``dmpl_light`` (git history shows manual multi-file sync commits), and
``base``'s tail must equal the Korean chain in ``lang-kr`` so appending
``-kr`` only *reprioritizes* families rather than changing the set.
The docs table rows are intentionally abbreviated, so they are checked
as ordered prefixes, not exact copies.
"""

from __future__ import annotations

from pathlib import Path

from dartwork_mpl.style import load_style_dict

_REPO = Path(__file__).resolve().parent.parent
_DOCS_STYLES = _REPO / "docs" / "usage_guide" / "styles.md"


def _chain(style_name: str) -> list[str]:
    value = load_style_dict(style_name)["font.sans-serif"]
    return [part.strip() for part in str(value).split(",")]


def test_dmpl_layers_share_base_chain() -> None:
    base = _chain("base")
    assert _chain("dmpl") == base
    assert _chain("dmpl_light") == base


def test_base_chain_ends_with_korean_chain() -> None:
    base = _chain("base")
    kr = _chain("lang-kr")
    assert base[-len(kr) :] == kr, (
        "base font.sans-serif no longer ends with the lang-kr chain — "
        "the -kr suffix would change the family *set*, not just priority"
    )


def test_docs_chain_rows_are_prefixes() -> None:
    text = _DOCS_STYLES.read_text(encoding="utf-8")
    rows = {}
    for line in text.splitlines():
        if line.startswith("| **English**"):
            rows["en"] = [f.strip() for f in line.split("|")[2].split("→")]
        if line.startswith("| **Korean**"):
            rows["kr"] = [f.strip() for f in line.split("|")[2].split("→")]
    assert set(rows) == {"en", "kr"}, "styles.md chain table rows not found"
    assert rows["en"] == _chain("base")[: len(rows["en"])]
    assert rows["kr"] == _chain("lang-kr")[: len(rows["kr"])]
