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
    return 0


if __name__ == "__main__":
    sys.exit(main())
