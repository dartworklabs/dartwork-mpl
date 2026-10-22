"""CLI entry point for dartwork_mpl.ui scaffolding.

Usage (interactive)::

    python -m dartwork_mpl.ui init
    dartwork-mpl-ui init

Usage (non-interactive)::

    python -m dartwork_mpl.ui init ./my-viewer --example simple
    dartwork-mpl-ui init ./my-viewer --example simple

A refused request (unknown example, non-empty target) prints a message
to stderr and exits non-zero; argparse usage errors exit 2.
"""

import argparse
import sys

from .scaffold import (
    EXAMPLES,
    Scaffolded,
    ScaffoldRefusal,
    TargetNotEmpty,
    UnknownExample,
    scaffold,
)

_EXAMPLE_LABELS = {"simple": "simple  — single subplot, basic waveform"}
"""Interactive-prompt label for each name in ``EXAMPLES``."""


def _report(outcome: Scaffolded | ScaffoldRefusal) -> None:
    """Print the scaffold outcome; exit with status 1 on a refusal.

    ``Scaffolded`` prints the created files and run instructions to stdout
    and returns. ``TargetNotEmpty`` and ``UnknownExample`` print their
    reason to stderr and raise ``SystemExit(1)``.
    """
    if isinstance(outcome, TargetNotEmpty):
        print(
            f"Error: {outcome.dest} already exists and is not empty.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if isinstance(outcome, UnknownExample):
        print(
            f"Error: unknown example {outcome.example!r}; "
            f"choose from {', '.join(outcome.available)}.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print("\n  Created Dartwork UI project at:")
    print(f"  \033[1;36m{outcome.dest}\033[0m\n")
    print("  Files:")
    print(f"    app.py      — figure function ({outcome.example} example)")
    print("    README.md   — usage guide")
    print("    .gitignore  — excludes generated files")
    print()
    print("  To run:")
    print(f"    cd {outcome.dest}")
    print("    uv run --extra ui python app.py")
    print()


def _interactive_init() -> None:
    """Run the init command via interactive prompts.

    Uses InquirerPy to ask the user for the target directory and
    example template, then runs the scaffold and reports it through
    ``_report`` (exit status 1 on a refusal). Raises ``SystemExit`` with
    install advice when the ``ui`` extra (InquirerPy) is missing.
    """
    try:
        from InquirerPy import inquirer
    except ImportError as exc:
        # Mirror the graceful optional-dep gating used by the mcp /
        # notebook extras instead of surfacing a raw ImportError.
        raise SystemExit(
            "Interactive init requires the 'ui' extra: "
            'pip install "dartwork-mpl[ui]" — or skip the prompts by '
            "passing a target directory: dartwork-mpl-ui init ./my-viewer"
        ) from exc

    print()
    print("  \033[1;36m◆ Dartwork UI — New Project\033[0m")
    print()

    target = inquirer.text(
        message="Target directory:", default="./my-viewer"
    ).execute()

    example = inquirer.select(
        message="Example template:",
        choices=[
            {"name": _EXAMPLE_LABELS.get(name, name), "value": name}
            for name in EXAMPLES
        ],
        default="simple",
    ).execute()

    _report(scaffold(target, example=example))


def main() -> None:
    """Parse CLI arguments and run the scaffold.

    Supports the ``init`` subcommand. Falls back to interactive mode
    if the target directory or ``--example`` is omitted. Exits 1 without
    a subcommand or when the scaffold refuses; argparse exits 2 for an
    ``--example`` outside ``EXAMPLES``.
    """
    parser = argparse.ArgumentParser(
        prog="ui", description="Dartwork UI project scaffolder"
    )
    sub = parser.add_subparsers(dest="command")

    init_parser = sub.add_parser(
        "init", help="Create a new Dartwork UI project folder"
    )
    init_parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Target directory (interactive prompt if omitted)",
    )
    init_parser.add_argument(
        "--example",
        choices=list(EXAMPLES),
        default=None,
        help="Example template: simple (1 subplot)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        # Interactive mode if target is not given
        if args.target is None or args.example is None:
            _interactive_init()
        else:
            _report(scaffold(args.target, example=args.example))


if __name__ == "__main__":
    main()
