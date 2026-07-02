"""mplstyle font references ↔ the pinned contract families (G8 layer 2).

The style files name font families in ``font.sans-serif`` chains and
``mathtext.*`` keys. Bundled families among those are pinned by
``test_font.CONTRACT_FAMILIES`` (deleting one fails the eager-contract
test); the rest must be on the explicit system-fallback allowlist. A
brand-new family typed into a preset therefore forces a conscious
decision — bundle it (and extend the contract) or allowlist it —
instead of silently falling through matplotlib's findfont chain.

Deliberately NOT derived by intersecting the chains with the live
bundle: after a deletion the family drops out of both sides and such a
test passes vacuously.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _contract_families() -> tuple[str, ...]:
    spec = importlib.util.spec_from_file_location(
        "_test_font_contract", Path(__file__).with_name("test_font.py")
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return tuple(mod.CONTRACT_FAMILIES)


CONTRACT_FAMILIES = _contract_families()

_MPLSTYLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "mplstyle"
)

# Families the presets may reference without bundling them — OS-provided
# fallbacks further down the chains. Every entry is justified by an
# actual occurrence in a chain today.
_SYSTEM_FALLBACKS: frozenset[str] = frozenset(
    {
        "Lato",  # base/dmpl sans chain slot 2
        "Open Sans",  # sans chain slot 4
        "Arial",  # ubiquitous OS fallback
        "Helvetica",  # macOS fallback
        "Gothic A1",  # Korean OS fallback
        "Freesentation",  # Korean fallback
        "AppleGothic",  # macOS Korean fallback
        "Malgun Gothic",  # Windows Korean fallback
        "sans-serif",  # matplotlib generic terminator
    }
)


def _referenced_families() -> set[str]:
    families: set[str] = set()
    for style_file in _MPLSTYLE_DIR.glob("*.mplstyle"):
        for line in style_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.split("#")[0].strip()
            if key == "font.sans-serif":
                # Only the first two entries are the *identity* of a
                # chain; the tail is fallback ladder shared repo-wide.
                families.update(
                    v.strip() for v in value.split(",")[:2] if v.strip()
                )
            elif key.startswith("mathtext.") and key not in (
                "mathtext.default",
                "mathtext.fallback",
                "mathtext.fontset",
            ):
                family = value.split(":")[0].strip()
                if family:
                    families.add(family)
    return families


def test_referenced_families_are_pinned_or_allowlisted() -> None:
    referenced = _referenced_families()
    assert referenced, "no font families parsed from mplstyles — parser broken?"
    known = set(CONTRACT_FAMILIES) | _SYSTEM_FALLBACKS
    unknown = referenced - known
    assert not unknown, (
        f"mplstyle files reference unpinned families {sorted(unknown)} — "
        f"either bundle them and extend test_font.CONTRACT_FAMILIES, or "
        f"add them to _SYSTEM_FALLBACKS with a justification comment"
    )


def test_contract_families_still_referenced() -> None:
    """Reverse direction: a family in the pinned contract that no style
    references anymore signals the contract is stale."""
    referenced = _referenced_families()
    # Inter/Roboto head the sans chains; Paperlogy heads the -kr chain;
    # Noto Sans Math is every mathtext face. Pretendard sits mid-chain
    # (slot 3 of the -kr chain), so check it against the full chains.
    full: set[str] = set()
    for style_file in _MPLSTYLE_DIR.glob("*.mplstyle"):
        for line in style_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("font.sans-serif"):
                full.update(
                    v.strip() for v in stripped.partition(":")[2].split(",")
                )
    unreferenced = [f for f in CONTRACT_FAMILIES if f not in referenced | full]
    assert not unreferenced, (
        f"contract families no style references: {unreferenced}"
    )
