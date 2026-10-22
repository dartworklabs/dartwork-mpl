"""The anti-pattern catalog: the ``Rule`` and ``Issue`` values and the YAML loader.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``Rule``, ``Issue``,
``load_rules``. The bundled catalog is
``asset/prompt/02-anti-patterns.yaml``.

Inside the lint package a rule's detector is the closed union
``_Detector`` (``_RegexDetector | _SubstringDetector | _AstNameDetector``).
``load_rules`` parses each YAML ``detector`` mapping into it once and fills
the public ``Rule.detector_kind`` / ``detector_value`` strings from the
parsed value; ``_rule_detector`` recovers the union from any ``Rule``,
including one a caller built by hand.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

import yaml

_RULES_PATH: Path = (
    Path(__file__).parent.parent / "asset" / "prompt" / "02-anti-patterns.yaml"
)

_Severity: TypeAlias = Literal["critical", "warning", "info"]
"""A catalog severity. ``load_rules`` admits only these three strings."""

_SEVERITIES: tuple[_Severity, ...] = ("critical", "warning", "info")

_AstCheck: TypeAlias = Literal["colormap-name", "color-name"]
"""The static AST name checks the engine implements."""

_AST_CHECKS: tuple[_AstCheck, ...] = ("colormap-name", "color-name")


@dataclass(frozen=True)
class _RegexDetector:
    """A rule found by a regular expression; ``pattern`` compiles."""

    pattern: str


@dataclass(frozen=True)
class _SubstringDetector:
    """A rule found by a literal substring of the raw source text."""

    literal: str


@dataclass(frozen=True)
class _AstNameDetector:
    """A rule found by checking literal names against matplotlib's registries."""

    check: _AstCheck


_Detector: TypeAlias = _RegexDetector | _SubstringDetector | _AstNameDetector


@dataclass(frozen=True)
class _UnsupportedDetector:
    """A hand-built ``Rule`` names a detector this engine does not implement.

    Such a rule matches nothing; ``load_rules`` never produces one.
    """

    kind: str
    value: str


@dataclass(frozen=True)
class Rule:
    """A single anti-pattern definition."""

    id: str
    severity: str  # "critical" | "warning" | "info"
    detector_kind: str  # "regex" | "substring" | "ast"
    detector_value: str  # pattern, literal, or AST check name
    message: str
    why: str | None = None
    fix_suggestion: str | None = None


@dataclass(frozen=True)
class Issue:
    """A detected violation.

    ``column`` is the absolute character offset of the match in the source
    string (0-indexed). It is included to disambiguate multiple
    violations on the same line — ``(rule_id, line)`` alone collapses
    them and hides the second occurrence from auto-fixers.

    ``fix_suggestion`` mirrors the YAML field of the same name and is
    surfaced inline by :func:`format_report` so AI agents can apply a
    fix without a second round-trip.
    """

    rule_id: str
    severity: str
    message: str
    line: int | None = None
    snippet: str | None = None
    column: int | None = None
    fix_suggestion: str | None = None


def _detector_fields(detector: _Detector) -> tuple[str, str]:
    """Return the public ``(detector_kind, detector_value)`` strings of a detector."""
    match detector:
        case _RegexDetector(pattern):
            return "regex", pattern
        case _SubstringDetector(literal):
            return "substring", literal
        case _AstNameDetector(check):
            return "ast", check


def _rule_detector(rule: Rule) -> _Detector | _UnsupportedDetector:
    """Read a rule's public detector strings back into the detector union.

    A regex detector's pattern is not recompiled here: a hand-built rule
    with an invalid pattern still fails when it is scanned, as before.
    """
    kind, value = rule.detector_kind, rule.detector_value
    if kind == "regex":
        return _RegexDetector(value)
    if kind == "substring":
        return _SubstringDetector(value)
    if kind == "ast":
        for check in _AST_CHECKS:
            if value == check:
                return _AstNameDetector(check)
    return _UnsupportedDetector(kind, value)


def _parse_severity(raw: object, context: str) -> _Severity:
    """Parse a YAML severity; raise ``ValueError`` naming the rule otherwise."""
    for severity in _SEVERITIES:
        if isinstance(raw, str) and raw == severity:
            return severity
    raise ValueError(f"Unsupported severity {raw!r} in {context}")


def _parse_detector(raw: object, context: str) -> _Detector:
    """Parse a YAML ``detector`` mapping; raise ``ValueError`` naming the rule.

    ``kind`` defaults to ``"regex"``. A regex must compile with
    ``re.MULTILINE``; a substring must be a string; an AST check must be
    one of ``_AST_CHECKS``.
    """
    if not isinstance(raw, Mapping):
        raise ValueError(f"Detector in {context} must be a mapping")
    kind = raw.get("kind", "regex")
    if kind == "regex":
        pattern = raw.get("pattern")
        if not isinstance(pattern, str):
            raise ValueError(
                f"Invalid regex in {context}: expected a string pattern"
            )
        try:
            re.compile(pattern, re.MULTILINE)
        except re.error as exc:
            raise ValueError(f"Invalid regex in {context}: {exc}") from exc
        return _RegexDetector(pattern)
    if kind == "substring":
        literal = raw.get("literal")
        if not isinstance(literal, str):
            raise ValueError(
                f"Invalid substring in {context}: expected a string literal"
            )
        return _SubstringDetector(literal)
    if kind == "ast":
        check = raw.get("check")
        for supported in _AST_CHECKS:
            if isinstance(check, str) and check == supported:
                return _AstNameDetector(supported)
    raise ValueError(f"Unsupported detector kind {kind!r} in {context}")


def load_rules(path: Path | None = None) -> list[Rule]:
    """Load and parse the anti-pattern catalog.

    Parameters
    ----------
    path : Path | None, optional
        Override path for testing. Defaults to the bundled
        ``02-anti-patterns.yaml``.

    Returns
    -------
    list[Rule]
        Parsed rule objects in declaration order. An empty mapping or
        explicit empty ``rules`` list returns an empty list.

    Raises
    ------
    ValueError
        If catalog containers or required rule fields are malformed,
        severity is unsupported, a detector kind/check is unsupported,
        or a regex is not a valid string pattern. These invalid-input
        errors are reported at load time with catalog/rule context.
        Filesystem and YAML syntax errors retain their native exceptions.
    """
    yaml_path = path or _RULES_PATH
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, Mapping):
        raise ValueError(f"Catalog {yaml_path} must be a mapping")
    entries = data.get("rules", [])
    if not isinstance(entries, list):
        raise ValueError(f"Catalog {yaml_path} rules must be a list")
    rules: list[Rule] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ValueError(f"Rule entry {index} must be a mapping")
        context = f"rule {entry.get('id')!r} (entry {index})"
        rule_id = entry.get("id")
        if not isinstance(rule_id, str):
            raise ValueError(f"Invalid id in {context}: expected a string")
        message = entry.get("message")
        if not isinstance(message, str):
            raise ValueError(f"Invalid message in {context}: expected a string")
        severity = _parse_severity(entry.get("severity"), context)
        kind, value = _detector_fields(
            _parse_detector(entry.get("detector", {}), context)
        )
        rules.append(
            Rule(
                id=rule_id,
                severity=severity,
                detector_kind=kind,
                detector_value=value,
                message=message.rstrip(),
                why=(entry.get("why") or None),
                fix_suggestion=entry.get("fix_suggestion"),
            )
        )
    return rules
