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

Installing is idempotent and conservative:

- A link this installer made (in any environment) is replaced in place.
- A copy records the SHA-256 of every file it wrote. It is refreshed only
  while those files are unchanged; a copy with local edits, and anything
  else at the destination, is left alone unless ``force`` is set.
- Every destination is checked, and every new link or copy is built under a
  temporary name next to it, before anything is replaced. The old install
  is renamed aside and restored if the swap fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
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
    "skill_version",
]

SKILL_NAME = "dartwork-mpl"

# Agent -> its skills directory, relative to a project (or home) directory.
TARGETS: dict[str, str] = {
    "claude": ".claude/skills",
    "codex": ".agents/skills",
}

_SOURCE = Path(__file__).resolve().parent / SKILL_NAME
# Written into copies: package version and the SHA-256 of each copied file.
_COPY_MARKER = ".dartwork-mpl-skill.json"
# Tail of every link this installer makes, in any environment.
_SOURCE_TAIL = ("dartwork_mpl", "skills", SKILL_NAME)

Action = Literal["linked", "copied", "replaced", "unchanged", "shared"]


class SkillInstallError(RuntimeError):
    """The skill could not be installed at a destination.

    What was at that destination before is kept. Targets earlier in the
    same call may already have been installed.
    """


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


def skill_version() -> str:
    """Return the installed dartwork-mpl version the skill belongs to."""
    try:
        return metadata.version("dartwork-mpl")
    except metadata.PackageNotFoundError:
        return "unknown"


