"""Project scaffolder for Dartwork UI.

Generates a ready-to-run project folder with:
- ``app.py`` — figure function + ParamModel + run()
- ``README.md`` — detailed usage guide
- ``.gitignore`` — excludes generated files

Template files are stored as real assets in the ``templates/``
directory next to this module and read at runtime.

``scaffold`` prints nothing; it returns ``Scaffolded`` or one of the
``ScaffoldRefusal`` values, and the CLI turns each into a message and an
exit status.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

_TEMPLATES_DIR = Path(__file__).parent / "templates"

EXAMPLES: tuple[str, ...] = ("simple",)
"""Example names with a bundled ``templates/<name>.py``.

``complex`` was removed deliberately with the dashboard features in
dc750a27 and is not offered.
"""


@dataclass(frozen=True)
class Scaffolded:
    """The project was written.

    Attributes
    ----------
    dest : Path
        Absolute path of the project directory.
    example : str
        The example template copied into ``app.py``.
    """

    dest: Path
    example: str


@dataclass(frozen=True)
class TargetNotEmpty:
    """The target already holds entries; nothing was written.

    Attributes
    ----------
    dest : Path
        Absolute path of the refused directory.
    """

    dest: Path


@dataclass(frozen=True)
class UnknownExample:
    """The requested example has no bundled template; nothing was written.

    Attributes
    ----------
    example : str
        The name that was requested.
    available : tuple[str, ...]
        The example names that can be requested instead.
    """

    example: str
    available: tuple[str, ...]


ScaffoldRefusal: TypeAlias = TargetNotEmpty | UnknownExample


def scaffold(
    target: str, *, example: str = "simple"
) -> Scaffolded | ScaffoldRefusal:
    """Create a new Dartwork UI project folder.

    Parameters
    ----------
    target : str
        Path to the target directory. Missing parents are created.
    example : str
        One of ``EXAMPLES``.

    Returns
    -------
    Scaffolded | ScaffoldRefusal
        ``Scaffolded`` after ``app.py``, ``README.md`` and ``.gitignore``
        were written; ``UnknownExample`` when ``example`` is not in
        ``EXAMPLES``; ``TargetNotEmpty`` when the target directory already
        has entries. Neither refusal creates or changes any file.

    Raises
    ------
    OSError
        When the filesystem refuses a read or write (for example the
        target is a regular file or is not writable).
    """
    if example not in EXAMPLES:
        return UnknownExample(example=example, available=EXAMPLES)

    dest = Path(target).resolve()
    if dest.exists() and any(dest.iterdir()):
        return TargetNotEmpty(dest=dest)

    dest.mkdir(parents=True, exist_ok=True)

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
    return Scaffolded(dest=dest, example=example)
