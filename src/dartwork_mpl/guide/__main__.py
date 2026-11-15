"""``python -m dartwork_mpl.guide install [--dest D] [--copy] [--force]`` / ``path``."""

from __future__ import annotations

import argparse
import sys

from .install import install_skill, skill_path


def main(argv: list[str] | None = None) -> int:
    """Install the skill, or print where it is."""
    parser = argparse.ArgumentParser(prog="python -m dartwork_mpl.guide")
    commands = parser.add_subparsers(dest="command", required=True)
    install = commands.add_parser(
        "install", help="link the skill into a project"
    )
    install.add_argument(
        "--dest", default=".", help="project or home directory"
    )
    install.add_argument(
        "--copy", action="store_true", help="copy, do not link"
    )
    install.add_argument(
        "--force", action="store_true", help="replace what is there"
    )
    commands.add_parser("path", help="print the installed skill folder")
    args = parser.parse_args(argv)
    if args.command == "path":
        print(skill_path())
        return 0
    try:
        done = install_skill(args.dest, copy=args.copy, force=args.force)
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1
    for item in done:
        print(f"{item.action}: {item.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
