"""The bundled anti-pattern catalog."""

from __future__ import annotations

from functools import cache
from importlib.resources import files

from .model import Rules

ASSETS = files("dartwork_mpl.guide") / "assets"
SKILL = ASSETS / "skill"
CATALOG = ASSETS / "anti-patterns.yaml"


@cache
def rules() -> Rules:
    """The parsed anti-pattern catalog."""
    return Rules.parse(CATALOG.read_text(encoding="utf-8"))
