"""Installation utilities for IDE integration and LLM assistants.

This module provides functions for automatically installing or removing
the dartwork-mpl usage guide in various IDE environments (e.g., Cursor)
and AI coding assistants (e.g., Claude Code).

The installed bundle is composed at install-time from the SSOT prompt
directory under ``asset/prompt/`` so it always tracks the canonical
0.4 guides (00-index, 01-policy, 02-anti-patterns, 03-recipes).

Eight install targets are supported: ``claude``, ``cursor``, ``copilot``
(GitHub Copilot Chat), ``codex`` (OpenAI Codex CLI / generic ``AGENTS.md``
convention), ``gemini`` (Gemini CLI / Antigravity), ``continue``
(Continue.dev), ``aider``, and ``windsurf``. The default ``targets=None``
preserves the historical behaviour (Claude Code + Cursor only); pass
``targets="all"`` or a list to expand coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path

__all__ = ["INSTALL_TARGETS", "install_llm_txt", "uninstall_llm_txt"]

# SSOT prompt directory.
_PROMPT_DIR: Path = Path(__file__).parent / "asset" / "prompt"
_TEMPLATE_DIR: Path = _PROMPT_DIR / "05-templates"

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


_META_RE = re.compile(
    r"# ai-template-meta-start\s*\n((?:#[^\n]*\n)+?)# ai-template-meta-end",
    re.MULTILINE,
)


def _parse_meta_block(block_body: str) -> dict[str, str]:
    """Parse ``# key: value`` lines inside a meta block into a dict."""
    fields: dict[str, str] = {}
    for line in block_body.splitlines():
        body = line.lstrip("#").rstrip()
        if not body.strip() or ":" not in body:
            continue
        key, _, value = body.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def _load_template_index() -> dict[str, dict[str, str]]:
    """Build the template index from either the pre-built JSON or
    by parsing the bundled ``05-templates/*.py`` directly.

    The Sphinx docs build writes ``05-templates/_index.json``, but in
    a fresh editable checkout (or a wheel that pre-dates the doc build)
    that file may be absent. Falling back to source parsing keeps
    :func:`install_llm_txt` resilient in those cases.
    """
    index_path = _TEMPLATE_DIR / "_index.json"
    if index_path.exists():
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = None
        if isinstance(raw, dict):
            return {
                tid: {k: str(v) for k, v in (meta or {}).items()}
                for tid, meta in raw.items()
            }

    # Fallback: scan source templates and parse their meta blocks.
    if not _TEMPLATE_DIR.exists():
        return {}
    index: dict[str, dict[str, str]] = {}
    for path in sorted(_TEMPLATE_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        m = _META_RE.search(text)
        if not m:
            continue
        meta = _parse_meta_block(m.group(1))
        if meta:
            # Source filenames already match the canonical template_id
            # (``bar``, ``bar_grouped``, ``plot_3d``, …).
            index[path.stem] = meta
    return index


def _compose_templates_quick_reference() -> str:
    """Build a one-paragraph-per-template summary table.

    The result is appended to every installed bundle so file-based
    fallback agents (Aider, Copilot, plain ChatGPT) get a paste-able
    catalog of the 18 ready-to-use plot templates without having to
    fetch them one by one.
    """
    index = _load_template_index()
    if not index:
        return ""

    lines: list[str] = [
        "AI Plot Templates — Quick Reference",
        "",
        "Each template lives at "
        "``dartwork_mpl/asset/prompt/05-templates/<id>.py`` and is "
        "reachable through the MCP resource "
        "``dartwork-mpl://templates/<id>`` or the Python helper "
        '``dm.get_prompt("05-templates/<id>")``.',
        "",
        "| Template | Difficulty | Use case | Data shape |",
        "|---|---|---|---|",
    ]
    for tid in sorted(index):
        meta = index[tid]
        difficulty = meta.get("difficulty", "?")
        use_case = meta.get("use_case", "?")
        data_shape = meta.get("data_shape", "?")
        lines.append(
            f"| `{tid}` | {difficulty} | {use_case} | `{data_shape}` |"
        )
    lines.append("")
    return "\n".join(lines)


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

    templates_ref = _compose_templates_quick_reference()
    if templates_ref:
        parts.append("\n---\n\n## ")
        parts.append(templates_ref)

    return "".join(parts)


# ---------------------------------------------------------------------------
# Install targets
# ---------------------------------------------------------------------------
#
# Each target writes the bundle (or a thin wrapper around it) to one or
# more files relative to ``project_dir``. The header text customises the
# preamble for the specific tool. To add a new target:
#
# 1. Pick a stable key (``"my_tool"``).
# 2. Add an entry to ``_TARGETS`` with the destination paths and a
#    header function.
# 3. Add the key to ``INSTALL_TARGETS`` so users can discover it.
#
# Headers receive the composed bundle as their only argument so they can
# wrap, prefix, or reformat it. They must return the full file content.


def _claude_header(bundle: str) -> str:
    return (
        "# dartwork-mpl Library Usage Command\n\n"
        "This command exposes the canonical 0.4 dartwork-mpl guides "
        "to AI coding assistants.\n\n"
        "## Usage\nType `/dartwork-mpl` to get help with dartwork-mpl "
        "usage.\n\n---\n\n" + bundle
    )


def _cursor_header(bundle: str) -> str:
    return (
        "// Cursor IDE Instructions for dartwork-mpl library\n"
        "// This file provides context about dartwork-mpl library "
        "usage\n\n" + bundle
    )


def _cursor_mdc_header(bundle: str) -> str:
    """Cursor 2026-era ``rules/*.mdc`` format with YAML front-matter."""
    front_matter = (
        "---\n"
        "description: dartwork-mpl publication-quality matplotlib design system\n"
        "globs:\n"
        '  - "**/*.py"\n'
        '  - "**/*.ipynb"\n'
        "alwaysApply: false\n"
        "---\n\n"
    )
    return front_matter + bundle


def _copilot_header(bundle: str) -> str:
    return (
        "# GitHub Copilot Workspace Instructions — dartwork-mpl\n\n"
        "GitHub Copilot reads this file as a project-wide instruction. "
        "When the user is plotting with matplotlib, follow the rules "
        "below.\n\n---\n\n" + bundle
    )


def _codex_header(bundle: str) -> str:
    return (
        "# AGENTS.md — dartwork-mpl plotting instructions\n\n"
        "This repo uses dartwork-mpl for matplotlib visualisations. "
        "Any agent (Codex CLI, Aider, generic AGENTS.md-aware tools) "
        "must follow the canonical 0.4 rules below.\n\n---\n\n" + bundle
    )


def _gemini_header(bundle: str) -> str:
    return (
        "# GEMINI.md — dartwork-mpl plotting context\n\n"
        "Gemini CLI / Antigravity read this file for project-wide "
        "context. Use the canonical 0.4 dartwork-mpl rules below when "
        "writing or editing matplotlib code.\n\n---\n\n" + bundle
    )


def _continue_header(bundle: str) -> str:
    return (
        "---\n"
        "name: dartwork-mpl\n"
        "description: Publication-quality matplotlib design system\n"
        "globs:\n"
        "  - '**/*.py'\n"
        "  - '**/*.ipynb'\n"
        "alwaysApply: false\n"
        "---\n\n" + bundle
    )


def _aider_header(bundle: str) -> str:
    return (
        "# CONVENTIONS.md — dartwork-mpl plotting conventions\n\n"
        "Aider reads ``CONVENTIONS.md`` (or any file passed with "
        "``--read``) as a system-level prompt. Apply the following "
        "rules whenever matplotlib code is touched.\n\n---\n\n" + bundle
    )


def _windsurf_header(bundle: str) -> str:
    return (
        "# Windsurf Rules — dartwork-mpl\n\n"
        "Drop this file under ``.windsurf/rules/`` (project) or in "
        "Cascade settings (global). The library policies below should "
        "drive every matplotlib edit.\n\n---\n\n" + bundle
    )


# Mapping of target key → (header function, list of relative destination
# paths). All destinations are project-relative.
_HeaderFn = Callable[[str], str]
_TARGETS: dict[str, tuple[_HeaderFn, tuple[str, ...]]] = {
    "claude": (_claude_header, (".claude/commands/dartwork-mpl-usage.md",)),
    "cursor": (_cursor_header, (".cursor/dartwork-mpl-usage.md",)),
    # New 2026-era target that uses Cursor's ``rules/*.mdc`` format.
    "cursor-rules": (_cursor_mdc_header, (".cursor/rules/dartwork-mpl.mdc",)),
    "copilot": (_copilot_header, (".github/copilot-instructions.md",)),
    # ``codex`` writes the universal ``AGENTS.md`` convention at the
    # repo root, picked up by Codex CLI and a growing list of
    # AGENTS.md-aware agents (Aider, Cline, etc.).
    "codex": (_codex_header, ("AGENTS.md",)),
    "gemini": (_gemini_header, ("GEMINI.md",)),
    # Continue.dev's per-rule files (one .md per topic, scanned at
    # workspace open).
    "continue": (_continue_header, (".continue/rules/dartwork-mpl.md",)),
    # Aider's ``CONVENTIONS.md`` is the de-facto place for project
    # rules. Users with a custom ``--read`` path can still reuse this.
    "aider": (_aider_header, ("CONVENTIONS.md",)),
    "windsurf": (_windsurf_header, (".windsurf/rules/dartwork-mpl.md",)),
}

# Public catalogue of install target keys (exported so callers can
# enumerate). Sorted alphabetically for stable output.
INSTALL_TARGETS: tuple[str, ...] = tuple(sorted(_TARGETS.keys()))

# Default historical behaviour: install only for Claude Code + Cursor
# (legacy 0.x format). Cursor's modern ``rules/*.mdc`` is opt-in via
# ``targets="all"`` or explicit selection so existing users don't get a
# surprise second file.
_DEFAULT_TARGETS: tuple[str, ...] = ("claude", "cursor")


def _resolve_targets(targets: object) -> tuple[str, ...]:
    """Normalise the ``targets`` argument into a tuple of keys."""
    if targets is None:
        return _DEFAULT_TARGETS
    if isinstance(targets, str):
        if targets == "all":
            return INSTALL_TARGETS
        return (targets,)
    if isinstance(targets, Iterable):
        resolved: list[str] = []
        for t in targets:
            if not isinstance(t, str):
                raise TypeError(
                    f"install_llm_txt: each target must be a string, "
                    f"got {type(t).__name__}."
                )
            resolved.append(t)
        return tuple(resolved)
    raise TypeError(
        f"install_llm_txt: targets must be None, 'all', a string, or "
        f"an iterable of strings, got {type(targets).__name__}."
    )


def install_llm_txt(
    project_dir: str | Path | None = None, *, targets: object = None
) -> dict[str, list[Path]]:
    """Install the dartwork-mpl usage guide into IDE integration folders.

    Composes a single markdown bundle from the canonical 0.4 SSOT
    files (``asset/prompt/{00-index, 01-policy, 03-recipes}`` plus a
    quick reference for the 18 bundled plot templates) and writes it
    to the destinations selected by ``targets``.

    Parameters
    ----------
    project_dir : str | Path | None, optional
        Target project directory. If None, the current working
        directory is used. Default is None.
    targets : None | str | Iterable[str], optional
        Which integration targets to write to. ``None`` (default)
        installs the legacy pair (``claude`` + ``cursor``).
        ``"all"`` installs every target in :data:`INSTALL_TARGETS`.
        Pass a single key (``"copilot"``) or a list
        (``["claude", "continue", "aider"]``) for a custom set.

    Returns
    -------
    dict[str, list[Path]]
        Mapping of target key to the list of files written for that
        target. Lets callers verify the install programmatically.

    Raises
    ------
    FileNotFoundError
        If the SSOT prompt directory cannot be found.
    KeyError
        If any requested target key is unknown.
    """
    if not _PROMPT_DIR.exists():
        raise FileNotFoundError(
            f"SSOT prompt directory not found at: {_PROMPT_DIR}"
        )

    selected = _resolve_targets(targets)
    unknown = [t for t in selected if t not in _TARGETS]
    if unknown:
        raise KeyError(
            f"Unknown install target(s): {unknown}. "
            f"Available: {INSTALL_TARGETS}"
        )

    project = Path(project_dir) if project_dir is not None else Path.cwd()
    bundle = _compose_bundle()

    written: dict[str, list[Path]] = {}
    for key in selected:
        header_fn, dest_rels = _TARGETS[key]
        content = header_fn(bundle)
        files: list[Path] = []
        for rel in dest_rels:
            out_path = project / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            files.append(out_path)
        written[key] = files

    print("✅ dartwork-mpl usage guide installed successfully!")
    print(f"📁 Project: {project}")
    for key, files in written.items():
        for f in files:
            print(f"📁 {key}: {f}")
    print()
    print("🔧 Usage:")
    if "claude" in written:
        print("- In Claude Code: Type '/dartwork-mpl' for help")
    if "cursor" in written or "cursor-rules" in written:
        print("- In Cursor IDE: AI auto-loads the dartwork-mpl context")
    if "copilot" in written:
        print("- In GitHub Copilot: workspace instructions apply globally")
    if "codex" in written:
        print("- In Codex CLI / AGENTS.md-aware agents: pre-loaded")
    if "gemini" in written:
        print("- In Gemini CLI / Antigravity: pre-loaded as project context")
    if "continue" in written:
        print("- In Continue.dev: rule auto-loads on workspace open")
    if "aider" in written:
        print("- In Aider: ``aider --read CONVENTIONS.md`` (or auto-detect)")
    if "windsurf" in written:
        print("- In Windsurf: rule auto-loads from .windsurf/rules/")

    return written


def uninstall_llm_txt(
    project_dir: str | Path | None = None, *, targets: object = None
) -> list[Path]:
    """Remove the dartwork-mpl usage guide from IDE integration folders.

    Parameters
    ----------
    project_dir : str | Path | None, optional
        Target project directory. If None, the current working
        directory is used. Default is None.
    targets : None | str | Iterable[str], optional
        Which integration targets to remove. ``None`` (default) removes
        every target in :data:`INSTALL_TARGETS` — this is safer than
        the historical behaviour because previously-installed files
        from now-unselected targets would otherwise linger. Pass an
        explicit list to scope the removal.

    Returns
    -------
    list[Path]
        Sorted list of files actually deleted.
    """
    # Different default from install_llm_txt: when uninstalling we
    # default to *all* targets so the user can clear every artifact
    # without enumerating them.
    if targets is None:
        selected: tuple[str, ...] = INSTALL_TARGETS
    else:
        selected = _resolve_targets(targets)

    unknown = [t for t in selected if t not in _TARGETS]
    if unknown:
        raise KeyError(
            f"Unknown uninstall target(s): {unknown}. "
            f"Available: {INSTALL_TARGETS}"
        )

    project = Path(project_dir) if project_dir is not None else Path.cwd()

    files_to_remove: list[Path] = []
    for key in selected:
        _header_fn, dest_rels = _TARGETS[key]
        files_to_remove.extend(project / rel for rel in dest_rels)

    removed: list[Path] = []
    for file_path in files_to_remove:
        if file_path.exists():
            file_path.unlink()
            removed.append(file_path)

    removed.sort()
    if removed:
        print("✅ dartwork-mpl usage guide uninstalled successfully!")
        for file_path in removed:
            print(f"🗑️  Removed: {file_path}")
    else:
        print("ℹ️  No dartwork-mpl usage guides found to remove.")  # noqa: RUF001
    return removed


if __name__ == "__main__":
    install_llm_txt()
