"""The anti-pattern catalog: the ``Rule`` and ``Issue`` values and the YAML loader.

Surface (re-exported by :mod:`dartwork_mpl.lint`): ``Rule``, ``Issue``,
``load_rules``. The bundled catalog is
``asset/prompt/02-anti-patterns.yaml``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

_RULES_PATH: Path = (
    Path(__file__).parent.parent / "asset" / "prompt" / "02-anti-patterns.yaml"
)


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
        for field in ("id", "message"):
            if not isinstance(entry.get(field), str):
                raise ValueError(
                    f"Invalid {field} in {context}: expected a string"
                )
        severity = entry.get("severity")
        if not isinstance(severity, str) or severity not in {
            "critical",
            "warning",
            "info",
        }:
            raise ValueError(f"Unsupported severity {severity!r} in {context}")
        detector = entry.get("detector", {})
        if not isinstance(detector, Mapping):
            raise ValueError(f"Detector in {context} must be a mapping")
        kind = detector.get("kind", "regex")
        if kind == "regex":
            value = detector.get("pattern")
            if not isinstance(value, str):
                raise ValueError(
                    f"Invalid regex in {context}: expected a string pattern"
                )
            try:
                re.compile(value, re.MULTILINE)
            except re.error as exc:
                raise ValueError(f"Invalid regex in {context}: {exc}") from exc
        elif kind == "substring":
            value = detector.get("literal")
            if not isinstance(value, str):
                raise ValueError(
                    f"Invalid substring in {context}: expected a string literal"
                )
        elif kind == "ast" and detector.get("check") in (
            "colormap-name",
            "color-name",
        ):
            value = detector["check"]
        else:
            raise ValueError(f"Unsupported detector kind {kind!r} in {context}")
        rules.append(
            Rule(
                id=entry["id"],
                severity=severity,
                detector_kind=kind,
                detector_value=value,
                message=entry["message"].rstrip(),
                why=(entry.get("why") or None),
                fix_suggestion=entry.get("fix_suggestion"),
            )
        )
    return rules
