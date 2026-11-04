"""The guide resources' text: prompt-corpus documents and the migration pointer."""

from ...prompt import get_prompt, open_anti_pattern_catalog


def guide_text(name: str) -> str:
    """The prompt-corpus document ``name`` (e.g. ``"00-index"``), as ``dm.get_prompt`` returns it."""
    return get_prompt(name)


def anti_pattern_catalog() -> str:
    """The raw ``02-anti-patterns.yaml`` catalog text (the lint engine's source)."""
    with open_anti_pattern_catalog() as fh:
        return fh.read()


def migration_pointer() -> str:
    """The fixed 0.3 -> 0.4 migration pointer text."""
    return (
        "0.3 → 0.4 migration guide: "
        "https://dartworklabs.github.io/dartwork-mpl/migration.html\n\n"
        "For an automated rewrite, call the migrate_legacy_code MCP "
        "tool (or dm.migrate_legacy_code in Python)."
    )
