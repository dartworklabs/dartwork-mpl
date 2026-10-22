"""``python -m dartwork_mpl.skills`` — install or locate the agent skill."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import (
    TARGETS,
    SkillInstallError,
    _recover_all,
    install_skill,
    skill_path,
    skill_version,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dartwork_mpl.skills",
        description="Install the dartwork-mpl skill for Claude Code and Codex.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser(
        "install",
        help="link the skill into .claude/skills and/or .agents/skills",
        description=(
            "Link the skill bundled with this dartwork-mpl into "
            ".claude/skills/dartwork-mpl (Claude Code) and "
            ".agents/skills/dartwork-mpl (Codex). Without --claude or "
            "--codex, both are installed."
        ),
    )
    install.add_argument(
        "--claude", action="store_true", help="install for Claude Code"
    )
    install.add_argument(
        "--codex", action="store_true", help="install for Codex"
    )
    install.add_argument(
        "--dest",
        default=".",
        metavar="DIR",
        help="project directory to install into (default: current; ~ for user-level)",
    )
    install.add_argument(
        "--copy",
        action="store_true",
        help="copy instead of symlinking (no symlinks, or to check the skill "
        "into the repository); rerun after upgrading dartwork-mpl",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="replace a file or folder this installer did not create, or a "
        "copy with local edits",
    )
    sub.add_parser(
        "path",
        help="print the folder that holds SKILL.md (and put back a copy an "
        "interrupted install left aside in this project)",
    )
    return parser


def _shown(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; return the process exit status."""
    args = _parser().parse_args(argv)
    if args.command == "path":
        # An interrupted copy replacement in this project is put back here
        # too, so the agent that runs `path` finds the skill again.
        for restored in _recover_all("."):
            print(
                f"note: put back {restored} after an interrupted install",
                file=sys.stderr,
            )
        print(skill_path())
        return 0

    chosen = [name for name in TARGETS if getattr(args, name)]
    try:
        results = install_skill(
            args.dest,
            targets=chosen or list(TARGETS),
            copy=args.copy,
            force=args.force,
        )
    except SkillInstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"dartwork-mpl {skill_version()} skill: {skill_path()}")
    for result in results:
        line = f"{result.action:<9} {_shown(result.path)}"
        if result.detail:
            line += f" ({result.detail})"
        print(line)
    if not args.copy:
        print(
            "note: the links point into this Python environment; moving or "
            "recreating it breaks them until you rerun this command. Use "
            "--copy for a copy you can check into the repository."
        )
    if any(r.action in ("linked", "copied", "replaced") for r in results):
        print("If the skill does not appear, start a new agent session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
