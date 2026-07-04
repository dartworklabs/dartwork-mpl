"""T2 — codemod-scope parity against the migration guide.

Every legacy ``dc.*`` base listed in the guide's "dc.* palette migration
(cumulative)" table must either be a :data:`PALETTE_RENAMES` key (so the codemod
actually rewrites it) or an explicit entry in the ``_MANUAL_ONLY`` allowlist
below with a stated reason. This forces a conscious decision for any future
palette removal instead of letting a dead token drop through the codemod
silently.
"""

from __future__ import annotations

import re
from pathlib import Path

_MIGRATION_MD = Path(__file__).parents[1] / "docs" / "migration.md"

# Legacy bases that legitimately need NO rename key — each with its reason.
_MANUAL_ONLY: dict[str, str] = {
    # dc.vivid* still resolves in v5 (the bare token is a live palette family),
    # so a lowercase `vivid` source needs no rewrite. The dead *capitalized*
    # alias `dc.Vivid*` is covered by the `Vivid` rename key.
    "vivid": "resolves in v5 — bare token still valid, no rewrite needed"
}


def _cumulative_table_bases() -> set[str]:
    """Legacy base names in the 'dc.* palette migration (cumulative)' table."""
    text = _MIGRATION_MD.read_text(encoding="utf-8")
    start = text.index("## dc.* palette migration (cumulative)")
    rest = text[start:]
    end = rest.find("\n## ", 1)
    section = rest if end == -1 else rest[:end]

    bases: set[str] = set()
    for raw in section.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        legacy = cells[0]  # first column = "Legacy token" cell
        # skip the header row and the |---|---| separator row
        if legacy.startswith("Legacy token") or set(legacy) <= set("- "):
            continue
        # a cell may hold "A / B" alias forms — grab every dc.<base>* in it
        bases.update(re.findall(r"dc\.(\w+)\*", legacy))
    return bases


def test_cumulative_table_bases_are_covered() -> None:
    from dartwork_mpl.colors._migrate import PALETTE_RENAMES

    bases = _cumulative_table_bases()
    assert bases, "parsed no legacy bases — has the table format changed?"
    uncovered = {
        b for b in bases if b not in PALETTE_RENAMES and b not in _MANUAL_ONLY
    }
    assert not uncovered, (
        "cumulative-table bases missing from PALETTE_RENAMES and _MANUAL_ONLY: "
        f"{sorted(uncovered)}"
    )


def test_manual_only_bases_are_not_also_renames() -> None:
    """An allowlisted base must not also be a rename key (a contradiction)."""
    from dartwork_mpl.colors._migrate import PALETTE_RENAMES

    overlap = set(_MANUAL_ONLY) & set(PALETTE_RENAMES)
    assert not overlap, f"both allowlisted and renamed: {sorted(overlap)}"
