"""Everything an agent reads or runs to draw a good chart on the first try.

The bundled skill (``SKILL.md`` and its references), the plot templates and
the anti-pattern lint, read through one small API:

- :func:`references` lists every guide page and template with an id, a title
  and a summary; :func:`search` ranks them for a free-text query;
  :func:`read` returns one by id (``"guide/layout"``, ``"template/bar"``,
  ``"template/advanced/bar"``).
- :func:`lint` (``dm.lint_code``) checks a script against the catalog.
- :func:`install_skill` (``python -m dartwork_mpl.guide install``) links the
  skill into ``.claude/skills`` and ``.agents/skills``.
"""

from __future__ import annotations

from ..edgecase import settle
from . import corpus, decide, measure
from .edges import EDGES
from .install import SKILL_DIRS, Installed, install_skill, skill_path
from .model import Code, Finding, LintFacts, Severity
from .reference import Query, Reference

__all__ = [
    "SKILL_DIRS",
    "Finding",
    "Installed",
    "Reference",
    "Severity",
    "install_skill",
    "lint",
    "read",
    "references",
    "search",
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


def references() -> tuple[Reference, ...]:
    """Every guide page and template: ``id``, ``kind``, ``title``, ``summary``."""
    return corpus.references()


def search(query: str, limit: int = 5) -> tuple[Reference, ...]:
    """The references that best match a free-text query, best first.

    ``search("grouped bars")`` ranks the grouped-bar templates first; read one
    with :func:`read`. An empty result means no reference shares a word.
    """
    return decide.rank(Query.parse(query, limit), corpus.references())


def read(ref: str) -> str:
    """The text of one reference by id; an unknown id raises ``ValueError``."""
    return corpus.read(ref)
