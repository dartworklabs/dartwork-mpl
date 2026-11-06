"""Write the anti-pattern catalog's removed-name rules from the registry.

``_LINT_RULES`` in ``src/dartwork_mpl/_compat.py`` is the only place these
rules are edited. This script renders them, in registry order, over the one
contiguous block of the same rule ids in
``src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`` and leaves every
other byte of the catalog as it is. It runs at development time only: the
installed package reads the catalog and never writes it.

Run after editing ``_LINT_RULES``::

    uv run python scripts/generate_removed_name_rules.py

Check without writing (exit 1 when the catalog is stale)::

    uv run python scripts/generate_removed_name_rules.py --check

``tests/contracts/test_deprecation_registry_parity.py`` runs the same check.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "src" / "dartwork_mpl" / "_compat.py"
CATALOG = (
    REPO_ROOT
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "prompt"
    / "02-anti-patterns.yaml"
)
_RULE_START = re.compile(r"^  - id: (\S+)$", re.MULTILINE)


class CatalogError(ValueError):
    """The catalog has no single block the registry's rules can replace."""


def load_registry(path: Path) -> ModuleType:
    """Load the registry module from the source tree, not the installed package.

    The module imports only the standard library, so it is loaded by path
    without importing (and initialising) the ``dartwork_mpl`` package.
    """
    name = "_dartwork_mpl_removed_name_registry"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load the registry from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules[name]
    return module


def _quoted(value: str) -> str:
    """A YAML single-quoted scalar."""
    return "'" + value.replace("'", "''") + "'"


def _literal_block(key: str, text: str) -> list[str]:
    """A YAML ``|`` block keeping ``text``'s line breaks."""
    return [f"    {key}: |"] + [
        f"      {line}" if line else "" for line in text.split("\n")
    ]


def render_rule(rule: Any) -> str:
    """One catalog rule in the catalog's layout, with its trailing blank line."""
    lines = [
        f"  - id: {rule.id}",
        f"    severity: {rule.severity}",
        "    detector:",
        "      kind: regex",
        f"      pattern: {_quoted(rule.pattern)}",
        *_literal_block("message", rule.message),
    ]
    if rule.why is not None:
        lines.extend(_literal_block("why", rule.why))
    if rule.fix_suggestion is not None:
        lines.append(f"    fix_suggestion: {_quoted(rule.fix_suggestion)}")
    return "\n".join(lines) + "\n\n"


def build(catalog: str, rules: Sequence[Any]) -> str:
    """``catalog`` with its block of the registry's rule ids re-rendered."""
    starts = [match.start() for match in _RULE_START.finditer(catalog)]
    ids = [match.group(1) for match in _RULE_START.finditer(catalog)]
    generated = {rule.id for rule in rules}
    found = [index for index, rule_id in enumerate(ids) if rule_id in generated]
    if not found:
        raise CatalogError("the catalog has no removed-name rule to replace")
    first, last = found[0], found[-1]
    if found != list(range(first, last + 1)):
        between = [ids[i] for i in range(first, last + 1) if i not in found]
        raise CatalogError(
            "the removed-name rules must be one contiguous block; "
            f"hand-written rules inside it: {between}"
        )
    if last == len(ids) - 1:
        raise CatalogError("the removed-name block cannot end the catalog")
    return (
        catalog[: starts[first]]
        + "".join(render_rule(rule) for rule in rules)
        + catalog[starts[last + 1] :]
    )


def expected() -> str:
    """The catalog text the registry implies."""
    rules = load_registry(REGISTRY)._LINT_RULES
    return build(CATALOG.read_text(encoding="utf-8"), rules)


def _shown(path: Path) -> str:
    """``path`` relative to the repository when it is inside it."""
    return str(
        path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Rewrite the catalog, or with ``--check`` report whether it is stale."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when the catalog differs; write nothing",
    )
    args = parser.parse_args(argv)
    current = CATALOG.read_text(encoding="utf-8")
    text = expected()
    if text == current:
        print(f"{_shown(CATALOG)} is up to date")
        return 0
    if args.check:
        print(
            f"{_shown(CATALOG)} differs from _LINT_RULES in "
            f"{_shown(REGISTRY)}; run "
            "`uv run python scripts/generate_removed_name_rules.py`",
            file=sys.stderr,
        )
        return 1
    CATALOG.write_text(text, encoding="utf-8")
    print(f"wrote {_shown(CATALOG)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
