"""Put the bundled skill where agents look for it.

``install_skill`` links the skill folder into every project skill folder in
:data:`SKILL_DIRS`, or copies it where links are not possible. A link to a
dartwork-mpl skill (this one or an older install's) is replaced; anything
else already there is kept unless ``force`` is set.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .corpus import SKILL

SKILL_NAME = "dartwork-mpl"
# Skill folders agents read, relative to a project (or the home) directory.
SKILL_DIRS = (".claude/skills", ".agents/skills")


@dataclass(frozen=True)
class Installed:
    """One destination and what happened there: linked, copied or unchanged."""

    path: Path
    action: str


def skill_path() -> Path:
    """The installed skill folder (``SKILL.md`` and ``references/``)."""
    return Path(str(SKILL)).resolve()


def _ours(target: Path) -> bool:
    """A link this installer made: it points into a dartwork_mpl package."""
    return target.is_symlink() and "dartwork_mpl" in str(target.readlink())


def _targets(dest: Path) -> list[Path]:
    """One target per skill folder; a folder linked to another counts once."""
    found: dict[Path, Path] = {}
    for folder in SKILL_DIRS:
        parent = dest.expanduser() / folder
        found.setdefault(parent.resolve(), parent / SKILL_NAME)
    return list(found.values())


def install_skill(
    dest: str | Path = ".", *, copy: bool = False, force: bool = False
) -> list[Installed]:
    """Link (or ``copy``) the skill into ``dest``'s skill folders.

    Every destination is checked first: one that holds something else raises
    ``FileExistsError`` before anything is written, unless ``force`` replaces it.
    """
    source = skill_path()
    targets = _targets(Path(dest))
    blocked = [
        t
        for t in targets
        if (t.exists() or t.is_symlink())
        and t.resolve() != source
        and not _ours(t)
    ]
    if blocked and not force:
        raise FileExistsError(
            f"{blocked[0]} already exists; pass force=True (--force) to replace it"
        )
    done: list[Installed] = []
    for target in targets:
        if target.resolve() == source:
            done.append(Installed(target, "unchanged"))
            continue
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not copy:
            try:
                target.symlink_to(source, target_is_directory=True)
                done.append(Installed(target, "linked"))
                continue
            except OSError:  # no symlinks (Windows without developer mode)
                pass
        shutil.copytree(source, target)
        done.append(Installed(target, "copied"))
    return done
