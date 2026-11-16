"""``dartwork-mpl install [--dest D] [--copy] [--force]`` / ``dartwork-mpl path``.

The console script; ``python -m dartwork_mpl.guide`` runs the same.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .install import install_skill, links_into, skill_path


def main(argv: list[str] | None = None) -> int:
    """Install the skill, or print where it is."""
    parser = argparse.ArgumentParser(prog="dartwork-mpl")
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser(
        "install",
        help="put the skill into a project's .claude/skills and .agents/skills",
    )
    install.add_argument(
        "--dest", default=".", help="project or home directory"
    )
    install.add_argument(
        "--copy",
        action="store_true",
        help="copy even where a link would last (a link is made only when the package is installed inside --dest, as after uv add)",
    )
    install.add_argument(
        "--force", action="store_true", help="replace what is there"
    )
    install.set_defaults(run=_install)
    path = commands.add_parser("path", help="print the installed skill folder")
    path.set_defaults(run=_path)
    args = parser.parse_args(argv)
    return args.run(args)


def _path(_args: argparse.Namespace) -> int:
    print(skill_path())
    return 0


def _install(args: argparse.Namespace) -> int:
    try:
        done = install_skill(args.dest, copy=args.copy, force=args.force)
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1
    for item in done:
        print(f"{item.action}: {item.path}")
    if not args.copy and not links_into(Path(args.dest)):
        print(
            f"copied, not linked: the package at {Path(__file__).resolve().parents[1]} "
            "lives outside this project (uvx's cache or a global install), so a "
            "link would break; run this again after upgrading to refresh the copy"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
