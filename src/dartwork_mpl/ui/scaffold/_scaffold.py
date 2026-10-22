"""Project scaffolder for Dartwork UI.

Generates a ready-to-run project folder with:
- ``app.py`` — figure function + ParamModel + run()
- ``README.md`` — detailed usage guide
- ``.gitignore`` — excludes generated files

Template files are stored as real assets in the ``templates/``
directory next to this module and read at runtime.
"""

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def scaffold(target: str, *, example: str = "simple") -> None:
    """Create a new Dartwork UI project folder.

    Parameters
    ----------
    target : str
        Path to the target directory.
    example : str
        ``"simple"`` or ``"complex"``.
    """
    dest = Path(target).resolve()

    if dest.exists() and any(dest.iterdir()):
        print(f"\n  Error: {dest} already exists and is not empty.\n")
        return

    dest.mkdir(parents=True, exist_ok=True)

    # Read template files and write to destination
    app_template = _TEMPLATES_DIR / f"{example}.py"
    readme_template = _TEMPLATES_DIR / "README.md"
    gitignore_template = _TEMPLATES_DIR / ".gitignore.template"

    (dest / "app.py").write_text(
        app_template.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (dest / "README.md").write_text(
        readme_template.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (dest / ".gitignore").write_text(
        gitignore_template.read_text(encoding="utf-8"), encoding="utf-8"
    )

    print("\n  Created Dartwork UI project at:")
    print(f"  \033[1;36m{dest}\033[0m\n")
    print("  Files:")
    print(f"    app.py      — figure function ({example} example)")
    print("    README.md   — usage guide")
    print("    .gitignore  — excludes generated files")
    print()
    print("  To run:")
    print(f"    cd {dest}")
    print("    uv run --extra ui python app.py")
    print()
