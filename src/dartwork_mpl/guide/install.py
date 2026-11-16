"""Put the bundled skill where agents look for it.

``install_skill`` puts the skill folder into every project skill folder in
:data:`SKILL_DIRS`. It links when the package is installed inside the
destination (the project's own ``.venv`` after ``uv add``), so an upgrade
reaches the skill. Anywhere else (``uvx``'s cache, a global install) a link
would break when that environment goes, so it copies, and running it again
after an upgrade refreshes the copy. A dartwork-mpl skill already there
(linked or copied) is replaced; anything else is kept unless ``force`` is set.
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


#: This package's import name (``dartwork_mpl``).
PACKAGE = __name__.partition(".")[0]


def skill_path() -> Path:
    """The installed skill folder (``SKILL.md`` and ``references/``)."""
    return Path(str(SKILL)).resolve()


def links_into(dest: Path) -> bool:
    """Whether a link from ``dest`` lasts: the package lives inside ``dest``."""
    return skill_path().is_relative_to(dest.expanduser().resolve())


def _ours(target: Path) -> bool:
    """A skill this installer put there: a link into a dartwork_mpl package,
    or a folder (or a link to one) whose ``SKILL.md`` names this skill."""
    if target.is_symlink() and PACKAGE in str(target.readlink()):
        return True  # even dangling: uvx's cache was cleaned under it
    head = target / "SKILL.md"
    return head.is_file() and f"name: {SKILL_NAME}\n" in head.read_text(
        encoding="utf-8"
    )


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
    """Link or copy the skill into ``dest``'s skill folders.

    It copies when ``copy`` is set or when :func:`links_into` says a link
    would not last. Every destination is checked first: one that holds
    something else raises ``FileExistsError`` before anything is written,
    unless ``force`` replaces it.
    """
    source = skill_path()
    link = not copy and links_into(Path(dest))
    targets = _targets(Path(dest))
    blocked = [
        t for t in targets if (t.exists() or t.is_symlink()) and not _ours(t)
    ]
    if blocked and not force:
        raise FileExistsError(
            f"{blocked[0]} already exists; pass force=True (--force) to replace it"
        )
    done: list[Installed] = []
    for target in targets:
        if link and target.is_symlink() and target.resolve() == source:
            done.append(Installed(target, "unchanged"))
            continue
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if link:
            try:
                target.symlink_to(source, target_is_directory=True)
                done.append(Installed(target, "linked"))
                continue
            except OSError:  # no symlinks (Windows without developer mode)
                pass
        shutil.copytree(source, target)
        done.append(Installed(target, "copied"))
    return done
