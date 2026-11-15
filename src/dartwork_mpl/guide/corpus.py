"""The bundled guidance files: the skill, its references, the catalog and the templates.

Every file is addressed by a reference id, never by a path: ``guide/skill``
is ``SKILL.md``, ``guide/<name>`` a file in ``references/`` (and
``guide/anti-patterns`` the lint catalog), ``template/<kind>`` and
``template/advanced/<kind>`` the two template tiers. An id outside that
table is refused, so a caller cannot read anything else in the package.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable

from .model import Reference, Rules, ref_id

ASSETS = files("dartwork_mpl.guide") / "assets"
SKILL = ASSETS / "skill"
CATALOG = ASSETS / "anti-patterns.yaml"


@cache
def table() -> Mapping[str, Traversable]:
    """Every reference id and the file it reads."""
    found: dict[str, Traversable] = {"guide/skill": SKILL / "SKILL.md"}
    for page in sorted((SKILL / "references").iterdir(), key=lambda p: p.name):
        if page.name.endswith(".md"):
            found[f"guide/{page.name.removesuffix('.md')}"] = page
    found["guide/anti-patterns"] = CATALOG
    for tier, prefix in (
        ("basic", "template/"),
        ("advanced", "template/advanced/"),
    ):
        scripts = (ASSETS / "templates" / tier).iterdir()
        for script in sorted(scripts, key=lambda p: p.name):
            if script.name.endswith(".py"):
                found[prefix + script.name.removesuffix(".py")] = script
    return found


def read(ref: str) -> str:
    """The text of one reference; an unknown id raises ``ValueError``."""
    path = table().get(ref_id(ref))
    if path is None:
        raise ValueError(
            f"no reference {ref!r}; dm.guide.references() lists the "
            f"{len(table())} ids"
        )
    return path.read_text(encoding="utf-8")


@cache
def references() -> tuple[Reference, ...]:
    """Every guide page and template, with the words a search ranks."""
    return tuple(
        Reference.template(ref, read(ref))
        if ref.startswith("template/")
        else Reference.guide(ref, read(ref))
        for ref in table()
    )


@cache
def rules() -> Rules:
    """The parsed anti-pattern catalog."""
    return Rules.parse(CATALOG.read_text(encoding="utf-8"))
