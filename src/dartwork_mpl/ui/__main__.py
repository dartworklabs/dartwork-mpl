"""CLI entry point for dartwork_mpl.ui scaffolding.

Usage (interactive)::

    python -m dartwork_mpl.ui init
    dartwork-ui init

Usage (non-interactive)::

    python -m dartwork_mpl.ui init ./my-viewer --example simple
    dartwork-ui init ./my-viewer --example complex
"""

import argparse
import sys

from ._scaffold import scaffold


def _interactive_init() -> None:
    """대화형 프롬프트를 통해 init 명령을 실행한다.

    InquirerPy를 사용하여 대상 디렉토리와 예제 템플릿을
    사용자에게 질의한 뒤 scaffold를 실행한다.
    """
    from InquirerPy import inquirer

    print()
    print("  \033[1;36m◆ Dartwork UI — New Project\033[0m")
    print()

    target = inquirer.text(
        message="Target directory:", default="./my-viewer"
    ).execute()

    example = inquirer.select(
        message="Example template:",
        choices=[
            {
                "name": "simple  — single subplot, basic waveform",
                "value": "simple",
            },
            {
                "name": "complex — 3 subplots (signal + FFT + histogram)",
                "value": "complex",
            },
        ],
        default="simple",
    ).execute()

    scaffold(target, example=example)


def main() -> None:
    """CLI 인자를 파싱하고 스캐폴드를 실행한다.

    ``init`` 서브커맨드를 지원하며, 대상 디렉토리가
    생략되면 대화형 모드로 전환한다.
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
        choices=["simple", "complex"],
        default=None,
        help="Example template: simple (1 subplot) or complex (3 subplots)",
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
            scaffold(args.target, example=args.example)


if __name__ == "__main__":
    main()
