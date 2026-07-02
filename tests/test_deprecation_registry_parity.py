"""Parity guard for the three removed-name registries.

The removal lifecycle is tracked in three places that historically
drifted apart (``auto_layout`` had a runtime hint but no lint/codemod
coverage; ``style_spines``/``auto_select_colors`` were lint-flagged but
raised a bare AttributeError):

1. runtime ``dartwork_mpl._REMOVED_NAMES`` (``__getattr__`` hints),
2. the lint SSOT ``asset/prompt/02-anti-patterns.yaml``,
3. the codemod ``dartwork_mpl.lint._MIGRATE_HINTS``.

These tests assert that every runtime-removed name is *mentioned* by at
least one lint rule and one codemod hint, so a future removal added to
one registry fails CI until the other two follow.
"""

from __future__ import annotations

from importlib.resources import files

import pytest
import yaml

from dartwork_mpl import _REMOVED_NAMES
from dartwork_mpl.lint import _MIGRATE_HINTS, _MIGRATE_SAFE_REWRITES


def _lint_rules_corpus() -> str:
    """Every pattern + message + fix of the anti-pattern SSOT, joined."""
    raw = (
        files("dartwork_mpl") / "asset" / "prompt" / "02-anti-patterns.yaml"
    ).read_text(encoding="utf-8")
    rules = yaml.safe_load(raw)["rules"]
    parts: list[str] = []
    for rule in rules:
        parts.append(rule["detector"].get("pattern", ""))
        parts.append(rule.get("message", ""))
        parts.append(rule.get("fix_suggestion", "") or "")
    return "\n".join(parts)


def _codemod_corpus() -> str:
    """Every pattern + hint of the migrator, joined."""
    parts: list[str] = []
    for pattern, replacement in _MIGRATE_SAFE_REWRITES:
        parts.append(pattern.pattern)
        parts.append(replacement)
    for pattern, hint in _MIGRATE_HINTS:
        parts.append(pattern.pattern)
        parts.append(hint)
    return "\n".join(parts)


@pytest.mark.parametrize("name", sorted(_REMOVED_NAMES))
def test_removed_name_covered_by_lint_ssot(name: str) -> None:
    """Each runtime-removed name appears in some anti-pattern rule."""
    assert name in _lint_rules_corpus(), (
        f"{name!r} is in _REMOVED_NAMES but no rule in "
        f"02-anti-patterns.yaml mentions it — add a lint rule so static "
        f"analysis flags it too."
    )


@pytest.mark.parametrize("name", sorted(_REMOVED_NAMES))
def test_removed_name_covered_by_codemod(name: str) -> None:
    """Each runtime-removed name appears in some migrator entry."""
    assert name in _codemod_corpus(), (
        f"{name!r} is in _REMOVED_NAMES but migrate_legacy_code has no "
        f"rewrite/hint for it — add a _MIGRATE_HINTS entry."
    )


def test_fs_prefix_family_covered_everywhere() -> None:
    """The ``FS_*`` family is keyed by prefix (not exact name) in the
    runtime map; the other two registries must still know about it."""
    assert "FS_" in _lint_rules_corpus()
    assert "FS_" in _codemod_corpus()


def test_agent_doc_bundle_matches_pyproject_force_include() -> None:
    """The agent-doc filename list is hand-maintained in both
    ``agent.AGENT_DOCS`` and pyproject's wheel ``force-include`` table —
    keep them 1:1 so a doc added to one can't silently miss the wheel
    (PA-2). Skipped on py<3.11 (no stdlib tomllib) or when running
    against an installed wheel (pyproject not reachable)."""
    from pathlib import Path

    tomllib = pytest.importorskip("tomllib")

    from dartwork_mpl.agent import _SUFFIXES, AGENT_DOCS

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.is_file():
        pytest.skip("pyproject.toml not reachable (installed-wheel run)")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    force_include = data["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    bundled = {
        src
        for src, dest in force_include.items()
        if dest.startswith("dartwork_mpl/asset/agent/")
    }
    expected = {f"{name}{_SUFFIXES[name]}" for name in AGENT_DOCS}
    assert bundled == expected, (
        f"wheel bundle {sorted(bundled)} != AGENT_DOCS {sorted(expected)}"
    )
