"""Meta-tests pinning hand-written catalog docstrings to their SSOT.

``Style.use``'s docstring enumerates the preset names and the MCP
``style_preset`` resource docstring enumerates the ``.mplstyle`` layer
stems. Both are static strings (cannot be built at runtime), so these
tests force them to be updated in the same PR as any preset/layer
add/remove/rename — the ``TestClassificationOverridesParity`` pattern
applied to prose.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_MPLSTYLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "mplstyle"
)


def _preset_names() -> list[str]:
    presets = json.loads(
        (_MPLSTYLE_DIR / "presets.json").read_text(encoding="utf-8")
    )
    return sorted(presets)


@pytest.mark.parametrize("preset", _preset_names())
def test_style_use_docstring_lists_every_preset(preset: str) -> None:
    import dartwork_mpl as dm

    doc = dm.Style.use.__doc__ or ""
    assert f'"{preset}"' in doc, (
        f"preset {preset!r} missing from Style.use docstring — update the "
        f"'Available presets' list"
    )


def test_style_use_docstring_has_no_phantom_presets() -> None:
    """Every quoted token in the 'Available presets' block must be a
    real presets.json key (catches the reverse drift)."""
    import re

    import dartwork_mpl as dm

    doc = dm.Style.use.__doc__ or ""
    block = doc.split("Available presets:")[1].split("**kwargs")[0]
    quoted = re.findall(r'"([a-z-]+)"', block)
    assert quoted, "docstring parser found no presets — format changed?"
    assert set(quoted) == set(_preset_names())


def test_mcp_style_preset_docstring_lists_every_layer() -> None:
    fastmcp = pytest.importorskip("fastmcp")  # noqa: F841

    import dartwork_mpl.mcp.resources as resources_mod

    src = Path(resources_mod.__file__).read_text(encoding="utf-8")
    stems = sorted(p.stem for p in _MPLSTYLE_DIR.glob("*.mplstyle"))
    for stem in stems:
        assert stem in src, (
            f"mplstyle layer {stem!r} missing from mcp/resources.py "
            f"style_preset docstring 'Available presets' list"
        )
