"""The guide resources' text: prompt-corpus documents and the migration pointer."""

from pathlib import Path

from ...prompt import get_prompt

# Path to the SSOT prompt directory (00-index, 01-policy, 03-recipes,
# 05-templates/, _legacy/, ...)
_PROMPT_DIR = Path(__file__).parents[2] / "asset" / "prompt"


def guide_text(name: str) -> str:
    """The prompt-corpus document ``name`` (e.g. ``"00-index"``), as ``dm.get_prompt`` returns it."""
    return get_prompt(name)


def anti_pattern_catalog() -> str:
    """The raw ``02-anti-patterns.yaml`` catalog text (the lint engine's source)."""
    path = _PROMPT_DIR / "02-anti-patterns.yaml"
    return path.read_text(encoding="utf-8")


def migration_pointer() -> str:
    """The fixed 0.3 -> 0.4 migration pointer text."""
    return (
        "0.3 → 0.4 migration guide: "
        "https://dartworklabs.github.io/dartwork-mpl/migration.html\n\n"
        "For an automated rewrite, call the migrate_legacy_code MCP "
        "tool (or dm.migrate_legacy_code in Python)."
    )
