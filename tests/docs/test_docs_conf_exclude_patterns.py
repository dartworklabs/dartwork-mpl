"""Sphinx's source discovery does not walk into ``docs/superpowers``.

``docs/superpowers`` keeps internal plans and specs for provenance, and
``docs/conf.py`` keeps them off the public site with ``exclude_patterns``.
During source discovery (``sphinx.util.matching.get_matching_files``) Sphinx
prunes a directory only when a pattern matches the directory's own path.
``"superpowers/**"`` matches only paths below the directory, so discovery
still listed ``superpowers`` and its files before excluding them; the parent
pattern ``"superpowers"`` prunes the directory itself.

The build here runs in-process on a synthetic tree (a public page and decoy
pages under ``superpowers/``) with ``exclude_patterns`` as written in
``docs/conf.py``. It covers Sphinx's discovery walk only. Code that names a
path below ``superpowers`` directly, such as the provenance resolver's
``is_file`` in ``docs/_ext/build_hooks.py``, is outside it.
"""

from __future__ import annotations

import ast
import os
from io import StringIO
from pathlib import Path

_CONF = Path(__file__).resolve().parents[2] / "docs" / "conf.py"


def _exclude_patterns() -> list[str]:
    """``exclude_patterns`` as written in ``docs/conf.py``.

    The reader understands one literal assignment; any other use of the name
    (an ``append`` or ``+=`` later in the file) fails here instead of being
    silently left out of the build below.
    """
    tree = ast.parse(_CONF.read_text(encoding="utf-8"))
    uses = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "exclude_patterns"
    ]
    assigns = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "exclude_patterns"
            for t in node.targets
        )
    ]
    assert len(uses) == 1 and len(assigns) == 1, (
        "docs/conf.py must set exclude_patterns in one literal assignment"
    )
    patterns = ast.literal_eval(assigns[0].value)
    assert isinstance(patterns, list), patterns
    return patterns


def _project(root: Path, patterns: list[str]) -> Path:
    """A minimal MyST project with a public page and decoy internal pages."""
    src = root / "src"
    (src / "public").mkdir(parents=True)
    (src / "superpowers" / "specs").mkdir(parents=True)
    (src / "index.md").write_text(
        "# Index\n\n```{toctree}\npublic/page\n```\n", encoding="utf-8"
    )
    (src / "public" / "page.md").write_text("# Public page\n", encoding="utf-8")
    (src / "superpowers" / "top.md").write_text(
        "# Synthetic decoy\n", encoding="utf-8"
    )
    (src / "superpowers" / "specs" / "decoy.md").write_text(
        "# Synthetic decoy\n", encoding="utf-8"
    )
    (src / "conf.py").write_text(
        f"extensions = ['myst_parser']\nexclude_patterns = {patterns!r}\n",
        encoding="utf-8",
    )
    return src.resolve()


def _build(src: Path, builddir: Path, monkeypatch):
    """Build in-process and record every directory listed while doing so."""
    from sphinx.testing.util import SphinxTestApp

    listed: list[Path] = []
    real_scandir, real_listdir = os.scandir, os.listdir

    def _note(path) -> None:
        if not isinstance(path, int):
            listed.append(Path(os.path.abspath(os.fsdecode(path))))

    def scandir(path="."):
        _note(path)
        return real_scandir(path)

    def listdir(path="."):
        _note(path)
        return real_listdir(path)

    with monkeypatch.context() as patch:
        patch.setattr(os, "scandir", scandir)
        patch.setattr(os, "listdir", listdir)
        app = SphinxTestApp(
            "html",
            srcdir=src,
            builddir=builddir,
            freshenv=True,
            status=StringIO(),
            warning=StringIO(),
        )
        try:
            app.build()
            found = set(app.env.found_docs)
        finally:
            app.cleanup()
    return listed, found


def test_conf_keeps_both_superpowers_patterns():
    """The parent prunes the walk; the glob still names the documents below.

    Sphinx's other ``exclude_patterns`` users (the toctree's excluded-document
    check, for one) match document names such as ``superpowers/specs/x``,
    which only ``"superpowers/**"`` covers.
    """
    patterns = _exclude_patterns()
    assert "superpowers" in patterns
    assert "superpowers/**" in patterns


def test_discovery_skips_superpowers_and_keeps_public_pages(
    tmp_path, monkeypatch
):
    """conf.py's patterns prune the decoy directory and keep the public page."""
    src = _project(tmp_path, _exclude_patterns())
    listed, found = _build(src, tmp_path / "build", monkeypatch)

    internal = src / "superpowers"
    entered = [p for p in listed if p == internal or internal in p.parents]
    assert entered == [], entered
    # The recorder saw the discovery walk itself, so an empty list above is
    # an observation rather than a recorder that never fired.
    assert src in listed and src / "public" in listed, listed
    assert found == {"index", "public/page"}, found
    assert (tmp_path / "build" / "html" / "public" / "page.html").is_file()
