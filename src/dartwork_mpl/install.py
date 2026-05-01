"""Installation utilities for IDE integration and LLM assistants.

This module provides functions for automatically installing or removing
the dartwork-mpl usage guide in various IDE environments (e.g., Cursor)
and AI coding assistants (e.g., Claude Code).

The installed bundle is composed at install-time from the SSOT prompt
directory under ``asset/prompt/`` so it always tracks the canonical
0.4 guides (00-index, 01-policy, 02-anti-patterns, 03-recipes).
"""

from pathlib import Path

__all__ = ["install_llm_txt", "uninstall_llm_txt"]

# SSOT prompt directory.
_PROMPT_DIR: Path = Path(__file__).parent / "asset" / "prompt"

# Pieces composed into the installed bundle, in order. Each entry is
# a (heading, source-file) pair; missing files are skipped so an
# in-progress repo (e.g. early in a migration) still installs whatever
# is available. The machine-readable anti-pattern YAML is intentionally
# omitted — it is reachable via the MCP `dartwork-mpl://guide/anti-
# patterns` resource, and lifting its rule-detector strings into a
# human-facing bundle would re-introduce phrases (e.g. "Zero-Resize")
# that lint specifically warns against.
_BUNDLE_PIECES: tuple[tuple[str, str], ...] = (
    ("Agent entry point", "00-index.md"),
    ("Policy", "01-policy.md"),
    ("Recipes (intent → function call)", "03-recipes.md"),
)


def _compose_bundle() -> str:
    """Concatenate the SSOT pieces into a single markdown payload."""
    parts: list[str] = ["# dartwork-mpl Usage Bundle\n"]
    for heading, filename in _BUNDLE_PIECES:
        path = _PROMPT_DIR / filename
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8")
        parts.append(f"\n---\n\n## {heading} (`{filename}`)\n\n")
        if filename.endswith(".yaml"):
            # Render YAML as a fenced block so it stays legible.
            parts.append(f"```yaml\n{body}\n```\n")
        else:
            parts.append(body)
            if not body.endswith("\n"):
                parts.append("\n")
    return "".join(parts)


def install_llm_txt(project_dir: str | Path | None = None) -> None:
    """Install the dartwork-mpl usage guide into IDE integration folders.

    Composes a single markdown bundle from the canonical 0.4 SSOT
    files (``asset/prompt/{00-index, 01-policy, 02-anti-patterns,
    03-recipes}``) and writes it to:

    - ``.claude/commands/dartwork-mpl-usage.md`` (Claude Code)
    - ``.cursor/dartwork-mpl-usage.md`` (Cursor IDE)

    Parameters
    ----------
    project_dir : str | Path | None, optional
        Target project directory. If None, the current working
        directory is used. Default is None.

    Raises
    ------
    FileNotFoundError
        If the SSOT prompt directory cannot be found.
    """
    if not _PROMPT_DIR.exists():
        raise FileNotFoundError(
            f"SSOT prompt directory not found at: {_PROMPT_DIR}"
        )

    project = Path(project_dir) if project_dir is not None else Path.cwd()

    bundle = _compose_bundle()

    claude_dir: Path = project / ".claude" / "commands"
    claude_dir.mkdir(parents=True, exist_ok=True)
    claude_file: Path = claude_dir / "dartwork-mpl-usage.md"
    claude_file.write_text(
        "# dartwork-mpl Library Usage Command\n\n"
        "This command exposes the canonical 0.4 dartwork-mpl guides "
        "to AI coding assistants.\n\n"
        "## Usage\nType `/dartwork-mpl` to get help with dartwork-mpl "
        "usage.\n\n---\n\n" + bundle,
        encoding="utf-8",
    )

    cursor_dir: Path = project / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    cursor_file: Path = cursor_dir / "dartwork-mpl-usage.md"
    cursor_file.write_text(
        "// Cursor IDE Instructions for dartwork-mpl library\n"
        "// This file provides context about dartwork-mpl library "
        "usage\n\n" + bundle,
        encoding="utf-8",
    )

    print("✅ dartwork-mpl usage guide installed successfully!")
    print(f"📁 Project: {project}")
    print(f"📁 Claude Code: {claude_file}")
    print(f"📁 Cursor IDE: {cursor_file}")
    print()
    print("🔧 Usage:")
    print("- In Claude Code: Type '/dartwork-mpl' for help")
    print(
        "- In Cursor IDE: The AI will automatically have access to "
        "dartwork-mpl context"
    )


def uninstall_llm_txt(project_dir: str | Path | None = None) -> None:
    """Remove the dartwork-mpl usage guide from IDE integration folders.

    Parameters
    ----------
    project_dir : str | Path | None, optional
        Target project directory. If None, the current working
        directory is used. Default is None.
    """
    project = Path(project_dir) if project_dir is not None else Path.cwd()

    files_to_remove: list[Path] = [
        project / ".claude" / "commands" / "dartwork-mpl-usage.md",
        project / ".cursor" / "dartwork-mpl-usage.md",
    ]

    removed: list[Path] = []
    for file_path in files_to_remove:
        if file_path.exists():
            file_path.unlink()
            removed.append(file_path)

    if removed:
        print("✅ dartwork-mpl usage guide uninstalled successfully!")
        for file_path in removed:
            print(f"🗑️  Removed: {file_path}")
    else:
        print("ℹ️  No dartwork-mpl usage guides found to remove.")  # noqa: RUF001


if __name__ == "__main__":
    install_llm_txt()
