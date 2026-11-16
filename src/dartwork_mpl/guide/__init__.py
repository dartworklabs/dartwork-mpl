"""Everything an agent reads or runs to draw a good chart on the first try.

The bundled skill (``SKILL.md`` and its references) and the anti-pattern
lint:

- :func:`skill_path` is the folder the skill and its pages are read from.
- :func:`lint` (``dm.lint_code``) checks a script against the catalog.
- :func:`install_skill` (``dartwork-mpl install``) puts the skill into
  ``.claude/skills`` and ``.agents/skills``.
"""

from __future__ import annotations

from ..edgecase import settle
from . import corpus, decide, measure
from .edges import EDGES
from .install import SKILL_DIRS, Installed, install_skill, skill_path
from .model import Code, Critical, Finding, Info, LintFacts, Severity, Warn

__all__ = [
    "SKILL_DIRS",
    "Critical",
    "Finding",
    "Info",
    "Installed",
    "Severity",
    "Warn",
    "install_skill",
    "lint",
    "skill_path",
]


def lint(code: str) -> list[Finding]:
    """Check a Python source against the anti-pattern catalog, without running it.

    Each :class:`Finding` has ``rule_id``, ``severity`` (``critical``,
    ``warning`` or ``info``), ``line``, ``message`` and ``fix``. Fix every
    critical one; a warning on a value the user asked for stays and is
    reported. More than 500,000 characters raise ``ValueError``.
    """
    facts = LintFacts(Code.parse(code), measure.known())
    plan = decide.findings(facts, corpus.rules())
    return list(settle(facts, plan, EDGES).plan)
