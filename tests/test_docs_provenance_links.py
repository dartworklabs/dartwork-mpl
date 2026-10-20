"""Build public ADR links without publishing excluded provenance documents."""

import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESIGN = "superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md"
DESIGN_URL = (
    "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/" + DESIGN
)


class _Links(HTMLParser):
    """Read rendered anchor destinations and captions, including nested text."""

    def __init__(self):
        """Start with no active anchor or collected links."""
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        """Remember the destination when entering an anchor."""
        if tag == "a":
            self.current = [dict(attrs).get("href"), ""]

    def handle_data(self, data):
        """Collect caption text through nested inline markup."""
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        """Finish the anchor after reading its entire caption."""
        if tag == "a" and self.current is not None:
            self.links.append(tuple(self.current))
            self.current = None


@pytest.fixture
def docs_project(tmp_path):
    """Use real frozen ADR sources with only their excluded design as input."""
    source = tmp_path / "docs"
    source.mkdir()
    shutil.copytree(ROOT / "docs/adr", source / "adr")
    design = source / DESIGN
    design.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "docs" / DESIGN, design)
    (source / "index.md").write_text(
        "# Test documentation\n\n```{toctree}\nadr/index\n```\n",
        encoding="utf-8",
    )
    (source / "conf.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT / 'docs/_ext')!r})\n"
        "extensions = ['myst_parser', 'build_hooks']\n"
        "exclude_patterns = ['superpowers/**']\n",
        encoding="utf-8",
    )
    return source


def _build(source, *, fresh=True):
    """Run the actual MyST/Sphinx warning gate against a small docs tree."""
    output = source.parent / "html"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            "-W",
            "--keep-going",
            *(["-E", "-a"] if fresh else []),
            str(source),
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result, output


def test_existing_doctree_cache_is_invalidated_when_resolver_is_enabled(
    docs_project,
):
    """Restoring pre-fix doctrees must rebuild the unchanged ADR link sources."""
    conf = docs_project / "conf.py"
    fixed = conf.read_text(encoding="utf-8")
    conf.write_text(
        fixed.replace("'myst_parser', 'build_hooks'", "'myst_parser'"),
        encoding="utf-8",
    )
    before, output = _build(docs_project, fresh=False)
    assert before.returncode != 0
    assert "Unknown source document" in before.stderr
    conf.write_text(fixed, encoding="utf-8")
    after, output = _build(docs_project, fresh=False)
    assert after.returncode == 0, after.stdout + after.stderr
    assert DESIGN_URL in (output / "adr/index.html").read_text(encoding="utf-8")


def test_accepted_adr_links_render_to_repository_without_source_edits(
    docs_project,
):
    """All three real provenance links retain captions and resolve externally."""
    with (docs_project / "index.md").open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n[**Approved** design][design]\n\n"
            f"[design]: {DESIGN}#intent-and-scope\n\n"
            f"`[literal]({DESIGN})`\n"
        )
    originals = {path: path.read_bytes() for path in docs_project.rglob("*.md")}
    result, output = _build(docs_project)
    assert result.returncode == 0, result.stdout + result.stderr
    for page, captions in {
        "adr/index.html": ["artifact delivery 설계의 검증 기록"],
        "adr/0003-allow-scoped-mcp-artifact-discovery.html": [
            "artifact design"
        ],
    }.items():
        parser = _Links()
        parser.feed((output / page).read_text(encoding="utf-8"))
        assert [
            text for url, text in parser.links if url == DESIGN_URL
        ] == captions
    assert not (output / Path(DESIGN).with_suffix(".html")).exists()
    parser = _Links()
    root_html = (output / "index.html").read_text(encoding="utf-8")
    parser.feed(root_html)
    assert (DESIGN_URL + "#intent-and-scope", "Approved design") in parser.links
    assert f"[literal]({DESIGN})" in root_html
    assert all(path.read_bytes() == data for path, data in originals.items())


@pytest.mark.parametrize(
    "broken", ["missing-design", "other-excluded", "unknown"]
)
def test_unresolved_links_still_fail_warning_gate(docs_project, broken):
    """Routing one provenance source must not hide missing or unrelated links."""
    if broken == "missing-design":
        (docs_project / DESIGN).unlink()
    else:
        target = (
            "superpowers/specs/unrelated.md"
            if broken == "other-excluded"
            else "unknown.md"
        )
        if broken == "other-excluded":
            (docs_project / target).write_text(
                "# Other note\n", encoding="utf-8"
            )
        with (docs_project / "index.md").open("a", encoding="utf-8") as stream:
            stream.write(f"\n[Broken link]({target})\n")
    result, _ = _build(docs_project)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "myst.xref_missing" in result.stderr
    target = DESIGN if broken == "missing-design" else target
    assert target.removesuffix(".md") in result.stderr