def _digests(root: Path) -> dict[str, str]:
    """SHA-256 of every file under ``root``, keyed by POSIX relative path."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and p.name != _COPY_MARKER
        and "__pycache__" not in p.parts
    }


def _recorded_digests(copy: Path) -> dict[str, str] | None:
    """The file digests a copy's marker recorded, or ``None`` if unreadable."""
    try:
        data = json.loads((copy / _COPY_MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in files.items()
    ):
        return None
    return dict(files)


def _is_installer_link(link: Path) -> bool:
    """True for a symlink whose target ends in ``dartwork_mpl/skills/dartwork-mpl``."""
    target = Path(os.readlink(link))
    return target.parts[-len(_SOURCE_TAIL) :] == _SOURCE_TAIL


def _plan(link: Path, *, copy: bool, force: bool) -> Action:
    """Decide the action for one destination, raising rather than losing work."""
    if link.is_symlink():
        if not copy and link.resolve() == _SOURCE:
            return "unchanged"
        if _is_installer_link(link) or force:
            return "replaced"
    elif link.is_dir() and (link / _COPY_MARKER).is_file():
        current = _digests(link)
        recorded = _recorded_digests(link)
        if recorded is not None and current == recorded:
            if copy and current == _digests(_SOURCE):
                return "unchanged"
            return "replaced"
        if force:
            return "replaced"
        if recorded is None:
            what = f"an unreadable {_COPY_MARKER}"
        else:
            edited = {
                f
                for f in set(current) | set(recorded)
                if current.get(f) != recorded.get(f)
            }
            what = "local edits to " + ", ".join(sorted(edited))
        raise SkillInstallError(
            f"{link} is a copy with {what}; move it away or rerun with "
            f"--force to discard it."
        )
    elif not link.exists():
        return "copied" if copy else "linked"
    elif force:
        return "replaced"
    raise SkillInstallError(
        f"{link} exists and was not made by this installer; move it away "
        f"or rerun with --force to replace it."
    )


def _remove(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        path.unlink()
    else:
        shutil.rmtree(path)


def _stage(link: Path, *, copy: bool) -> Path:
    """Build the new link or copy in a temporary folder next to ``link``.

    Returns the staged path; its parent is the temporary folder, on the same
    filesystem as ``link`` so the later rename is a rename, not a copy.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix=f".{SKILL_NAME}-", dir=link.parent))
    staged = workdir / SKILL_NAME
    try:
        if copy:
            shutil.copytree(
                _SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__")
            )
            marker = {
                "package": "dartwork-mpl",
                "version": skill_version(),
                "source": str(_SOURCE),
                "note": "Copied by `python -m dartwork_mpl.skills install "
                "--copy`; rerun it after upgrading dartwork-mpl.",
                "files": _digests(staged),
            }
            (staged / _COPY_MARKER).write_text(
                json.dumps(marker, indent=2) + "\n", encoding="utf-8"
            )
        else:
            staged.symlink_to(_SOURCE, target_is_directory=True)
    except OSError as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        hint = "" if copy else "; rerun with --copy to copy the skill instead"
        raise SkillInstallError(
            f"could not prepare {link} ({exc}){hint}."
        ) from exc
    return staged


def _swap_in(staged: Path, link: Path) -> None:
    """Move ``staged`` to ``link``; on failure the old ``link`` is restored."""
    workdir = staged.parent
    backup = workdir / "previous"
    try:
        if link.exists() or link.is_symlink():
            os.replace(link, backup)
            try:
                os.replace(staged, link)
            except OSError:
                os.replace(backup, link)
                raise
        else:
            os.replace(staged, link)
    except OSError as exc:
        if backup.exists() or backup.is_symlink():
            raise SkillInstallError(
                f"could not replace {link} ({exc}); the previous install "
                f"was moved to {backup}."
            ) from exc
        shutil.rmtree(workdir, ignore_errors=True)
        raise SkillInstallError(
            f"could not replace {link} ({exc}); the previous install was kept."
        ) from exc
    # The old install (if any) sits in workdir as "previous"; rmtree removes a
    # symlink there without following it.
    shutil.rmtree(workdir, ignore_errors=True)


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
        upgrades; rerun the installer after upgrading. A link follows the
        Python environment it points into; moving or recreating that
        environment breaks it until the installer runs again.
    force
        Replace a file or folder at the destination that this installer
        did not create, or a copy with local edits.

    Returns
    -------
    list[InstallResult]
        One entry per target. ``"shared"`` means the target's skills
        directory is the same directory as an earlier target's (for
        example ``.claude/skills`` linked to ``.agents/skills``).

    Raises
    ------
    SkillInstallError
        If a target's skills directory resolves outside ``dest`` (through a
        linked ``.claude``, ``.agents`` or ``skills`` folder), if a
        destination holds something else or an edited copy and ``force`` is
        false, or if a link or copy cannot be built. Every
        destination is checked and every replacement staged before any is
        swapped in; a failed swap restores the previous install.
    """
    base = Path(dest).expanduser()
    names = list(dict.fromkeys(targets))
    unknown = [t for t in names if t not in TARGETS]
    if unknown or not names:
        raise ValueError(
            f"targets must be a non-empty subset of {sorted(TARGETS)}; "
            f"got {names!r}"
        )

    # ``dest`` itself may be a link; it is the root. Below it, a linked
    # ``.claude`` / ``.agents`` / ``skills`` folder must stay inside the root
    # (``.claude/skills -> ../.agents/skills`` does), or the install would land
    # somewhere the caller did not name.
    root = base.resolve()
    resolved = {name: (base / TARGETS[name]).resolve() for name in names}
    for name, key in resolved.items():
        if key != root and root not in key.parents:
            raise SkillInstallError(
                f"{base / TARGETS[name]} resolves to {key}, outside {root}; "
                f"nothing was installed. Pass that location as --dest to "
                f"install there."
            )

    plans: list[tuple[str, Path, Action, str]] = []
    first_by_dir: dict[Path, Path] = {}
    for name in names:
        skills_dir = base / TARGETS[name]
        link = skills_dir / SKILL_NAME
        key = resolved[name]
        if key in first_by_dir:
            plans.append(
                (name, link, "shared", f"same directory as {first_by_dir[key]}")
            )
            continue
        first_by_dir[key] = link
        plans.append((name, link, _plan(link, copy=copy, force=force), ""))

    staged: dict[Path, Path] = {}
    try:
        for _, link, action, _ in plans:
            if action in ("linked", "copied", "replaced"):
                staged[link] = _stage(link, copy=copy)
    except SkillInstallError:
        for path in staged.values():
            shutil.rmtree(path.parent, ignore_errors=True)
        raise

    results: list[InstallResult] = []
    try:
        for name, link, action, detail in plans:
            if link in staged:
                _swap_in(staged.pop(link), link)
            results.append(InstallResult(name, link, action, detail))
    finally:
        for path in staged.values():
            shutil.rmtree(path.parent, ignore_errors=True)
    return results
