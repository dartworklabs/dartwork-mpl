"""Every prefixed color token in every ``.mplstyle`` must resolve.

matplotlib *silently skips* an unresolvable color token in a style file
(a logging warning only — the default tab cycle ships and the preset
matrix stays green), so a palette rename that misses a ``.mplstyle``
edit would ship default colors with all tests passing. This test makes
that a hard failure; its caplog twin in ``test_preset_matrix.py`` gates
the same class at ``style.use`` time.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl  # noqa: F401  — registers the color namespaces

_MPLSTYLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "mplstyle"
)


def _prefixes() -> set[str]:
    """Color-library prefixes derived from the live registry."""
    return {
        k.split(".")[0] + "."
        for k in mcolors.get_named_colors_mapping()
        if "." in k
    }


def _tokens_in(path: Path) -> set[str]:
    prefixes = _prefixes()
    pattern = re.compile(
        r"\b("
        + "|".join(re.escape(p[:-1]) for p in prefixes)
        + r")\.[A-Za-z_0-9]+\b"
    )
    tokens: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens.update(m.group(0) for m in pattern.finditer(stripped))
    return tokens


@pytest.mark.parametrize(
    "style_file", sorted(_MPLSTYLE_DIR.glob("*.mplstyle")), ids=lambda p: p.stem
)
def test_every_style_color_token_resolves(style_file: Path) -> None:
    mapping = mcolors.get_named_colors_mapping()
    unresolved = {t for t in _tokens_in(style_file) if t not in mapping}
    assert not unresolved, (
        f"{style_file.name}: unresolvable color tokens {sorted(unresolved)} "
        f"— matplotlib would silently skip these and ship default colors"
    )


def test_parser_finds_tokens_at_all() -> None:
    """Guard the guard: the extractor must find a non-empty union, or a
    format change has silently disabled the check."""
    union: set[str] = set()
    for f in _MPLSTYLE_DIR.glob("*.mplstyle"):
        union |= _tokens_in(f)
    assert union, "no color tokens found in any .mplstyle — parser broken?"
