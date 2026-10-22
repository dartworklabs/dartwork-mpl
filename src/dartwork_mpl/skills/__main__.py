"""``python -m dartwork_mpl.skills`` — install or locate the agent skill."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import TARGETS, SkillInstallError, install_skill, skill_path


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
        help="copy instead of symlinking (for systems without symlinks); "
        "rerun after upgrading dartwork-mpl",
    )
    install.add_argument(
        "--force",
        action="store_true",
        help="replace a file or folder this installer did not create",
    )
    sub.add_parser("path", help="print the folder that holds SKILL.md")
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

    for result in results:
        line = f"{result.action:<9} {_shown(result.path)}"
        if result.action in ("linked", "replaced") and not args.copy:
            line += f" -> {skill_path()}"
        if result.detail:
            line += f" ({result.detail})"
        print(line)
    if any(r.action in ("linked", "copied", "replaced") for r in results):
        print("If the skill does not appear, start a new agent session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
