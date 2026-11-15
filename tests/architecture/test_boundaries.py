"""The package respects its slice boundaries (ADR 0005).

``boundaries.py`` holds the rules and the table of slices, allowed
dependencies and decision modules; this runs it over the real tree.
"""

from pathlib import Path

from . import boundaries

ROOT = Path(__file__).resolve().parents[2]


def test_repository_respects_its_boundaries():
    assert boundaries.check(ROOT / "src" / "dartwork_mpl") == []
    assert dict(boundaries.DEBT) == {}
