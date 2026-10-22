"""The agent skill bundled with dartwork-mpl, and its installer.

The skill folder ``dartwork-mpl/`` (``SKILL.md`` plus ``references/``) ships
inside the package, so it always describes the installed version. Claude
Code reads project skills from ``.claude/skills/`` and Codex from
``.agents/skills/``; :func:`install_skill` links the folder into either or
both, or copies it where symlinks are unavailable.

Command line::

    python -m dartwork_mpl.skills install             # both agents, this project
    python -m dartwork_mpl.skills install --claude    # Claude Code only
    python -m dartwork_mpl.skills install --dest ~    # user-level skills
    python -m dartwork_mpl.skills install --copy      # no symlinks (Windows)
    python -m dartwork_mpl.skills path                # print the skill folder

Installing is idempotent. A link or copy made by this installer is updated
in place; anything else at the destination is left alone unless ``force``
is set.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Literal

__all__ = [
    "SKILL_NAME",
    "TARGETS",
    "InstallResult",
    "SkillInstallError",
    "install_skill",
    "skill_path",
]

SKILL_NAME = "dartwork-mpl"

# Agent -> its skills directory, relative to a project (or home) directory.
TARGETS: dict[str, str] = {
    "claude": ".claude/skills",
    "codex": ".agents/skills",
}

_SOURCE = Path(__file__).resolve().parent / SKILL_NAME
# Written into copies so a later run can recognise and refresh them.
_COPY_MARKER = ".dartwork-mpl-skill"
# Tail of every link this installer makes, in any environment.
_SOURCE_TAIL = ("dartwork_mpl", "skills", SKILL_NAME)

Action = Literal["linked", "copied", "replaced", "unchanged", "shared"]


class SkillInstallError(RuntimeError):
    """The skill could not be installed; nothing was changed."""


@dataclass(frozen=True)
class InstallResult:
    """What :func:`install_skill` did for one agent."""

    target: str
    path: Path
    action: Action
    detail: str = ""


def skill_path() -> Path:
    """Return the installed skill folder (the one holding ``SKILL.md``)."""
    return _SOURCE


def _version() -> str:
    try:
        return metadata.version("dartwork-mpl")
    except metadata.PackageNotFoundError:
        return "unknown"


def _is_installer_link(link: Path) -> bool:
    """True for a symlink whose target ends in ``dartwork_mpl/skills/dartwork-mpl``."""
    target = Path(os.readlink(link))
    return target.parts[-len(_SOURCE_TAIL) :] == _SOURCE_TAIL


def _tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and p.name != _COPY_MARKER
        and "__pycache__" not in p.parts
    }


def _plan(link: Path, *, copy: bool, force: bool) -> Action:
    """Decide the action for one destination, raising for foreign content."""
    if link.is_symlink():
        if not copy and link.resolve() == _SOURCE:
            return "unchanged"
        if _is_installer_link(link) or force:
            return "replaced"
    elif link.is_dir() and (link / _COPY_MARKER).is_file():
        if copy and _tree(link) == _tree(_SOURCE):
            return "unchanged"
        return "replaced"
    elif not link.exists():
        return "copied" if copy else "linked"
    elif force:
        return "replaced"
    raise SkillInstallError(
        f"{link} exists and was not made by this installer; move it away "
        f"or rerun with --force to replace it."
    )


def _remove(link: Path) -> None:
    if link.is_symlink() or not link.is_dir():
        link.unlink()
    else:
        shutil.rmtree(link)


def _create(link: Path, *, copy: bool) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if copy:
        shutil.copytree(
            _SOURCE, link, ignore=shutil.ignore_patterns("__pycache__")
        )
        (link / _COPY_MARKER).write_text(
            f"dartwork-mpl {_version()}\n"
            "Copied by `python -m dartwork_mpl.skills install --copy`; "
            "rerun it after upgrading dartwork-mpl.\n",
            encoding="utf-8",
        )
        return
    try:
        link.symlink_to(_SOURCE, target_is_directory=True)
    except OSError as exc:
        raise SkillInstallError(
            f"could not create a symlink at {link} ({exc}); rerun with "
            f"--copy to copy the skill instead."
        ) from exc


def install_skill(
    dest: str | os.PathLike[str] = ".",
    *,
    targets: Iterable[str] = ("claude", "codex"),
    copy: bool = False,
    force: bool = False,
) -> list[InstallResult]:
    """Install the skill for Claude Code and/or Codex under ``dest``.

    Parameters
    ----------
    dest
        Project directory (default: the current one). ``~`` installs the
        user-level skills of both agents.
    targets
        Keys of :data:`TARGETS`: ``"claude"`` (``.claude/skills``) and/or
        ``"codex"`` (``.agents/skills``).
    copy
        Copy the folder instead of linking it. A copy does not follow
        upgrades; rerun the installer after upgrading.
    force
        Replace a file or folder at the destination that this installer
        did not create.

    Returns
    -------
    list[InstallResult]
        One entry per target. ``"shared"`` means the target's skills
        directory is the same directory as an earlier target's (for
        example ``.claude/skills`` linked to ``.agents/skills``).

    Raises
    ------
    SkillInstallError
        If a destination holds something else and ``force`` is false, or a
        symlink cannot be created. Every destination is checked before any
        is changed.
    """
    base = Path(dest).expanduser()
    names = list(dict.fromkeys(targets))
    unknown = [t for t in names if t not in TARGETS]
    if unknown or not names:
        raise ValueError(
            f"targets must be a non-empty subset of {sorted(TARGETS)}; "
            f"got {names!r}"
        )

    plans: list[tuple[str, Path, Action, str]] = []
    first_by_dir: dict[Path, Path] = {}
    for name in names:
        skills_dir = base / TARGETS[name]
        link = skills_dir / SKILL_NAME
        key = skills_dir.resolve()
        if key in first_by_dir:
            plans.append(
                (name, link, "shared", f"same directory as {first_by_dir[key]}")
            )
            continue
        first_by_dir[key] = link
        plans.append((name, link, _plan(link, copy=copy, force=force), ""))

    results: list[InstallResult] = []
    for name, link, action, detail in plans:
        if action == "replaced":
            _remove(link)
        if action in ("linked", "copied", "replaced"):
            _create(link, copy=copy)
        results.append(InstallResult(name, link, action, detail))
    return results
