"""Build accepted ADR links without publishing excluded provenance documents."""

import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests.support.excluded_dirs import watch_access

ROOT = Path(__file__).resolve().parents[2]
DESIGN = "superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md"
DESIGN_URL = (
    "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/" + DESIGN
)
SECURITY_PLAN = "superpowers/plans/2026-11-05-python311-security-upgrade.md"
PREFLIGHT_PROVENANCE = (
    (
        "superpowers/plans/2026-10-29-finite-margins.md",
        ["B plan", "B plan"],
        "review-focus",
    ),
    (
        "superpowers/plans/2026-10-29-template-format-preflight.md",
        ["C plan", "C plan"],
        "review-focus",
    ),
    (
        "superpowers/specs/2026-10-29-input-preflight-design.md",
        ["Approved specification"],
        "current-invariants",
    ),
)
PROVENANCE_SOURCES = (
    DESIGN,
    SECURITY_PLAN,
    *(path for path, _, _ in PREFLIGHT_PROVENANCE),
)
# A same-folder record linked from the public ADR index (never ``../``).
_ADR_LINK = re.compile(r"\]\((\d{4}-[a-z0-9-]+\.md)(?:#[^)]*)?\)")


def _adr_inputs():
    """Name the public ADR index and the records it links, without listing."""
    index = (ROOT / "docs/adr/index.md").read_text(encoding="utf-8")
    return ("index.md", *sorted(set(_ADR_LINK.findall(index))))


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
    """Use the frozen public ADRs and synthetic stand-ins for their sources.

    The approved provenance documents are never read or copied: Sphinx
    excludes ``superpowers/**`` and the resolver only requires that each
    accepted source exists, so a one-line stand-in at the same path keeps the
    build, its links and the missing-source negatives meaningful.
    """
    source = tmp_path / "docs"
    (source / "adr").mkdir(parents=True)
    for name in _adr_inputs():
        shutil.copyfile(ROOT / "docs/adr" / name, source / "adr" / name)
    for relative in PROVENANCE_SOURCES:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"# Synthetic stand-in for {relative}\n", encoding="utf-8"
        )
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


def test_docs_project_takes_only_public_adrs_from_the_root(
    tmp_path, monkeypatch, request
):
    """Build the fixture from a root that holds no excluded provenance source."""
    root = tmp_path / "repo"
    adr = root / "docs/adr"
    adr.mkdir(parents=True)
    (adr / "index.md").write_text(
        "[ADR 0001](0001-synthetic-record.md)\n\n"
        "[design](../superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md)\n",
        encoding="utf-8",
    )
    (adr / "0001-synthetic-record.md").write_text(
        "# Synthetic record\n", encoding="utf-8"
    )
    monkeypatch.setitem(globals(), "ROOT", root)

    with watch_access(root / "docs/superpowers") as accesses:
        project = request.getfixturevalue("docs_project")

    assert accesses == []
    assert sorted(path.name for path in (project / "adr").iterdir()) == [
        "0001-synthetic-record.md",
        "index.md",
    ]
    for relative in PROVENANCE_SOURCES:
        assert (project / relative).read_text(encoding="utf-8") == (
            f"# Synthetic stand-in for {relative}\n"
        )


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
    """Accepted provenance links retain captions, fragments and source bytes."""
    with (docs_project / "index.md").open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n[**Approved** design][design]\n\n"
            f"[design]: {DESIGN}#intent-and-scope\n\n"
            f"`[literal]({DESIGN})`\n"
        )
        for relative, captions, fragment in PREFLIGHT_PROVENANCE:
            stream.write(f"\n[**{captions[0]}**]({relative}#{fragment})\n")
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
    preflight_links = _Links()
    preflight_links.feed(
        (output / "adr/0006-scoped-input-preflight-contract.html").read_text(
            encoding="utf-8"
        )
    )
    for relative, captions, _ in PREFLIGHT_PROVENANCE:
        target_url = (
            "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/"
            + relative
        )
        assert [
            text for url, text in preflight_links.links if url == target_url
        ] == captions
        assert not (output / Path(relative).with_suffix(".html")).exists()
    assert not (output / Path(DESIGN).with_suffix(".html")).exists()
    security_links = _Links()
    security_links.feed(
        (
            output / "adr/0007-python311-security-dependency-floor.html"
        ).read_text(encoding="utf-8")
    )
    assert (
        "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/"
        + SECURITY_PLAN,
        "2026-11-05-python311-security-upgrade",
    ) in security_links.links
    assert not (output / Path(SECURITY_PLAN).with_suffix(".html")).exists()
    parser = _Links()
    root_html = (output / "index.html").read_text(encoding="utf-8")
    parser.feed(root_html)
    assert (DESIGN_URL + "#intent-and-scope", "Approved design") in parser.links
    for relative, captions, fragment in PREFLIGHT_PROVENANCE:
        target_url = (
            "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/"
            + relative
        )
        assert (target_url + "#" + fragment, captions[0]) in parser.links
    assert f"[literal]({DESIGN})" in root_html
    assert all(path.read_bytes() == data for path, data in originals.items())


@pytest.mark.parametrize(
    "broken",
    ["missing-design", "missing-security-plan", "other-excluded", "unknown"],
)
def test_unresolved_links_still_fail_warning_gate(docs_project, broken):
    """Routing one provenance source must not hide missing or unrelated links."""
    if broken == "missing-design":
        (docs_project / DESIGN).unlink()
    elif broken == "missing-security-plan":
        target = SECURITY_PLAN
        (docs_project / target).unlink()
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


@pytest.mark.parametrize("source_exists", [False, True])
def test_security_plan_resolver_requires_actual_source(tmp_path, source_exists):
    """The adapter preserves a missing source and links only an existing plan."""
    from types import SimpleNamespace

    from docutils import nodes
    from docutils.utils import new_document
    from sphinx import addnodes

    from docs._ext.build_hooks import resolve_provenance_links

    if source_exists:
        source = tmp_path / SECURITY_PLAN
        source.parent.mkdir(parents=True)
        source.write_text("# Fixture plan\n", encoding="utf-8")
    document = new_document("fixture")
    reference = addnodes.pending_xref(
        "",
        refdomain="doc",
        reftype="myst",
        reftarget=SECURITY_PLAN.removesuffix(".md"),
    )
    reference.append(nodes.Text("support plan"))
    document.append(reference)
    resolve_provenance_links(SimpleNamespace(srcdir=str(tmp_path)), document)
    links = [
        (node["refuri"], node.astext())
        for node in document.findall(nodes.reference)
    ]
    if source_exists:
        assert links == [
            (
                "https://github.com/dartworklabs/dartwork-mpl/blob/main/docs/"
                + SECURITY_PLAN,
                "support plan",
            )
        ]
    else:
        assert links == []
        assert [
            node["reftarget"]
            for node in document.findall(addnodes.pending_xref)
        ] == [SECURITY_PLAN.removesuffix(".md")]
