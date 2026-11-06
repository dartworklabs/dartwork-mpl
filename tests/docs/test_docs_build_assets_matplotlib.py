"""The docs assets the docs build rewrites are tracked as it writes them.

``docs/_ext/build_hooks.generate_gallery_assets`` re-renders the usage-guide
and API figures, the preset-comparison widget and the font comparison pair
on every docs build. The tracked copies are what GitHub shows and what a
clean build must leave untouched, so they have to be rendered with a
Matplotlib the package supports. The Matplotlib 3.11 floor change
regenerated only the colour-theory figures, and these 25 kept saying
``Matplotlib v3.10.9`` (follow-up F5). Every SVG records the Matplotlib that
wrote it, so the check reads the files and renders nothing.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
# Written by generate_gallery_assets: docs/usage_guide/generate_assets.py
# (with generate_preset_compare.py), docs/api/generate_assets.py and
# docs/fonts/generate_assets.py's copies into _static/.
_WRITTEN = (
    "docs/usage_guide/images/*.svg",
    "docs/usage_guide/images/preset_compare.html",
    "docs/api/images/*.svg",
    "docs/_static/before_default.svg",
    "docs/_static/after_dartwork.svg",
)
_VERSION = re.compile(r"Matplotlib v(\d+)\.(\d+)\.(\d+)")


def _floor() -> tuple[int, int]:
    """The Matplotlib floor in pyproject (``matplotlib>=3.11.0``)."""
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'"matplotlib>=(\d+)\.(\d+)', text)
    assert match, "matplotlib floor not found in pyproject.toml"
    return int(match.group(1)), int(match.group(2))


def _tracked(*patterns: str) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", *patterns],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def test_docs_build_assets_are_rendered_by_a_supported_matplotlib():
    assets = sorted(_tracked(*_WRITTEN))
    assert len(assets) >= 20, assets
    floor = _floor()
    stale = {}
    for path in assets:
        found = {
            tuple(map(int, m.groups()))
            for m in _VERSION.finditer(
                (_ROOT / path).read_text(encoding="utf-8")
            )
        }
        assert found, f"{path} records no Matplotlib version"
        old = sorted(v for v in found if v[:2] < floor)
        if old:
            stale[path] = ".".join(map(str, old[0]))
    assert stale == {}, (
        f"rendered below Matplotlib {floor[0]}.{floor[1]}; regenerate with "
        f"the docs build's generators: {stale}"
    )
