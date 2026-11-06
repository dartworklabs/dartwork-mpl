"""Every sphinx-gallery example has a file name no other gallery uses.

sphinx-gallery warns "Duplicate example file name(s) found. Having duplicate
file names will break some links" when two of ``conf.py``'s
``examples_dirs`` hold the same basename, and ``sphinx-build -W`` turns that
into a failed build. The 18 tier-2 templates in ``09_ai_templates_advanced``
shared their names with the basic tier (``plot_bar.py`` twice); they now
carry an ``_advanced`` suffix, while their template ids stay the basic
names (``bar``, ``plot_3d``).

sphinx-gallery checks the directories relative to the working directory,
so a build started from the repository root (CI) never saw the warning; one
started in ``docs/`` did. This test reads the directories from ``conf.py``
itself, whatever the working directory.
"""

from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

_DOCS = Path(__file__).resolve().parents[2] / "docs"
_INDEX = (
    _DOCS.parent
    / "src"
    / "dartwork_mpl"
    / "asset"
    / "prompt"
    / "05-templates"
    / "_index.json"
)
# sphinx-gallery's default ``ignore_pattern``; conf.py keeps it.
_IGNORED = {"__init__.py"}


def _examples_dirs() -> list[Path]:
    """``sphinx_gallery_conf["examples_dirs"]`` as written in ``conf.py``."""
    tree = ast.parse((_DOCS / "conf.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "sphinx_gallery_conf"
                for t in node.targets
            )
            and isinstance(node.value, ast.Dict)
        ):
            conf = ast.literal_eval(node.value)
            return [_DOCS / d for d in conf["examples_dirs"]]
    raise AssertionError("sphinx_gallery_conf not found in docs/conf.py")


def _example_files(directory: Path) -> list[Path]:
    """The example files sphinx-gallery collects there (one level down too)."""
    files = [*directory.glob("*.py"), *directory.glob("*/*.py")]
    return [f for f in files if f.name not in _IGNORED]


def test_gallery_example_file_names_are_unique():
    dirs = _examples_dirs()
    assert len(dirs) >= 10 and all(d.is_dir() for d in dirs), dirs
    names = Counter(f.name for d in dirs for f in _example_files(d))
    repeated = sorted(name for name, count in names.items() if count > 1)
    assert repeated == [], repeated


def test_advanced_templates_keep_their_ids():
    """The renamed files still register under the basic tier's ids."""
    index = json.loads(_INDEX.read_text(encoding="utf-8"))
    advanced = index["advanced"]
    basic = {k for k in index if k != "advanced"}
    assert set(advanced) == basic and len(basic) == 18, sorted(advanced)
    for template_id, meta in advanced.items():
        source = _DOCS.parent / str(meta["source_path"])
        assert source.is_file(), (template_id, source)
        assert source.stem.endswith("_advanced"), source
