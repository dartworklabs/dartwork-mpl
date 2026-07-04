"""v4 → v5 color-token migration codemod (spec §11.3).

Migration is visible and opt-in, never a silent runtime rewrite. This tool
rewrites the palette-token names that the v0.5.5 overhaul *removed* (so the
old names no longer resolve and break scripts) to their current curated
equivalents, and reports — but does not auto-apply — the two ambiguous v5
changes: the ``teal``/``indigo``/``gray`` collision-token colour shift under
:func:`set_palette_version` (5), and the ``aurora``/``teal_rose`` colormap
rename. Every rewrite is shown as a unified diff, and each token change is
accompanied by its old→new CIEDE2000 ΔE so the size of the visual shift is
explicit.

Run::

    python -m dartwork_mpl.colors._migrate path/to/script.py ...   # dry-run
    python -m dartwork_mpl.colors._migrate --apply path/to/*.py    # write
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

from ._compat_v4 import _COLLISIONS, _FROZEN
from ._metrics import de2000_hex

__all__ = [
    "CMAP_RENAMES",
    "PALETTE_RENAMES",
    "collision_shift_table",
    "migrate_text",
]

# Removed v0.5.5 palette bases → current base, tagged with whether the colours
# are preserved (``rename``) or changed (``merge`` — review the result). These
# old names no longer resolve, so a script using them is already broken; the
# rewrite makes it run again. Source: docs/migration.md (v0.5.5 overhaul).
PALETTE_RENAMES: dict[str, tuple[str, str]] = {
    "spectrum": ("vivid", "rename"),
    "coolwarm": ("cool_warm", "rename"),
    "bold": ("vivid", "merge"),
    "corporate": ("trustworthy", "merge"),
    "warm_cool": ("blue_orange", "merge"),
}

# v5 ceded these colormap names to a differently-tuned map; a script that wants
# the *pre-v5* rendering must switch to the ``legacy_`` name. Ambiguous (the
# bare name is now a valid v5 map), so this is reported, never auto-applied.
CMAP_RENAMES: dict[str, str] = {
    "aurora": "legacy_aurora",
    "teal_rose": "legacy_teal_rose",
}

# ``dc.spectrum3`` / ``dc.coolwarm`` (bare cycle name) / ``dc.warm_cool7`` …
_TOKEN_RE = re.compile(
    r"\bdc\.("
    + "|".join(sorted(PALETTE_RENAMES, key=len, reverse=True))
    + r")(\d*)\b"
)


class Change:
    """One token rewrite: ``dc.{old}{step}`` → ``dc.{new}{step}``."""

    __slots__ = ("kind", "new", "old", "step")

    def __init__(self, old: str, new: str, step: str, kind: str) -> None:
        self.old, self.new, self.step, self.kind = old, new, step, kind

    def old_token(self) -> str:
        return f"dc.{self.old}{self.step}"

    def new_token(self) -> str:
        return f"dc.{self.new}{self.step}"


def migrate_text(src: str) -> tuple[str, list[Change]]:
    """Rewrite removed v0.5.5 palette tokens to their current names.

    Returns the rewritten source and the list of changes applied. A pure
    ``rename`` preserves colours; a ``merge`` points at a different palette,
    so those changes are flagged for review.
    """
    changes: list[Change] = []

    def _sub(m: re.Match[str]) -> str:
        old_base, step = m.group(1), m.group(2)
        new_base, kind = PALETTE_RENAMES[old_base]
        changes.append(Change(old_base, new_base, step, kind))
        return f"dc.{new_base}{step}"

    return _TOKEN_RE.sub(_sub, src), changes


def collision_shift_table() -> list[tuple[str, str, str, float]]:
    """``(token, frozen_v4_hex, v5_hex, ΔE00)`` for every collision token.

    The ``teal``/``indigo``/``gray`` (steps 0-7) tokens exist in both
    catalogs. Under the default palette version they stay at the frozen v4
    hex; :func:`set_palette_version` (5) remaps them to the v5 hex. This table
    quantifies that shift so adopting v5 is an informed choice, not a surprise.
    """
    rows = []
    for token in sorted(_COLLISIONS):
        old, new = _FROZEN[token], _COLLISIONS[token]
        rows.append((token, old, new, de2000_hex(old, new)))
    return rows


def _render_report(
    path: Path, src: str, new: str, changes: list[Change]
) -> str:
    diff = "".join(
        difflib.unified_diff(
            src.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (migrated)",
        )
    )
    lines = [diff.rstrip("\n")] if diff else []
    seen: dict[str, Change] = {c.old_token(): c for c in changes}
    for tok, c in sorted(seen.items()):
        note = (
            "colours preserved"
            if c.kind == "rename"
            else "MERGE — review colours"
        )
        lines.append(f"  {tok:>18} → {c.new_token():<18}  ({note})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dartwork_mpl.colors._migrate",
        description="Rewrite removed v0.5.5 dc.* palette tokens to their v5 names.",
    )
    parser.add_argument(
        "paths", nargs="+", type=Path, help="source files to scan"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the rewrites (default: dry-run)",
    )
    parser.add_argument(
        "--no-advisory",
        action="store_true",
        help="suppress the collision-shift ΔE advisory table",
    )
    args = parser.parse_args(argv)

    total = 0
    for path in args.paths:
        if not path.is_file():
            print(f"skip (not a file): {path}", file=sys.stderr)
            continue
        src = path.read_text(encoding="utf-8")
        new, changes = migrate_text(src)
        if not changes:
            continue
        total += len(changes)
        print(_render_report(path, src, new, changes))
        if args.apply:
            path.write_text(new, encoding="utf-8")
            print(f"  ✓ wrote {path} ({len(changes)} token(s))")
        print()

    if total == 0:
        print("No removed v0.5.5 palette tokens found.")

    if not args.no_advisory:
        print(
            "\nAdvisory — teal/indigo/gray shift under set_palette_version(5):"
        )
        print(f"  {'token':<12} {'v4 (frozen)':<12} {'v5':<12} {'ΔE00':>6}")
        for tok, old, new, de in collision_shift_table():
            print(f"  {tok:<12} {old:<12} {new:<12} {de:>6.1f}")
        print(
            "\n  Colormaps: cmap='dc.aurora' / 'dc.teal_rose' now render the v5 map; "
            "switch to 'dc.legacy_aurora' / 'dc.legacy_teal_rose' for the pre-v5 look."
        )

    return 1 if (total and not args.apply) else 0


if __name__ == "__main__":
    raise SystemExit(main())
