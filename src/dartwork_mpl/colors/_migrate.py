"""v4 → v5 color-token migration codemod (spec §11.3).

Migration is visible and opt-in, never a silent runtime rewrite. This tool
rewrites the palette-token names that the v0.5.4/v0.5.5 overhaul waves
*removed* (so the old names no longer resolve and break scripts) to their
current curated equivalents, and reports — but does not auto-apply — the two
ambiguous v5 changes: the ``teal``/``indigo``/``gray`` collision-token colour
shift under :func:`set_palette_version` (5), and the ``aurora``/``teal_rose``
colormap rename. Every rewrite is shown as a unified diff. The
:func:`collision_shift_table` *advisory* (not the per-token rewrites) carries
the old→new CIEDE2000 ΔE for each collision token, so opting into the v5
colours is an informed choice; removed-token rewrites have no old hex to diff.

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
from typing import NamedTuple

from ._compat_v4 import _COLLISIONS, _FROZEN
from ._metrics import de2000_hex

__all__ = [
    "CMAP_RENAMES",
    "PALETTE_RENAMES",
    "BareHit",
    "collision_shift_table",
    "find_bare_names",
    "migrate_text",
]

# Removed palette bases → current base, tagged with whether the colours are
# preserved (``rename``) or changed (``merge`` — review the result). These old
# names no longer resolve, so a script using them is already broken; the
# rewrite makes it run again. Source: docs/migration.md — the "dc.* palette
# migration (cumulative)" table folds every 0.5.4/0.5.5 rename hop into a
# single 1:1 lookup (shade index preserved). The cumulative table's own note
# states migrated tokens are "a starting point, not a byte-identical swap"
# (colours re-generated in the overhaul), so every entry sourced from it is
# tagged ``merge`` — "review colours" is the honest note.
PALETTE_RENAMES: dict[str, tuple[str, str]] = {
    # v0.5.5 overhaul (unchanged from the original codemod).
    "spectrum": ("vivid", "rename"),
    "coolwarm": ("cool_warm", "rename"),
    "bold": ("vivid", "merge"),
    "corporate": ("trustworthy", "merge"),
    "warm_cool": ("blue_orange", "merge"),
    # v0.5.4 legacy-alias removal (base names) — colours re-generated, so merge.
    "sunset": ("earth", "merge"),
    "ocean": ("teal", "merge"),
    "pop": ("vivid", "merge"),
    "cyber": ("jewel", "merge"),
    "autumn": ("dusty", "merge"),
    "nordic": ("teal_indigo", "merge"),
    # v0.5.4 snake_case renames — colours re-generated, so merge.
    "teal_seq": ("teal", "merge"),
    "focus": ("teal_accent", "merge"),
    "focus_warm": ("coral_accent", "merge"),
    "muted": ("pastel", "merge"),
    "teal_amber_div": ("teal_amber", "merge"),
    # v0.5.4 capitalized back-compat aliases (Vivid/Sunset/... no longer
    # resolve). Vivid maps to the still-valid lowercase ``vivid``.
    "Vivid": ("vivid", "merge"),
    "Sunset": ("earth", "merge"),
    "Ocean": ("teal", "merge"),
    "Pop": ("vivid", "merge"),
    "Cyber": ("jewel", "merge"),
    "Autumn": ("dusty", "merge"),
    "Nordic": ("teal_indigo", "merge"),
}

# v5 ceded these colormap names to a differently-tuned map; a script that wants
# the *pre-v5* rendering must switch to the ``legacy_`` name. Ambiguous (the
# bare name is now a valid v5 map), so this is reported, never auto-applied.
CMAP_RENAMES: dict[str, str] = {
    "aurora": "legacy_aurora",
    "teal_rose": "legacy_teal_rose",
}

# ``dc.spectrum3`` / ``"dc.warm_cool"`` / ``dm.ocean2`` …
# The loader mirrors every ``dc.*`` token to ``dm.*``, so a v4 script may have
# written either prefix; capture it (group 1) and preserve it on rewrite. The
# base alternation is longest-match first (``focus_warm`` before ``focus``) so
# a longer removed name wins over one that is a prefix of it. A token is
# rewritten ONLY when it is a real palette reference: group 3 requires a shade
# index (``\d+`` — a colour like ``dc.ocean2``) OR a bare name immediately
# followed by a string quote (``(?=["'])`` — ``set_cycle("dc.warm_cool")``).
# That excludes ordinary attribute/method access on a user variable named
# ``dc``/``dm`` — ``dc.pop(k)`` / ``dm.focus()`` / ``dm.muted`` are NOT
# rewritten (several removed bases — ``pop``/``focus``/``muted`` — collide with
# common method names). The trailing ``\b`` rejects ``dc.spectrum3x`` /
# ``dc.bold_r`` (word char after the token → no boundary).
_TOKEN_RE = re.compile(
    r"\b(dc|dm)\.("
    + "|".join(sorted(PALETTE_RENAMES, key=len, reverse=True))
    + r")(\d+|(?=[\"']))\b"
)


class Change:
    """One token rewrite: ``{prefix}.{old}{step}`` → ``{prefix}.{new}{step}``.

    ``prefix`` is the matched namespace (``dc`` or its mirrored ``dm`` alias),
    preserved so a rewrite keeps the same namespace it was written with.
    """

    __slots__ = ("kind", "new", "old", "prefix", "step")

    def __init__(
        self, old: str, new: str, step: str, kind: str, prefix: str = "dc"
    ) -> None:
        self.old, self.new, self.step, self.kind = old, new, step, kind
        self.prefix = prefix

    def old_token(self) -> str:
        return f"{self.prefix}.{self.old}{self.step}"

    def new_token(self) -> str:
        return f"{self.prefix}.{self.new}{self.step}"


def migrate_text(src: str) -> tuple[str, list[Change]]:
    """Rewrite removed v0.5.4/v0.5.5 palette tokens to their current names.

    Returns the rewritten source and the list of changes applied. A pure
    ``rename`` preserves colours; a ``merge`` points at a different palette,
    so those changes are flagged for review. The ``dc``/``dm`` prefix of each
    matched token is preserved on rewrite.
    """
    changes: list[Change] = []

    def _sub(m: re.Match[str]) -> str:
        prefix, old_base, step = m.group(1), m.group(2), m.group(3)
        new_base, kind = PALETTE_RENAMES[old_base]
        changes.append(Change(old_base, new_base, step, kind, prefix))
        return f"{prefix}.{new_base}{step}"

    return _TOKEN_RE.sub(_sub, src), changes


# ── report-only detection of unprefixed bare names ─────────────────────────
# Removed palette bases that were also first-class *unprefixed* v4 API —
# ``set_cycle("spectrum")`` / ``get_palette("ocean")``. Unlike the ``dc.*`` /
# ``dm.*`` tokens these have no namespace to prove intent, so they are NEVER
# auto-rewritten — only reported. Derived from ``PALETTE_RENAMES`` so the two
# stay in lockstep: every removed base, minus the ones that are still a live
# v5 target (``vivid`` remains a valid family, so a bare ``"vivid"`` needs no
# migration — matches the ``_MANUAL_ONLY`` allowlist in test_color_migrate_scope).
_CURRENT_TARGETS: frozenset[str] = frozenset(
    new for new, _kind in PALETTE_RENAMES.values()
)
_BARE_REMOVED: dict[str, str] = {
    old.lower(): new
    for old, (new, _kind) in PALETTE_RENAMES.items()
    if old.lower() not in _CURRENT_TARGETS
}

# A removed bare name is flagged only inside a recognisable palette-API
# context immediately before the quoted string — a ``set_cycle(`` /
# ``get_palette(`` call or a ``cycle=`` / ``palette=`` kwarg — so an unrelated
# bare word (``focus`` in prose, ``d.pop("focus")``) is not a false positive.
# The string must be EXACTLY the bare name: the closing backreference quote
# rejects a shade index or a ``dc.``-prefixed value (those the codemod already
# rewrites), so the two paths never double-report the same site. Longest base
# first so ``focus_warm`` wins over ``focus``.
_BARE_RE = re.compile(
    r"(?:\b(?:set_cycle|get_palette)\s*\(\s*|\b(?:cycle|palette)\s*=\s*)"
    r"(['\"])("
    + "|".join(
        re.escape(b) for b in sorted(_BARE_REMOVED, key=len, reverse=True)
    )
    + r")\1"
)


class BareHit(NamedTuple):
    """One report-only bare-name hit: ``{name}`` at ``{lineno}`` → ``{suggestion}``.

    ``name`` is the removed unprefixed base as written in the source;
    ``suggestion`` is its current curated equivalent. These are advisory —
    the codemod never rewrites bare names (no namespace to disambiguate).
    """

    lineno: int
    name: str
    suggestion: str


def find_bare_names(src: str) -> list[BareHit]:
    """Report unprefixed removed palette names used as a palette-API argument.

    Detection only, never rewriting: returns a :class:`BareHit` per quoted
    bare removed base (``set_cycle("spectrum")``, ``get_palette("ocean")``,
    ``cycle="pop"`` …), with its 1-based line number and the suggested current
    name. Prefixed tokens (``set_cycle("dc.spectrum")``) are excluded here —
    :func:`migrate_text` rewrites those — so a site is never double-reported.
    """
    hits: list[BareHit] = []
    for m in _BARE_RE.finditer(src):
        name = m.group(2)
        lineno = src.count("\n", 0, m.start()) + 1
        hits.append(BareHit(lineno, name, _BARE_REMOVED[name]))
    return hits


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
    path: Path,
    src: str,
    new: str,
    changes: list[Change],
    bare: list[BareHit] | None = None,
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
    lines.extend(
        f"  {path}:{hit.lineno}: bare '{hit.name}' → '{hit.suggestion}'  "
        "(not auto-rewritten (bare name — verify context))"
        for hit in sorted(bare or [])
    )
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
    bare_total = 0
    for path in args.paths:
        if not path.is_file():
            print(f"skip (not a file): {path}", file=sys.stderr)
            continue
        src = path.read_text(encoding="utf-8")
        new, changes = migrate_text(src)
        bare = find_bare_names(src)
        if not changes and not bare:
            continue
        total += len(changes)
        bare_total += len(bare)
        print(_render_report(path, src, new, changes, bare))
        # --apply only writes the prefixed rewrites; bare names are advisory.
        if args.apply and changes:
            path.write_text(new, encoding="utf-8")
            print(f"  ✓ wrote {path} ({len(changes)} token(s))")
        print()

    if total == 0 and bare_total == 0:
        print("No removed v0.5.5 palette tokens found.")

    if not args.no_advisory:
        print(
            "\nAdvisory — teal/indigo/gray shift under set_palette_version(5):"
        )
        print(f"  {'token':<12} {'v4 (frozen)':<12} {'v5':<12} {'ΔE00':>6}")
        for tok, old, new, de in collision_shift_table():
            print(f"  {tok:<12} {old:<12} {new:<12} {de:>6.1f}")
        # Derive the sentence from CMAP_RENAMES so a third entry surfaces
        # automatically (the dict is the single source of truth).
        cmap_bare_names = " / ".join(f"'dc.{k}'" for k in CMAP_RENAMES)
        cmap_legacy_names = " / ".join(
            f"'dc.{v}'" for v in CMAP_RENAMES.values()
        )
        print(
            f"\n  Colormaps: cmap={cmap_bare_names} now render the v5 map; "
            f"switch to {cmap_legacy_names} for the pre-v5 look."
        )

    return 1 if (total and not args.apply) else 0


if __name__ == "__main__":
    raise SystemExit(main())
